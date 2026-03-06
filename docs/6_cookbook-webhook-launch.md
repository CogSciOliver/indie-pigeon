# Webhook Launch Cookbook
Production checklist after this test succeeds:
- Square payment link
- Webhook verification
- Cloudflare Worker download
- Email delivery
+================================================================================+

Production Operations Cookbook you can drop directly into your repo (e.g., docs/production-cookbook.md). It assumes the dev cookbooks you drafted earlier and the architecture you built:

Square → webhook → FastAPI backend

Backend verifies payment → generates signed Cloudflare Worker URL

Worker streams ebook from Cloudflare R2

Backend emails the download link to the buyer

# Indie-Pigeon Production Operations Cookbook

## 1. System Overview

**Production architecture**

```
Customer checkout
        │
        ▼
Square Payment
        │
        ▼
Square Webhook → https://api.unschooldiscoveries.com/square/webhook
        │
        ▼
FastAPI Backend (Vercel / server / container)
        │
        ├─ Verify webhook signature
        ├─ Confirm payment via Square API
        ├─ Generate signed download link
        └─ Send email to customer
                 │
                 ▼
https://ebooks.unschooldiscoveries.com/dl
        │
        ▼
Cloudflare Worker verifies signature
        │
        ▼
Cloudflare R2 → ebook download
```

---

# 2. Production Environment Setup

## 2.1 Environment Variables

These must exist in **production hosting** (Vercel / server / container).

```
SQUARE_ENV=production
SQUARE_ACCESS_TOKEN=<square production access token>
SQUARE_WEBHOOK_SIGNATURE_KEY=<square webhook signature key>

DOWNLOAD_BASE_URL=https://ebooks.unschooldiscoveries.com/dl
DOWNLOAD_SECRET=<same secret configured in cloudflare worker>
PRODUCT_KEY=usd-ebook-one.pdf
LINK_EXPIRES_SECONDS=86400

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email account>
SMTP_PASS=<app password>
FROM_EMAIL=Unschool Discoveries <support@unschooldiscoveries.com>
```

Never commit these values to Git.

---

# 3. Cloudflare Infrastructure

## 3.1 Worker (download gateway)

Worker endpoint:

```
https://ebooks.unschooldiscoveries.com/dl
```

Responsibilities:

* verify HMAC token
* validate expiration timestamp
* fetch ebook from R2 bucket
* stream file to user

Worker secret:

```
DOWNLOAD_SECRET
```

Must match backend environment variable.

---

## 3.2 R2 Storage

Bucket:

```
digital-products
```

Object key:

```
usd-ebook-one.pdf
```

Only accessed via Worker (not public).

---

# 4. Square Configuration

## 4.1 Webhook Endpoint

Square Dashboard → Developer → Webhooks

Endpoint:

```
https://api.unschooldiscoveries.com/square/webhook
```

Events:

```
payment.updated
payment.created
```

---

## 4.2 Payment Flow

```
Customer checkout
     ↓
Square processes payment
     ↓
Webhook sent
     ↓
Backend verifies + fulfills order
```

---

# 5. Email Delivery

The backend sends an email containing a **signed download URL**.

Example email:

```
Subject: Your Unschool Discoveries ebook download is here

Thanks for your purchase!

Download your ebook here:
https://ebooks.unschooldiscoveries.com/dl?key=usd-ebook-one.pdf&exp=...

This link expires in 24 hours.
```

---

# 6. Production Deployment

## 6.1 Backend deployment

Typical options:

* Vercel
* Fly.io
* Railway
* VPS + Docker
* Kubernetes

Recommended command if containerized:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 6.2 Domain Routing

DNS configuration:

```
api.unschooldiscoveries.com → backend server
ebooks.unschooldiscoveries.com → Cloudflare Worker
```

---

# 7. Monitoring

Monitor the following:

### Application Logs

Watch for:

```
POST /square/webhook
order fulfilled
email sent
```

### Square Dashboard

Confirm:

```
webhook delivery success
payment status
```

### Cloudflare Analytics

Confirm download activity.

---

# 8. Failure Recovery

## Webhook failed

If Square webhook fails:

1. Check backend logs
2. Confirm webhook signature key
3. Verify endpoint reachable
4. Re-send webhook from Square dashboard

---

## Email failure

Check:

```
SMTP credentials
email provider limits
```

Retry sending manually if necessary.

---

## Download link invalid

Verify:

```
DOWNLOAD_SECRET matches worker secret
expiration timestamp
product key correct
```

---

# 9. Order Idempotency

Database must enforce uniqueness:

```
square_event_id
square_payment_id
```

This prevents duplicate deliveries when Square retries webhooks.

---

# 10. Security Practices

* never expose R2 publicly
* signed links expire
* webhook signature verification required
* secrets stored only in environment variables

---

# 11. Production Checklist

Before launch verify:

✓ Square webhook endpoint active
✓ Worker serving downloads correctly
✓ R2 file accessible through worker
✓ Email delivery functioning
✓ Successful sandbox payment test
✓ Successful production payment test

---

# 12. Operational Runbook

Daily operational checks:

1. Confirm webhook endpoint responding
2. Confirm Cloudflare Worker operational
3. Verify email service health
4. Review order fulfillment logs

---

# 13. Scaling Considerations

If order volume grows:

* move email delivery to background queue
* add retry queue for webhook processing
* add CDN caching for large file downloads
* add analytics tracking for downloads

---

# 14. Future Enhancements

Potential upgrades:

* multiple product support
* license key delivery
* subscription support
* creator dashboard
* usage analytics

---

# 15. Launch Summary

Once production is active:

>Customer buys ebook
> Webhook fires
> Backend verifies payment
> Signed download link generated
> Email delivered
> Customer downloads ebook

This completes the Indie-Pigeon digital delivery pipeline.
