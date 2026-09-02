#!/usr/bin/env python3
"""
AflaThrive contact enrichment wizard.

Run with no arguments for the interactive wizard:
  python enrich.py

Or with flags to skip steps:
  python enrich.py --type bank --country Philippines --orgs "PNB,Allied Bank" --candidates 2
  python enrich.py --type school --country Kenya --discover 20 --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import anthropic

from bank_research import discover_orgs
from send_pipeline import run as pipeline_run, load_config

CONTACTS_CSV = os.path.join(os.path.dirname(__file__), "contacts.csv")
FIELDNAMES = ["bank", "name", "first_name", "role", "email", "bank_type", "country", "org_type"]

CONFIG_PATH = os.path.expanduser("~/.outreach_config.json")

# ── Role definitions per org type ─────────────────────────────────────────────

ROLES = {
    "bank": [
        ("Foundation President / Executive Director", True),
        ("Chief Sustainability Officer", True),
        ("Head of Financial Inclusion / Financial Inclusion Director", True),
        ("Head of CSR (general)", False),
        ("Chief People Officer", False),
    ],
    "corporate": [
        ("Head of CSR / Chief Sustainability Officer", True),
        ("Chief People Officer / CHRO", True),
        ("Head of Learning & Development", True),
        ("Employee Financial Wellness Manager", False),
    ],
    "school": [
        ("Principal / Head of School / School Director", True),
        ("Director of Academic Programs / Curriculum Director", True),
        ("Dean of Student Affairs", False),
        ("Financial Literacy Coordinator", False),
    ],
}

BANK_TYPES = {
    "bank": "foundation",
    "corporate": "corporate",
    "school": "school",
}

COUNTRIES = [
    "Philippines", "Singapore", "Kenya",
    "Indonesia", "Nigeria",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)


def _pick(prompt: str, options: list[str], default: int = 1) -> str:
    for i, opt in enumerate(options, 1):
        marker = " (recommended)" if i == default else ""
        print(f"  {i}. {opt}{marker}")
    while True:
        raw = _input(f"\n{prompt} [{default}]: ") or str(default)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"  Enter a number between 1 and {len(options)}.")


def _toggle_roles(org_type: str) -> list[str]:
    role_list = ROLES[org_type]
    selected = {i + 1 for i, (_, default) in enumerate(role_list) if default}

    while True:
        print()
        for i, (role, _) in enumerate(role_list, 1):
            tick = "x" if i in selected else " "
            print(f"  [{tick}] {i}. {role}")
        print()
        raw = _input("  Toggle role numbers to change (e.g. 4,5), or press Enter to accept: ")
        if not raw:
            break
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                n = int(part)
                if 1 <= n <= len(role_list):
                    if n in selected:
                        selected.discard(n)
                    else:
                        selected.add(n)

    return [role_list[i - 1][0] for i in sorted(selected)]


def load_existing_emails() -> set[str]:
    if not os.path.exists(CONTACTS_CSV):
        return set()
    with open(CONTACTS_CSV, newline="", encoding="utf-8") as f:
        return {row["email"].lower() for row in csv.DictReader(f) if row.get("email")}


def append_to_csv(rows: list[dict]) -> None:
    file_exists = os.path.exists(CONTACTS_CSV)
    with open(CONTACTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def _print_table(rows: list[dict]) -> None:
    if not rows:
        return
    print()
    print(f"  {'#':<4} {'Organisation':<28} {'Name':<22} {'Role':<30} {'Email':<35} {'Conf'}")
    print("  " + "-" * 125)
    for i, r in enumerate(rows, 1):
        conf = r.get("email_confidence", "?")
        print(
            f"  {i:<4} {r.get('bank','')[:27]:<28} {r.get('name','')[:21]:<22} "
            f"{r.get('role','')[:29]:<30} {r.get('email','')[:34]:<35} {conf}"
        )


# ── Enrichment core ───────────────────────────────────────────────────────────

def enrich_orgs(
    orgs: list[str],
    org_type: str,
    country: str,
    roles: list[str],
    candidates: int,
    client: anthropic.Anthropic,
) -> list[dict]:
    """
    For each org, find up to `candidates` named contacts via web research.
    Does NOT call research_org() here — that happens at send time in send_pipeline.py.
    """
    existing = load_existing_emails()
    found = []
    role_hint = ", ".join(roles)

    for i, org in enumerate(orgs, 1):
        print(f"\n  [{i}/{len(orgs)}] {org}")
        slots_found = 0

        for slot in range(candidates):
            contact = _find_contact(org, org_type, country, role_hint, slot, client)

            if not contact or not contact.get("name"):
                print(f"    Slot {slot + 1}: could not find a named contact.")
                break

            name = contact.get("name", "")
            role = contact.get("role", "")
            email = contact.get("email", "")
            confidence = contact.get("email_confidence", "low")

            if not email:
                print(f"    Slot {slot + 1}: {name} found but no email constructed.")
                continue

            if email.lower() in existing:
                print(f"    Slot {slot + 1}: {email} already in contacts.csv, skipping.")
                continue

            conf_label = f"[{confidence} confidence]"
            print(f"    Slot {slot + 1}: {name} | {role} | {email} {conf_label}")

            row = {
                "bank": org,
                "name": name,
                "first_name": name.split()[0] if name else "",
                "role": role,
                "email": email,
                "email_confidence": confidence,
                "bank_type": BANK_TYPES.get(org_type, "foundation"),
                "country": country,
                "org_type": org_type,
            }
            found.append(row)
            existing.add(email.lower())
            slots_found += 1

    return found


def _find_contact(
    org: str, org_type: str, country: str, role_hint: str, slot: int, client: anthropic.Anthropic
) -> dict | None:
    """Dedicated contact-finder for a single org, avoiding contacts already found (slot > 0)."""
    prompt = f"""\
Find a real named contact at {org} in {country} for an outreach email.

Target role (prefer in this order): {role_hint}
{"This is contact #" + str(slot + 1) + " — find a different person than the most obvious one." if slot > 0 else ""}

Search for their name, exact title, and the organisation's email format.

Return ONLY valid JSON:
{{
  "name": "Full Name",
  "first_name": "First name",
  "role": "Exact job title",
  "email": "constructed email",
  "email_confidence": "high | medium | low",
  "source": "where you found this"
}}

Do not use dashes or em-dashes. If you cannot find a real named person, return {{"name": null}}.
"""
    from bank_research import _call_api
    return _call_api(prompt, client)


# ── Wizard ────────────────────────────────────────────────────────────────────

def wizard(client: anthropic.Anthropic) -> None:
    print()
    print("=" * 60)
    print("  AflaThrive Contact Enrichment Wizard")
    print("=" * 60)

    # Step 1: Target type
    print("\nStep 1 — What type of organisation are you targeting?")
    org_type = _pick("Choose", ["Banks (financial institutions)",
                                "Corporates (CSR / employee wellness)",
                                "Schools (educational curriculum)"])
    org_type = "bank" if org_type.startswith("Banks") else ("corporate" if org_type.startswith("Corp") else "school")

    # Step 2: Country
    print("\nStep 2 — Which country?")
    country_opts = COUNTRIES + ["Other (type name)"]
    country_choice = _pick("Choose", country_opts, default=1)
    if country_choice.startswith("Other"):
        country = _input("  Country name: ")
    else:
        country = country_choice

    # Step 3: Roles
    print(f"\nStep 3 — Which roles to target? (defaults shown for {org_type}s)")
    print("  Type numbers to toggle on/off, press Enter to accept:")
    roles = _toggle_roles(org_type)
    if not roles:
        print("  No roles selected — using all defaults.")
        roles = [r for r, _ in ROLES[org_type]]
    print(f"\n  Targeting: {', '.join(roles)}")

    # Step 4: Candidates per org
    print("\nStep 4 — How many contacts per organisation?")
    candidates_str = _pick("Choose", ["1 contact (fastest)",
                                      "2 contacts (recommended)",
                                      "3 contacts (thorough)",
                                      "5 contacts (maximum coverage)"], default=2)
    candidates = int(candidates_str.split()[0])

    # Step 5: Organisation source
    print("\nStep 5 — Where should the organisation list come from?")
    source = _pick("Choose", ["Type names now (comma-separated)",
                              "Auto-discover — search for organisations in " + country], default=1)

    if source.startswith("Type"):
        raw = _input("  Organisation names (comma-separated): ")
        orgs = [o.strip() for o in raw.split(",") if o.strip()]
        if not orgs:
            print("  No organisations entered. Exiting.")
            return
    else:
        print(f"\n  Searching for {org_type}s in {country}...")
        limit_str = _pick("How many to find?", ["10", "20 (recommended)", "30", "50"], default=2)
        limit = int(limit_str.split()[0])
        orgs = discover_orgs(org_type, country, limit, client)
        if not orgs:
            print("  No organisations found. Try typing names manually.")
            return
        print(f"  Found {len(orgs)} organisations:")
        for o in orgs:
            print(f"    - {o}")
        cont = _input("\n  Continue with these? [Y/n]: ").lower()
        if cont == "n":
            return

    # Step 6: Run enrichment
    print(f"\n{'='*60}")
    print(f"  Enriching {len(orgs)} organisations, {candidates} contact(s) each...")
    print(f"  Roles: {', '.join(roles)}")
    print("=" * 60)

    found = enrich_orgs(orgs, org_type, country, roles, candidates, client)

    if not found:
        print("\n  No contacts found. Try different organisations or roles.")
        return

    # Step 7: Review results
    print(f"\n{'='*60}")
    print(f"  Found {len(found)} contact(s):")
    _print_table(found)

    print()
    remove_raw = _input("  Remove any rows? Type numbers (e.g. 2,5) or press Enter to keep all: ")
    if remove_raw:
        to_remove = {int(x.strip()) for x in remove_raw.split(",") if x.strip().isdigit()}
        found = [r for i, r in enumerate(found, 1) if i not in to_remove]
        print(f"  Kept {len(found)} contact(s).")

    if not found:
        print("  Nothing to add.")
        return

    # Step 8: Next action
    print(f"\n{'='*60}")
    print("  Step 8 — What would you like to do next?")
    print("  1. Dry run   — preview generated emails (does not send)")
    print("  2. Test send — send all to julian.coul@gmail.com")
    print("  3. Live send — send to real contacts now")
    print("  4. Save only — write to contacts.csv and exit")
    print()

    while True:
        action = _input("  Choose [1-4]: ")
        if action in ("1", "2", "3", "4"):
            break
        print("  Please enter 1, 2, 3, or 4.")

    # Always save first
    clean = [{k: r.get(k, "") for k in FIELDNAMES} for r in found]
    append_to_csv(clean)
    print(f"\n  Saved {len(clean)} contact(s) to contacts.csv.")

    if action == "4":
        return

    cfg = load_config()

    # Build a temp contacts list for the pipeline
    temp_contacts = []
    for r in found:
        c = {k: r.get(k, "") for k in FIELDNAMES}
        temp_contacts.append(c)

    # Write a temp CSV for the pipeline to use
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(temp_contacts)
        temp_path = f.name

    test_address = "julian.coul@gmail.com" if action == "2" else None
    dry_run = action == "1"
    auto_confirm = action == "2"

    print()
    pipeline_run(
        dry_run=dry_run,
        bank_filter=None,
        banks_filter=None,
        test_address=test_address,
        auto_confirm=auto_confirm,
        contacts_file=temp_path,
    )

    os.unlink(temp_path)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AflaThrive enrichment wizard")
    parser.add_argument("--type", choices=["bank", "corporate", "school"],
                        help="Organisation type (skip Step 1)")
    parser.add_argument("--country", help="Country (skip Step 2)")
    parser.add_argument("--orgs", help="Comma-separated org names (skip Step 5)")
    parser.add_argument("--discover", type=int, metavar="N",
                        help="Auto-discover N orgs instead of typing names")
    parser.add_argument("--candidates", type=int, default=2,
                        help="Contacts per organisation (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only — do not write to contacts.csv or send")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.get("anthropic_api_key"):
        sys.exit("Missing ANTHROPIC_API_KEY.")
    client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])

    # If no flags given, run the interactive wizard
    if not any([args.type, args.country, args.orgs, args.discover]):
        wizard(client)
        return

    # Non-interactive fast path
    org_type = args.type or "bank"
    country = args.country or "Philippines"
    roles = [r for r, _ in ROLES[org_type]]

    if args.discover:
        print(f"Discovering {args.discover} {org_type}s in {country}...")
        orgs = discover_orgs(org_type, country, args.discover, client)
        print(f"Found: {orgs}")
    elif args.orgs:
        orgs = [o.strip() for o in args.orgs.split(",") if o.strip()]
    else:
        sys.exit("Provide --orgs or --discover.")

    found = enrich_orgs(orgs, org_type, country, roles, args.candidates, client)
    _print_table(found)

    if args.dry_run or not found:
        print(f"\n[DRY RUN] {len(found)} contact(s) found, not written.")
        return

    clean = [{k: r.get(k, "") for k in FIELDNAMES} for r in found]
    append_to_csv(clean)
    print(f"\nAdded {len(clean)} contact(s) to contacts.csv.")


if __name__ == "__main__":
    main()
