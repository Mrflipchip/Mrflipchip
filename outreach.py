#!/usr/bin/env python3
"""
outreach.py — Julian Coulbert's cold outreach automation CLI.

Commands:
  send      Generate a draft, log to Airtable, and optionally send via Gmail.
  research  AI-research a company then pipe into the send flow.
  status    Show recent outreach attempts from Airtable.
  setup     (Re-)run the credential configuration wizard.

Usage:
  python outreach.py send
  python outreach.py research
  python outreach.py status
  python outreach.py setup
"""

import os
import sys
from datetime import date
from pathlib import Path

import click

DRAFTS_DIR = Path(__file__).parent / "drafts"


def _save_draft(company_name: str, subject: str, body_plain: str) -> Path:
    DRAFTS_DIR.mkdir(exist_ok=True)
    safe_name = company_name.lower().replace(" ", "_")
    filename = DRAFTS_DIR / f"{safe_name}_{date.today()}.txt"
    with open(filename, "w") as f:
        f.write(f"Subject: {subject}\n")
        f.write("=" * 60 + "\n\n")
        f.write(body_plain)
    return filename


def _print_draft(subject: str, body_plain: str) -> None:
    print("\n" + "=" * 60)
    print("DRAFT EMAIL")
    print("=" * 60)
    print(f"Subject: {subject}")
    print("-" * 60)
    print(body_plain)
    print("=" * 60 + "\n")


def _collect_inputs_manually() -> dict:
    """Prompt the user for all send-flow inputs interactively."""
    print("\nEnter details for the outreach email.\n")

    def ask(label: str, required: bool = True) -> str:
        while True:
            val = input(f"{label}: ").strip()
            if val or not required:
                return val
            print("  This field is required.")

    company_name  = ask("Company name")
    founder_name  = ask("Founder full name")
    founder_first = ask("Founder first name (for greeting)")
    founder_email = ask("Founder email")
    sector        = ask("Sector / industry")
    funding       = ask("Recent funding details (e.g. '$15M Series A, March 2024')", required=False)
    recent_fact   = ask("One specific recent fact about the company")
    why_now       = ask("Why is this the right moment to reach out?")

    return {
        "company_name":    company_name,
        "founder_name":    founder_name,
        "founder_first":   founder_first,
        "founder_email":   founder_email,
        "sector":          sector,
        "funding_details": funding,
        "recent_fact":     recent_fact,
        "why_now":         why_now,
    }


def _run_send_flow(inputs: dict) -> None:
    """
    Core send flow: generate → review → save draft → Airtable → Gmail.
    Shared between `send` and `research` commands.
    """
    from template import generate_email, suggest_subject
    from airtable_client import log_outreach, update_status

    email = generate_email(inputs)

    _print_draft(email["subject"], email["body_plain"])
    print(f"Suggested subject: {email['subject']}")
    override = input("Press Enter to keep this subject, or type a new one: ").strip()
    if override:
        email["subject"] = override
        inputs["subject_override"] = override

    draft_path = _save_draft(
        inputs["company_name"], email["subject"], email["body_plain"]
    )
    print(f"\nDraft saved: {draft_path}")

    airtable_record_id = None
    log_choice = input("\nLog this to Airtable? [y/N]: ").strip().lower()
    if log_choice == "y":
        airtable_record_id = log_outreach(
            company_name=inputs["company_name"],
            founder_name=inputs["founder_name"],
            founder_email=inputs["founder_email"],
            sector=inputs.get("sector", ""),
            subject_line=email["subject"],
            status="drafted",
        )

    send_choice = input("\nSend this email now via Gmail? [y/N]: ").strip().lower()
    if send_choice == "y":
        import gmail_client
        print("\nConnecting to Gmail...")
        service = gmail_client.authenticate()

        print("\n" + "=" * 60)
        print("FINAL REVIEW — about to send:")
        print(f"  To:      {inputs['founder_email']}")
        print(f"  Subject: {email['subject']}")
        print("=" * 60)
        confirm = input("Confirm send? Type 'yes' to proceed: ").strip().lower()

        if confirm == "yes":
            success = gmail_client.send_email(
                service=service,
                to=inputs["founder_email"],
                subject=email["subject"],
                body_plain=email["body_plain"],
                body_html=email["body_html"],
            )
            if success and airtable_record_id:
                update_status(airtable_record_id, "sent")
        else:
            print("Send cancelled.")
    else:
        print("Email not sent. Draft saved for manual review.")

    print("\nDone.\n")


@click.group()
def cli():
    """Julian Coulbert's cold outreach automation tool."""
    pass


@cli.command()
def send():
    """Manually enter company details and generate + send an outreach email."""
    from config import setup_wizard
    setup_wizard(keys_needed=["airtable_api_key", "airtable_base_id",
                               "airtable_table_name", "gmail_credentials_path"])
    inputs = _collect_inputs_manually()
    _run_send_flow(inputs)


@cli.command()
def research():
    """AI-research a company (web search), review results, then send."""
    from config import setup_wizard
    from research import (
        run_research, discover_companies, display_and_confirm, research_to_send_inputs
    )

    setup_wizard(keys_needed=["anthropic_api_key"])

    company_name = input("\nCompany name to research (press Enter to discover options): ").strip()

    if not company_name:
        specific = input("Do you have a specific company in mind? [y/N]: ").strip().lower()

        if specific == "y":
            company_name = input("Company name: ").strip()
            if not company_name:
                print("Company name is required.")
                sys.exit(1)
            sector = input("Sector / industry: ").strip()
        else:
            sector_hint = input("Any sector preference? (press Enter to skip): ").strip()
            suggestions = discover_companies(sector_hint)

            print("\n" + "=" * 60)
            print("COMPANY SUGGESTIONS")
            print("=" * 60)
            for i, s in enumerate(suggestions, 1):
                print(f"\n  {i}. {s.get('company_name')}  —  {s.get('company_location')}")
                print(f"     {s.get('sector')}")
                print(f"     {s.get('what_they_do')}")
                print(f"     Why Julian: {s.get('why_julian')}")
            print("\n" + "=" * 60)

            while True:
                choice = input("\nSelect a company [1-5]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                    chosen = suggestions[int(choice) - 1]
                    company_name = chosen["company_name"]
                    sector = chosen.get("sector", "")
                    print(f"\nSelected: {company_name}\n")
                    break
                print(f"  Please enter a number between 1 and {len(suggestions)}.")
    else:
        sector = input("Sector / industry: ").strip()

    raw_data = run_research(company_name, sector)
    confirmed_data = display_and_confirm(raw_data)
    inputs = research_to_send_inputs(confirmed_data)

    print("\n" + "-" * 60)
    print("Confirmed inputs for email generation:")
    for k, v in inputs.items():
        if v:
            print(f"  {k:<20} {v}")
    print("-" * 60)
    proceed = input("\nGenerate email with these inputs? [Y/n]: ").strip().lower()
    if proceed == "n":
        print("Aborted.")
        sys.exit(0)

    setup_wizard(keys_needed=["airtable_api_key", "airtable_base_id",
                               "airtable_table_name", "gmail_credentials_path"])
    _run_send_flow(inputs)


@cli.command()
@click.option("--limit", default=10, help="Number of recent records to show.")
def status(limit):
    """Show recent outreach attempts from Airtable."""
    from airtable_client import list_recent

    records = list_recent(limit=limit)
    if not records:
        print("No records found (or Airtable not yet configured).")
        return

    print(f"\n{'Company':<20} {'Founder':<20} {'Status':<16} {'Date':<12} Subject")
    print("-" * 100)
    for rec in records:
        f = rec.get("fields", {})
        print(
            f"{f.get('Company',''):<20} "
            f"{f.get('Founder Name',''):<20} "
            f"{f.get('Status',''):<16} "
            f"{f.get('Date Sent',''):<12} "
            f"{f.get('Subject Line','')}"
        )
    print()


@cli.command()
def setup():
    """Configure or update API credentials (Airtable, Gmail, Anthropic)."""
    from config import CONFIG_PATH, REQUIRED_KEYS, load_config, save_config

    print(f"\nCredential setup. Config stored at: {CONFIG_PATH}\n")
    config = load_config()

    for key, label in REQUIRED_KEYS.items():
        current = config.get(key, "")
        masked = ("*" * 8 + current[-4:]) if len(current) > 4 else ("(not set)" if not current else current)
        print(f"  {label:<50} {masked}")

    print()
    print("Which credentials would you like to update?")
    print("  1. All missing credentials")
    print("  2. Airtable only")
    print("  3. Gmail only")
    print("  4. Anthropic API key only")
    print("  5. All (overwrite everything)")

    choice = input("\nChoice [1]: ").strip() or "1"

    from config import setup_wizard

    if choice == "1":
        setup_wizard()
    elif choice == "2":
        setup_wizard(keys_needed=["airtable_api_key", "airtable_base_id", "airtable_table_name"])
    elif choice == "3":
        setup_wizard(keys_needed=["gmail_credentials_path"])
    elif choice == "4":
        setup_wizard(keys_needed=["anthropic_api_key"])
    elif choice == "5":
        for key in REQUIRED_KEYS:
            config.pop(key, None)
        save_config(config)
        setup_wizard()
    else:
        print("Invalid choice.")

    print("\nSetup complete.\n")


if __name__ == "__main__":
    cli()
