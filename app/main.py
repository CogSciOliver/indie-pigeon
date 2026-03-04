import os
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal, init_db
from .models import Order, DeliveryLog
from .square_client import verify_square_signature, get_payment
from .emailer import send_ebook_email
import hmac, hashlib, time, urllib.parse

def make_cf_download_url(key: str) -> str:
    base = os.environ["DOWNLOAD_BASE_URL"].rstrip("/")  # e.g. https://ebooks.unschooldiscoveries.com/dl
    secret = os.environ["DOWNLOAD_SECRET"]
    exp = int(time.time()) + int(os.environ.get("LINK_EXPIRES_SECONDS", "86400"))  # default 24h

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

    # IMPORTANT: notification URL must exactly match what Square calls (scheme/host/path)
    notification_url = os.environ["WEBHOOK_PUBLIC_URL"]

    if not verify_square_signature(signature, signature_key, notification_url, raw):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    event_id = event.get("event_id") or event.get("id")  # Square naming can vary by tooling
    event_type = event.get("type", "")

    # Only fulfill on successful payment events.
    # If Square account emits different types, whitelist the right one(s) after a sample payload.
    if "payment" not in event_type.lower():
        return {"ignored": True}

    payment_id = None
    data_obj = (event.get("data") or {}).get("object") or {}
    # common shapes: data.object.payment.id OR data.object.id
    payment_id = (data_obj.get("payment") or {}).get("id") or data_obj.get("id")
    if not payment_id or not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id/payment_id")

    # Confirm payment via Square API
    payment = get_payment(payment_id)
    status = (payment.get("status") or "").upper()
    if status not in ("COMPLETED", "APPROVED"):  # be strict
        return {"ignored": True, "payment_status": status}

    buyer_email = payment.get("buyer_email_address")
    if not buyer_email:
        # Some flows may not include email; you can fall back to receipt_email_address
        buyer_email = payment.get("receipt_email_address")
    if not buyer_email:
        raise HTTPException(status_code=400, detail="No buyer email on payment")

    # Save order idempotently
    db = SessionLocal()
    try:
        order = Order(square_event_id=event_id, square_payment_id=payment_id, buyer_email=buyer_email, status="paid")
        db.add(order)
        db.commit()
        db.refresh(order)
    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}  # already processed
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
        db.close()

    # Fulfill: Email Message with ebook link
    product_key = os.environ.get("PRODUCT_KEY", "usd-ebook-one.pdf")
    # **WHY ONLY ONE LINK? This is a single-product store. For multiple products, I'd look up the product_key based on order details.** !IMPORTANT: product_key should not be user input or guessable to prevent abuse.
    
    
    download_url = make_cf_download_url(product_key)
    
    subject = "Your Unschool Discoveries ebook download is here!"
    body = f"""Thanks for your purchase! Your can download your ebook using the link below.\n\nIf you have any trouble, reply to this email.\n\nDownload link: {download_url}"""

    db = SessionLocal()
    try:
        provider_id = send_ebook_email(buyer_email, subject, body, attachment_path=None)

        # mark fulfilled + log
        order = db.query(Order).filter(Order.square_payment_id == payment_id).first()
        order.status = "fulfilled"
        order.fulfilled_at = datetime.utcnow()
        db.add(DeliveryLog(order_id=order.id, email_status="sent", provider_message_id=provider_id))
        db.commit()

    except Exception as e:
        db.rollback()
        # mark failed
        order = db.query(Order).filter(Order.square_payment_id == payment_id).first()
        if order:
            order.status = "failed"
            db.add(DeliveryLog(order_id=order.id, email_status="error", error=str(e)))
            db.commit()
        raise HTTPException(status_code=500, detail=f"Fulfillment error: {e}")
    finally:
        db.close()

    return {"ok": True, "fulfilled": True, "email": buyer_email}