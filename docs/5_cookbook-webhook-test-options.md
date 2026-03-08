# How to Trigger a Real Payment Event
`payment.updated` / `payment.created` Webhook in Square Sandbox

There are **three practical ways** to trigger a real `payment.updated` / `payment.created` webhook in Square Sandbox. Only one of them needs a checkout page.

The goal is simply: **create a real payment object in Square Sandbox** so the webhook fires and your app processes it.


## Square Payment Link (Easiest / No Code)

### Step 1

Go to **Square Dashboard (Sandbox)**
[Square Developer Explorer ](https://developer.squareup.com/explorer/square_2026-01-22/payments-api/create-payment)

54.212.177.79:0 - "POST /square/webhook HTTP/1.1" 500 Internal Server Error


Do this on the Square Explorer page:

Fill only these fields

At the top:
click Select token
choose your Sandbox Access Token
- token = sandbox
- idempotency_key = Generate
- source_id = cnon:card-nonce-ok
- amount = 1
- currency = USD
- autocomplete = true
- buyer_email_address = your email
Everything else empty.








#### Step 2

Create a payment link:
> Items → Create Item → Ebook → $1
Then:
> Online Checkout → Payment Links → Create
Select the item.

#### Step 3

Open the payment link and use the **Sandbox test card**:
```
Card Number: 4111 1111 1111 1111
Expiration: any future date
CVV: 111
ZIP: 12345
```

#### What happens:
```
Payment created
      ↓
Square fires webhook
      ↓
Your FastAPI webhook receives event
      ↓
get_payment() fetches payment
      ↓
Email sent
```


### Option 2 — Create Payment via API (Fastest for developers)

Instead of a checkout page, you directly create a payment.
Use this **curl command** (Sandbox):

bash
```
curl https://connect.squareupsandbox.com/v2/payments \
-H "Square-Version: 2024-01-17" \
-H "Authorization: Bearer YOUR_SANDBOX_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{
"idempotency_key": "test-payment-123",
"amount_money": {
  "amount": 100,
  "currency": "USD"
},
"source_id": "cnon:card-nonce-ok",
"autocomplete": true
}'
```

Square provides the special sandbox nonce:
```
cnon:card-nonce-ok
```
This immediately creates a payment.

Webhook fires instantly.



### Option 3 — Square API Explorer (No terminal)

Go here:
> [https://developer.squareup.com/explorer/square/payments-api/create-payment](https://developer.squareup.com/explorer/square/payments-api/create-payment)

Fills Fields:
> authority. amount_money.amount = 100,
> currency = USD,
> source_id = cnon:card-nonce-ok,
> autocomplete = true,
Then click **Execute**.

Webhook fires.

--- 

## Recommended 
### Use Option 1 (Payment Link)

**Why:**
- Closest to real checkout
- Easiest to demo
- Easiest to debug customer email field
- Triggers exactly the same webhook your production flow will use

---

## What should happen when it works

Your FastAPI logs should show something like:

> `POST /square/webhook`
> `payment status COMPLETED`
> `order stored`
> `email sent`

Then the buyer receives:

> Your Unschool Discoveries ebook download is here!
> Download link: [https://ebooks.unschooldiscoveries.com/dl?key=...](https://ebooks.unschooldiscoveries.com/dl?key=...)
>
Click → Worker verifies → R2 streams PDF.

---

## One thing to verify before you test

If the code you currently read:

```python
buyer_email = payment.get("buyer_email_address")
```

Payment Links sometimes store the email under:

```python
receipt_email_address
```

Make sure to add the fallback.
