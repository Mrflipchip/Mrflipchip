SUBJECT_A = "AflaThrive x {bank}, Globally Validated Financial Education"

BODY_PLAIN_A = """\
Dear {first_name},

{opening_line}

{foundation_ref} has the reach and the delivery infrastructure. What it does not yet have is a structured, \
globally validated curriculum that changes financial behaviour measurably and gives {bank} a \
reportable, third-party-validated outcome to show the Bangko Sentral ng Pilipinas and your \
{stakeholder_label} stakeholders.

That is what AflaThrive provides.

I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated \
financial education organisation deployed in 112 countries, with 42 million young people reached \
across 50 languages. We license a structured financial education curriculum that embeds directly \
into your {delivery_label}. Your brand. Your interface. Your customer relationship.

For {bank} specifically:

Impact: {retention_line}

Regulator narrative: The Bangko Sentral ng Pilipinas has made financial inclusion a national \
priority under its National Strategy for Financial Inclusion. AflaThrive gives {bank} a globally \
validated, independently assessed delivery mechanism you can report to the BSP and surface \
externally as a market-leading initiative.

Scale: The curriculum is modular, short, structured modules that drop into {delivery_label}. \
Pre and post assessment data flows back to you. It scales without adding operational burden.

I have attached a one-pager with more detail. I would welcome a brief call to explore the fit, \
would next week work for you?

Best regards,
Julian Coulbert
AflaThrive
"""

BODY_HTML_A = """\
<p>Dear {first_name},</p>

<p>{opening_line}</p>

<p>{foundation_ref} has the reach and the delivery infrastructure. What it does not yet have is a structured,
globally validated curriculum that changes financial behaviour measurably and gives {bank} a
reportable, third-party-validated outcome to show the Bangko Sentral ng Pilipinas and your
{stakeholder_label} stakeholders.</p>

<p>That is what AflaThrive provides.</p>

<p>I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated
financial education organisation deployed in 112 countries, with 42 million young people reached
across 50 languages. We license a structured financial education curriculum that embeds directly
into your {delivery_label}. Your brand. Your interface. Your customer relationship.</p>

<p><strong>For {bank} specifically:</strong></p>

<p><strong>Impact:</strong> {retention_line}</p>

<p><strong>Regulator narrative:</strong> The Bangko Sentral ng Pilipinas has made financial inclusion a national
priority under its National Strategy for Financial Inclusion. AflaThrive gives {bank} a globally
validated, independently assessed delivery mechanism you can report to the BSP and surface
externally as a market-leading initiative.</p>

<p><strong>Scale:</strong> The curriculum is modular, short, structured modules that drop into {delivery_label}.
Pre and post assessment data flows back to you. It scales without adding operational burden.</p>

<p>I have attached a one-pager with more detail. I would welcome a brief call to explore the fit,
would next week work for you?</p>

<p>Best regards,<br>
<strong>Julian Coulbert</strong><br>
AflaThrive</p>
"""

SUBJECT_B = "AflaThrive x {bank}, Financial Education Built for Mobile First Banking"

BODY_PLAIN_B = """\
Dear {first_name},

{opening_line}

{bank} has built a mobile first product with real distribution. What most digital banks lack is a \
structured, globally validated financial education layer inside the app itself, one that increases \
activation, deepens engagement, and gives users a reason to open the app beyond checking a balance.

That is what AflaThrive provides.

I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated \
financial education organisation deployed in 112 countries, with 42 million young people reached \
across 50 languages. We license a structured financial education curriculum that embeds directly \
into your onboarding flow and in app experience. Your brand. Your interface. Your customer relationship.

For {bank} specifically:

Engagement: {retention_line}

Onboarding: A short, gamified financial education module during onboarding increases completion \
rates and gives new users an early, positive interaction with the app, rather than a blank dashboard.

Retention: Structured content keeps users returning between transactions. It integrates via SDK or \
embedded webview and scales without adding operational burden.

I have attached a one-pager with more detail. I would welcome a brief call to explore the fit, \
would next week work for you?

Best regards,
Julian Coulbert
AflaThrive
"""

BODY_HTML_B = """\
<p>Dear {first_name},</p>

<p>{opening_line}</p>

<p>{bank} has built a mobile first product with real distribution. What most digital banks lack is a
structured, globally validated financial education layer inside the app itself, one that increases
activation, deepens engagement, and gives users a reason to open the app beyond checking a balance.</p>

<p>That is what AflaThrive provides.</p>

<p>I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated
financial education organisation deployed in 112 countries, with 42 million young people reached
across 50 languages. We license a structured financial education curriculum that embeds directly
into your onboarding flow and in app experience. Your brand. Your interface. Your customer relationship.</p>

<p><strong>For {bank} specifically:</strong></p>

<p><strong>Engagement:</strong> {retention_line}</p>

<p><strong>Onboarding:</strong> A short, gamified financial education module during onboarding increases
completion rates and gives new users an early, positive interaction with the app, rather than a
blank dashboard.</p>

<p><strong>Retention:</strong> Structured content keeps users returning between transactions. It integrates
via SDK or embedded webview and scales without adding operational burden.</p>

<p>I have attached a one-pager with more detail. I would welcome a brief call to explore the fit,
would next week work for you?</p>

<p>Best regards,<br>
<strong>Julian Coulbert</strong><br>
AflaThrive</p>
"""

DELIVERY_LABELS = {
    "youth": "youth banking product or school programmes",
    "employees": "employee financial wellness programme",
    "communities": "community outreach and foundation delivery",
    "mixed": "foundation and community programmes",
}

STAKEHOLDER_LABELS = {
    "youth": "ESG and youth-banking",
    "employees": "HR and ESG",
    "communities": "foundation and CSR",
    "mixed": "foundation, CSR, and ESG",
}


def generate_email(contact: dict, profile: dict) -> tuple:
    required = ["opening_line", "retention_line"]
    missing = [f for f in required if not profile.get(f)]
    if missing:
        raise ValueError(f"Missing verified fields for {contact['bank']}: {missing}. Run research first.")

    bank_type = contact.get("bank_type", "foundation")

    if bank_type == "digital":
        fields = {
            "first_name": contact["first_name"],
            "bank": contact["bank"],
            "opening_line": profile["opening_line"],
            "retention_line": profile["retention_line"],
        }
        return SUBJECT_B.format(**fields), BODY_PLAIN_B.format(**fields), BODY_HTML_B.format(**fields)

    audience = profile.get("audience", "mixed")
    foundation_ref = profile.get("foundation_name") or f"{contact['bank']} Foundation"

    fields = {
        "first_name": contact["first_name"],
        "bank": contact["bank"],
        "opening_line": profile["opening_line"],
        "foundation_ref": foundation_ref,
        "retention_line": profile["retention_line"],
        "stakeholder_label": STAKEHOLDER_LABELS.get(audience, STAKEHOLDER_LABELS["mixed"]),
        "delivery_label": DELIVERY_LABELS.get(audience, DELIVERY_LABELS["mixed"]),
    }

    return SUBJECT_A.format(**fields), BODY_PLAIN_A.format(**fields), BODY_HTML_A.format(**fields)
