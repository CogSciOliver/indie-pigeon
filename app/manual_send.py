import os
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from pathlib import Path

from .r2 import make_cf_download_url
from .emailer import send_ebook_email

@router.get("/favicon.ico")
def favicon():
    return FileResponse(Path(__file__).parent / "favicon.ico")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def manual_send_form():
    return """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Manual Ebook Send</title>
<link rel="icon" href="/favicon.ico">
<style>
body {
  font-family: Arial, sans-serif;
  max-width: 600px;
  margin: 40px auto;
  padding: 20px;
}
input, button {
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  font-size: 16px;
}
button {
  cursor: pointer;
}
</style>
</head>
<body>

<h2>Manual Ebook Send</h2>

<form method="post" action="/manual-send">
  <input type="password" name="password" placeholder="Password" required />
  <input type="email" name="buyer_email" placeholder="Customer Email" required />
  <input type="text" name="product_key" value="usd-ebook-one.pdf" required />
  <button type="submit">Send Download Email</button>
</form>

</body>
</html>
"""


@router.post("/manual-send", response_class=HTMLResponse)
def manual_send(
    password: str = Form(...),
    buyer_email: str = Form(...),
    product_key: str = Form(...)
):

    if password != os.environ["MANUAL_SEND_PASSWORD"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    download_url = make_cf_download_url(product_key)

    subject = "Your Unschool Discoveries ebook download"

    body = f"""
Thanks for your purchase!

Download your ebook here:

{download_url}

If you have trouble accessing the file, reply to this email.
"""

    provider_id = send_ebook_email(buyer_email, subject, body)

    return f"""
<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body>
<h2>Email sent</h2>
<p>Sent to: <strong>{buyer_email}</strong></p>
<p>Provider ID: {provider_id}</p>
<p><a href="/">Send another</a></p>
</body>
</html>
"""