"""
Email templates for AflaThrive outreach.
Template A: Banks / Corporates — foundation, CSR, or employee wellness pitch
Template B: Digital banks / neobanks — product engagement pitch
Template C: Schools — curriculum partnership pitch
"""

SUBJECT = "AflaThrive x {bank}: Globally Validated Financial Education"

# ── Template A: Banks & Corporates ────────────────────────────────────────────

BODY_PLAIN_A = """\
Dear {first_name},

{opening_line}

{foundation_ref} has the reach and the delivery infrastructure. What it does not yet have is a \
structured, globally validated curriculum that changes financial behaviour measurably and gives \
{bank} a reportable, third-party-validated outcome to show your {stakeholder_label} stakeholders.

That is what AflaThrive provides.

I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated \
financial education organisation deployed in 112 countries, with 42 million young people reached \
across 50 languages. We license a structured financial education curriculum that embeds directly \
into your {delivery_label}. Your brand. Your interface. Your customer relationship.

For {bank} specifically:

Impact: {retention_line}

Scale: The curriculum is modular, with short, structured modules that drop into {delivery_label}. \
Pre and post assessment data flows back to you. It scales without adding operational burden.

I have attached a one-pager with more detail. I would welcome a brief call to explore the fit. \
Would next week work for you?

Best regards,
Julian Coulbert
AflaThrive
"""

BODY_HTML_A = """\
<p>Dear {first_name},</p>

<p>{opening_line}</p>

<p>{foundation_ref} has the reach and the delivery infrastructure. What it does not yet have is a
structured, globally validated curriculum that changes financial behaviour measurably and gives
{bank} a reportable, third-party-validated outcome to show your {stakeholder_label} stakeholders.</p>

<p>That is what AflaThrive provides.</p>

<p>I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated
financial education organisation deployed in 112 countries, with 42 million young people reached
across 50 languages. We license a structured financial education curriculum that embeds directly
into your {delivery_label}. Your brand. Your interface. Your customer relationship.</p>

<p><strong>For {bank} specifically:</strong></p>

<p><strong>Impact:</strong> {retention_line}</p>

<p><strong>Scale:</strong> The curriculum is modular, with short, structured modules that drop into {delivery_label}.
Pre and post assessment data flows back to you. It scales without adding operational burden.</p>

<p>I have attached a one-pager with more detail. I would welcome a brief call to explore the fit.
Would next week work for you?</p>

<p>Best regards,<br>
<strong>Julian Coulbert</strong><br>
AflaThrive</p>
"""

# ── Template B: Digital banks / neobanks ──────────────────────────────────────

BODY_PLAIN_B = """\
Dear {first_name},

{opening_line}

{bank} is building one of the most accessible digital banking experiences in the region. \
Financial access is the platform. Sustained engagement comes from behaviour change. Customers who \
understand money manage it better, stay longer, and refer more.

That is what AflaThrive delivers.

I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated \
financial education organisation deployed in 112 countries, with 42 million participants reached \
across 50 languages. We license a structured financial education curriculum that embeds directly \
into your product experience. Your brand. Your interface. Your user relationship.

For {bank} specifically:

Engagement: {retention_line}

Regulator narrative: Regulators across the region are driving financial inclusion as a national \
priority. An embedded, globally validated financial education layer gives {bank} a differentiated \
compliance narrative and a stronger story for regulators and investors.

Integration: The curriculum is modular, with bite-sized, mobile-first content that drops into \
onboarding flows or a dedicated learning section. Assessment data flows back to you. No operational overhead.

I have attached a one-pager with more detail. Happy to set up a short call to explore the fit. \
Would next week work?

Best regards,
Julian Coulbert
AflaThrive
"""

BODY_HTML_B = """\
<p>Dear {first_name},</p>

<p>{opening_line}</p>

<p>{bank} is building one of the most accessible digital banking experiences in the region.
Financial access is the platform. Sustained engagement comes from behaviour change. Customers who
understand money manage it better, stay longer, and refer more.</p>

<p>That is what AflaThrive delivers.</p>

<p>I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated
financial education organisation deployed in 112 countries, with 42 million participants reached
across 50 languages. We license a structured financial education curriculum that embeds directly
into your product experience. Your brand. Your interface. Your user relationship.</p>

<p><strong>For {bank} specifically:</strong></p>

<p><strong>Engagement:</strong> {retention_line}</p>

<p><strong>Regulator narrative:</strong> Regulators across the region are driving financial inclusion as a
national priority. An embedded, globally validated financial education layer gives {bank} a
differentiated compliance narrative and a stronger story for regulators and investors.</p>

<p><strong>Integration:</strong> The curriculum is modular, with bite-sized, mobile-first content that drops into
onboarding flows or a dedicated learning section. Assessment data flows back to you. No operational overhead.</p>

<p>I have attached a one-pager with more detail. Happy to set up a short call to explore the fit.
Would next week work?</p>

<p>Best regards,<br>
<strong>Julian Coulbert</strong><br>
AflaThrive</p>
"""

# ── Template C: Schools ───────────────────────────────────────────────────────

BODY_PLAIN_C = """\
Dear {first_name},

{opening_line}

{bank} is shaping students who will make financial decisions for decades. What {bank} does not \
yet have is a globally validated curriculum with pre and post assessment data that gives you a \
measurable, reportable learning outcome.

That is what AflaThrive provides.

I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated \
financial education organisation deployed in 112 countries, with 42 million young people reached \
across 50 languages. We license a structured financial literacy curriculum designed specifically \
for young people. Your school delivers it. Your students own the outcome.

For {bank} specifically:

Impact: {retention_line}

Integration: The curriculum is modular and classroom-ready, with structured lessons that map to \
your existing timetable. Self-paced digital modules are also available. Pre and post assessment \
data flows to your academic team. No additional operational burden.

I have attached a one-pager with more detail. I would welcome a brief call to explore whether \
there is a fit. Would next week work?

Best regards,
Julian Coulbert
AflaThrive
"""

BODY_HTML_C = """\
<p>Dear {first_name},</p>

<p>{opening_line}</p>

<p>{bank} is shaping students who will make financial decisions for decades. What {bank} does not
yet have is a globally validated curriculum with pre and post assessment data that gives you a
measurable, reportable learning outcome.</p>

<p>That is what AflaThrive provides.</p>

<p>I work with AflaThrive, the commercial arm of Aflatoun International. We are a World Bank-validated
financial education organisation deployed in 112 countries, with 42 million young people reached
across 50 languages. We license a structured financial literacy curriculum designed specifically
for young people. Your school delivers it. Your students own the outcome.</p>

<p><strong>For {bank} specifically:</strong></p>

<p><strong>Impact:</strong> {retention_line}</p>

<p><strong>Integration:</strong> The curriculum is modular and classroom-ready, with structured lessons that map to
your existing timetable. Self-paced digital modules are also available. Pre and post assessment
data flows to your academic team. No additional operational burden.</p>

<p>I have attached a one-pager with more detail. I would welcome a brief call to explore whether
there is a fit. Would next week work?</p>

<p>Best regards,<br>
<strong>Julian Coulbert</strong><br>
AflaThrive</p>
"""

# ── Lookup tables ─────────────────────────────────────────────────────────────

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


def generate_email(contact: dict, profile: dict) -> tuple[str, str, str]:
    """
    Returns (subject, body_plain, body_html).
    Routes by bank_type:
      "digital"    -> Template B
      "school"     -> Template C
      everything else -> Template A (foundation, corporate, mixed)
    Raises ValueError if any critical field is missing.
    """
    required = ["opening_line", "retention_line"]
    missing = [f for f in required if not profile.get(f)]
    if missing:
        raise ValueError(f"Missing verified fields for {contact['bank']}: {missing}. Run research first.")

    audience = profile.get("audience", "mixed")
    foundation_ref = profile.get("foundation_name") or f"{contact['bank']} Foundation"
    bank_type = contact.get("bank_type", "foundation")

    fields = {
        "first_name": contact["first_name"],
        "bank": contact["bank"],
        "opening_line": profile["opening_line"],
        "foundation_ref": foundation_ref,
        "retention_line": profile["retention_line"],
        "stakeholder_label": STAKEHOLDER_LABELS.get(audience, STAKEHOLDER_LABELS["mixed"]),
        "delivery_label": DELIVERY_LABELS.get(audience, DELIVERY_LABELS["mixed"]),
    }

    subject = SUBJECT.format(**fields)

    if bank_type == "digital":
        body_plain = BODY_PLAIN_B.format(**fields)
        body_html = BODY_HTML_B.format(**fields)
    elif bank_type == "school":
        body_plain = BODY_PLAIN_C.format(**fields)
        body_html = BODY_HTML_C.format(**fields)
    else:
        body_plain = BODY_PLAIN_A.format(**fields)
        body_html = BODY_HTML_A.format(**fields)

    return subject, body_plain, body_html
