# Indie Pigeon – Production Setup Cookbook

This document records the exact steps taken to bring the **Indie Pigeon digital delivery system** from local development to a working production pipeline.

The goal of the system is to:

1. Accept a purchase through **Square Checkout**
2. Capture the buyer email before checkout
3. Receive a **Square webhook**
4. Verify payment
5. Generate a **signed download link**
6. Send the ebook via **Resend email**
7. Deliver the file securely through **Cloudflare Worker + R2**

---

# 1. Core Architecture

Final production architecture:

```
Customer
   ↓
Email Capture Form (FastAPI)
   ↓
Square Checkout
   ↓
Square Webhook → FastAPI API
   ↓
Verify payment status
   ↓
Store order in database
   ↓
Generate signed download URL
   ↓
Send email (Resend API)
   ↓
Customer clicks download
   ↓
Cloudflare Worker validates signature
   ↓
R2 serves ebook file
```

Services used:

| Component       | Service           |
| --------------- | ----------------- |
| API             | FastAPI           |
| Hosting         | Vercel            |
| Payments        | Square            |
| Email           | Resend            |
| File Storage    | Cloudflare R2     |
| Secure Download | Cloudflare Worker |
| Database        | Neon Postgres     |

---

# 2. Initial Problem: SQLite Read-Only Error

Original database configuration:

```
sqlite:///./app.db
```

This worked **locally**, but failed in Vercel with:

```
sqlite3.OperationalError: attempt to write a readonly database
```

Reason:

Vercel serverless environments do **not allow writing to the project directory**.

---

# 3. Solution: Use Neon Postgres

A hosted PostgreSQL database was added using **Neon**.

Steps:

1. Create account at
   https://neon.tech

2. Create project

3. Copy connection string from dashboard.

Example Neon connection string:

```
postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

---

# 4. SQLAlchemy Connection String Conversion

SQLAlchemy requires a driver specification.

Change:

```
postgresql://
```

to:

```
postgresql+psycopg://
```

Final environment variable:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

---

# 5. Vercel Environment Variables

The following variables were configured.

```
SQUARE_ENV=production
SQUARE_ACCESS_TOKEN=xxxxx
SQUARE_WEBHOOK_SIGNATURE_KEY=xxxxx
WEBHOOK_PUBLIC_URL=https://api.unschooldiscoveries.com/square/webhook

DOWNLOAD_BASE_URL=https://ebooks.unschooldiscoveries.com/dl
DOWNLOAD_SECRET=xxxxx
PRODUCT_KEY=usd-ebook-one.pdf
LINK_EXPIRES_SECONDS=86400

RESEND_API_KEY=xxxxx
EMAIL_FROM=productions@kidofamilyranch.com

MANUAL_SEND_PASSWORD=xxxxx
SQUARE_CHECKOUT_URL=https://kidofamilyranchpublishing.square.site/product/ebook1/6?cp=true&sa=true&sbp=false&q=false

DATABASE_URL=postgresql+psycopg://...
```

---

# 6. Python Database Configuration

The database layer was updated to support both:

* local SQLite development
* production Postgres

```
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
```

Tables created automatically:

```
orders
delivery_logs
```

---

# 7. Square Webhook Flow

Webhook endpoint:

```
POST /square/webhook
```

Steps performed:

1. Verify Square webhook signature
2. Retrieve payment using Square API
3. Confirm payment status = `COMPLETED`
4. Match most recent pending order
5. Generate signed download URL
6. Send email

Example webhook log:

```
EVENT TYPE: payment.updated
PAYMENT STATUS: COMPLETED
BUYER EMAIL: theartist@damnemail.com
ABOUT TO SEND EMAIL
```

---

# 8. Email Delivery Issue

Initial failure:

```
403 Client Error: Forbidden for url: https://api.resend.com/emails
```

Cause:

The email sender domain was **not verified in Resend**.

---

# 9. Fix: Resend Domain Verification

Steps:

1. Open **Resend Dashboard**
2. Add sending domain:

```
kidofamilyranch.com
```

3. Add DNS records provided by Resend

Typically:

```
DKIM
SPF
```

4. Wait for verification.

After DNS verification, email sending succeeds.

---

# 10. Secure Download Worker

Cloudflare Worker endpoint:

```
https://ebooks.unschooldiscoveries.com/dl
```

Parameters:

```
key
exp
sig
```

Signature algorithm:

```
sig = HMAC_SHA256(secret, f"{key}.{exp}")
```

Worker validation:

1. Validate parameters
2. Check expiration
3. Verify HMAC signature
4. Fetch file from R2
5. Serve file as download

Example response headers:

```
Content-Type: application/pdf
Content-Disposition: attachment
```

---

# 11. Manual Email Recovery Tool

A manual email sender was implemented.

Endpoint:

```
/manual-send
```

Features:

* password protected
* regenerate signed download URL
* resend ebook email

Useful for:

* webhook failure
* customer support
* resending lost emails

---

# 12. Final System Status

Working components:

| Component                  | Status |
| -------------------------- | ------ |
| Square Checkout            | ✓      |
| Webhook verification       | ✓      |
| Database persistence       | ✓      |
| Signed download URLs       | ✓      |
| Cloudflare Worker security | ✓      |
| R2 file storage            | ✓      |
| Resend email delivery      | ✓      |
| Manual resend tool         | ✓      |

---

# 13. Security Measures

Implemented protections:

* Square webhook signature verification
* signed download links
* download expiration
* disabled direct file route
* manual send password
* server-side order tracking

---

# 14. Future Improvements

Potential enhancements:

* tie `checkout_ref` directly to Square order metadata
* one-time download tokens
* download count tracking
* customer purchase history
* admin dashboard
* license key support
* subscription support

---

# 15. Result

The Indie Pigeon prototype is now a fully functional **digital delivery platform** capable of:

* accepting payments
* verifying transactions
* sending secure download links
* delivering digital files automatically.

This establishes the foundation for expanding into a full creator commerce platform.
