import os
import requests


def send_ebook_email(to_email: str, subject: str, body: str) -> str:
    api_key = os.environ["RESEND_API_KEY"]
    email_from = os.environ["EMAIL_FROM"]

    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": email_from,
            "to": [to_email],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )

    r.raise_for_status()
    data = r.json()

    return data.get("id", "resend")