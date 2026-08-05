"""
airtable_client.py — Airtable integration for logging outreach attempts.

Table fields:
  Company, Founder Name, Founder Email, Sector, Date Sent,
  Subject Line, Status, Notes
"""
from __future__ import annotations

import sys
from datetime import date

from pyairtable import Api

from config import get_config_value

STATUS_OPTIONS = ["drafted", "sent", "replied", "meeting booked", "dead"]


def _get_table():
    api_key    = get_config_value("airtable_api_key")
    base_id    = get_config_value("airtable_base_id")
    table_name = get_config_value("airtable_table_name") or "Outreach"

    if not api_key or not base_id:
        print("Error: Airtable credentials missing. Run `python outreach.py setup` first.")
        sys.exit(1)

    api = Api(api_key)
    return api.table(base_id, table_name)


def log_outreach(
    company_name: str,
    founder_name: str,
    founder_email: str,
    sector: str,
    subject_line: str,
    status: str = "drafted",
    notes: str = "",
) -> str | None:
    table = _get_table()

    fields = {
        "Company":       company_name,
        "Founder Name":  founder_name,
        "Founder Email": founder_email,
        "Sector":        sector,
        "Date Sent":     str(date.today()),
        "Subject Line":  subject_line,
        "Status":        status,
        "Notes":         notes,
    }

    try:
        record = table.create(fields)
        print(f"Logged to Airtable. Record ID: {record['id']}")
        return record["id"]
    except Exception as exc:
        print(f"Airtable error: {exc}")
        return None


def update_status(record_id: str, status: str, notes: str = "") -> bool:
    if status not in STATUS_OPTIONS:
        print(f"Warning: '{status}' is not a standard status value.")

    table = _get_table()
    fields = {"Status": status}
    if notes:
        fields["Notes"] = notes

    try:
        table.update(record_id, fields)
        return True
    except Exception as exc:
        print(f"Airtable update error: {exc}")
        return False


def list_recent(limit: int = 10) -> list[dict]:
    table = _get_table()
    try:
        records = table.all(sort=["-Date Sent"])
        return records[:limit]
    except Exception as exc:
        print(f"Airtable fetch error: {exc}")
        return []
