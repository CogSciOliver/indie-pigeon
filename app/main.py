import os
import hmac
import hashlib
import time
import urllib.parse
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from requests.exceptions import HTTPError
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal, init_db
from .models import Order, DeliveryLog
from .square_client import verify_square_signature, get_payment, get_customer
from .emailer import send_ebook_email


def make_cf_download_url(key: str) -> str:
    base = os.environ["DOWNLOAD_BASE_URL"].rstrip("/")
    secret = os.environ["DOWNLOAD_SECRET"]
    exp = int(time.time()) + int(os.environ.get("LINK_EXPIRES_SECONDS", "86400"))

    msg = f"{key}.{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    return f"{base}?key={urllib.parse.quote(key)}&exp={exp}&sig={sig}"


app = FastAPI()


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


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

    # Only fulfill on payment.updated
    if event_type != "payment.updated":
        return {"ok": True, "ignored": True, "event_type": event_type}

    data_obj = (event.get("data") or {}).get("object") or {}
    payment_id = (data_obj.get("payment") or {}).get("id") or data_obj.get("id")

    if not payment_id or not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id/payment_id")

    # Confirm payment via Square API
    try:
        payment = get_payment(payment_id)
    except HTTPError:
        # Square "Send Test Event" often uses a fake sample payment ID
        return {
            "ok": True,
            "ignored": True,
            "reason": "Square test webhook used a non-retrievable payment id",
            "payment_id": payment_id,
        }

    status = (payment.get("status") or "").upper()
    
    print("PAYMENT JSON:", customer)
    print("=============================================")
    print("CUSTOMER JSON:", customer)
    print("PAYMENT ID:", payment_id)
    print("PAYMENT STATUS:", status)

    if status != "COMPLETED":
        return {"ok": True, "ignored": True, "payment_status": status}

    customer = get_customer(payment["customer_id"])
    buyer_email = customer["email_address"]

    print("GOT_CUSTOMER EMAIL===", buyer_email)

    if not buyer_email:
        raise HTTPException(status_code=400, detail="No buyer email on payment")

    # Save order idempotently
    db = SessionLocal()
    try:
        order = Order(
            square_event_id=event_id,
            square_payment_id=payment_id,
            buyer_email=buyer_email,
            status="paid",
        )
        db.add(order)
        db.commit()
        db.refresh(order)
    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        db.close()

    # Fulfill: email download link
    # this is for one product below
    # upgrade MVP to select products based on Square item/metadata 
    #PRODUCT_MAP={"ebook-basic":"usd-ebook-one.pdf","ebook-bonus":"usd-ebook-bonus.pdf"}
    product_key = os.environ.get("PRODUCT_KEY", "usd-ebook-one.pdf")
    download_url = make_cf_download_url(product_key)

    subject = "Your Unschool Discoveries ebook download is here!"
    body = f"""Thanks for your purchase!

You can download your ebook using the link below:

{download_url}

If you have any trouble, reply to this email.
"""

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.square_payment_id == payment_id).first()

        # prevent duplicate fulfillment
        if order and order.status == "fulfilled":
            return {"ok": True, "duplicate_fulfillment": True}

        print("ABOUT TO SEND EMAIL")
        provider_id = send_ebook_email(buyer_email, subject, body)
        print("EMAIL SENT OK")

        if order:
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

    except Exception as e:
        print("EMAIL FAILED:", str(e))
        db.rollback()

        if order:
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