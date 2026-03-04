import os, smtplib
from email.message import EmailMessage
from pathlib import Path

def send_ebook_email(to_email: str, subject: str, body: str, attachment_path: str) -> str:
    msg = EmailMessage()
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    p = Path(attachment_path)
    data = p.read_bytes()
    # simple content type guess
    maintype = "application"
    subtype = "pdf" if p.suffix.lower() == ".pdf" else "octet-stream"
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pw = os.environ["SMTP_PASS"]

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pw)
        resp = s.send_message(msg)

    # SMTP send_message doesn't reliably give a provider message id; return something useful
    return f"smtp:{host}"