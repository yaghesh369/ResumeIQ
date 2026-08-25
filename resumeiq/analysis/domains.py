"""Domain-aware keyword vocabulary for ResumeIQ.

Provides curated keyword profiles for 9 broad job domains plus a shared
professional core. The active vocabulary for scoring is resolved from the
job description (auto-detect) or a manual sidebar override — keeping the
scoring pipeline fully deterministic (no AI calls).
"""

import re

# Word-boundary matcher: 'go' must not hit 'google', 'excel' not 'excellent',
# 'sql' not 'postgresql'. Compiled once per keyword.
_KW_CACHE = {}
_KW_LEFT = r"(?<![A-Za-z0-9_+.#/])"
_KW_RIGHT = r"(?![A-Za-z0-9_+#])"


def kw_in_text(keyword: str, text: str) -> bool:
    pat = _KW_CACHE.get(keyword)
    if pat is None:
        pat = re.compile(_KW_LEFT + re.escape(keyword) + _KW_RIGHT, re.IGNORECASE)
        _KW_CACHE[keyword] = pat
    return bool(pat.search(text))


# ---------------------------------------------------------------------------
# Shared professional core — relevant in virtually every white-collar domain
# ---------------------------------------------------------------------------

CORE_KEYWORDS = {
    # Deliberately slim: every term here must be unambiguous as a *skill*
    # (e.g. 'excel' ok, but bare 'planning'/'research' occur in normal prose
    # and would distort match percentages).
    "communication", "leadership", "teamwork", "negotiation",
    "presentation", "customer service", "stakeholder management",
    "project management", "time management", "problem solving",
    "ms office", "microsoft office", "excel", "powerpoint",
    "kpi", "analytics", "crm", "erp", "compliance", "quality assurance",
    "process improvement", "vendor management",
    "slack", "zoom", "notion", "trello", "asana",
}

# ---------------------------------------------------------------------------
# Domain profiles
# ---------------------------------------------------------------------------

DOMAIN_PROFILES = {
    "Technology": {
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "django", "flask", "fastapi", "spring", "node.js", "express", "laravel",
        "postgresql", "mysql", "mongodb", "redis", "sql", "oracle", "sqlite",
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins",
        "react", "angular", "vue", "next.js", "html", "css", "tailwind",
        "git", "github", "gitlab", "ci/cd", "linux", "rest", "graphql",
        "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn", "keras",
        "machine learning", "deep learning", "data analysis", "nlp",
        "microservices", "agile", "scrum", "jira", "kafka", "spark", "hadoop",
        "power bi", "tableau", "selenium", "android", "ios", "flutter",
    },
    "Marketing": {
        "seo", "sem", "google ads", "google analytics", "ga4", "meta ads",
        "facebook ads", "instagram marketing", "linkedin marketing",
        "content marketing", "email marketing", "social media",
        "copywriting", "content strategy", "brand management", "branding",
        "campaign management", "lead generation", "market research",
        "hubspot", "marketo", "mailchimp", "canva", "semrush", "ahrefs",
        "a/b testing", "conversion rate optimization", "roi", "roas",
        "influencer marketing", "affiliate marketing", "public relations",
        "event marketing", "product marketing", "growth marketing",
    },
    "Sales": {
        "salesforce", "pipeline management", "cold calling", "cold emailing",
        "prospecting", "lead qualification", "quota", "upselling",
        "cross-selling", "account management", "b2b", "b2c", "saas sales",
        "deal closing", "client relationship", "territory management",
        "sales forecasting", "demos", "contract negotiation", "zoho crm",
        "outreach", "revenue targets", "inside sales", "field sales",
        "channel partners", "rfp", "retention",
    },
    "Finance": {
        "accounting", "bookkeeping", "financial analysis", "financial modeling",
        "forecasting", "variance analysis", "audit", "internal audit",
        "taxation", "tax returns", "gst", "tds", "ifrs", "gaap", "ind as",
        "quickbooks", "tally", "sap fico", "xero", "accounts payable",
        "accounts receivable", "reconciliation", "payroll processing",
        "treasury", "risk management", "investment analysis", "portfolio management",
        "equity research", "credit analysis", "cost accounting", "mis reporting",
    },
    "Healthcare": {
        "patient care", "clinical", "clinical research", "hipaa", "medical terminology",
        "ehr", "emr", "epic", "cerner", "icd-10", "cpt coding", "medical coding",
        "medical billing", "phlebotomy", "vital signs", "medication administration",
        "pharmacology", "pathology", "radiology", "triage", "care plan",
        "cpr", "bls", "acls", "infection control", "telehealth", "laboratory",
        "specimen collection", "patient assessment", "nursing", "physiotherapy",
    },
    "Human Resources": {
        "recruitment", "talent acquisition", "onboarding", "offboarding",
        "payroll", "hrms", "workday", "bamboohr", "greenhouse", "naukri",
        "employee relations", "performance management", "appraisal",
        "compensation and benefits", "labor law", "labour law", "statutory compliance",
        "employee engagement", "hr policies", "exit interviews", "succession planning",
        "learning and development", "training needs", "grievance handling",
        "attendance management", "esic", "provident fund", "gratuity",
    },
    "Design": {
        "figma", "adobe xd", "sketch", "photoshop", "illustrator", "indesign",
        "after effects", "premiere pro", "ui", "ux", "ui/ux", "wireframing",
        "prototyping", "user research", "usability testing", "personas",
        "user flows", "information architecture", "interaction design",
        "typography", "color theory", "design systems", "accessibility",
        "motion graphics", "3d modeling", "blender", "brand identity",
        "print design", "packaging design",
    },
    "Education": {
        "curriculum development", "lesson planning", "classroom management",
        "pedagogy", "instructional design", "assessment", "grading",
        "student engagement", "differentiated instruction", "e-learning",
        "lms", "moodle", "blackboard", "canvas lms", "teaching", "tutoring",
        "syllabus", "academic advising", "parent communication",
        "extracurricular", "cbse", "icse", "ib", "montessori", "special education",
    },
    "Operations": {
        "supply chain", "logistics", "procurement", "purchasing", "inventory management",
        "warehouse management", "six sigma", "lean", "5s", "kaizen",
        "process optimization", "capacity planning", "demand forecasting",
        "production planning", "vendor development", "supplier negotiation",
        "iso", "root cause analysis", "continuous improvement", "fleet management",
        "distribution", "dispatch", "stock reconciliation", "material management",
    },
}

# Manual override options shown in the sidebar
DOMAIN_CHOICES = ["Auto", "Custom"] + list(DOMAIN_PROFILES.keys())

# Minimum keyword hits before a profile is considered 'active'
DETECT_THRESHOLD = 3


def detect_domains(jd_text: str) -> dict:
    """Count profile-keyword hits in the JD text.

    Returns {"scores": {domain: hits}, "primary": best|None, "matched": [active]}
    where matched = profiles with >= DETECT_THRESHOLD hits, ranked by hits.
    """
    text = jd_text or ""
    scores = {
        name: sum(1 for kw in kws if kw_in_text(kw, text))
        for name, kws in DOMAIN_PROFILES.items()
    }
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    primary = ranked[0][0] if ranked and ranked[0][1] > 0 else None
    matched = [name for name, hits in ranked if hits >= DETECT_THRESHOLD][:2]
    return {"scores": scores, "primary": primary, "matched": matched}


def active_keywords(jd_text: str, override: str = "Auto", custom_keywords=None) -> set:
    """Resolve the active scoring vocabulary.

    override='Auto' -> core + up to 2 auto-detected profiles (fallback: core only).
    override=<domain> -> core + that full profile.
    """
    vocab = set(CORE_KEYWORDS)
    if override == "Custom":
        return vocab | {
            str(keyword).strip().lower()
            for keyword in (custom_keywords or [])
            if str(keyword).strip()
        }
    if override and override in DOMAIN_PROFILES:
        vocab |= DOMAIN_PROFILES[override]
        return vocab
    result = detect_domains(jd_text)
    for name in result["matched"]:
        vocab |= DOMAIN_PROFILES[name]
    return vocab


def resolve_domain(jd_text: str, override: str = "Auto", custom_keywords=None) -> dict:
    """Full resolution used by the UI: detected info + final label."""
    detection = detect_domains(jd_text)
    if override == "Custom":
        label = "Custom"
    elif override and override in DOMAIN_PROFILES:
        label = override
    else:
        label = detection["primary"] or "General"
    return {
        "label": label,
        "override": bool(override == "Custom" or (override and override in DOMAIN_PROFILES)),
        **detection,
    }


# Backwards-compat alias: existing imports of TECH_KEYWORDS keep working
TECH_KEYWORDS = DOMAIN_PROFILES["Technology"]
