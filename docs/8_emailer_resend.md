The quickest production-safe option is Resend. It is extremely simple, works great for transactional email, and has a free tier (3,000 emails/month).

Step 1 — Create Resend account

Go to:

https://resend.com

Sign up.

Step 2 — Add your domain

In Resend dashboard:

Domains → Add Domain

Enter:

unschooldiscoveries.com

Resend will give you DNS records to add in Cloudflare:

Usually:

TXT   resend._domainkey
TXT   resend._spf
CNAME resend._domainkey

Add those in Cloudflare DNS.

Verification usually takes 30 seconds–2 minutes.

Step 3 — Create API key

In Resend:

API Keys → Create API Key

Copy it.

Step 4 — Update .env

Replace the SMTP variables with:

EMAIL_PROVIDER=resend
RESEND_API_KEY=your_resend_api_key
EMAIL_FROM=Unschool Discoveries <productions@unschooldiscoveries.com>
Step 5 — Replace emailer.py

Use this version:

import os
import requests


def send_ebook_email(to_email: str, subject: str, body: str) -> str:

    api_key = os.environ["RESEND_API_KEY"]

    payload = {
        "from": os.environ["EMAIL_FROM"],
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers=headers,
        timeout=20,
    )

    r.raise_for_status()

    return "resend"
Step 6 — Restart API
CTRL+C
python -m uvicorn app.main:app --reload --port 8000
Step 7 — Run one payment

Create one sandbox payment again.

Your terminal should show:

EVENT TYPE: payment.updated
PAYMENT STATUS: COMPLETED
BUYER EMAIL: ...
ABOUT TO SEND EMAIL
EMAIL SENT OK

And the email will arrive.

Why this is better than Gmail

Gmail SMTP is bad for apps because:

rate limits

spam filtering

authentication headaches

sender rewriting

Resend is designed specifically for transactional email like:

purchase receipts
download links
password resets
After this works

Your full pipeline becomes:

Square payment
   ↓
Webhook
   ↓
FastAPI
   ↓
Signed R2 download link
   ↓
Resend email
   ↓
Customer downloads ebook

Which is exactly the Indie Pigeon digital delivery system you set out to build.