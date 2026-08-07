#!/usr/bin/env python3
"""
AflaThrive outreach pipeline.

Usage:
  python send_pipeline.py                        # interactive menu
  python send_pipeline.py --dry-run              # preview emails, nothing sends
  python send_pipeline.py --bank "BDO"           # filter to one bank
  python send_pipeline.py --banks "Metrobank,RCBC"
  python send_pipeline.py --auto-confirm --test-address you@example.com
  python send_pipeline.py --contacts other.csv   # use a different contacts file
  python send_pipeline.py --from-queue           # process the overflow queue

Requires env vars (or ~/.outreach_config.json):
  TITAN_EMAIL, TITAN_PASSWORD, ANTHROPIC_API_KEY
  AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME (optional)
  daily_limit (optional, default 480)
"""

import argparse
import csv
import json
import os
import sys
from datetime import date

import anthropic

from ph_contacts import load_contacts
from bank_research import research_org
from aflathrive_template import generate_email
from titan_client import send_email
from onepager_bridge import render_onepager

CONFIG_PATH = os.path.expanduser("~/.outreach_config.json")
SEND_LOG_PATH = os.path.expanduser("~/.outreach_send_log.json")
QUEUE_CSV = os.path.join(os.path.dirname(__file__), "queue.csv")
DEFAULT_TEST_ADDRESS = "julian.coul@gmail.com"
DAILY_LIMIT_DEFAULT = 480

CONTACTS_FIELDNAMES = ["bank", "name", "first_name", "role", "email", "bank_type", "country", "org_type"]
QUEUE_FIELDNAMES = CONTACTS_FIELDNAMES + ["scheduled_for"]


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    cfg.setdefault("titan_email", os.environ.get("TITAN_EMAIL", ""))
    cfg.setdefault("titan_password", os.environ.get("TITAN_PASSWORD", ""))
    cfg.setdefault("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
    return cfg


# ── Daily send tracking ───────────────────────────────────────────────────────

def _load_send_log() -> dict:
    if os.path.exists(SEND_LOG_PATH):
        with open(SEND_LOG_PATH) as f:
            return json.load(f)
    return {}


def _save_send_log(log: dict) -> None:
    with open(SEND_LOG_PATH, "w") as f:
        json.dump(log, f)


def get_today_count() -> int:
    today = str(date.today())
    return _load_send_log().get(today, 0)


def increment_send_count() -> int:
    today = str(date.today())
    log = _load_send_log()
    log = {k: v for k, v in log.items() if k == today}  # drop old dates
    log[today] = log.get(today, 0) + 1
    _save_send_log(log)
    return log[today]


# ── Queue ──────────────────────────────────────────────────────────────────────

def save_to_queue(contacts: list[dict]) -> None:
    from datetime import date, timedelta
    tomorrow = str(date.today() + timedelta(days=1))
    file_exists = os.path.exists(QUEUE_CSV)
    with open(QUEUE_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for c in contacts:
            row = {k: c.get(k, "") for k in CONTACTS_FIELDNAMES}
            row["scheduled_for"] = tomorrow
            writer.writerow(row)
    print(f"\n  {len(contacts)} contact(s) queued for {tomorrow} in queue.csv")


def load_queue() -> list[dict]:
    if not os.path.exists(QUEUE_CSV):
        return []
    with open(QUEUE_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def clear_queue() -> None:
    if os.path.exists(QUEUE_CSV):
        os.remove(QUEUE_CSV)


# ── Airtable logging ──────────────────────────────────────────────────────────

def log_to_airtable(cfg: dict, contact: dict, status: str):
    try:
        from pyairtable import Api
        api = Api(cfg["airtable_api_key"])
        table = api.table(cfg["airtable_base_id"], cfg["airtable_table_name"])
        table.create({
            "Name": contact["name"],
            "Email": contact["email"],
            "Bank": contact["bank"],
            "Role": contact["role"],
            "Status": status,
            "Country": contact.get("country", ""),
        })
    except Exception as e:
        print(f"  [Airtable] Could not log: {e}")


# ── Menu ──────────────────────────────────────────────────────────────────────

def show_menu(has_queue: bool = False) -> tuple[bool, str | None, str | None, bool]:
    """Returns (dry_run, test_address, banks_filter, from_queue)."""
    print("\nAflaThrive Outreach Pipeline")
    print("=" * 40)
    opts = [
        "Dry run       — preview all emails, nothing sends",
        "Test send     — all emails go to your address",
        "Live send     — send to real contacts",
        "Filter banks  — pick specific banks, then send live",
    ]
    if has_queue:
        opts.append("Send queue    — process overflow queue from yesterday")
    opts.append("Quit")

    for i, o in enumerate(opts, 1):
        print(f"  {i}. {o}")
    print()

    max_choice = len(opts)
    while True:
        raw = input(f"  Choose [1-{max_choice}]: ").strip()
        if not raw.isdigit() or not (1 <= int(raw) <= max_choice):
            print(f"  Please enter a number between 1 and {max_choice}.")
            continue
        choice = int(raw)

        if choice == 1:
            return True, None, None, False
        elif choice == 2:
            return False, DEFAULT_TEST_ADDRESS, None, False
        elif choice == 3:
            confirm = input("  Send to real contacts? Type YES to confirm: ").strip()
            if confirm == "YES":
                return False, None, None, False
            print("  Cancelled.")
            return show_menu(has_queue)
        elif choice == 4:
            banks = input("  Banks (comma-separated, e.g. BDO,RCBC): ").strip()
            return False, None, banks, False
        elif has_queue and choice == 5:
            return False, None, None, True
        elif choice == max_choice:
            sys.exit(0)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run(
    dry_run: bool,
    bank_filter: str | None,
    banks_filter: str | None,
    test_address: str | None,
    auto_confirm: bool,
    contacts_file: str | None,
    from_queue: bool = False,
    live: bool = False,
):
    cfg = load_config()

    if not cfg["anthropic_api_key"]:
        sys.exit("Missing ANTHROPIC_API_KEY.")

    if auto_confirm and not test_address:
        sys.exit("--auto-confirm requires --test-address for safety.")

    daily_limit = int(cfg.get("daily_limit", DAILY_LIMIT_DEFAULT))
    has_queue = os.path.exists(QUEUE_CSV)

    # Interactive menu when no flags given
    if not any([dry_run, bank_filter, banks_filter, test_address, auto_confirm, live, from_queue, contacts_file]):
        dry_run, test_address, banks_filter, from_queue = show_menu(has_queue)

    # --live skips menu and sends to real contacts immediately
    if live:
        test_address = None

    # Prompt about queue if it exists and user didn't explicitly handle it
    if has_queue and not from_queue and not dry_run:
        queue = load_queue()
        ans = input(f"\n  queue.csv has {len(queue)} contact(s) from a previous run. Process queue first? [y/N]: ").strip().lower()
        if ans == "y":
            from_queue = True

    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])

    if from_queue:
        contacts = load_queue()
        if not contacts:
            print("  Queue is empty.")
            return
        print(f"\n  Processing {len(contacts)} queued contact(s)...")
    elif contacts_file:
        contacts = load_contacts(contacts_file)
    else:
        contacts = load_contacts()

    if banks_filter and not from_queue:
        names = [b.strip().lower() for b in banks_filter.split(",")]
        contacts = [c for c in contacts if any(n in c["bank"].lower() for n in names)]
        if not contacts:
            sys.exit(f"No contacts found matching banks '{banks_filter}'")
    elif bank_filter and not from_queue:
        contacts = [c for c in contacts if bank_filter.lower() in c["bank"].lower()]
        if not contacts:
            sys.exit(f"No contacts found matching bank '{bank_filter}'")

    profile_cache = {}
    sent_today = get_today_count()
    queued_overflow = []

    for i, contact in enumerate(contacts):
        # Daily limit check (skip in dry run or test mode)
        if not dry_run and not test_address and sent_today >= daily_limit:
            print(f"\n  Daily limit of {daily_limit} reached ({sent_today} sent today).")
            queued_overflow = contacts[i:]
            break

        idx = i + 1
        print(f"\n{'='*60}")
        print(f"[{idx}/{len(contacts)}] {contact['name']} — {contact['role']} @ {contact['bank']}")
        print(f"  Email: {contact['email']}")

        org = contact["bank"]
        org_type = contact.get("org_type", "bank")

        if org not in profile_cache:
            print(f"  Researching {org}...")
            profile_cache[org] = research_org(org, org_type, contact.get("country", "Philippines"), client)

        profile = profile_cache[org]

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
            pdf_path = render_onepager(org, contact["name"])
            print(f"  One-pager: {pdf_path}")
        except NotImplementedError:
            print("  One-pager: skipped (onepager_bridge.py not wired yet)")
        except Exception as e:
            print(f"  One-pager error: {e} — sending without attachment")

        if auto_confirm:
            choice = "1"
        else:
            print()
            print("  1. Send")
            print("  2. Skip")
            print("  3. Quit")
            choice = input("  Choose [1-3]: ").strip()

        if choice == "3":
            print("  Stopping pipeline.")
            queued_overflow = contacts[i + 1:]
            break
        if choice != "1":
            print("  Skipped.")
            continue

        to = test_address or contact["email"]
        try:
            send_email(
                to_address=to,
                subject=subject,
                body_plain=body_plain,
                body_html=body_html,
                from_name="Julian Coulbert | AflaThrive",
                attachments=[pdf_path] if pdf_path else None,
            )
            print(f"  Sent to {to}")
            if not test_address:
                sent_today = increment_send_count()
            if cfg.get("airtable_api_key"):
                log_to_airtable(cfg, contact, "Sent")
        except Exception as e:
            print(f"  SEND FAILED: {e}")

    if queued_overflow:
        save_to_queue(queued_overflow)

    if from_queue and not queued_overflow:
        clear_queue()
        print("\n  Queue processed and cleared.")

    remaining = daily_limit - get_today_count()
    if not dry_run and not test_address:
        print(f"\n  Today: {get_today_count()} sent, {max(0, remaining)} remaining before daily limit.")


def main():
    parser = argparse.ArgumentParser(description="AflaThrive outreach pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview emails without sending")
    parser.add_argument("--bank", help="Filter to contacts at a specific bank")
    parser.add_argument("--banks", help="Comma-separated list of banks")
    parser.add_argument("--test-address", help="Override recipient — send everything to this address")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip prompts (requires --test-address)")
    parser.add_argument("--live", action="store_true", help="Send to real contacts immediately, no menu")
    parser.add_argument("--contacts", help="Path to a contacts CSV file (default: contacts.csv)")
    parser.add_argument("--from-queue", action="store_true", help="Process the overflow queue")
    args = parser.parse_args()
    run(
        dry_run=args.dry_run,
        bank_filter=args.bank,
        banks_filter=args.banks,
        test_address=args.test_address,
        auto_confirm=args.auto_confirm,
        live=args.live,
        contacts_file=args.contacts,
        from_queue=args.from_queue,
    )


if __name__ == "__main__":
    main()
