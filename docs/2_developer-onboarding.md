# Developer Onboarding Guide

This guide helps a developer set up the Indie Pigeon system locally.

Estimated setup time: **10–15 minutes**

---

# 1. Clone the Repository

```
git clone https://github.com/CogSciOliver/indie-pigeon.git
cd indie-pigeon
```

---

# 2. Create Virtual Environment

```
python3 -m venv venv
source venv/bin/activate
```

---

# 3. Install Dependencies

```
pip install -r requirements.txt
```

---

# 4. Create Environment File

Copy the template:

```
cp .env.example .env
```

Edit `.env` and fill in required values.
> https://github.com/CogSciOliver/indie-pigeon/blob/main/docs/3_cookbook-webhook-setup.md

---

# 5. Run the Backend

```
python -m uvicorn app.main:app --reload --port 8000
```

Verify:

```
http://127.0.0.1:8000/health
```

Expected response:

```
{"ok": true}
```

---

# 6. Start Cloudflare Tunnel

```
cloudflared tunnel run indie-pigeon-api
```

Verify:

```
https://api.unschooldiscoveries.com/health
```

---

# 7. Test Square Webhook

Square Developer Dashboard → Webhooks

Send test event:

```
payment.updated
```

Confirm backend receives request.

---

# 8. Test Payment

Create sandbox payment using:

* Square payment link
* Square API Explorer
* Sandbox checkout

Expected flow:

```
payment created
webhook received
email sent
download link works
```

---

# 9. Test Download Worker

Open:

```
https://ebooks.unschooldiscoveries.com/dl
```

Valid signed link should download ebook.

---

# 10. Common Issues

### Webhook signature failure

Check:

```
WEBHOOK_PUBLIC_URL
SQUARE_WEBHOOK_SIGNATURE_KEY
```

---

### Email not sending

Verify:

```
SMTP credentials
```

---

### Download link invalid

Verify:

```
DOWNLOAD_SECRET matches Worker secret
```

---

# Development Workflow

Typical development session:

```
Terminal 1
run backend

Terminal 2
run cloudflare tunnel

Square dashboard
send webhook tests
```

---

# Next Steps for Developers

Possible contributions:

* add multiple product support
* build creator dashboard
* implement analytics tracking
* add subscription delivery
