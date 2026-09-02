import imaplib
import json
import os
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtpout.secureserver.net"
SMTP_PORT = 587
IMAP_HOST = "imap.secureserver.net"
IMAP_PORT = 993
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
CONFIG_PATH = os.path.expanduser("~/.outreach_config.json")


def _creds():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)

    gmail_email = os.environ.get("GMAIL_EMAIL") or cfg.get("gmail_email", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD") or cfg.get("gmail_app_password", "")
    if gmail_email and gmail_password:
        return "gmail", gmail_email, gmail_password

    email = os.environ.get("TITAN_EMAIL") or cfg.get("titan_email", "")
    password = os.environ.get("TITAN_PASSWORD") or cfg.get("titan_password", "")
    if not email or not password:
        raise RuntimeError(
            "No email credentials found. Set TITAN_EMAIL / TITAN_PASSWORD or "
            "GMAIL_EMAIL / GMAIL_APP_PASSWORD env vars, or add titan_email / titan_password "
            "or gmail_email / gmail_app_password to ~/.outreach_config.json"
        )
    return "titan", email, password


def _save_to_sent(provider, email, password, raw_message):
    if provider == "gmail":
        imap_host, imap_port = GMAIL_IMAP_HOST, GMAIL_IMAP_PORT
        folders = ("[Gmail]/Sent Mail",)
    else:
        imap_host, imap_port = IMAP_HOST, IMAP_PORT
        folders = ("Sent", "Sent Items", "Sent Messages", "INBOX.Sent")
    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
            imap.login(email, password)
            for folder in folders:
                try:
                    imap.append(folder, "\\Seen", imaplib.Time2Internaldate(time.time()), raw_message.encode("utf-8"))
                    return
                except Exception:
                    continue
    except Exception as e:
        print(f"  [Sent folder] Could not save copy: {e}")


def send_email(to_address, subject, body_plain, body_html, from_name="AflaThrive", attachments=None):
    provider, email, password = _creds()

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{email}>"
    msg["To"] = to_address

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_plain, "plain"))
    alt.attach(MIMEText(body_html, "html"))
    msg.attach(alt)

    for path in attachments or []:
        if not path:
            continue
        with open(path, "rb") as f:
            pdf = MIMEApplication(f.read(), _subtype="pdf")
        pdf.add_header("Content-Disposition", "attachment", filename=os.path.basename(path))
        msg.attach(pdf)

    raw = msg.as_string()

    smtp_host, smtp_port = (GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) if provider == "gmail" else (SMTP_HOST, SMTP_PORT)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(email, password)
        server.sendmail(email, to_address, raw)

    _save_to_sent(provider, email, password, raw)
