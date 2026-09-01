#!/usr/bin/env python3
"""
enrich.py — Find and verify contacts at US banks via RocketReach + ZeroBounce.

Usage:
  python3 enrich.py --type bank --country "United States" --candidates 2
  python3 enrich.py --bank "Wells Fargo" --candidates 3
  python3 enrich.py --dry-run
  python3 enrich.py --set-rocketreach <api_key>
  python3 enrich.py --set-zerobounce <api_key>
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests

CONFIG_PATH = Path.home() / ".outreach_config.json"

US_BANKS = [
    "Wells Fargo",
    "JPMorgan Chase",
    "Bank of America",
    "U.S. Bancorp",
    "PNC Financial Services",
    "Truist Financial",
    "Fifth Third Bank",
    "KeyBank",
    "Regions Financial",
    "Huntington National Bank",
    "Citizens Financial Group",
    "Comerica",
    "Zions Bancorporation",
    "First Horizon Bank",
]

ROLES = {
    "bank": {
        "Community Affairs Officer": True,
        "CRA Officer": True,
        "Community Reinvestment Act Officer": True,
        "Head of Community Development": True,
        "VP of Community Reinvestment": True,
        "Director of Financial Education": True,
        "Financial Wellness Program Manager": False,
        "Foundation President": False,
        "Head of Foundation": False,
        "Corporate Social Responsibility Officer": False,
    }
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def search_rocketreach(bank: str, title: str, api_key: str) -> list[dict]:
    url = "https://api.rocketreach.co/v2/api/search"
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    payload = {
        "query": {
            "name": [title],
            "current_employer": [bank],
            "location_country": ["United States"],
        },
        "start": 1,
        "page_size": 3,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.json().get("profiles", [])
        if r.status_code == 429:
            print("  RocketReach rate limit — waiting 15s...")
            time.sleep(15)
            return []
        print(f"  RocketReach {r.status_code}: {r.text[:200]}")
        return []
    except Exception as e:
        print(f"  RocketReach error: {e}")
        return []


def lookup_rocketreach_email(profile_id: int, api_key: str) -> str | None:
    url = "https://api.rocketreach.co/v2/api/lookupProfile"
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}
    try:
        r = requests.post(url, json={"id": profile_id}, headers=headers, timeout=20)
        if r.status_code == 200:
            emails = r.json().get("emails", [])
            for e in emails:
                if e.get("email"):
                    return e["email"]
        return None
    except Exception as e:
        print(f"  RocketReach lookup error: {e}")
        return None


def verify_zerobounce(email: str, api_key: str) -> bool:
    url = "https://api.zerobounce.net/v2/validate"
    try:
        r = requests.get(
            url,
            params={"api_key": api_key, "email": email, "ip_address": ""},
            timeout=10,
        )
        if r.status_code == 200:
            status = r.json().get("status", "unknown")
            print(f"    ZeroBounce: {email} → {status}")
            return status in ("valid", "catch-all")
        print(f"  ZeroBounce {r.status_code}")
        return False
    except Exception as e:
        print(f"  ZeroBounce error: {e}")
        return False


def find_contacts_for_bank(bank: str, org_type: str, candidates: int, cfg: dict, dry_run: bool, verify: bool = False) -> list[dict]:
    rr_key = cfg.get("rocketreach_api_key", "")
    zb_key = cfg.get("zerobounce_api_key", "") if verify else ""
    contacts: list[dict] = []

    roles = ROLES.get(org_type, {})
    ordered = sorted(roles.items(), key=lambda x: (0 if x[1] else 1, x[0]))

    for role, _primary in ordered:
        if len(contacts) >= candidates:
            break

        print(f"  Searching: {role} @ {bank}")
        if dry_run:
            print("    [DRY RUN] Skipping API call")
            continue

        if not rr_key:
            print("  ERROR: rocketreach_api_key not configured — run: python3 enrich.py --set-rocketreach <key>")
            break

        profiles = search_rocketreach(bank, role, rr_key)
        for profile in profiles:
            if len(contacts) >= candidates:
                break

            name = profile.get("name", "").strip()
            pid = profile.get("id")

            # Try email from search result first, then do a lookup
            email = None
            for e in profile.get("emails", []):
                if e.get("email"):
                    email = e["email"]
                    break
            if not email and pid:
                email = lookup_rocketreach_email(pid, rr_key)

            if not email:
                print(f"    No email for {name}")
                continue

            if zb_key:
                if not verify_zerobounce(email, zb_key):
                    print(f"    Skipping {email} — failed verification")
                    continue
            else:
                print("    (No ZeroBounce key — skipping verification)")

            title = profile.get("current_title", role)
            first_name = name.split()[0] if name else ""
            contact = {"bank": bank, "name": name, "first_name": first_name, "role": title, "email": email}
            print(f"    + {name} ({title}) — {email}")
            contacts.append(contact)

        time.sleep(1)

    return contacts


def write_contacts_py(contacts: list[dict], path: str) -> None:
    lines = ["CONTACTS = ["]
    for c in contacts:
        lines.append(
            f'    {{"bank": {json.dumps(c["bank"])}, "name": {json.dumps(c["name"])}, '
            f'"first_name": {json.dumps(c["first_name"])}, "role": {json.dumps(c["role"])}, '
            f'"email": {json.dumps(c["email"])}}},')
    lines.append("]")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {len(contacts)} contacts → {path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Find and verify bank contacts for AflaThrive outreach.")
    p.add_argument("--type", default="bank")
    p.add_argument("--country", default="United States")
    p.add_argument("--candidates", type=int, default=2, help="Contacts to find per bank")
    p.add_argument("--bank", help="Target one bank; omit to search all US_BANKS")
    p.add_argument("--output", default="us_contacts.py")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verify", action="store_true", help="Verify emails with ZeroBounce (uses 1 credit per email)")
    p.add_argument("--set-rocketreach", metavar="KEY", help="Save RocketReach API key to config")
    p.add_argument("--set-zerobounce", metavar="KEY", help="Save ZeroBounce API key to config")
    args = p.parse_args()

    cfg = load_config()

    if args.set_rocketreach:
        cfg["rocketreach_api_key"] = args.set_rocketreach
        save_config(cfg)
        print("RocketReach API key saved.")
        return

    if args.set_zerobounce:
        cfg["zerobounce_api_key"] = args.set_zerobounce
        save_config(cfg)
        print("ZeroBounce API key saved.")
        return

    banks = [args.bank] if args.bank else US_BANKS
    all_contacts: list[dict] = []

    if args.verify:
        if not cfg.get("zerobounce_api_key"):
            print("ERROR: --verify requires zerobounce_api_key — run: python3 enrich.py --set-zerobounce <key>")
            return
        max_emails = len(banks) * args.candidates
        print(f"\nWARNING: --verify will use up to {max_emails} ZeroBounce credit(s).")
        confirm = input("Continue? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    for bank in banks:
        print(f"\n{'='*55}")
        print(f"Bank: {bank}")
        found = find_contacts_for_bank(
            bank=bank,
            org_type=args.type,
            candidates=args.candidates,
            cfg=cfg,
            dry_run=args.dry_run,
            verify=args.verify,
        )
        all_contacts.extend(found)

    if args.dry_run:
        print(f"\n[DRY RUN] Would search {len(banks)} bank(s). No API calls made.")
        return

    if all_contacts:
        write_contacts_py(all_contacts, args.output)
    else:
        print("\nNo contacts found. Check your RocketReach API key.")


if __name__ == "__main__":
    main()
