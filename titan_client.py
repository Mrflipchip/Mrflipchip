import json
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.titan.email"
SMTP_PORT = 587
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

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(titan_email, titan_password)
        server.sendmail(titan_email, to_address, msg.as_string())
