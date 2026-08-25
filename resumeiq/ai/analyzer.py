from ..ai.gemini_client import (
    analyze_resume_against_jd,
    generate_resume_critic,
    generate_resume_improvement,
    generate_interview_questions,
)


def run_full_analysis(resume_text: str, jd_text: str) -> dict:
    """Run the complete AI analysis pipeline (used for one-shot analysis)."""
    return {
        "analysis": analyze_resume_against_jd(resume_text, jd_text),
        "critic": generate_resume_critic(resume_text, jd_text),
        "improvement": generate_resume_improvement(resume_text, jd_text),
    }
