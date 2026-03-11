import os
import hmac
import hashlib
import time
import urllib.parse
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from requests.exceptions import HTTPError

from .db import SessionLocal, init_db
from .models import Order, DeliveryLog
from .square_client import verify_square_signature, get_payment
from .emailer import send_ebook_email
from .manual_send import router as manual_send_router


ORDER_STATUS_PENDING_PAYMENT = "pending_payment"
ORDER_STATUS_PAID_EMAIL_PRESENT = "paid_email_present"
ORDER_STATUS_PAID_EMAIL_MISSING = "paid_email_missing"
ORDER_STATUS_EMAIL_CONFIRMED = "email_confirmed"
ORDER_STATUS_FULFILLED = "fulfilled"

EMAIL_SOURCE_PRE_CHECKOUT = "pre_checkout_form"
EMAIL_SOURCE_SQUARE = "square_checkout"
EMAIL_SOURCE_POST_PURCHASE = "post_purchase_form"
EMAIL_SOURCE_MANUAL = "manual_admin"


def utcnow() -> datetime:
    return datetime.utcnow()


def make_cf_download_url(key: str) -> str:
    base = os.environ["DOWNLOAD_BASE_URL"].rstrip("/")
    secret = os.environ["DOWNLOAD_SECRET"]
    exp = int(time.time()) + int(os.environ.get("LINK_EXPIRES_SECONDS", "86400"))

    msg = f"{key}.{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    return f"{base}?key={urllib.parse.quote(key)}&exp={exp}&sig={sig}"


def make_order_ref() -> str:
    return f"IP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"


def make_email_confirmation_token(order_id: int) -> str:
    secret = os.environ["EMAIL_CONFIRMATION_SECRET"]
    ttl = int(os.environ.get("EMAIL_CONFIRMATION_TTL_SECONDS", "86400"))
    exp = int(time.time()) + ttl
    payload = f"{order_id}.{exp}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_email_confirmation_token(token: str) -> int:
    secret = os.environ["EMAIL_CONFIRMATION_SECRET"]

    try:
        order_id_str, exp_str, sig = token.split(".", 2)
        payload = f"{order_id_str}.{exp_str}"
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid confirmation token") from exc

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=400, detail="Invalid confirmation token")

    if int(exp_str) < int(time.time()):
        raise HTTPException(status_code=400, detail="Confirmation token expired")

    try:
        return int(order_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid confirmation token") from exc


def get_square_checkout_url(order_ref: str) -> str:
    """
    Current version uses a static Square checkout URL from env.
    We append order_ref as a query param so the user flow can at least carry
    a local reference forward where possible.

    Later, this should be replaced with real dynamic checkout link creation
    through Square's API and saved on the Order row.
    """
    base = os.environ["SQUARE_CHECKOUT_URL"]
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}order_ref={urllib.parse.quote(order_ref)}"


def extract_square_buyer_email(payment: dict) -> Optional[str]:
    for key in ("buyer_email_address", "receipt_email_address"):
        value = payment.get(key)
        if value:
            return value

    customer_details = payment.get("customer_details") or {}
    if customer_details.get("email_address"):
        return customer_details["email_address"]

    return None


def extract_order_ref_from_payment(payment: dict) -> Optional[str]:
    """
    Best effort only.
    Prefer a real Square metadata/reference field once you wire dynamic checkout creation.
    """
    for key in ("reference_id", "referenceId"):
        value = payment.get(key)
        if value:
            return value

    note = payment.get("note")
    if isinstance(note, str) and "IP-" in note:
        return note.strip()

    return None


def set_order_paid_fields(order: Order, payment: dict) -> None:
    order.square_payment_id = payment.get("id")
    order.square_order_id = payment.get("order_id")
    order.paid_at = utcnow()

    amount_money = payment.get("amount_money") or {}
    if hasattr(order, "amount"):
        order.amount = amount_money.get("amount")
    if hasattr(order, "currency"):
        order.currency = amount_money.get("currency")


def ensure_delivery_email(order: Order, square_email: Optional[str]) -> bool:
    """
    Returns True if order has a usable delivery email after enrichment.
    """
    current_delivery_email = getattr(order, "delivery_email", None)
    if current_delivery_email:
        return True

    buyer_email = getattr(order, "buyer_email", None)
    if buyer_email:
        if hasattr(order, "delivery_email"):
            order.delivery_email = buyer_email
        return True

    if square_email:
        if hasattr(order, "buyer_email") and not getattr(order, "buyer_email", None):
            order.buyer_email = square_email
        if hasattr(order, "delivery_email"):
            order.delivery_email = square_email
        if hasattr(order, "email_source"):
            order.email_source = EMAIL_SOURCE_SQUARE
        return True

    return False


def log_delivery_event(
    db,
    order_id: int,
    email_status: str,
    provider_message_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    db.add(
        DeliveryLog(
            order_id=order_id,
            email_status=email_status,
            provider_message_id=provider_message_id,
            error=error,
        )
    )


def fulfill_order(db, order: Order) -> dict:
    if order.status == ORDER_STATUS_FULFILLED:
        return {"ok": True, "duplicate_fulfillment": True}

    delivery_email = getattr(order, "delivery_email", None) or getattr(order, "buyer_email", None)
    if not delivery_email:
        raise HTTPException(status_code=400, detail="Order missing delivery email")

    product_key = os.environ.get("PRODUCT_KEY", "usd-ebook-one.pdf")
    download_url = make_cf_download_url(product_key)

    subject = "Your Unschool Discoveries ebook download is here!"
    body = f"""Thanks for your purchase!

You can download your ebook using the link below:

{download_url}

If you have any trouble, reply to this email.
"""

    provider_id = send_ebook_email(delivery_email, subject, body)

    order.status = ORDER_STATUS_FULFILLED
    if hasattr(order, "fulfilled_at"):
        order.fulfilled_at = utcnow()

    log_delivery_event(
        db=db,
        order_id=order.id,
        email_status="sent",
        provider_message_id=provider_id,
    )
    db.commit()

    return {"ok": True, "fulfilled": True, "email": delivery_email}


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
  <title>Staging: Get Your Book</title>
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
      cursor: pointer;
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
    order_ref = make_order_ref()
    db = SessionLocal()

    try:
        order = Order(
            order_ref=order_ref,
            checkout_ref=order_ref,  # temporary compatibility if old column still exists
            square_payment_id=None,
            square_order_id=None,
            checkout_link_id=None,
            buyer_email=email,
            delivery_email=email,
            email_source=EMAIL_SOURCE_PRE_CHECKOUT,
            status=ORDER_STATUS_PENDING_PAYMENT,
            created_at=utcnow(),
        )
        db.add(order)
        db.commit()
        db.refresh(order)
    finally:
        db.close()

    square_checkout_url = get_square_checkout_url(order_ref)
    return RedirectResponse(square_checkout_url, status_code=303)


@app.get("/confirm-email", response_class=HTMLResponse)
def confirm_email_form(token: str):
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Confirm delivery email</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 560px;
      margin: 40px auto;
      padding: 20px;
    }}
    input, button {{
      width: 100%;
      padding: 12px;
      margin-top: 12px;
      font-size: 16px;
      box-sizing: border-box;
    }}
    button {{
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <h2>Confirm your delivery email</h2>
  <p>Payment received. Before we send your download, confirm the email address where you want it delivered.</p>

  <form method="post" action="/confirm-email">
    <input type="hidden" name="token" value="{token}" />
    <input type="email" name="email" placeholder="you@example.com" required />
    <button type="submit">Send my download</button>
  </form>
</body>
</html>
"""


@app.post("/confirm-email")
def confirm_email_submit(token: str = Form(...), email: str = Form(...)):
    order_id = verify_email_confirmation_token(token)
    db = SessionLocal()

    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status == ORDER_STATUS_FULFILLED:
            return HTMLResponse(
                "<h2>Already fulfilled</h2><p>Your order has already been sent.</p>"
            )

        order.delivery_email = email
        if not getattr(order, "buyer_email", None):
            order.buyer_email = email
        order.email_source = EMAIL_SOURCE_POST_PURCHASE
        if hasattr(order, "email_confirmed_at"):
            order.email_confirmed_at = utcnow()
        order.status = ORDER_STATUS_EMAIL_CONFIRMED
        db.commit()
        db.refresh(order)

        result = fulfill_order(db, order)
        delivered_email = result.get("email", email)

        return HTMLResponse(
            f"<h2>Success</h2><p>Your download has been sent to {delivered_email}.</p>"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if "order" in locals() and order and getattr(order, "id", None):
            log_delivery_event(
                db=db,
                order_id=order.id,
                email_status="error",
                error=str(e),
            )
            db.commit()
        raise HTTPException(status_code=500, detail=f"Email confirmation error: {e}")
    finally:
        db.close()


@app.post("/square/webhook")
async def square_webhook(request: Request):
    raw = await request.body()

    signature = request.headers.get("x-square-hmacsha256-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Square signature")

    signature_key = os.environ["SQUARE_WEBHOOK_SIGNATURE_KEY"]
    notification_url = os.environ["WEBHOOK_PUBLIC_URL"]

    if not verify_square_signature(signature, signature_key, notification_url, raw):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()

    event_id = event.get("event_id") or event.get("id")
    event_type = event.get("type", "")

    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id")

    db = SessionLocal()

    try:
        # -------------------------------
        # WEBHOOK DEDUPLICATION
        # -------------------------------
        from .models import WebhookEvent

        existing_event = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.provider == "square")
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )

        if existing_event:
            return {"ok": True, "duplicate_event": True}

        db.add(
            WebhookEvent(
                provider="square",
                event_id=event_id,
                event_type=event_type,
            )
        )
        db.commit()

        # -------------------------------
        # ONLY PROCESS PAYMENT EVENTS
        # -------------------------------
        if event_type != "payment.updated":
            return {"ok": True, "ignored": True}

        data_obj = (event.get("data") or {}).get("object") or {}
        payment_id = (data_obj.get("payment") or {}).get("id") or data_obj.get("id")

        if not payment_id:
            return {"ok": True, "ignored": True}

        try:
            payment = get_payment(payment_id)
        except HTTPError:
            return {"ok": True, "ignored": True}

        payment_status = (payment.get("status") or "").upper()

        if payment_status != "COMPLETED":
            return {"ok": True, "ignored": True}

        # -------------------------------
        # ORDER MATCHING
        # -------------------------------
        order = db.query(Order).filter(Order.square_payment_id == payment_id).first()

        if not order:
            order_ref = extract_order_ref_from_payment(payment)

            if order_ref:
                order = db.query(Order).filter(Order.order_ref == order_ref).first()

        if not order:
            square_email = extract_square_buyer_email(payment)

            order = Order(
                order_ref=make_order_ref(),
                square_payment_id=payment_id,
                square_order_id=payment.get("order_id"),
                buyer_email=square_email,
                delivery_email=None,
                email_source=EMAIL_SOURCE_SQUARE if square_email else None,
                status=ORDER_STATUS_PAID_EMAIL_MISSING,
                created_at=utcnow(),
                paid_at=utcnow(),
            )

            db.add(order)
            db.commit()
            db.refresh(order)

        # -------------------------------
        # ALREADY FULFILLED
        # -------------------------------
        if order.status == ORDER_STATUS_FULFILLED:
            return {"ok": True, "duplicate_fulfillment": True}

        square_email = extract_square_buyer_email(payment)

        set_order_paid_fields(order, payment)

        has_delivery_email = ensure_delivery_email(order, square_email)

        if has_delivery_email:
            order.status = ORDER_STATUS_PAID_EMAIL_PRESENT
            db.commit()
            db.refresh(order)

            return fulfill_order(db, order)

        order.status = ORDER_STATUS_PAID_EMAIL_MISSING
        db.commit()

        token = make_email_confirmation_token(order.id)

        return {
            "ok": True,
            "fulfilled": False,
            "status": ORDER_STATUS_PAID_EMAIL_MISSING,
            "confirm_email_token": token,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
        