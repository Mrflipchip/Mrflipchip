"""
config.py — credential storage and setup wizard.
All credentials are stored at ~/.outreach_config.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".outreach_config.json"

REQUIRED_KEYS = {
    "airtable_api_key": "Airtable API key",
    "airtable_base_id": "Airtable Base ID",
    "airtable_table_name": "Airtable table name (press Enter for default 'Outreach')",
    "gmail_credentials_path": "Path to Gmail OAuth credentials.json",
    "anthropic_api_key": "Anthropic API key (for the research command)",
    "titan_email": "Titan email address (SMTP login)",
    "titan_password": "Titan email password / app password",
}

DEFAULTS = {
    "airtable_table_name": "Outreach",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def setup_wizard(keys_needed: list[str] | None = None) -> dict:
    """
    Interactive prompt for any missing credentials.
    Pass keys_needed to restrict which keys to prompt for;
    None means prompt for all REQUIRED_KEYS that are missing.
    """
    config = load_config()
    if keys_needed is None:
        keys_needed = list(REQUIRED_KEYS.keys())

    changed = False
    for key in keys_needed:
        if key in config and config[key]:
            continue  # already set
        label = REQUIRED_KEYS.get(key, key)
        default = DEFAULTS.get(key, "")
        prompt = f"{label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = input(prompt).strip()
        if not value and default:
            value = default
        if value:
            config[key] = value
            changed = True

    if changed:
        save_config(config)
        print(f"Config saved to {CONFIG_PATH}\n")

    return config


def get_config_value(key: str, prompt_if_missing: bool = True) -> str | None:
    config = load_config()
    if config.get(key):
        return config[key]
    if prompt_if_missing:
        config = setup_wizard(keys_needed=[key])
        return config.get(key)
    return None


def save_gmail_token(token_data: dict) -> None:
    config = load_config()
    config["gmail_token"] = token_data
    save_config(config)


def load_gmail_token() -> dict | None:
    config = load_config()
    return config.get("gmail_token")
