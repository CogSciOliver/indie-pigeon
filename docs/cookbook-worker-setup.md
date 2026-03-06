# (Cloudflare) Worker Download Link Setup Cookbook
+================================================================================+
# Cloudflare Worker + R2 Setup & Testing Cookbook

This document describes the **complete setup and testing process** for the Cloudflare Worker and R2 storage used to securely deliver digital products.

The Worker acts as a **secure download gateway** between customers and the private R2 storage bucket.

---

## 1. Architecture Overview

Customer
   │
   ▼
Signed Download Link
https://ebooks.unschooldiscoveries.com/dl
   │
   ▼
Cloudflare Worker
   │
   ├─ Validate signature
   ├─ Check expiration
   └─ Fetch object from R2
   │
   ▼
Cloudflare R2 Bucket
digital-products
   │
   ▼
File streamed to user


---

## 2. Prerequisites

Before beginning, confirm the following are available:

• Cloudflare account
• Domain managed by Cloudflare
• Node.js installed (will be working in Typescript)
• Wrangler CLI installed

Install Wrangler:

bash
```
npm install -g wrangler
```

Verify installation:

bash
```
wrangler --version
```

create .gitignore 

---

## 3. Create the R2 Bucket

Navigate to:

**Cloudflare Dashboard → R2 Object Storage**

Create a bucket.

Example bucket:

> digital-products

Upload the ebook or digital file.

Example object key:

> usd-ebook-one.pdf

The object key is what the Worker will retrieve.

---

## 4. Create the Worker

Initialize the Worker project:

bash
```
npm create cloudflare@latest pub-worker
```

Choose:

> Hello World example
> TypeScript
> Deploy later

Navigate into the project:

bash
```
cd pub-worker
```

---

## 5. Configure Worker to Access R2

Open file:
> wrangler.jsonc

Add the R2 binding:

json
```
{
  "name": "pub-worker",
  "main": "src/index.ts",
  "compatibility_date": "2026-03-03",

  "r2_buckets": [
    {
      "binding": "PRODUCTS",
      "bucket_name": "digital-products"
    }
  ]
}
```

---

## 6. Worker Download Endpoint

Edit File:
> src/index.ts


Example Worker implementation:
ts
```
export interface Env {
  PRODUCTS: R2Bucket
  DOWNLOAD_SECRET: string
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {

    const url = new URL(request.url)

    if (url.pathname !== "/dl") {
      return new Response("Not found", { status: 404 })
    }

    const key = url.searchParams.get("key")
    const exp = url.searchParams.get("exp")
    const sig = url.searchParams.get("sig")

    if (!key || !exp || !sig) {
      return new Response("Missing parameters", { status: 400 })
    }

    const now = Math.floor(Date.now() / 1000)

    if (now > Number(exp)) {
      return new Response("Link expired", { status: 403 })
    }

    const msg = `${key}.${exp}`

    const enc = new TextEncoder()

    const cryptoKey = await crypto.subtle.importKey(
      "raw",
      enc.encode(env.DOWNLOAD_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    )

    const signature = await crypto.subtle.sign(
      "HMAC",
      cryptoKey,
      enc.encode(msg)
    )

    const expected = Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, "0"))
      .join("")

    if (expected !== sig) {
      return new Response("Invalid signature", { status: 403 })
    }

    const object = await env.PRODUCTS.get(key)

    if (!object) {
      return new Response("File not found", { status: 404 })
    }

    return new Response(object.body, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${key}"`
      }
    })
  }
}
```

---

## 7. Store Worker Secret

The Worker requires a secret used to validate download links.

Set it using Wrangler:


bash
```
wrangler secret put DOWNLOAD_SECRET
```

Use the **same secret** as the backend application.

---

## 8. Deploy the Worker

Deploy the Worker:


bash
```
npm run deploy
```

Example deployment URL:
> https://pub-worker.account.workers.dev (**<- update if different**)

---

## 9. Attach Worker to Custom Domain

Cloudflare Dashboard → Workers → Triggers.

Attach domain:
> ebooks.unschooldiscoveries.com/*

Now the download endpoint becomes:
> https://ebooks.unschooldiscoveries.com/dl

---

## 10. Testing the Worker

Create a signed test link.

Example script:


bash
```
node sign.js
```

Example generated link:
> https://ebooks.unschooldiscoveries.com/dl?key=usd-ebook-one.pdf&exp=1700000000&sig=abcdef123456


Open in browser.

Expected result:

• File download begins
• Worker logs show request

---

## 11. Validation Tests

Confirm the Worker correctly blocks invalid requests.

### Missing parameters
> /dl

Expected:
> 400 Missing parameters

---

### Invalid signature

> /dl?key=usd-ebook-one.pdf&exp=1700000000&sig=bad

Expected:
> 403 Invalid signature

---

### Expired link

>/dl?key=usd-ebook-one.pdf&exp=old_timestamp

Expected:

> 403 Link expired

---

## 12. Security Model

The Worker ensures:

• R2 bucket is never public
• Download links expire
• Links cannot be forged without secret

All file access must pass through the Worker.

---

## 13. Production Checklist

Before enabling downloads:

✓ Worker deployed
✓ R2 bucket created
✓ Object uploaded
✓ Worker secret configured
✓ Domain route attached
✓ Signed link verified

---

## 14. Troubleshooting

### File not downloading

Check:

• object key correct
• bucket binding configured

---

### Invalid signature errors

Verify:

• Worker secret matches backend secret
• link signing logic correct

---

### 404 file not found

Confirm file exists in bucket:
> digital-products/usd-ebook-one.pdf

---

# 15. Final Download Flow

Backend generates signed link
        │
        ▼
Customer receives email
        │
        ▼
Customer clicks link
        │
        ▼
Worker validates request
        │
        ▼
R2 streams file

--- 

This completes the **secure digital delivery pipeline**.
