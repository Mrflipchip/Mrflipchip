#!/usr/bin/env python3
import argparse
import json
import os
import sys
import anthropic

from ph_contacts import CONTACTS
from bank_research import research_bank
from aflathrive_template import generate_email
from titan_client import send_email
from onepager_bridge import render_onepager

CONFIG_PATH = os.path.expanduser("~/.outreach_config.json")


def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    cfg.setdefault("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    return cfg


def log_to_airtable(cfg, contact, status):
    try:
        from pyairtable import Api
        api = Api(cfg["airtable_api_key"])
        table = api.table(cfg["airtable_base_id"], cfg["airtable_table_name"])
        table.create({"Name": contact["name"], "Email": contact["email"],
                      "Bank": contact["bank"], "Role": contact["role"],
                      "Status": status, "Country": "Philippines"})
    except Exception as e:
        print(f"  [Airtable] Could not log: {e}")


def run(dry_run, bank_filter, test_address):
    cfg = load_config()
    if not cfg["anthropic_api_key"]:
        sys.exit("Missing ANTHROPIC_API_KEY.")

    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])
    contacts = CONTACTS
    if bank_filter:
        contacts = [c for c in contacts if bank_filter.lower() in c["bank"].lower()]
        if not contacts:
            sys.exit(f"No contacts found matching bank '{bank_filter}'")

    profile_cache = {}

    for i, contact in enumerate(contacts, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(contacts)}] {contact['name']} — {contact['role']} @ {contact['bank']}")
        print(f"  Email: {contact['email']}")

        bank = contact["bank"]
        if bank not in profile_cache:
            print(f"  Researching {bank}...")
            profile_cache[bank] = research_bank(bank, client)

        profile = profile_cache[bank]

        try:
            subject, body_plain, body_html = generate_email(contact, profile)
        except ValueError as e:
            print(f"  SKIPPED — {e}")
            continue

        print(f"\n  SUBJECT: {subject}")
        print(f"\n{'-'*40}")
        print(body_plain)
        print(f"{'-'*40}")

        if dry_run:
            print("  [DRY RUN] Not sending.")
            continue

        pdf_path = None
        try:
            pdf_path = render_onepager(bank, contact["name"])
            print(f"  One-pager: {pdf_path}")
        except Exception as e:
            print(f"  One-pager error: {e} — sending without attachment")

        choice = input("\n  Send? [y / n / skip] ").strip().lower()
        if choice != "y":
            print("  Skipped.")
            continue

        to = test_address or contact["email"]
        try:
            send_email(to_address=to, subject=subject, body_plain=body_plain, body_html=body_html,
                       from_name="Julian Coulbert | AflaThrive",
                       attachments=[pdf_path] if pdf_path else None)
            print(f"  Sent to {to}")
            if cfg.get("airtable_api_key"):
                log_to_airtable(cfg, contact, "Sent")
        except Exception as e:
            print(f"  SEND FAILED: {e}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--bank")
    p.add_argument("--test-address")
    args = p.parse_args()
    run(dry_run=args.dry_run, bank_filter=args.bank, test_address=args.test_address)


if __name__ == "__main__":
    main()
