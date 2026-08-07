from __future__ import annotations

import json
import os
import time

import anthropic
import requests

# ── Research prompts per org type ─────────────────────────────────────────────

BANK_RESEARCH_PROMPT = """\
You are researching a bank or financial institution for a B2B outreach email on behalf of AflaThrive,
a globally validated financial education organisation.

Organisation: {org}
Country: {country}

Search for:
1. The bank's foundation name and its primary financial literacy or financial inclusion programs
2. Any youth banking, community education, or CSR initiatives they run
3. One verified, specific fact (with a number or named program) you can use as an email opener

Return ONLY valid JSON in this exact format:
{{
  "org": "{org}",
  "foundation_name": "name of their foundation or CSR arm, or null",
  "known_programs": ["list of program names you found"],
  "program_description": "one sentence describing what their main program currently does",
  "program_gap": "one sentence on what structured curriculum would add that they currently lack",
  "audience": "youth | employees | communities | mixed",
  "opening_line": "one verified sentence with a specific fact (program name, reach number, or initiative). Do not use dashes or em-dashes. No fabrication.",
  "retention_line": "leave blank — will be overwritten"
}}

If you cannot find verified information for a field, use null. Never invent program names or statistics.
"""

CORPORATE_RESEARCH_PROMPT = """\
You are researching a company for a B2B outreach email on behalf of AflaThrive,
a globally validated financial education organisation.

Organisation: {org}
Country: {country}

Search for:
1. The company's CSR or sustainability programs, especially any employee financial wellness or
   community financial education initiatives
2. Their foundation or social impact arm if one exists
3. One verified, specific fact (a named program, award, or initiative) you can use as an email opener

Return ONLY valid JSON in this exact format:
{{
  "org": "{org}",
  "foundation_name": "name of their foundation or CSR arm, or null",
  "known_programs": ["list of relevant program names you found"],
  "program_description": "one sentence describing what their main CSR/wellness program currently does",
  "program_gap": "one sentence on what a structured financial education curriculum would add",
  "audience": "employees",
  "opening_line": "one verified sentence with a specific fact about their CSR or wellness work. Do not use dashes or em-dashes. No fabrication.",
  "retention_line": "leave blank — will be overwritten"
}}

If you cannot find verified information for a field, use null. Never invent program names or statistics.
"""

SCHOOL_RESEARCH_PROMPT = """\
You are researching a school or educational institution for a B2B outreach email on behalf of AflaThrive,
a globally validated financial education organisation.

Organisation: {org}
Country: {country}

Search for:
1. Any existing financial literacy or life skills programs the school runs
2. The school's stated educational mission or values, especially around student wellbeing
3. One verified, specific fact (a named program, award, student population, or initiative)
   you can use as an email opener

Return ONLY valid JSON in this exact format:
{{
  "org": "{org}",
  "foundation_name": null,
  "known_programs": ["list of relevant program names you found"],
  "program_description": "one sentence describing what their current life skills or financial education offering looks like",
  "program_gap": "one sentence on what a globally validated financial curriculum with pre/post assessment would add",
  "audience": "youth",
  "opening_line": "one verified sentence with a specific fact about the school or its programs. Do not use dashes or em-dashes. No fabrication.",
  "retention_line": "leave blank — will be overwritten"
}}

If you cannot find verified information for a field, use null. Never invent program names or statistics.
"""

DISCOVERY_PROMPT = """\
You are building a list of organisations for an outreach campaign on behalf of AflaThrive,
a globally validated financial education organisation.

Target type: {org_type}
Country: {country}
Goal: Find up to {limit} real organisations in {country} that are likely to have CSR programs,
financial inclusion work, or educational initiatives that AflaThrive could partner with.

Search for:
- "top {org_type_label} in {country} CSR financial inclusion"
- "{country} {org_type_label} financial literacy programs"
- "{country} {org_type_label} foundation community education"

Return ONLY valid JSON in this exact format:
{{
  "orgs": ["Organisation Name 1", "Organisation Name 2", "Organisation Name 3", ...]
}}

Rules:
- Return only the organisation names as strings, nothing else.
- Do not include duplicates.
- Do not include generic or fictional names.
- Aim for {limit} results but return fewer if you cannot find verified names.
"""

RETENTION_OPTIONS = {
    "youth": "Programme completers are 40% more likely to open savings accounts and hold 3x more funds than non-participants.",
    "employees": "Employees who complete AflaThrive financial wellness modules report 28% reduction in financial stress and demonstrate measurably improved savings behaviour.",
    "communities": "Community-level delivery through AflaThrive's model has produced verified behaviour change in 42 million participants across 112 countries.",
    "mixed": "Programme completers demonstrate measurable behaviour change across savings, budgeting, and entrepreneurship, validated by a World Bank randomised controlled trial.",
}

_PROMPTS = {
    "bank": BANK_RESEARCH_PROMPT,
    "corporate": CORPORATE_RESEARCH_PROMPT,
    "school": SCHOOL_RESEARCH_PROMPT,
}

_ORG_TYPE_LABELS = {
    "bank": "banks and financial institutions",
    "corporate": "companies with CSR or employee wellness programs",
    "school": "schools and educational institutions",
}


BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

_SEARCH_QUERIES = {
    "bank": [
        "{org} foundation financial literacy programs",
        "{org} CSR financial inclusion {country}",
    ],
    "corporate": [
        "{org} CSR sustainability employee wellness programs",
        "{org} foundation community education {country}",
    ],
    "school": [
        "{org} financial literacy life skills program",
        "{org} educational mission student wellbeing {country}",
    ],
    "discovery_bank": [
        "top banks {country} CSR financial inclusion programs",
        "{country} bank foundation financial literacy",
    ],
    "discovery_corporate": [
        "top companies {country} CSR employee financial wellness",
        "{country} corporate foundation community education",
    ],
    "discovery_school": [
        "top schools {country} financial literacy curriculum",
        "{country} school life skills financial education program",
    ],
}


def _brave_search(query: str, count: int = 5) -> str:
    if not BRAVE_API_KEY:
        return ""
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={"q": query, "count": count},
            timeout=10,
        )
        results = resp.json().get("web", {}).get("results", [])
        return "\n\n".join(
            f"{r.get('title','')}: {r.get('description','')}" for r in results
        )
    except Exception as e:
        print(f"  Brave search error: {e}")
        return ""


def _call_gemini(prompt: str, search_queries: list[str]) -> dict | None:
    """Brave search + Gemini Flash. Zero Anthropic credits used."""
    if not GEMINI_API_KEY:
        return None

    search_context = ""
    for q in search_queries:
        results = _brave_search(q)
        if results:
            search_context += f"\n\n--- Search: {q} ---\n{results}"

    if not search_context:
        return None

    full_prompt = (
        prompt
        + "\n\nUse ONLY the following search results — do not invent anything:\n"
        + search_context
    )

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": full_prompt}]}]},
            timeout=30,
        )
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        print(f"  Gemini error: {e}")
    return None


def _call_api(prompt: str, client: anthropic.Anthropic) -> dict | None:
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                tools=[{"type": "web_search_20260209", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text":
                    text = block.text
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end > start:
                        return json.loads(text[start:end])
        except anthropic.RateLimitError:
            wait = [15, 30, 60][attempt]
            print(f"  Rate limit, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"  API error: {e}")
            break
    return None


def research_org(org_name: str, org_type: str, country: str, client: anthropic.Anthropic) -> dict:
    """
    Research an organisation and return a profile dict.
    org_type: "bank" | "corporate" | "school"
    Uses Brave + OmniRoute (free) when available, falls back to Anthropic.
    """
    prompt_template = _PROMPTS.get(org_type, BANK_RESEARCH_PROMPT)
    prompt = prompt_template.format(org=org_name, country=country)

    if BRAVE_API_KEY and GEMINI_API_KEY:
        raw_queries = _SEARCH_QUERIES.get(org_type, _SEARCH_QUERIES["bank"])
        queries = [q.format(org=org_name, country=country) for q in raw_queries]
        data = _call_gemini(prompt, queries)
        if data:
            data.setdefault("bank", org_name)
            data["bank"] = org_name
            audience = data.get("audience", "mixed")
            data["retention_line"] = RETENTION_OPTIONS.get(audience, RETENTION_OPTIONS["mixed"])
            return data
        print("  Gemini unavailable, falling back to Anthropic...")

    data = _call_api(prompt, client)

    if not data:
        return _empty_profile(org_name)

    # Normalise: some prompts use "org" key, templates expect "bank"
    data.setdefault("bank", org_name)
    data["bank"] = org_name

    audience = data.get("audience", "mixed")
    data["retention_line"] = RETENTION_OPTIONS.get(audience, RETENTION_OPTIONS["mixed"])
    return data


def discover_orgs(org_type: str, country: str, limit: int, client: anthropic.Anthropic) -> list[str]:
    """
    Web-search for up to `limit` organisation names matching org_type in country.
    Uses Brave + OmniRoute (free) when available, falls back to Anthropic.
    """
    prompt = DISCOVERY_PROMPT.format(
        org_type=org_type,
        org_type_label=_ORG_TYPE_LABELS.get(org_type, org_type),
        country=country,
        limit=limit,
    )

    if BRAVE_API_KEY and GEMINI_API_KEY:
        disc_key = f"discovery_{org_type}"
        raw_queries = _SEARCH_QUERIES.get(disc_key, _SEARCH_QUERIES.get("discovery_bank"))
        queries = [q.format(org_type=org_type, country=country) for q in raw_queries]
        data = _call_gemini(prompt, queries)
        if data and isinstance(data.get("orgs"), list):
            return [o for o in data["orgs"] if isinstance(o, str) and o.strip()][:limit]
        print("  Gemini unavailable, falling back to Anthropic...")

    data = _call_api(prompt, client)
    if data and isinstance(data.get("orgs"), list):
        return [o for o in data["orgs"] if isinstance(o, str) and o.strip()][:limit]
    return []


def _empty_profile(org_name: str) -> dict:
    return {
        "bank": org_name,
        "foundation_name": None,
        "known_programs": [],
        "program_description": None,
        "program_gap": None,
        "audience": "mixed",
        "opening_line": None,
        "retention_line": RETENTION_OPTIONS["mixed"],
    }


# ── Backward-compatible alias ──────────────────────────────────────────────────

def research_bank(bank_name: str, client: anthropic.Anthropic) -> dict:
    """Kept for backward compatibility with send_pipeline.py."""
    return research_org(bank_name, "bank", "Philippines", client)


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    result = research_org("BDO Unibank", "bank", "Philippines", client)
    print(json.dumps(result, indent=2))
