#!/usr/bin/env python3
"""
titan_agent.py — cold outreach email agent (Titan SMTP).

Commands:
  setup   Prompt for titan_email + titan_password and save to config.
  send    Collect recipient details, generate an email, preview it,
          then Send / No / Edit. On send: delivers via Titan SMTP and
          logs the attempt to Airtable.

Examples:
  python titan_agent.py setup
  python titan_agent.py send
  python titan_agent.py send --name "Dorai" --bank "QIB" --role "Head of Retail" \
      --email "dorai@qib.com.qa" --location "Doha, Qatar"

This agent uses the existing generate_email() / log_outreach() interfaces
in template.py and airtable_client.py unchanged.
"""
from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
import tempfile

from config import load_config, save_config, CONFIG_PATH
from aflathrive_template import generate_email
from titan_client import send_email
from airtable_client import log_outreach


# --------------------------------------------------------------------------- #
# setup
# --------------------------------------------------------------------------- #
def cmd_setup(_args: argparse.Namespace) -> None:
    print("Titan email setup")
    print("-----------------")
    config = load_config()

    email = input("Titan email address: ").strip()
    if not email:
        print("No email entered. Aborting.")
        sys.exit(1)

    password = getpass.getpass("Titan password (input hidden): ").strip()
    if not password:
        print("No password entered. Aborting.")
        sys.exit(1)

    config["titan_email"] = email
    config["titan_password"] = password
    save_config(config)
    print(f"\nSaved Titan credentials to {CONFIG_PATH}")


# --------------------------------------------------------------------------- #
# send
# --------------------------------------------------------------------------- #
def _prompt(label: str, provided: str | None = None) -> str:
    if provided:
        return provided.strip()
    return input(f"{label}: ").strip()


def _plain_to_html(body_plain: str) -> str:
    """Rebuild a simple HTML body after a manual edit of the plain text."""
    blocks = [b.strip() for b in body_plain.split("\n\n") if b.strip()]
    paras = "\n".join(
        "<p>{}</p>".format(b.replace("\n", "<br>")) for b in blocks
    )
    return (
        '<!DOCTYPE html>\n<html>\n<body style="font-family: Georgia, serif; '
        'font-size: 15px; line-height: 1.7; color: #1a1a1a; max-width: 620px; '
        'margin: 0 auto; padding: 20px;">\n'
        f"{paras}\n</body>\n</html>"
    )


def _edit(subject: str, body_plain: str) -> tuple[str, str, str]:
    """Open subject + body in $EDITOR; return (subject, body_plain, body_html)."""
    editor = os.environ.get("EDITOR", "nano")
    header = (
        "# First line = Subject. Everything below the blank line = body.\n"
        "# Lines starting with '#' are ignored.\n"
    )
    initial = f"{header}Subject: {subject}\n\n{body_plain}\n"

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(initial)
        path = tf.name

    try:
        subprocess.call([editor, path])
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if not ln.startswith("#")]
    finally:
        os.unlink(path)

    # Pull the subject line, then the remaining body.
    new_subject = subject
    body_lines: list[str] = []
    seen_subject = False
    for ln in lines:
        if not seen_subject and ln.lower().startswith("subject:"):
            new_subject = ln.split(":", 1)[1].strip() or subject
            seen_subject = True
            continue
        body_lines.append(ln)

    new_plain = "\n".join(body_lines).strip("\n")
    return new_subject, new_plain, _plain_to_html(new_plain)


def _preview(to_email: str, subject: str, body_plain: str) -> None:
    print("\n" + "=" * 68)
    print(f"To:      {to_email}")
    print(f"Subject: {subject}")
    print("-" * 68)
    print(body_plain)
    print("=" * 68 + "\n")


def cmd_send(args: argparse.Namespace) -> None:
    name = _prompt("Recipient name", args.name)
    bank = _prompt("Bank / company", args.bank)
    role = _prompt("Role / title", args.role)
    email = _prompt("Email address", args.email)
    website = _prompt("Website", args.website)
    location = _prompt("Location", args.location)
    product = _prompt(f"Youth product name [default: {bank} Junior]", args.product)
    regulator = _prompt("Financial regulator (e.g. the Qatar Central Bank)", args.regulator)
    regulator_abbr = _prompt("Regulator short form (e.g. the QCB, optional)", args.regulator_abbr)
    blurb = _prompt("Opening line (optional, Enter to auto-generate)", args.blurb)

    if not (name and bank and email):
        print("Recipient name, bank, and email are required. Aborting.")
        sys.exit(1)

    inputs = {
        "company_name": bank,
        "founder_name": name,
        "company_location": location,
        "product": product,
        "regulator": regulator,
        "regulator_abbr": regulator_abbr,
        "opening": blurb,
    }

    result = generate_email(inputs)
    subject = result["subject"]
    body_plain = result["body_plain"]
    body_html = result["body_html"]

    while True:
        _preview(email, subject, body_plain)
        choice = input("[S]end / [N]o / [E]dit? ").strip().lower()

        if choice in ("s", "send"):
            print("\nSending via Titan...")
            send_email(email, subject, body_plain, body_html, from_name="Julian Coulbert")
            print(f"Sent to {email}.")

            log_outreach(
                company_name=bank,
                founder_name=name,
                founder_email=email,
                sector=role,
                subject_line=subject,
                status="sent",
                notes=f"website: {website}" if website else "",
            )
            return

        if choice in ("n", "no"):
            print("Not sent. Aborting.")
            return

        if choice in ("e", "edit"):
            subject, body_plain, body_html = _edit(subject, body_plain)
            continue

        print("Please answer S, N, or E.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Titan cold outreach email agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Save Titan email + password to config.")

    send = sub.add_parser("send", help="Compose, preview, and send an outreach email.")
    send.add_argument("--name", help="Recipient name (skips prompt).")
    send.add_argument("--bank", help="Bank / company (skips prompt).")
    send.add_argument("--role", help="Role / title (skips prompt).")
    send.add_argument("--email", help="Recipient email address (skips prompt).")
    send.add_argument("--location", help="Company location (skips prompt).")
    send.add_argument("--website", help="Company website (skips prompt).")
    send.add_argument("--product", help="Youth product name (default: '<bank> Junior').")
    send.add_argument("--regulator", help="Financial regulator, e.g. 'the Qatar Central Bank'.")
    send.add_argument("--regulator-abbr", dest="regulator_abbr",
                      help="Regulator short form, e.g. 'the QCB'.")
    send.add_argument("--blurb", help="Custom opening line (skips prompt; else auto-generated).")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "send":
        cmd_send(args)


if __name__ == "__main__":
    main()
