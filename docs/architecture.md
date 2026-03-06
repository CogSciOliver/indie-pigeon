# Indie Pigeon Architecture

## Overview

Indie Pigeon is a lightweight digital product delivery platform designed to automatically fulfill purchases by sending secure download links to customers.

Primary components:

* Square Payments
* FastAPI backend
* Cloudflare Worker
* Cloudflare R2 storage
* Email delivery service

---

# System Architecture

```
Customer
   │
   ▼
Square Checkout
   │
   ▼
Square Webhook
POST /square/webhook
   │
   ▼
FastAPI Backend
   │
   ├─ Verify webhook signature
   ├─ Confirm payment via Square API
   ├─ Save order
   └─ Generate signed download link
   │
   ▼
Email sent to customer
   │
   ▼
Customer clicks download link
   │
   ▼
Cloudflare Worker
   │
   ├─ Validate signed token
   ├─ Check expiration
   └─ Fetch file from R2
   │
   ▼
Cloudflare R2 Storage
```

---

# Component Responsibilities

## Square

Responsible for:

* payment processing
* webhook notifications
* payment status confirmation

---

## FastAPI Backend

Handles:

* webhook verification
* payment validation
* order storage
* download link generation
* email delivery

Key route:

``` 
/square/webhook
```

---

## Cloudflare Worker

Acts as the secure download gateway.

Responsibilities:

* validate signed URLs
* prevent unauthorized downloads
* stream files from R2

Endpoint:

```
https://ebooks.unschooldiscoveries.com/dl
```

---

## Cloudflare R2

Object storage for digital products.

Example object:

```
usd-ebook-one.pdf
```

Bucket:

```
digital-products
```

---

# Security Model

Security is enforced using three mechanisms:

1. Square webhook signature validation
2. Signed download links
3. Private R2 storage

Download links contain:

```
key
exp (expiration timestamp)
sig (HMAC signature)
```

Example:

```
https://ebooks.unschooldiscoveries.com/dl?key=usd-ebook-one.pdf&exp=...&sig=...
```

---

# Data Flow

```
Square Payment
      ↓
Webhook
      ↓
FastAPI validates payment
      ↓
Order stored
      ↓
Signed download link created
      ↓
Email sent
      ↓
Customer downloads ebook
```

---

# Deployment Topology

```
api.unschooldiscoveries.com
        │
        ▼
FastAPI backend

ebooks.unschooldiscoveries.com
        │
        ▼
Cloudflare Worker
        │
        ▼
Cloudflare R2
```

---

# Design Principles

The system is designed to be:

* simple
* server-light
* secure
* easy to extend
* cost-efficient

---

# Future Architecture Extensions

Possible additions:

* multiple product support
* license key generation
* creator dashboard
* subscription management
* analytics tracking
