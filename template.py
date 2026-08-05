"""
template.py — email generation logic.

Permanent generation rules (see CLAUDE.md for full list):
  1. Why paragraph: exactly one research fact, one sentence, most positive available.
     Priority: award > named partnership > product launch > funding (last resort).
  2. "Not the planning stage. The doing stage." and "I want to be in the room where
     it happens" are NOT template defaults. They do not appear in generated output.
  3. No negative facts (FDA warnings, lawsuits, layoffs) in any email field.
  4. Closing contribution line must be complete and specific to this company.
  5. No generic sentences. Every line must be specific to the company.
  6. No em dashes, en dashes, semicolons, colons as separators. No consultant language.
"""

import re

BANNED_PHRASES = [
    "pivotal inflection point",
    "inflection point",
    "outsized impact",
    "outsized",
    "leverage",
    "accelerate",
    "unlock",
    "synergy",
    "ecosystem",
    "game-changing",
    "game changer",
    "impactful",
    "capitalize on",
    "capitalise on",
    "strategic partnership",
    "go-to-market",
]

NEGATIVE_SIGNALS = [
    "fda warning",
    "warning letter",
    "lawsuit",
    "litigation",
    "layoff",
    "laid off",
    "withdrew",
    "withdrawal",
    "pulled from",
    "shut down",
    "pivot away",
    "failed",
    "failure",
    "regulatory action",
]


def clean_text(text: str) -> str:
    text = text.replace("\u2014", ". ").replace("\u2013", ". ")
    text = re.sub(r"\s*;\s*", ". ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text.strip()


def check_for_negatives(text: str, field_name: str) -> None:
    lower = text.lower()
    for signal in NEGATIVE_SIGNALS:
        if signal in lower:
            print(
                f"\n  WARNING: '{field_name}' may contain a negative fact ('{signal}'). "
                f"Remove it before sending. Negative facts must not appear in emails.\n"
            )
            break


BULLETS_PLAIN = """\
  \u2022 I play tennis. Wherever I land, I find a court.
  \u2022 I am probably addicted to travelling. New cultures, new food, new people.
  \u2022 Speaking of food, I love to cook. One day I want to spend a few weeks at a proper culinary school, just for fun.
  \u2022 I volunteer and do part time NGO work. Leaving an impact, whether in Africa or anywhere else, is something I take seriously."""

BULLETS_HTML = """\
<ul>
  <li>I play tennis. Wherever I land, I find a court.</li>
  <li>I am probably addicted to travelling. New cultures, new food, new people.</li>
  <li>Speaking of food, I love to cook. One day I want to spend a few weeks at a proper culinary school, just for fun.</li>
  <li>I volunteer and do part time NGO work. Leaving an impact, whether in Africa or anywhere else, is something I take seriously.</li>
</ul>"""

IMAGE_PLACEHOLDER = "[INSERT: Photo of Julian and cohort volunteering at school]"
IMAGE_PLACEHOLDER_HTML = (
    "<p><em>[INSERT: Photo of Julian and cohort volunteering at school]</em></p>"
)

LINKEDIN_URL = "https://www.linkedin.com/in/julian-coulbert-942b30274/"
INSTAGRAM_KICKSTARTER_URL = "https://www.instagram.com/reel/DUTM96KjMFc/"
TETR_URL = "https://tetr.com/"

TETR_PARA_PLAIN = (
    "I'm a British Ivorian undergraduate at TETR College of Business "
    f"[{TETR_URL}], a programme built around one idea: learn business by doing "
    "business across the globe. I've launched a D2C brand in India, run a "
    f"Kickstarter in Singapore [{INSTAGRAM_KICKSTARTER_URL}], and I am currently "
    "running a social impact venture in Accra. I've also spent time with "
    "early-stage venture funds and in UK real estate. I will be based in the UK "
    "this summer and available to contribute."
)

TETR_PARA_HTML = (
    "I'm a British Ivorian undergraduate at "
    f'<a href="{TETR_URL}">TETR College of Business</a>, a programme built '
    "around one idea: learn business by doing business across the globe. I've "
    "launched a D2C brand in India, run a "
    f'<a href="{INSTAGRAM_KICKSTARTER_URL}">Kickstarter in Singapore</a>, and '
    "I am currently running a social impact venture in Accra. I've also spent "
    "time with early-stage venture funds and in UK real estate. I will be based "
    "in the UK this summer and available to contribute."
)

SIGNOFF_PLAIN = f"""\
My CV is attached below.

Best Regards,
Julian Coulbert
LinkedIn: {LINKEDIN_URL}"""

SIGNOFF_HTML = f"""\
<p>My CV is attached below.</p>
<p>Best Regards,<br>
Julian Coulbert<br>
<a href="{LINKEDIN_URL}">LinkedIn</a></p>"""


def suggest_subject(inputs: dict) -> str:
    return "Internship Inquiry \u2014 Julian Coulbert"


def generate_email(inputs: dict) -> dict:
    company    = inputs["company_name"].strip()
    first_name = inputs.get("founder_first", inputs["founder_name"].split()[0]).strip()

    hook             = clean_text(inputs.get("hook", "").strip())
    one_fact         = clean_text(inputs.get("one_fact", "").strip())
    why_now          = clean_text(inputs.get("why_now", "").strip())
    contribution     = clean_text(inputs.get("contribution", "").strip())
    company_location = inputs.get("company_location", "").strip()

    check_for_negatives(one_fact, "one_fact")
    check_for_negatives(why_now, "why_now")

    subject = inputs.get("subject_override") or suggest_subject(inputs)

    if not hook:
        hook = f"I have been following what you are building at {company}."

    why_para = _build_why_para(company, one_fact, why_now)
    closing  = _build_closing(company, contribution, company_location)

    body_plain = f"""\
Dear {first_name},

{hook}

I'm Julian. Right now I am stationed in Accra, Ghana, building a social impact venture.

{why_para}

{TETR_PARA_PLAIN}

A bit about me:

{BULLETS_PLAIN}

{IMAGE_PLACEHOLDER}

{closing}

I'd love to have a conversation.

{SIGNOFF_PLAIN}"""

    body_html = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: Georgia, serif; font-size: 15px; line-height: 1.7; color: #1a1a1a; max-width: 620px; margin: 0 auto; padding: 20px;">

<p>Dear {first_name},</p>

<p>{hook.replace(chr(10), "<br>")}</p>

<p>I'm Julian. Right now I am stationed in Accra, Ghana, building a social impact venture.</p>

<p>{why_para.replace(chr(10), "<br>")}</p>

<p>{TETR_PARA_HTML}</p>

<p>A bit about me:</p>
{BULLETS_HTML}

{IMAGE_PLACEHOLDER_HTML}

<p>{closing.replace(chr(10), "<br>")}</p>

<p>I'd love to have a conversation.</p>

{SIGNOFF_HTML}

</body>
</html>"""

    return {
        "subject":    subject,
        "body_plain": body_plain,
        "body_html":  body_html,
    }


def _build_why_para(company: str, one_fact: str, why_now: str) -> str:
    parts = []

    if one_fact:
        fact_sentence = one_fact if one_fact.endswith(".") else one_fact + "."
        parts.append(fact_sentence)

    if why_now:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", why_now) if s.strip()]
        filtered = [s for s in sentences if not s.lower().startswith("that is")]
        if filtered:
            parts.append(" ".join(filtered))

    if not parts:
        parts.append(
            f"What you are doing at {company} is not something many people are doing."
        )

    return " ".join(parts)


UK_IDENTIFIERS = [
    "uk", "united kingdom", "england", "london", "manchester", "birmingham",
    "edinburgh", "glasgow", "bristol", "leeds", "cambridge", "oxford",
    "liverpool", "sheffield", "nottingham", "brighton",
]


def _is_uk_based(company_location: str) -> bool:
    loc = company_location.lower()
    return any(term in loc for term in UK_IDENTIFIERS)


def _build_closing(company: str, contribution: str, company_location: str = "") -> str:
    if _is_uk_based(company_location):
        avail = f"I am based in the UK this summer and available to contribute in person to {company}."
    else:
        avail = f"I am available remotely this summer and would love to contribute to {company}."

    if contribution:
        return f"{avail} {contribution}"

    return (
        f"{avail} "
        f"[EDIT: add specific contribution areas for {company} before sending.]"
    )
