"""
gmail_client.py — Gmail OAuth2 authentication and email sending.

Sending address: julian.coul@gmail.com
OAuth scope: https://www.googleapis.com/auth/gmail.send
"""

import base64
import json
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_config_value, load_gmail_token, save_gmail_token

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SENDER = "julian.coul@gmail.com"


def authenticate():
    """
    Run the OAuth2 flow (browser-based on first run).
    Caches the token in ~/.outreach_config.json for subsequent runs.
    Returns an authenticated Gmail API service object.
    """
    creds = None

    # Try to load a cached token
    token_data = load_gmail_token()
    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # If no valid credentials, run the flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_gmail_token(json.loads(creds.to_json()))
                print("Gmail token refreshed.")
            except Exception:
                creds = None

        if not creds or not creds.valid:
            credentials_path = get_config_value("gmail_credentials_path")
            if not credentials_path or not Path(credentials_path).exists():
                print(
                    "\nGmail credentials file not found.\n"
                    "Please:\n"
                    "  1. Go to https://console.cloud.google.com/\n"
                    "  2. Create an OAuth 2.0 Client ID (Desktop app)\n"
                    "  3. Download the credentials.json file\n"
                    "  4. Re-run: python outreach.py setup\n"
                )
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            save_gmail_token(json.loads(creds.to_json()))
            print("Gmail authorised and token cached.\n")

    return build("gmail", "v1", credentials=creds)


def send_email(service, to: str, subject: str, body_plain: str, body_html: str) -> bool:
    """
    Send an email via the Gmail API.
    Constructs a multipart/alternative message (plain + HTML).
    Returns True on success, False on failure.
    """
    message = MIMEMultipart("alternative")
    message["From"]    = SENDER
    message["To"]      = to
    message["Subject"] = subject

    part_plain = MIMEText(body_plain, "plain", "utf-8")
    part_html  = MIMEText(body_html,  "html",  "utf-8")

    message.attach(part_plain)
    message.attach(part_html)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
        print(f"\nEmail sent. Message ID: {sent['id']}")
        return True
    except HttpError as error:
        print(f"\nGmail API error: {error}")
        return False
