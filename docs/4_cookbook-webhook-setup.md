* okay lets start again because I lost my place when switching tasks. Goal for today is to get this app launched listening for payment confirmation and sending an email with the download link. I need to work until this is completed.

* Before we get started let's get a few things established I am sure there is a file I can create for the environment variables to live in be it in my code, on github, or vercel if need be. However having to change in terminal everytime I have to reset the random link.

* Lets also establish a cookbook for this process that I can follow that includes starting the virtual environment running the app in dev/local machine during development terminal #1 running needs terminal #2 running needs where I need to go to get the link where I need to go to test and anything else that is setup and process related outside of coding and code review

# Webhook Setup Cookbook
+================================================================================+

# Part A — One-time setup (do this once)
## A1) Create a .env file (do NOT commit to GitHub)

+ In your project root (indie-pigeon/), create:

.env
```
# --- Square ---
SQUARE_ENV=sandbox
SQUARE_ACCESS_TOKEN=PASTE_YOUR_SANDBOX_ACCESS_TOKEN
SQUARE_WEBHOOK_SIGNATURE_KEY=PASTE_YOUR_SANDBOX_WEBHOOK_SIGNATURE_KEY

# --- Public webhook URL (we will make this stable in A2) ---
WEBHOOK_PUBLIC_URL=https://api.unschooldiscoveries.com/square/webhook

# --- Cloudflare download worker ---
DOWNLOAD_BASE_URL=https://ebooks.unschooldiscoveries.com/dl
DOWNLOAD_SECRET=PASTE_THE_SAME_SECRET_AS_WRANGLER_DOWNLOAD_SECRET
PRODUCT_KEY=usd-ebook-one.pdf
LINK_EXPIRES_SECONDS=86400

# --- Email ---
# (whatever your emailer.py uses; example placeholders)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your_app_password
EMAIL_FROM=Unschool Discoveries <you@gmail.com>
```
---
```
Step-by-Step Setup
1️⃣ Turn on 2-Step Verification

Go to:

https://myaccount.google.com/security

Enable:

2-Step Verification

This is required before Google allows app passwords.

2️⃣ Generate an App Password

Go to:

https://myaccount.google.com/apppasswords

Select:

App: Mail
Device: Other → Indie Pigeon

Google will generate something like:

abcd efgh ijkl mnop
3️⃣ Use that in your .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourgmail@gmail.com
SMTP_PASS=abcdefghijklmnop
FROM_EMAIL=Unschool Discoveries <yourgmail@gmail.com>

Important:

remove the spaces from the app password if present.

Example:

abcdefghijklmnop
```
---


+ Now create .gitignore (or edit it) to include:

.gitignore
```
.env
venv/
__pycache__/
*.sqlite3
```

---
## A2) Make your tunnel URL stable (no more random links)

Instead of cloudflared tunnel --url ... (random URL), we create a named tunnel bound to a real subdomain like:

``` 
api.unschooldiscoveries.com 
``` 

### Step A2.1 — Login cloudflared
This opens a browser; choose your Cloudflare account and authorize.
``` 
cloudflared tunnel login 
```

### Step A2.2 — Create the tunnel
``` 
cloudflared tunnel create indie-pigeon-api 
```

### Step A2.3 — Route DNS to the tunnel
``` 
cloudflared tunnel route dns indie-pigeon-api api.unschooldiscoveries.com
```
Now api.unschooldiscoveries.com will point to your tunnel (stable).

### Step A2.4 — Create config file
Create this file:

~/.cloudflared/config.yml
```
tunnel: indie-pigeon-api
credentials-file: /Users/dee/.cloudflared/<YOUR_TUNNEL_ID>.json

ingress:
  - hostname: api.unschooldiscoveries.com
    service: http://localhost:8000
  - service: http_status:404
```

How to find the tunnel id / credentials file:
```
cloudflared tunnel list
ls ~/.cloudflared
```

---
## A3) Update Square webhook endpoint (one time)
Square Developer Dashboard → your app → Webhooks (Sandbox)
[Square Developer Dashboard Sandbox Config](https://developer.squareup.com/apps)

Set endpoint URL to:

>  https://api.unschooldiscoveries.com/square/webhook

Make sure your subscription includes:

payment.updated (or payment.created also fine)

Save.

Now your .env WEBHOOK_PUBLIC_URL never changes again.

---
## A4) Load .env automatically in FastAPI (one-time code tweak)

In app/main.py add near the very top (before you read env vars):
```
from dotenv import load_dotenv
load_dotenv()
```

Install dotenv if you haven’t:
```
pip install python-dotenv
```
Now you don’t need terminal exports.

---

# Part B — Daily development cookbook (what you run every time)
## Terminal #1 — Run the API

From project root: **dee@Dees-MacBook-Pro indie-pigeon %**
```
cd ~/WorkingCode/indie-pigeon
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```
Verify it’s alive:

open this link in the browser 
> http://127.0.0.1:8000/health 
be sure the terminal states 
> → {"ok": true}

## Terminal #2 — Run the tunnel
```
cloudflared tunnel run indie-pigeon-api
```

Verify tunnel is live:

open this link in the browser 
> https://api.unschooldiscoveries.com/health 
be sure the terminal states 
> → {"ok": true}

**That’s your “is Square able to reach me?” check.**

---

# Part C — Testing cookbook (where to go + what to click)
## Test 1: Square can hit your webhook

Square Developer Dashboard → Webhooks (Sandbox) → your endpoint → Send Test

Expected:
- Square shows Code (500)
- Your API logs show POST /square/webhook error (don't worry)

If it errors, with a stable URL move on to a real payment

## Test 2: Real payment triggers email

Square Sandbox testing options depend on how you’re taking payment. Pick one:

### Option 1 (fastest): Square “Test a card payment” via sandbox checkout/payment

If you’re using Square Checkout/Payment Links, do a sandbox purchase and watch the webhook hit.

Expected:
- Webhook arrives
- The code calls get_payment()
- Payment status becomes COMPLETED/APPROVED
- Email sends with the DOWNLOAD_BASE_URL signed link

---

# Part D — “Launch” checklist for today

To consider sandbox testing to be “done”:

> ✅ https://api.unschooldiscoveries.com/health returns {"ok": true}
> ✅ Square sandbox webhook test returns 500 Error
> ✅ A real sandbox payment results in:
> - webhook processed (not duplicate)
> -order saved
>- email sent
>- link works and downloads from R2 through Worker

---

# Key points to note before proceeding

> The download domain is already:
> ebooks.unschooldiscoveries.com (Worker → R2)

> The “public-facing” webhooks is:
> api.unschooldiscoveries.com (Tunnel → localhost)
