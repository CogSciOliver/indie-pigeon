import os
import hmac
import hashlib
import time
import urllib.parse
import uuid
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from requests.exceptions import HTTPError
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal, init_db
from .models import Order, DeliveryLog
from .square_client import verify_square_signature, get_payment
from .emailer import send_ebook_email
from .manual_send import router as manual_send_router


def make_cf_download_url(key: str) -> str:
    base = os.environ["DOWNLOAD_BASE_URL"].rstrip("/")
    secret = os.environ["DOWNLOAD_SECRET"]
    exp = int(time.time()) + int(os.environ.get("LINK_EXPIRES_SECONDS", "86400"))

    msg = f"{key}.{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    return f"{base}?key={urllib.parse.quote(key)}&exp={exp}&sig={sig}"


app = FastAPI()
app.include_router(manual_send_router)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def checkout_start_form():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>v1.1.05_Staging: Get Your Book</title>
  <link rel="icon" href="/favicon.ico">
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 560px;
      margin: 40px auto;
      padding: 20px;
    }
    input, button {
      width: 100%;
      padding: 12px;
      margin-top: 12px;
      font-size: 16px;
      box-sizing: border-box;
    }
    button {
        background-image: linear-gradient(to right, #FF5500 0%, #F4D03F 51%, #16A085 100%);
        cursor: pointer;
        margin: 10px;
        padding: 15px 45px;
        text-align: center;
        text-transform: uppercase;
        transition: 0.5s;
        background-size: 200% auto;
        color: white;
        box-shadow: 0 0 20px #eee;
        border-radius: 10px;
        display: block;
        outline: none;
        border: none;
    }

    button:hover {
        background-position: right center;
        color: #fff;
        text-decoration: none;
    }   
    .note {
      color: #555;
      font-size: 14px;
      margin-top: 10px;
    }
  </style>
</head>
<body>
    <h1>Staging Indie Pigeon</h1>
    <h2>Get Your Book</h2>
    <p>Enter your email, then continue to checkout.</p>

    <form method="post" action="/start-order">
        <input type="email" name="email" placeholder="you@example.com" required />
        <button type="submit">Continue to Checkout</button>
    </form>

    <p class="note">Your download will be delivered to this email after payment.</p>
</body>
</html>
"""


@app.post("/start-order")
def start_order(email: str = Form(...)):
    checkout_ref = str(uuid.uuid4())
    db = SessionLocal()

    try:
        order = Order(
            checkout_ref=checkout_ref,
            square_payment_id=None,
            buyer_email=email,
            status="pending",
        )
        db.add(order)
        db.commit()
    finally:
        db.close()

    square_checkout_url = os.environ["SQUARE_CHECKOUT_URL"]
    return RedirectResponse(square_checkout_url, status_code=303)


@app.post("/square/webhook")
async def square_webhook(request: Request):
    raw = await request.body()

    signature = request.headers.get("x-square-hmacsha256-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Square signature")

    signature_key = os.environ["SQUARE_WEBHOOK_SIGNATURE_KEY"]
    notification_url = os.environ["WEBHOOK_PUBLIC_URL"]

    print("Incoming URL:", str(request.url))
    print("Expected URL:", notification_url)

    if not verify_square_signature(signature, signature_key, notification_url, raw):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_id = event.get("event_id") or event.get("id")
    event_type = event.get("type", "")

    print("EVENT TYPE:", event_type)

    if event_type != "payment.updated":
        return {"ok": True, "ignored": True, "event_type": event_type}

    data_obj = (event.get("data") or {}).get("object") or {}
    payment_id = (data_obj.get("payment") or {}).get("id") or data_obj.get("id")

    if not payment_id or not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id/payment_id")

    try:
        payment = get_payment(payment_id)
    except HTTPError:
        return {
            "ok": True,
            "ignored": True,
            "reason": "Square test webhook used a non-retrievable payment id",
            "payment_id": payment_id,
        }

    status = (payment.get("status") or "").upper()

    print("PAYMENT JSON:", payment)
    print("PAYMENT ID:", payment_id)
    print("PAYMENT STATUS:", status)

    if status != "COMPLETED":
        return {"ok": True, "ignored": True, "payment_status": status}

    db = SessionLocal()
    order = None
    buyer_email = None

    try:
        existing = db.query(Order).filter(Order.square_payment_id == payment_id).first()
        if existing:
            if existing.status == "fulfilled":
                return {"ok": True, "duplicate_fulfillment": True}
            order = existing
        else:
            order = (
                db.query(Order)
                .filter(Order.status == "pending")
                .order_by(Order.id.desc())
                .first()
            )

            if not order:
                raise HTTPException(status_code=400, detail="No pending order/email found")

            order.square_payment_id = payment_id
            order.status = "paid"
            db.commit()

        buyer_email = order.buyer_email
        print("BUYER EMAIL:", buyer_email)

        if not buyer_email:
            raise HTTPException(status_code=400, detail="Stored order missing buyer email")

        product_key = os.environ.get("PRODUCT_KEY", "usd-ebook-one.pdf")
        download_url = make_cf_download_url(product_key)

        subject = "Your Unschool Discoveries ebook download is here!"
        body = f"""Thanks for your purchase!

You can download your ebook using the link below:

{download_url}

If you have any trouble, reply to this email.
"""

        print("ABOUT TO SEND EMAIL")
        provider_id = send_ebook_email(buyer_email, subject, body)
        print("EMAIL SENT OK")

        order.status = "fulfilled"
        order.fulfilled_at = datetime.utcnow()

        db.add(
            DeliveryLog(
                order_id=order.id,
                email_status="sent",
                provider_message_id=provider_id,
            )
        )
        db.commit()

    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}
    except Exception as e:
        print("EMAIL FAILED:", str(e))
        db.rollback()

        if order and getattr(order, "id", None):
            order.status = "failed"
            db.add(
                DeliveryLog(
                    order_id=order.id,
                    email_status="error",
                    error=str(e),
                )
            )
            db.commit()

        raise HTTPException(status_code=500, detail=f"Fulfillment error: {e}")
    finally:
        db.close()

    return {"ok": True, "fulfilled": True, "email": buyer_email}