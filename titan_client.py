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
CONFIG_PATH = os.path.expanduser("~/.outreach_config.json")


def _creds():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    email = os.environ.get("TITAN_EMAIL") or cfg.get("titan_email", "")
    password = os.environ.get("TITAN_PASSWORD") or cfg.get("titan_password", "")
    if not email or not password:
        raise RuntimeError(
            "Titan credentials not found. Set TITAN_EMAIL / TITAN_PASSWORD env vars "
            "or add titan_email / titan_password to ~/.outreach_config.json"
        )
    return email, password


def _save_to_sent(titan_email, titan_password, raw_message):
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(titan_email, titan_password)
            for folder in ("Sent", "Sent Items", "Sent Messages", "INBOX.Sent"):
                try:
                    imap.append(folder, "\\Seen", imaplib.Time2Internaldate(time.time()), raw_message.encode("utf-8"))
                    return
                except Exception:
                    continue
    except Exception as e:
        print(f"  [Sent folder] Could not save copy: {e}")


def send_email(to_address, subject, body_plain, body_html, from_name="AflaThrive", attachments=None):
    titan_email, titan_password = _creds()

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{titan_email}>"
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

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(titan_email, titan_password)
        server.sendmail(titan_email, to_address, raw)

    _save_to_sent(titan_email, titan_password, raw)
