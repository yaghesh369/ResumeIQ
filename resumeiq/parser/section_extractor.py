"""Free-text skill/experience extraction helpers (domain-aware)."""

import re

from ..analysis.domains import DOMAIN_PROFILES, CORE_KEYWORDS, detect_domains, kw_in_text


def extract_skill_names(text) -> list:
    """Extract known skill names from free text using the domain vocabulary.

    Auto-detects which domain profile(s) the text belongs to, then scans for
    those keywords plus the shared professional core — works for nurses,
    teachers and accountants, not just developers.
    """
    if not text:
        return []

    vocab = set(CORE_KEYWORDS)
    detection = detect_domains(text)
    if detection["matched"]:
        for name in detection["matched"]:
            vocab |= DOMAIN_PROFILES[name]
    else:
        # No clear domain: scan every profile (cheap, word-boundary regex)
        for kws in DOMAIN_PROFILES.values():
            vocab |= kws

    found = [kw for kw in sorted(vocab) if kw_in_text(kw, text)]
    return found


def extract_experience_years(text):
    """Extract total years of experience from text."""
    if not text:
        return None

    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
        r"experience.*?(\d+)\+?\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None
