import json
import time
import anthropic

RESEARCH_PROMPT = """\
You are researching a Philippine bank for a B2B outreach email on behalf of AflaThrive.

Bank: {bank}

Search for:
1. The bank's foundation name and its primary financial literacy or financial inclusion programs
2. Any youth banking, community education, or CSR initiatives they run
3. One verified, specific fact (with a number or named program) you can use as an email opener

Return ONLY valid JSON in this exact format:
{{
  "bank": "{bank}",
  "foundation_name": "name of their foundation or CSR arm, or null",
  "known_programs": ["list of program names you found"],
  "program_description": "one sentence describing what their main program currently does",
  "program_gap": "one sentence on what structured/validated curriculum would add that they currently lack",
  "audience": "youth | employees | communities | mixed",
  "opening_line": "one verified sentence with a specific fact (program name, reach number, or initiative). Do not use dashes or em-dashes. No fabrication.",
  "retention_line": "one specific AflaThrive stat or outcome that fits their model best"
}}

If you cannot find verified information for a field, use null. Never invent program names or statistics.
"""

RETENTION_OPTIONS = {
    "youth": "Programme completers are 40% more likely to open savings accounts and hold 3x more funds than non-participants.",
    "employees": "Employees who complete AflaThrive financial wellness modules report 28% reduction in financial stress and demonstrate measurably improved savings behaviour.",
    "communities": "Community-level delivery through AflaThrive's model has produced verified behaviour change in 42 million participants across 112 countries.",
    "mixed": "Programme completers demonstrate measurable behaviour change across savings, budgeting, and entrepreneurship, validated by a World Bank randomised controlled trial.",
}


def research_bank(bank_name: str, client: anthropic.Anthropic) -> dict:
    prompt = RESEARCH_PROMPT.format(bank=bank_name)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=[{"type": "web_search_20260209", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )

            for block in response.content:
                if block.type == "text":
                    text = block.text
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end > start:
                        data = json.loads(text[start:end])
                        audience = data.get("audience", "mixed")
                        data["retention_line"] = RETENTION_OPTIONS.get(audience, RETENTION_OPTIONS["mixed"])
                        return data

        except anthropic.RateLimitError:
            wait = [15, 30, 60][attempt]
            print(f"Rate limit — waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"Error researching {bank_name}: {e}")
            break

    return {
        "bank": bank_name,
        "foundation_name": None,
        "known_programs": [],
        "program_description": None,
        "program_gap": None,
        "audience": "mixed",
        "opening_line": None,
        "retention_line": RETENTION_OPTIONS["mixed"],
    }


if __name__ == "__main__":
    import os
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    result = research_bank("BDO Unibank", client)
    print(json.dumps(result, indent=2))
