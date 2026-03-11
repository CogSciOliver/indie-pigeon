# Indie Pigeon — Order Processing & Fulfillment Flow

## Overview

Indie Pigeon delivers digital products via email after a successful Square payment.

The system collects a delivery email before checkout when possible. If payment occurs without a confirmed email, the system pauses fulfillment and requests email confirmation.

The system is **webhook-driven** and fulfillment occurs only after payment is confirmed.

---

# System Architecture


User
│
│ enters delivery email
▼
Indie Pigeon API
│
│ create order record
│ status = pending_payment
│
▼
Square Checkout Link
│
│ payment
▼
Square Webhook
│
▼
Indie Pigeon Webhook Handler
│
├─ email present → fulfill
│
└─ email missing → request confirmation
│
▼
Email Confirmation Page
│
▼
Fulfillment Service
│
▼
Email Delivery


---

# Order State Machine


pending_payment
│
▼
paid_email_present ─────────► fulfilled
│
▼
paid_email_missing
│
▼
email_confirmed
│
▼
fulfilled


## State definitions

### `pending_payment`

Checkout started but payment not completed.

Created when:

- user enters email
- checkout link generated

---

### `paid_email_present`

Payment completed and delivery email exists.

Next action:


trigger fulfillment


---

### `paid_email_missing`

Payment completed but no delivery email exists.

Next action:


prompt user to confirm email


Fulfillment is paused.

---

### `email_confirmed`

User submitted delivery email after payment.

Next action:


trigger fulfillment


---

### `fulfilled`

Digital product successfully sent.

This is the terminal state.

---

# Database Model

## orders table


id
order_ref
square_payment_id
square_order_id
checkout_link_id

item_id
item_name

amount
currency

status

buyer_email
delivery_email
email_source

created_at
paid_at
email_confirmed_at
fulfilled_at


---

## Status values


pending_payment
paid_email_present
paid_email_missing
email_confirmed
fulfilled


---

## Email source values


pre_checkout_form
square_checkout
post_purchase_form
manual_admin


---

# Checkout Flow

## Step 1 — Email collection

User enters delivery email.

System:


create order
status = pending_payment
delivery_email = collected_email
email_source = pre_checkout_form


System generates Square checkout link and redirects user.

---

# Payment Processing

Square sends webhook event when payment completes.

Webhook handler:

1. verify event type
2. verify payment status
3. match payment to order

Matching priority:


order_ref
square_order_id
checkout_link_id


---

# Webhook Behavior

## Case A — Order exists with delivery email


status → paid_email_present
paid_at → timestamp


Then trigger fulfillment.

If fulfillment succeeds:


status → fulfilled
fulfilled_at → timestamp


---

## Case B — Order exists but delivery email missing


status → paid_email_missing
paid_at → timestamp


Fulfillment paused.

User must confirm email.

---

## Case C — No order record found

Create new record:


status = paid_email_missing
square_payment_id = payment.id
buyer_email = square_email_if_available


System waits for email confirmation.

---

# Email Confirmation Flow

User visits:


/confirm-email?token=...


Token identifies order.

User submits email.

System updates order:


delivery_email = submitted_email
email_source = post_purchase_form
email_confirmed_at = now
status = email_confirmed


System triggers fulfillment.

---

# Fulfillment Process

Fulfillment service:

1. verify delivery_email exists
2. send product email
3. attach download link

On success:


status = fulfilled
fulfilled_at = now


---

# Idempotency Protection

Webhook events may retry.

Fulfillment must be safe to run multiple times.

Before sending product:


if status == fulfilled:
exit


---

# Edge Cases

## Direct Square Checkout

User may access checkout link directly without passing through email collection.

System response:


payment completes
→ status = paid_email_missing
→ require email confirmation


---

## Webhook Retry

Square may resend webhook events.

Protection:


check order status
prevent duplicate fulfillment


---

## Email Typo

User may mistype email during confirmation.

Mitigation options:

- double entry confirmation
- manual resend ability

---

## Fulfillment Failure

Possible causes:

- SMTP error
- file storage unavailable

Recommended future state:


fulfillment_failed


---

# Security Considerations

Confirmation links must use signed tokens.

Token must include:


order_id
expiration
signature


Prevents unauthorized order modification.

---

# Future Extensions

Potential additions:


license_keys
subscriptions
multiple file delivery
creator storefronts
analytics


Additional states may include:


fulfillment_failed
refunded


---

# Summary

Core rule of system:

**Payment alone does not trigger fulfillment.  
Fulfillment requires a confirmed delivery email.**

This ensures digital products are delivered only when a valid recipient address exists.