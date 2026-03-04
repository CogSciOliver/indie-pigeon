# Software Needs:
```
pip install -r requirements.txt
```
- should have all imports needed listed

# Platform Needs:

1.  **Product catalog**
    -   Digital files, bundles, versions, drip content
2.  **Checkout + payments**
    -   Stripe first (cards, Apple Pay, etc.), later PayPal
3.  **Fulfillment & secure delivery**
    -   Signed expiring download links
    -   Bandwidth limits, download counts, IP/device heuristics
4.  **Licensing**
    -   License keys, activations, seats, device resets
5.  **Customer portal**
    -   Order history, downloads, license management, refunds/help
6.  **Seller admin**
    -   Upload files, create products, coupons, analytics, webhooks
7.  **Integrations**
    -   Webhooks + "buy button" embeds + API keys
8.  **Affiliates**
    -   Referral links, attribution windows, payouts
9.  **Compliance & security**
    -   Audit logs, encryption at rest, GDPR basics, tax/VAT later

## MVP Scope 
1. Seller creates product + uploads file
2. Buyer pays via Stripe Checkout
3. Webhook confirms payment → order created
4. Buyer gets email + portal link
5. Downloads served via expiring signed URL
6. Seller sees orders + can resend links/refund flag
**Launch to start charging customers.**

## Business model (simple)
- Starter: $15–$29/mo + small fee per transaction
- Pro: $59–$99/mo, lower fee, affiliates + licensing
- Enterprise: custom, SSO, SLAs, advanced tax/VAT

## Prototype Flow
```
Customer pays → Square sends webhook
                ↓
Python backend verifies signature
                ↓
Backend confirms payment via Square API
                ↓
Backend generates signed Cloudflare link
                ↓
Email sent to customer
                ↓
Customer clicks link
                ↓
Cloudflare Worker verifies signature
                ↓
R2 sends ebook
```