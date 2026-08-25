import re

from ..analysis.ats_scorer import _clean_skill, calculate_keyword_match
from .domains import active_keywords, kw_in_text


def _extract_explicit_jd_skills(jd_text: str) -> set:
    """Extract comma/bullet skill lists from common non-canonical JD headings."""
    candidates = set()
    for line in str(jd_text or "").splitlines():
        if not re.search(
            r"\b(skills?|requirements?|qualifications?|technologies|tools|competencies)\b",
            line,
            re.IGNORECASE,
        ):
            continue
        _, separator, values = line.partition(":")
        if not separator:
            continue
        from ..utils.text_cleaner import extract_skills_list

        candidates.update(_clean_skill(value) for value in extract_skills_list(values))
    return {skill for skill in candidates if skill}


def analyze_skill_gap(resume_data, jd_data, domain_keywords=None, ai_analysis=None) -> dict:
    """Analyze skill gap between resume and job description."""
    if not isinstance(resume_data, dict) or not isinstance(jd_data, dict):
        return _empty_skill_gap()
    if not resume_data.get("clean_text") or not jd_data.get("clean_text"):
        return _empty_skill_gap()

    keyword_result = calculate_keyword_match(resume_data, jd_data, domain_keywords)

    from ..utils.text_cleaner import get_skills_from_sections

    # Robust extraction: dedicated skills section first, vocab-scan fallback
    jd_skills = {str(s).lower() for s in keyword_result.get("jd_skills", [])}
    jd_text = jd_data.get("clean_text", jd_data.get("raw_text", ""))
    resume_text = resume_data.get("clean_text", resume_data.get("raw_text", ""))

    # Always scan complete documents. Section extraction is helpful for display,
    # but must not decide whether a valid skill participates in matching.
    known_vocab = active_keywords(jd_text, custom_keywords=domain_keywords)
    jd_skills |= {skill for skill in known_vocab if kw_in_text(skill, jd_text)}
    jd_skills |= _extract_explicit_jd_skills(jd_text)

    # AI can identify niche skills outside the curated vocabulary. Use those
    # labels only as a recovery source when deterministic extraction is empty.
    if not jd_skills and isinstance(ai_analysis, dict):
        for key in ("matched_skills", "partial_skills", "missing_skills"):
            jd_skills.update(
                _clean_skill(skill)
                for skill in ai_analysis.get(key, [])
                if _clean_skill(skill)
            )
    resume_skills = {
        str(s).lower() for s in get_skills_from_sections(resume_data.get("sections", {}))
    }
    from ..parser.section_extractor import extract_skill_names

    resume_skills |= {
        str(s).lower() for s in extract_skill_names(resume_text)
    }
    resume_skills |= {
        skill for skill in (domain_keywords or set())
        if kw_in_text(skill, resume_text)
    }
    if not resume_skills:
        resume_sections_text = resume_data.get("sections", {}).get("skills", "")
        resume_skills = {
            _clean_skill(s)
            for s in re.split(r"[,;\n]", resume_sections_text)
            if _clean_skill(s)
        }
        resume_skills.discard("")

    matched_skills = jd_skills.intersection(resume_skills)

    # Partial: JD skill present anywhere in the resume prose (word-boundary
    # match — 'go' must not match 'google') but not claimed in the skills list
    resume_text = resume_text.lower()
    partial_skills = set()
    missing_skills = set()

    for skill in jd_skills - matched_skills:
        if kw_in_text(skill, resume_text):
            partial_skills.add(skill)
        else:
            missing_skills.add(skill)

    if isinstance(ai_analysis, dict) and jd_skills:
        ai_matched = {
            _clean_skill(skill) for skill in ai_analysis.get("matched_skills", [])
            if _clean_skill(skill)
        }
        ai_partial = {
            _clean_skill(skill) for skill in ai_analysis.get("partial_skills", [])
            if _clean_skill(skill)
        }
        matched_skills |= ai_matched & jd_skills
        partial_skills |= ai_partial & jd_skills
        missing_skills -= matched_skills | partial_skills

    total = len(matched_skills) + len(partial_skills) + len(missing_skills)

    return {
        "matched_skills": sorted(matched_skills),
        "partial_skills": sorted(partial_skills),
        "missing_skills": sorted(missing_skills),
        "matched_count": len(matched_skills),
        "partial_count": len(partial_skills),
        "missing_count": len(missing_skills),
        "match_percentage": round(
            ((len(matched_skills) + len(partial_skills)) / total) * 100
        ) if total else 0,
        "resume_skills_detected": sorted(resume_skills),
        "jd_skills_detected": sorted(jd_skills),
    }


def _empty_skill_gap() -> dict:
    """Return a stable empty result for incomplete analysis inputs."""
    return {
        "matched_skills": [], "partial_skills": [], "missing_skills": [],
        "matched_count": 0, "partial_count": 0, "missing_count": 0,
        "match_percentage": 0, "resume_skills_detected": [],
        "jd_skills_detected": [],
    }


def build_skill_gap_dataframe(skill_gap: dict):
    """Build a Pandas DataFrame pipeline view of the skill gap.

    Columns: Skill | Requirement | Match | Priority
    This DataFrame feeds st.data_editor and Plotly visualizations directly.
    """
    import pandas as pd

    rows = []
    for skill in skill_gap.get("matched_skills", []):
        rows.append({
            "Skill": str(skill).title(),
            "Requirement": "Required",
            "Match": "Matched",
            "Priority": "High",
            "_level": 0,
        })
    for skill in skill_gap.get("partial_skills", []):
        rows.append({
            "Skill": str(skill).title(),
            "Requirement": "Required",
            "Match": "Partial",
            "Priority": "Medium",
            "_level": 1,
        })
    for skill in skill_gap.get("missing_skills", []):
        rows.append({
            "Skill": str(skill).title(),
            "Requirement": "Missing",
            "Match": "Missing",
            "Priority": "Medium",
            "_level": 2,
        })

    if not rows:
        return pd.DataFrame(columns=["Skill", "Requirement", "Match", "Priority"])

    df = pd.DataFrame(rows)
    return (
        df.sort_values(["_level", "Skill"])
        .drop(columns="_level")
        .reset_index(drop=True)
    )


def build_breakdown_dataframe(breakdown: dict):
    """ATS breakdown dict -> tidy DataFrame (Category | Score) for charting."""
    import pandas as pd

    df = pd.DataFrame(
        [{"Category": k, "Score": int(v)} for k, v in breakdown.items()]
    )
    return df.sort_values("Score", ascending=False).reset_index(drop=True)


def get_skill_priority(missing_skills, jd_data) -> list:
    """Assign priority to missing skills based on how often they appear in the JD."""
    priorities = []
    jd_text = jd_data.get("clean_text", "").lower()

    for skill in missing_skills:
        skill_lower = str(skill).lower()
        occurrences = jd_text.count(skill_lower)
        priority_level = "High" if occurrences >= 2 else "Medium"
        priorities.append({"skill": skill, "priority": priority_level})

    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(priorities, key=lambda x: order.get(x["priority"], 3))
