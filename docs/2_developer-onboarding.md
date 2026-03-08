# Developer Onboarding Guide

This guide helps a developer set up the Indie Pigeon system locally.

Estimated setup time: **10–25 minutes** **maybe days if you need to review docs or AI sucks**

## Helpful Jumps:

[Developer Onboarding Guide](#developer-onboarding-guide)
- [Developer Onboarding Guide](#developer-onboarding-guide)
  - [Helpful Jumps:](#helpful-jumps)
- [1. Clone the Repository](#1-clone-the-repository)
- [2. Create Virtual Environment](#2-create-virtual-environment)
- [3. Install Dependencies](#3-install-dependencies)
- [4. Create Environment File](#4-create-environment-file)
    - [Open VS Code Settings:](#open-vs-code-settings)
    - [Navigate to Python Extension Settings:](#navigate-to-python-extension-settings)
    - [Enable the Setting:](#enable-the-setting)
    - [Verify the .env file path (Optional):](#verify-the-env-file-path-optional)
    - [Restart the Terminal:](#restart-the-terminal)
- [5. Run the Backend](#5-run-the-backend)
- [6. Create/Start Cloudflare Tunnel](#6-createstart-cloudflare-tunnel)
  - [Start The App](#start-the-app)
  - [Verify It: Try the Tunnel](#verify-it-try-the-tunnel)
- [7. Test Square Webhook](#7-test-square-webhook)
    - [This means](#this-means)
- [8. Test Payment](#8-test-payment)
- [9. Test Download Worker](#9-test-download-worker)
- [10. Common Issues](#10-common-issues)
    - [Webhook signature failure](#webhook-signature-failure)
    - [Email not sending](#email-not-sending)
    - [Download link invalid](#download-link-invalid)
- [Development Workflow](#development-workflow)
- [Next Steps for Developers](#next-steps-for-developers)

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
[How To Setup .ENV Secrets](https://github.com/CogSciOliver/indie-pigeon/blob/main/docs/4_cookbook-webhook-setup.md)

### Open VS Code Settings:
- Go to the File menu (on Windows/Linux) or Code menu (on macOS) and select Preferences > Settings.
- Alternatively, you can open settings using the Command Palette by pressing Ctrl+Shift+P (Windows/Linux) or Cmd+Shift+P (macOS) and typing "Open Settings".
### Navigate to Python Extension Settings:
- In the search bar at the top of the Settings tab, type python.terminal.useEnvFile.
### Enable the Setting:
- Check the box next to the setting Python > Terminal: Use Env File.
### Verify the .env file path (Optional):
- The extension looks for a .env file by default in your workspace root. If your file is located elsewhere, you can specify its path using the python.envFile setting.
### Restart the Terminal:
- Close and reopen any existing terminals in VS Code for the changes to take effect. 

After these steps, environment variables defined in your .env file will be automatically injected into new terminals you open within VS Code.

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

# 6. Create/Start Cloudflare Tunnel

How To Setup API URL & Create Tunnel [Stable Named Path for CloudFlared](https://github.com/CogSciOliver/indie-pigeon/blob/main/docs/3_cookbook-api-tunnel-setup.md)

Once Created verify it exists and connect

Run:
```
cloudflared tunnel list
```

Select required tunnel api name:
```
cloudflared tunnel run indie-pigeon-api
```

## Start The App
**This step REQUIRES the 2 terminal workflow**

`Terminal 1:`
bash
```
cd ~/WorkingCode/indie-pigeon
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

`Terminal 2:`
**Leave it running.**
bash
```
cloudflared tunnel run indie-pigeon-api
```

## Verify It: Try the Tunnel 
Open:
> https://api.unschooldiscoveries.com/health

Expected:
> {"ok": true}

---

# 7. Test Square Webhook

How To Setup and Connect to Square Webhooks [Square Webhook](https://github.com/CogSciOliver/indie-pigeon/blob/main/docs/4_cookbook-webhook-setup.md)

Square Developer Dashboard → Webhooks

Send test event:

```
payment.updated
```

Confirm backend receives request.

You will get a `500 Internal Server Error`

### This means
> Cloudflare is fine
> webhook signature is fine
> FastAPI route is fine
> the Square test event is not a real order fulfillment test

**Move On to Make a Real Sandbox Payment**


---

# 8. Test Payment
How To Run Test Triggers [Square Sandbox](https://github.com/CogSciOliver/indie-pigeon/blob/main/docs/5_cookbook-webhook-test-options.md)

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
