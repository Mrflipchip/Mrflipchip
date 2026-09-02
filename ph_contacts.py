import csv
import os

_CSV = os.path.join(os.path.dirname(__file__), "contacts.csv")


def load_contacts(csv_path: str = _CSV) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


CONTACTS = load_contacts()
