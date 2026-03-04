# Prototype goal (v0)

When a Square payment is confirmed, send an email to the buyer with the ebook delivered (attachment if small enough; otherwise an expiring download link).

## Prototype inputs you already have
- Square checkout/cart (existing)
- Google Form signup (lead capture)
- You (author) as first “store”

## Prototype outputs
- Buyer gets the ebook automatically
- You get a log of who received what and when

## Recommended v0 architecture (simple but not sloppy)
- **Backend:** FastAPI (leaner than Django for this v0)
- **DB:** SQLite to start (Postgres later)
- **Email:** SMTP (Gmail/Workspace) or Postmark/SES later
- **Storage:** local `/data/ebooks/` for v0 → S3/R2 for v1
- **Webhooks:** Square Webhooks → your `/webhooks/square` endpoint
- **Code hosting:** GitHub (great for code; not file delivery storage)

## Reality check on “email with attachment”
Many providers clip or block attachments above ~10–25 MB and spam filters hate automated attachments. For ebooks it’s usually fine, but a secure download link is more reliable. You can still attach for small files and fall back to link if large.

## Data model (v0)
You only need 4 tables to ship this:
| Table | Columns |
|---|---|
| products | id, name, file_path, active |
| orders | id, square_event_id, square_payment_id, buyer_email, buyer_name, product_id, status (pending|paid|fulfilled|failed), timestamps |
| delivery_logs | id, order_id, email_status, provider_message_id, error, timestamps |
| form_signups | id, email, name, source, timestamps |

## The v0 flow (exact sequence)
a) Payment-confirmed webhook → fulfillment
1. Square sends webhook event to your app.
2. Your app verifies:
   - the webhook signature,
   - event is a “payment completed/approved” type.
3. Your app extracts payment_id (and any buyer info available).
4. Your app calls Square API to fetch payment details (source of truth).
5. Your app maps the payment to a product.
6. Your app sends email to buyer with:
   - attachment or
   - expiring download link.
7. Mark order fulfilled.
b) Google Form signup → lead capture + optional “free delivery”
1. Form submits email/name → your app stores it.
2. You can send the free ebook immediately OR require “confirmed purchase” (your call).
3. For “free tier”: it’s basically a form-triggered fulfillment system + simple analytics.

## How to map Square purchases to the correct file (v0 options)
pick the least annoying one:
every paid event triggers sending the same ebook.
or: Map catalog_object_id from line items to your products.id.
or: Use Square `reference_id` set as "EBOOK_MAIN" during checkout creation.
to keep it simple for prototypes and giveaways—Option 1 works perfectly.

## Endpoints (v0)
paste in your server code:
schema:
description: API endpoints for handling webhooks and form submissions.
details:
apis:
definitions:
type: object
title: Endpoint Definitions
description: List of API endpoints used in prototype setup.
e.g.,
payloads:
description: Payloads expected by each endpoint.