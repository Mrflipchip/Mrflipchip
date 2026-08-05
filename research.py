"""
research.py — AI-powered company research using the Anthropic API with web search.

Uses claude-sonnet-4-6 with the web_search_20250305 tool to look up a company
and return structured data ready to pipe into the email send flow.
"""

import json
import sys
import time

import anthropic

from config import get_config_value

RESEARCH_PROMPT = """\
You are researching a company for a cold outreach internship email. Search the web thoroughly.

Return only a valid JSON object with no preamble and no markdown.

Hard rules for every field:
- No em dashes, en dashes, semicolons, or colons used as separators
- No consultant language. Never use: pivotal, inflection point, outsized, leverage, accelerate, transform, synergy, ecosystem, unlock, scale (as a verb), impactful, strategic, capitalize
- Short sentences. Fragments are fine.
- Every sentence must be specific to this company only.
- CRITICAL: Never include negative facts in hook, one_fact, or why_now. No FDA warnings, lawsuits, regulatory failures, layoffs, pivots away from failure, or market withdrawals. These can inform your research but must not appear in the output fields.

Fields required:
- company_name
- founder_name
- founder_first_name
- founder_email_guess: use common startup patterns like firstname@companyname.com
- sector
- what_they_do: one sentence, specific to this company
- funding_stage
- funding_amount
- funding_date
- company_location: city and country of the company headquarters. Example: "London, UK" or "New York, USA" or "Remote".
- hook: one sentence maximum. Personal and specific. Tied to something real about the product, mission, or what makes this company different. Never generic. Example style: "You turned a tampon into a diagnostic device." or "I lived your product."
- one_fact: the single most positive and specific verifiable recent fact. Priority order: named award or recognition first, then named partnership, then product launch with a real detail, then funding as a last resort. One sentence only. No negative facts. Example: "Your Diagnostic Tampon was named one of TIME Magazine's Best Inventions of 2024."
- why_now: two to three short punchy sentences on why this is the right moment. Specific to this company. No negative facts. No consultant language. Do not start any sentence with "That is".
- contribution: one to two sentences describing specifically what an intern could work on at this company right now, based on their actual goals and projects. Must be complete sentences. Must name real work. Never cut off mid-sentence. Never use "wherever an extra pair of hands would be useful". Example: "Whether that is expanding the diagnostic tampon into new pharmacy channels, or building out the B2B clinical partnerships pipeline."

Company: {company_name}. Sector: {sector}."""

FIELD_LABELS = {
    "company_name":        "Company name",
    "company_location":    "Company location",
    "founder_name":        "Founder full name",
    "founder_first_name":  "Founder first name",
    "founder_email_guess": "Founder email (guess)",
    "sector":              "Sector",
    "what_they_do":        "What they do",
    "funding_stage":       "Funding stage",
    "funding_amount":      "Funding amount",
    "funding_date":        "Funding date",
    "hook":                "Hook",
    "one_fact":            "One fact",
    "why_now":             "Why now",
    "contribution":        "Contribution areas",
}


DISCOVERY_PROMPT = """\
You are finding cold outreach internship targets for Julian Coulbert. Julian is a British Ivorian \
undergraduate at TETR College of Business. He has built a D2C brand in India, run a Kickstarter \
in Singapore, worked in UK real estate and early-stage venture funds, and is currently running a \
social impact venture in Accra. He is based in the UK this summer.

Search the web and return exactly five company suggestions as a JSON array. No preamble, no markdown.

Criteria:
- Series A or earlier, or bootstrapped and growing fast
- Small team where the founder is accessible (under 50 people)
- Sectors matching Julian's interests: sustainability, wellness, consumer brands, food and nutrition, \
femtech, impact, proptech, fintech, Africa-focused startups, or adjacent
- No large corporations, no companies past Series B
- Mix of UK-based and international companies

Each element in the array must have:
- company_name
- company_location: city and country
- sector: two to four words
- what_they_do: one sentence
- why_julian: one sentence on why Julian specifically would fit and add value here{sector_filter}"""


def _parse_json(text_content: str) -> object:
    text = text_content.strip()

    start = -1
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            start = i
            break

    if start == -1:
        print(f"Error: No JSON found in API response.\n\nRaw:\n{text_content}")
        sys.exit(1)

    opener = text[start]
    closer = "}" if opener == "{" else "]"
    end = text.rfind(closer)
    if end == -1:
        print(f"Error: Unterminated JSON in API response.\n\nRaw:\n{text_content}")
        sys.exit(1)

    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        print(f"Error: Could not parse JSON from API response.\n\nRaw:\n{text_content}")
        print(f"\nJSON error: {exc}")
        sys.exit(1)


def _api_call(client, prompt: str) -> str:
    delays = [15, 30, 60]
    for attempt, delay in enumerate(delays + [None], start=1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text":
                    return block.text
            print("Error: No text response received from the API.")
            sys.exit(1)
        except anthropic.RateLimitError:
            if delay is None:
                print("Error: Rate limit exceeded after 3 retries. Wait a minute and try again.")
                sys.exit(1)
            print(f"Rate limit hit. Waiting {delay}s before retry {attempt}/3...")
            time.sleep(delay)


def discover_companies(sector_hint: str = "") -> list:
    api_key = get_config_value("anthropic_api_key")
    if not api_key:
        print("Error: Anthropic API key not found. Run `python outreach.py setup` first.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    sector_filter = (
        f"\n\nFocus specifically on the {sector_hint} sector." if sector_hint else ""
    )
    prompt = DISCOVERY_PROMPT.format(sector_filter=sector_filter)

    print("\nSearching for companies... (this may take 15-30 seconds)\n")

    text = _api_call(client, prompt)
    data = _parse_json(text)

    if not isinstance(data, list):
        print("Error: Expected a list of companies from the API.")
        sys.exit(1)

    return data[:5]


def run_research(company_name: str, sector: str) -> dict:
    api_key = get_config_value("anthropic_api_key")
    if not api_key:
        print("Error: Anthropic API key not found. Run `python outreach.py setup` first.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    prompt = RESEARCH_PROMPT.format(company_name=company_name, sector=sector)

    print(f"\nResearching {company_name}... (this may take 15-30 seconds)\n")

    text = _api_call(client, prompt)
    return _parse_json(text)


def display_and_confirm(data: dict) -> dict:
    print("\n" + "=" * 60)
    print("RESEARCH RESULTS")
    print("=" * 60)

    ordered_keys = list(FIELD_LABELS.keys())
    extra_keys = [k for k in data if k not in ordered_keys]
    all_keys = ordered_keys + extra_keys

    for key in all_keys:
        if key in data:
            label = FIELD_LABELS.get(key, key)
            print(f"  {label:<25} {data[key]}")

    print("=" * 60)
    print("\nEnter a field name to edit it, or press Enter to confirm.\n")

    while True:
        raw = input("Field to edit (or Enter to confirm): ").strip().lower()
        if not raw:
            break

        matched_key = None
        for key in all_keys:
            label = FIELD_LABELS.get(key, key).lower()
            if raw == key or raw in label:
                matched_key = key
                break

        if matched_key is None:
            print(f"  Field '{raw}' not found. Try one of: {', '.join(all_keys)}")
            continue

        current = data.get(matched_key, "")
        print(f"  Current value: {current}")
        new_val = input(f"  New value: ").strip()
        if new_val:
            data[matched_key] = new_val
            label = FIELD_LABELS.get(matched_key, matched_key)
            print(f"  Updated {label} → {new_val}\n")

    return data


def research_to_send_inputs(data: dict) -> dict:
    return {
        "company_name":     data.get("company_name", ""),
        "company_location": data.get("company_location", ""),
        "founder_name":     data.get("founder_name", ""),
        "founder_first":    data.get("founder_first_name", ""),
        "founder_email":    data.get("founder_email_guess", ""),
        "sector":           data.get("sector", ""),
        "what_they_do":     data.get("what_they_do", ""),
        "hook":             data.get("hook", ""),
        "one_fact":         data.get("one_fact", ""),
        "why_now":          data.get("why_now", ""),
        "contribution":     data.get("contribution", ""),
    }
