"""Text cleaning, robust section detection and skills-list extraction."""

import re

# Canonical sections -> header keyword patterns (substring match on a
# short normalized line). Order matters only for combined headers:
# e.g. "EDUCATION & CERTIFICATIONS" should win for BOTH keys.
SECTION_PATTERNS = {
    "summary": [
        r"professional\s+summary", r"career\s+(summary|objective|profile)",
        r"^summary", r"\bprofile\b", r"objective",
    ],
    "experience": [
        r"(work|professional|employment|relevant)\s+(experience|history)",
        r"employment\b", r"career\s+history", r"\bexperience\b",
    ],
    "skills": [
        r"(technical|core|key|professional|it)\s+(skills|competencies|expertise|proficiencies)",
        r"skills?\s*(&|and)?\s*(tools|technologies|interests)?",
        r"competencies", r"proficiencies", r"tech\s*stack", r"technologies",
        r"(software|technical)\s+(tools|proficiencies)",
    ],
    "education": [
        r"(academic|educational)\s+(background|qualification)",
        r"\beducation\b", r"qualifications?", r"academics?",
    ],
    "projects": [
        r"(key|selected|personal|academic)?\s*projects?",
        r"project\s+experience",
    ],
    "certifications": [
        r"certifications?(\s*(&|and)\s*(courses|licenses|training))?",
        r"certificates?", r"licenses?", r"courses?",
        r"achievements?( & awards)?", r"awards?",
    ],
}

# Precompiled: {section: [compiled_patterns]}
_COMPILED = {
    section: [re.compile(p, re.IGNORECASE) for p in patterns]
    for section, patterns in SECTION_PATTERNS.items()
}

_HEADER_STRIP = re.compile(r"^[\s\W_]+|[\s\W_:=\-]+$")  # decorative chars
_BULLET = re.compile(r"^[\s]*[•·▪‣◦\-–—*o]\s+", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Clean and normalize extracted text from PDF/TXT/DOCX/OCR."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _looks_like_header(line: str):
    """Return list of canonical sections this line looks like a header for.

    A header = short line (<= 60 chars), few lowercase words in the middle of
    the sentence sense, and matching one of the known section patterns after
    stripping decorations like '---', ':', '==', bullets.
    """
    if not line or len(line) > 60:
        return []

    stripped = _HEADER_STRIP.sub("", line.strip())
    if not stripped or len(stripped) > 50:
        return []
    # Headers rarely end with sentence punctuation
    if stripped.endswith((".", ";", ",")):
        return []
    # Reject obvious sentences (>=6 words with a verb-ish length)
    if len(stripped.split()) >= 7:
        return []

    hits = [s for s, pats in _COMPILED.items() if any(p.search(stripped) for p in pats)]
    return hits


def _is_generic_boundary(line: str) -> bool:
    """Detect UNKNOWN headers ('Responsibilities:', 'ABOUT US', 'PERKS & BENEFITS')
    so their content never leaks into a previous known section."""
    if not line or len(line) > 50:
        return False
    stripped = _HEADER_STRIP.sub("", line.strip())
    words = stripped.split()
    if not words or len(words) > 5:
        return False
    if line.strip().endswith(":"):
        return True
    return stripped.isupper() and len(words) <= 5


def _caps_colon_boundary(line: str):
    """Detect ALL-CAPS unknown labels starting a line: 'RESPONSIBILITIES: ...',
    'BENEFITS: ...'. Returns the inline remainder, or None. Conservative on
    purpose — Title-case sub-labels ('Languages: Python') stay as content."""
    head, sep, tail = line.partition(":")
    if not sep:
        return None
    head = head.strip()
    if not head or len(head) > 30 or len(head.split()) > 4:
        return None
    if not head.replace(" ", "").isalpha():
        return None
    if not head.isupper():
        return None
    return tail.strip()


def extract_sections(text: str) -> dict:
    """Detect resume sections and return {section: content}.

    Handles decorated real-world headers ('TECHNICAL SKILLS', 'Work
    Experience', 'PROFESSIONAL SUMMARY ----------'), INLINE values
    ('PREFERRED SKILLS: Kubernetes, React'), and isolates unknown headers
    ('RESPONSIBILITIES:') into '_other' so they cannot pollute known sections.
    """
    sections = {
        "summary": "", "skills": "", "education": "",
        "experience": "", "projects": "", "certifications": "",
    }
    current = None
    buffer: dict = {}

    def _push(bucket, value):
        if value.strip():
            buffer.setdefault(bucket, []).append(value.strip())

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        hits = _looks_like_header(line)
        if hits:
            current = hits[0]  # primary section for subsequent lines
            # Inline value after the header phrase: 'SKILLS: Python, Go'
            m = re.search(r"[:\-\u2013\u2014]\s*(.+)$", line)
            if m:
                rest = m.group(1).strip()
                if rest and re.search(r"[A-Za-z0-9]", rest):
                    _push(current, rest)
            continue

        if _is_generic_boundary(line):
            current = "_other"
            continue

        caps_tail = _caps_colon_boundary(line)
        if caps_tail is not None:
            current = "_other"
            _push("_other", caps_tail)
            continue

        if current is None:
            _push("_header", line)
        else:
            _push(current, line)

    for key, lines in buffer.items():
        joined = "\n".join(lines).strip()
        sections[key] = joined

    return sections


# Matches 'Languages:', 'Core:', 'Frontend -' style labels glued to a token
_LABEL_PREFIX = re.compile(r"^[A-Za-z][A-Za-z /&+#.]{0,24}[:\-\u2013]\s+")


def extract_skills_list(skills_text: str) -> list:
    """Turn a raw SKILLS section into a clean list of skill names.

    Splits on commas, semicolons, pipes, bullets and newlines; strips noise,
    category labels ('Languages: Python' -> 'Python') and sentence fragments.
    """
    if not skills_text:
        return []

    parts = re.split(r"[,\n;|•·▪]+", skills_text)
    skills = []
    seen_lower = set()
    stop_words = {
        "and", "the", "with", "of", "in", "etc", "others", "tools",
        "technologies", "skills", "proficient", "familiar", "working",
        "knowledge", "excellent", "good", "strong", "years",
    }

    for part in parts:
        token = part.strip(" .:*()[]-–—")
        token = _LABEL_PREFIX.sub("", token)  # drop 'Languages:' prefixes
        token = token.strip(" .:*()[]-–—")
        if not token or len(token) < 2 or len(token) > 40:
            continue
        lower = token.lower()
        if lower in stop_words or lower.isdigit() or lower in seen_lower:
            continue
        if len(token.split()) >= 5:  # sentence-like prose fragment
            continue
        seen_lower.add(lower)
        skills.append(token)

    return skills


def get_skills_from_sections(sections: dict) -> list:
    """Best-effort skills list: dedicated section first, then tech-keyword scan."""
    skills = extract_skills_list(sections.get("skills", ""))
    if skills:
        return skills
    # Fallback: scan whole text for known technology names
    try:
        from ..parser.section_extractor import extract_skill_names

        full_text = " ".join(str(v) for v in sections.values())
        return extract_skill_names(full_text)
    except Exception:
        return []
