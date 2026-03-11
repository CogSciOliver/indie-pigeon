# system-design.md

# Indie Pigeon — System Design & Product Specification

---

# 1. System Design Document (SDD)

## 1.1 Overview

Indie Pigeon is a digital product delivery platform that integrates with Square Checkout. After a successful payment, the platform automatically sends digital products to the buyer via email.

The system is **webhook-driven**, meaning fulfillment occurs only after a verified payment event from Square.

Because Square checkout links may be accessed directly without passing through Indie Pigeon’s email collection page, the system includes a **recovery flow** for collecting a delivery email post-purchase.

---

## 1.2 Goals

Primary goals:

* Deliver digital products automatically after payment
* Prevent fulfillment without a valid delivery email
* Handle webhook retries safely
* Support edge cases where users bypass the intended checkout flow
* Maintain an auditable order state machine

---

## 1.3 Non-Goals

Current prototype excludes:

* subscription billing
* license key generation
* multi-product bundles
* storefront UI
* creator accounts

These features may be added later.

---

## 1.4 High-Level Architecture

```
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
  │ payment processed
  ▼
Square Webhook
  │
  ▼
Webhook Handler
  │
  ├─ email present → fulfill order
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
```

---

## 1.5 Order State Machine

```
pending_payment
      │
      ▼
paid_email_present ───────► fulfilled
      │
      ▼
paid_email_missing
      │
      ▼
email_confirmed
      │
      ▼
fulfilled
```

### State Descriptions

**pending_payment**

Checkout initiated but payment not completed.

Created when:

* user submits email
* checkout link generated

---

**paid_email_present**

Payment completed and a valid delivery email exists.

Next action:

```
trigger fulfillment
```

---

**paid_email_missing**

Payment completed but delivery email is missing.

Next action:

```
prompt user to confirm email
```

Fulfillment is paused.

---

**email_confirmed**

User submits email after purchase.

Next action:

```
trigger fulfillment
```

---

**fulfilled**

Digital product email successfully sent.

Terminal state.

---

## 1.6 Database Model

### orders table

```
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
```

---

### Status values

```
pending_payment
paid_email_present
paid_email_missing
email_confirmed
fulfilled
```

---

### Email source values

```
pre_checkout_form
square_checkout
post_purchase_form
manual_admin
```

---

## 1.7 Webhook Flow

Square sends webhook events when payments update.

Webhook handler performs:

1. verify signature
2. confirm payment status = COMPLETED
3. match payment to order

Matching priority:

```
order_ref
square_order_id
checkout_link_id
```

---

### Case A — Email exists

```
status → paid_email_present
paid_at → timestamp
```

Then trigger fulfillment.

If fulfillment succeeds:

```
status → fulfilled
fulfilled_at → timestamp
```

---

### Case B — Email missing

```
status → paid_email_missing
paid_at → timestamp
```

System waits for email confirmation.

---

### Case C — No matching order

Create record:

```
status = paid_email_missing
square_payment_id = payment.id
buyer_email = square_email_if_available
```

---

## 1.8 Fulfillment

Fulfillment service:

1. verify delivery_email exists
2. generate download link
3. send product email

On success:

```
status = fulfilled
fulfilled_at = now
```

---

## 1.9 Idempotency Protection

Webhook events may retry.

Before fulfillment:

```
if order.status == "fulfilled":
    return
```

This prevents duplicate delivery.

---

## 1.10 Edge Cases

### Direct Square Checkout

Users may access checkout without passing through Indie Pigeon.

System response:

```
payment completes
→ status = paid_email_missing
→ request email confirmation
```

---

### Webhook Retries

Square may resend events.

System behavior:

```
ignore if order already fulfilled
```

---

### Email Typos

Possible mitigations:

* double entry confirmation
* manual resend functionality

---

### Fulfillment Failure

Future state recommended:

```
fulfillment_failed
```

---

## 1.11 Security Considerations

Email confirmation links use signed tokens.

Token payload includes:

```
order_id
expiration
signature
```

This prevents unauthorized order modification.

---

# 2. Architecture Decision Records (ADR)

---

## ADR-001 — Use Square Hosted Checkout

### Context

Payment processing must be reliable and PCI compliant.

Building a custom payment UI introduces compliance complexity.

### Decision

Use Square hosted checkout links.

### Consequences

Pros:

* PCI handled by Square
* simple integration
* secure checkout

Cons:

* limited control over checkout UI
* users may bypass pre-checkout flow

---

## ADR-002 — Pre-Checkout Email Collection

### Context

Digital products require a delivery email.

Square may not always return a usable email.

### Decision

Collect delivery email before redirecting to Square checkout.

### Consequences

Pros:

* reliable delivery address
* better order matching

Cons:

* users may bypass this step

---

## ADR-003 — Post-Purchase Email Recovery

### Context

Users may access checkout links directly.

Payment may complete without an email stored in Indie Pigeon.

### Decision

Orders without delivery email enter:

```
paid_email_missing
```

User must confirm email before fulfillment.

### Consequences

Pros:

* prevents lost deliveries
* supports recovery flow

Cons:

* additional step for edge cases

---

## ADR-004 — Webhook-Driven Fulfillment

### Context

Client-side payment confirmation is unreliable.

### Decision

Trigger fulfillment only after verified webhook event.

### Consequences

Pros:

* secure
* prevents fraudulent triggers
* consistent state transitions

Cons:

* slightly slower delivery due to webhook processing

---

# 3. Product Requirements Document (PRD)

---

## 3.1 Problem

Creators selling digital products need a reliable way to deliver files automatically after payment.

Existing tools often require expensive platforms or third-party services.

Indie Pigeon provides a lightweight delivery platform that integrates with existing checkout systems.

---

## 3.2 Goals

* deliver digital files automatically
* support Square payments
* ensure products are delivered only after verified payment
* handle edge cases gracefully
* maintain simple architecture

---

## 3.3 User Stories

### Buyer receives digital product

```
As a buyer
I want my purchased digital product delivered to my email
So that I can download it after payment.
```

---

### Creator sells digital product

```
As a creator
I want my product delivered automatically
So that I do not manually fulfill each order.
```

---

### Recover missing email

```
As a buyer
If payment completes without providing my email
I want a way to confirm the correct delivery address
So I can receive my product.
```

---

## 3.4 Functional Requirements

### Checkout

* system collects delivery email
* system generates Square checkout link
* user completes payment via Square

---

### Payment Verification

* webhook verifies payment status
* system records payment details

---

### Fulfillment

* digital product sent via email
* email includes download link

---

### Recovery Flow

If delivery email missing:

* system pauses fulfillment
* system requests email confirmation
* fulfillment resumes after confirmation

---

## 3.5 Non-Functional Requirements

Performance:

* fulfillment within seconds after webhook event

Reliability:

* idempotent webhook processing

Security:

* signed confirmation tokens
* webhook verification

---

## 3.6 Success Metrics

Initial prototype metrics:

* successful delivery rate
* webhook processing success
* recovery flow completion rate
* fulfillment latency

---

## 3.7 Future Features

Potential platform expansion:

```
license key distribution
subscriptions
creator storefronts
analytics dashboard
download tracking
multi-file delivery
```

---

# Summary

Core system rule:

**Payment alone does not trigger fulfillment.
Fulfillment requires a confirmed delivery email.**

This guarantees digital products are delivered only to a verified recipient.
