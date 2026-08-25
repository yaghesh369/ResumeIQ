import re

from .domains import active_keywords, kw_in_text, DOMAIN_PROFILES


# Backwards-compat alias for older imports
TECH_KEYWORDS = DOMAIN_PROFILES["Technology"]


def _kw_in_text(keyword: str, text: str) -> bool:
    return kw_in_text(keyword, text)


def _clean_skill(raw):
    """Normalize a raw skill token: strip labels, punctuation, empties."""
    s = re.sub(r"^(required|preferred|nice\s*to\s*have|must\s*have)\s*[:\-]\s*", "", str(raw).strip(), flags=re.IGNORECASE)
    s = s.strip(" .;:-*•")
    return s.lower()


def extract_experience_years(text):
    """Extract years of experience mentioned in text."""
    if not text:
        return None
    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:professional\s*)?(?:work\s*)?experience",
        r"experience\s*:?\s*(\d+)\+?\s*years?",
        r"(\d+)\+?\s*years?\s+in\s",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def _vocab_for(jd_data, domain_keywords) -> set:
    """Active vocabulary = auto-detected profiles (+ optional manual override)."""
    vocab = active_keywords(jd_data.get("clean_text", ""))
    if domain_keywords:
        vocab |= {str(k).lower() for k in domain_keywords}
    return vocab


def calculate_keyword_match(resume_data, jd_data, domain_keywords=None) -> dict:
    """Calculate keyword match percentage between resume and job description."""
    resume_text = resume_data["clean_text"].lower()
    jd_text = jd_data["clean_text"].lower()

    jd_sections = jd_data.get("sections", {})
    resume_sections = resume_data.get("sections", {})
    vocab = _vocab_for(jd_data, domain_keywords)

    # 1) Dedicated skills section of the JD (robust extractor)
    from ..utils.text_cleaner import extract_skills_list, get_skills_from_sections

    jd_skills = {
        _clean_skill(s) for s in extract_skills_list(jd_sections.get("skills", ""))
    }
    jd_skills.discard("")

    # 2) Always supplement with domain keywords present in the JD —
    #    skill bullets are often prose ('Strong PostgreSQL knowledge') that a
    #    tokenizer cannot cleanly split.
    jd_skills |= {kw for kw in vocab if _kw_in_text(kw, jd_text)}

    # Resume skills: robust extraction (section + scan fallback)
    resume_skills = {_clean_skill(s) for s in get_skills_from_sections(resume_sections)}
    resume_skills.discard("")
    if not resume_skills:
        resume_skills = {kw for kw in vocab if _kw_in_text(kw, resume_text)}

    matched_skills = jd_skills.intersection(resume_skills)
    total_skills = len(jd_skills) if jd_skills else 1

    match_pct = round((len(matched_skills) / total_skills) * 100) if total_skills else 0

    return {
        "keyword_match": min(match_pct, 100),
        "matched_skills": sorted(matched_skills),
        "jd_skills": sorted(jd_skills),
        "total_skills": total_skills,
        "resume_skills": sorted(resume_skills),
    }


def calculate_technical_skills_score(resume_data, jd_data, domain_keywords=None) -> dict:
    """Score how many domain keywords from the JD appear anywhere in the resume."""
    jd_text = jd_data["clean_text"].lower()
    resume_text = resume_data["clean_text"].lower()
    vocab = _vocab_for(jd_data, domain_keywords)

    required = [kw for kw in vocab if _kw_in_text(kw, jd_text)]
    if not required:
        return {"technical_score": 75, "required_tech": [], "found_tech": []}

    found = [kw for kw in required if _kw_in_text(kw, resume_text)]
    score = round((len(found) / len(required)) * 100)

    return {
        "technical_score": min(score, 100),
        "required_tech": sorted(required),
        "found_tech": sorted(found),
    }


def calculate_experience_match(resume_data, jd_data) -> dict:
    """Calculate experience match score."""
    resume_exp = resume_data.get("sections", {}).get("experience", "")
    resume_full = resume_data.get("clean_text", "")
    jd_full = jd_data.get("clean_text", "")

    resume_years = extract_experience_years(resume_exp) or extract_experience_years(resume_full)
    jd_years = extract_experience_years(jd_full)

    if not jd_years:
        return {"experience_score": 80, "required_years": None, "resume_years": resume_years}

    if resume_years is None:
        return {"experience_score": 50, "required_years": jd_years, "resume_years": None}

    if resume_years >= jd_years:
        score = 100
    elif resume_years >= jd_years * 0.7:
        score = 80
    elif resume_years >= jd_years * 0.5:
        score = 60
    else:
        score = 30

    return {
        "experience_score": score,
        "required_years": jd_years,
        "resume_years": resume_years,
    }


def calculate_project_match(resume_data, jd_data) -> dict:
    """Calculate projects relevance score (domain-neutral)."""
    resume_projects = resume_data.get("sections", {}).get("projects", "")
    jd_text = jd_data.get("clean_text", "").lower()

    jd_emphasizes_projects = any(
        _kw_in_text(w, jd_text) for w in ("project", "portfolio", "case study")
    )

    if not resume_projects.strip():
        # No projects listed: penalise more when the JD actually asks for them
        return {"project_score": 40 if jd_emphasizes_projects else 65}
    return {"project_score": 85 if jd_emphasizes_projects else 90}


def calculate_education_match(resume_data, jd_data) -> dict:
    """Calculate education match score."""
    resume_edu = resume_data.get("sections", {}).get("education", "")
    jd_edu = jd_data.get("sections", {}).get("education", "") + " " + jd_data.get("clean_text", "")

    degree_words = ["degree", "bachelor", "master", "phd", "b.tech", "m.tech", "bsc", "msc"]

    resume_has_degree = any(w in resume_edu.lower() for w in degree_words)
    jd_requires_degree = any(w in jd_edu.lower() for w in degree_words)

    if jd_requires_degree and not resume_has_degree:
        return {"education_score": 30}
    if jd_requires_degree and resume_has_degree:
        return {"education_score": 100}
    return {"education_score": 85}


def calculate_structure_score(resume_data) -> dict:
    """Calculate structure/format completeness score."""
    sections = resume_data.get("sections", {})
    expected = ["summary", "skills", "education", "experience", "projects"]
    found = [s for s in expected if sections.get(s, "").strip()]

    score = round((len(found) / len(expected)) * 100)
    return {"structure_score": score}


def calculate_ats_score(resume_data, jd_data, domain_keywords=None) -> dict:
    """Calculate overall Estimated ATS Compatibility Score.

    Deterministic weighted engine per the project plan:
    Keyword Match 25% | Skill Relevance 25% | Experience 20%
    Projects 15% | Education 10% | Structure 5%

    domain_keywords: optional manual-override vocabulary from the sidebar.
    """
    keyword = calculate_keyword_match(resume_data, jd_data, domain_keywords)
    technical = calculate_technical_skills_score(resume_data, jd_data, domain_keywords)
    experience = calculate_experience_match(resume_data, jd_data)
    projects = calculate_project_match(resume_data, jd_data)
    education = calculate_education_match(resume_data, jd_data)
    structure = calculate_structure_score(resume_data)

    ats_score = (
        keyword["keyword_match"] * 0.25
        + technical["technical_score"] * 0.25
        + experience["experience_score"] * 0.20
        + projects["project_score"] * 0.15
        + education["education_score"] * 0.10
        + structure["structure_score"] * 0.05
    )

    return {
        "ats_score": round(ats_score),
        "breakdown": {
            "Keyword Match": keyword["keyword_match"],
            "Skill Relevance": technical["technical_score"],
            "Experience": experience["experience_score"],
            "Projects": projects["project_score"],
            "Education": education["education_score"],
            "Structure": structure["structure_score"],
        },
        "details": {
            "matched_keywords": keyword["matched_skills"],
            "resume_years": experience["resume_years"],
            "required_years": experience["required_years"],
        },
    }
