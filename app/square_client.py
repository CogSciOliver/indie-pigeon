import base64, hashlib, hmac, os
import requests

def square_base_url():
    return "https://connect.squareup.com" if os.getenv("SQUARE_ENV","sandbox") == "production" else "https://connect.squareupsandbox.com"

def verify_square_signature(signature_header: str, signature_key: str, notification_url: str, raw_body: bytes) -> bool:
    # Square signature is base64(hmac_sha1(key, url + body))
    mac = hmac.new(signature_key.encode("utf-8"), (notification_url.encode("utf-8") + raw_body), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode("utf-8")
    return hmac.compare_digest(expected, signature_header or "")

def get_payment(payment_id: str) -> dict:
    url = f"{square_base_url()}/v2/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {os.environ['SQUARE_ACCESS_TOKEN']}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()["payment"]