"""Experience analysis utilities (plan module: analysis/experience_analyzer.py)."""

import re

from .ats_scorer import extract_experience_years


def analyze_experience(resume_data, jd_data) -> dict:
    """Compare candidate experience against the job requirement.

    Returns a structured summary used by the dashboard and recommendations.
    """
    resume_text = resume_data.get("clean_text", "")
    jd_text = jd_data.get("clean_text", "")

    resume_years = extract_experience_years(resume_text)
    required_years = extract_experience_years(jd_text)

    verdict, score = _evaluate(resume_years, required_years)

    return {
        "resume_years": resume_years,
        "required_years": required_years,
        "score": score,
        "verdict": verdict,
        "seniority": estimate_seniority(resume_years),
        "job_titles": extract_job_titles(resume_text),
    }


def _evaluate(resume_years, required_years):
    if required_years is None:
        return "No explicit experience requirement detected.", 80
    if resume_years is None:
        return (
            f"JD asks for {required_years}+ years but your resume does not state "
            "total years of experience. Add a clear years figure to your summary.",
            50,
        )
    if resume_years >= required_years:
        return f"Meets requirement ({resume_years}y >= {required_years}y).", 100
    if resume_years >= required_years * 0.7:
        return f"Close: {resume_years}y vs {required_years}y required. Emphasize relevant depth.", 80
    if resume_years >= required_years * 0.5:
        return f"Below bar: {resume_years}y vs {required_years}y. Lead with strongest projects.", 60
    return f"Significantly under: {resume_years}y vs {required_years}y required.", 30


def estimate_seniority(years):
    """Map total experience to a seniority band."""
    if years is None:
        return "Unknown"
    if years < 1:
        return "Entry-level"
    if years < 3:
        return "Junior"
    if years < 5:
        return "Mid-level"
    if years < 8:
        return "Senior"
    return "Staff/Principal"


def extract_job_titles(text):
    """Heuristic extraction of likely job titles across all supported domains."""
    titles = [
        # Technology
        "Software Engineer", "Backend Developer", "Frontend Developer",
        "Full Stack Developer", "Data Scientist", "Data Analyst",
        "Machine Learning Engineer", "DevOps Engineer", "Product Manager",
        "QA Engineer", "Mobile Developer", "Web Developer",
        # Marketing / Sales
        "Marketing Executive", "Marketing Manager", "Digital Marketing",
        "SEO Specialist", "Content Writer", "Social Media Manager",
        "Sales Executive", "Sales Manager", "Business Development",
        "Account Manager",
        # Finance / Operations
        "Accountant", "Financial Analyst", "Auditor", "Tax Consultant",
        "Operations Manager", "Supply Chain", "Logistics Coordinator",
        # Healthcare
        "Registered Nurse", "Staff Nurse", "Physiotherapist",
        "Medical Coder", "Pharmacist", "Lab Technician",
        # HR / Design / Education
        "HR Executive", "HR Manager", "Recruiter",
        "UI Designer", "UX Designer", "Graphic Designer",
        "Teacher", "Lecturer", "Professor", "Trainer",
    ]
    found = [t for t in titles if re.search(rf"\b{re.escape(t)}s?\b", text or "", re.IGNORECASE)]
    return found[:5]
