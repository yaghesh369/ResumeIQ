"""Regression tests for real-world messy resumes (decorated headers,
inline values, category labels) — the bugs reported in user testing."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resumeiq.parser.resume_parser import parse_resume_txt
from resumeiq.parser.jd_parser import parse_job_description
from resumeiq.analysis.ats_scorer import calculate_ats_score
from resumeiq.analysis.skill_matcher import analyze_skill_gap
from resumeiq.utils.text_cleaner import (
    extract_sections,
    extract_skills_list,
    get_skills_from_sections,
)

MESSY_RESUME = """================================
    RAHUL SHARMA
 rahul@email.com | +91-9876543210 | Bangalore
================================

PROFESSIONAL SUMMARY ------------------
Results-driven Python developer with 4 years of experience in web development.

WORK EXPERIENCE
Software Engineer, InfoTech Pvt Ltd (2021-Present)
- Built REST APIs using Django REST Framework serving 40k users daily.
Junior Developer, WebWorks (2019-2021)
- Developed Flask microservices and automated reports.

TECHNICAL SKILLS:
Languages: Python, JavaScript, SQL
Frameworks: Django, Flask, React
Databases: PostgreSQL, MongoDB
Tools: Docker, Git, AWS, Jenkins

KEY PROJECTS
1. Ecommerce API - Django + PostgreSQL + JWT auth
2. Analytics Dashboard - React + Chart.js

EDUCATION & QUALIFICATION
B.Tech Computer Science, VTU (2015-2019)

CERTIFICATIONS & COURSES
AWS Certified Developer (2023)"""

MESSY_JD = """SENIOR PYTHON DEVELOPER - ACME Corp

REQUIRED SKILLS:
- 5+ years of experience with Python
- Expert in Django and REST APIs
- Strong PostgreSQL and Docker knowledge
- AWS cloud experience required

PREFERRED SKILLS: Kubernetes, React, CI/CD

RESPONSIBILITIES: Build scalable backend services, mentor juniors.
EDUCATION: Bachelor degree required."""


class TestDecoratedHeaders(unittest.TestCase):
    """Core bug fix: exact-match headers never fired on real resumes."""

    def setUp(self):
        self.sections = extract_sections(MESSY_RESUME)

    def test_all_six_sections_detected(self):
        for key in ("summary", "skills", "experience", "projects", "education", "certifications"):
            content = self.sections[key].strip()
            self.assertTrue(content, f"'{key}' section was NOT detected")

    def test_skills_section_content(self):
        skills_lower = self.sections["skills"].lower()
        self.assertIn("python", skills_lower)
        self.assertIn("docker", skills_lower)

    def test_summary_with_trailing_dashes(self):
        self.assertIn("results-driven", self.sections["summary"].lower())

    def test_combined_header_education(self):
        self.assertIn("b.tech", self.sections["education"].lower())


class TestInlineHeaderValues(unittest.TestCase):
    def test_inline_skills_captured(self):
        sections = extract_sections(MESSY_JD)
        skills_lower = sections["skills"].lower()
        self.assertIn("kubernetes", skills_lower)
        self.assertIn("ci/cd", skills_lower)

    def test_unknown_header_isolated(self):
        sections = extract_sections(MESSY_JD)
        # RESPONSIBILITIES must not leak into skills
        skills_lower = sections["skills"].lower()
        self.assertNotIn("mentor juniors", skills_lower)
        self.assertNotIn("scalable backend", skills_lower)


class TestSkillsTokenizer(unittest.TestCase):
    def test_common_proficiencies_header(self):
        sections = extract_sections("JANE DOE\nTECHNICAL PROFICIENCIES\nPython, Docker, SQL")
        self.assertEqual(sections["skills"], "Python, Docker, SQL")

    def test_category_labels_stripped(self):
        raw = "Languages: Python, JavaScript\nFrameworks: Django, Flask"
        skills = [s.lower() for s in extract_skills_list(raw)]
        self.assertIn("python", skills)
        self.assertIn("django", skills)
        self.assertFalse(any("languages" in s or "frameworks" in s for s in skills))

    def test_junk_filtered(self):
        raw = "Python, 123, , and, the, Machine Learning"
        skills = [s.lower() for s in extract_skills_list(raw)]
        self.assertEqual(skills, ["python", "machine learning"])

    def test_fallback_scan_without_skills_section(self):
        text = "I have experience with Python, Docker and Kubernetes on AWS."
        sections = extract_sections(text)
        skills = [s.lower() for s in get_skills_from_sections(sections)]
        self.assertIn("docker", skills)
        self.assertIn("kubernetes", skills)


class TestEndToEndMessyResume(unittest.TestCase):
    """Full pipeline on the messy fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.resume = parse_resume_txt(MESSY_RESUME.encode("utf-8"))
        cls.jd = parse_job_description(MESSY_JD)
        cls.gap = analyze_skill_gap(cls.resume, cls.jd)
        cls.ats = calculate_ats_score(cls.resume, cls.jd)

    def test_core_skills_match(self):
        matched = set(self.gap["matched_skills"]) | {s.lower() for s in self.gap["partial_skills"]}
        self.assertIn("python", matched)
        self.assertIn("django", matched)
        self.assertIn("postgresql", matched)

    def test_missing_skills_are_real_gaps(self):
        missing = self.gap["missing_skills"]
        self.assertIn("kubernetes", [m.lower() for m in missing])
        # No prose fragments leaked into the gap lists
        for skill in missing + self.gap["matched_skills"]:
            self.assertLessEqual(len(skill.split()), 4, f"prose leaked as skill: {skill!r}")

    def test_keyword_match_not_zero(self):
        kw = self.ats["breakdown"]["Keyword Match"]
        self.assertGreater(kw, 30, f"keyword match suspiciously low: {kw}")

    def test_ats_in_bounds(self):
        score = self.ats["ats_score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertGreater(score, 30)


class TestSkillMatcherRobustness(unittest.TestCase):
    """Regression: crash + substring bugs found in the feature audit."""

    def test_no_skills_section_does_not_crash(self):
        # Old fallback path used re.split without importing re -> NameError
        resume = parse_resume_txt(
            b"JANE DOE\nSUMMARY\nHard worker with 3 years of experience.\n"
            b"EXPERIENCE\nOffice assistant, data entry and filing."
        )
        jd = parse_job_description(
            "OFFICE ADMINISTRATOR\nSKILLS\nData Entry, MS Office, Filing, Communication"
        )
        gap = analyze_skill_gap(resume, jd)
        self.assertIsInstance(gap["match_percentage"], int)

    def test_full_text_skills_are_used_when_section_is_unhelpful(self):
        resume = parse_resume_txt(
            b"JANE DOE\nWorked with Python and Docker (learning) on AWS deployments."
        )
        jd = parse_job_description(
            "BACKEND ENGINEER\nRequired skills: Python, Docker, AWS"
        )
        gap = analyze_skill_gap(resume, jd)
        self.assertIn("python", gap["matched_skills"])
        self.assertIn("docker", gap["matched_skills"])
        self.assertIn("aws", gap["matched_skills"])

    def test_requirements_heading_creates_skill_rows(self):
        resume = parse_resume_txt(b"JANE DOE\nExperience with GIS and field surveying.")
        jd = parse_job_description(
            "SPECIALIST\nRequirements: GIS, field surveying, zoning analysis"
        )
        gap = analyze_skill_gap(resume, jd)
        self.assertTrue(gap["jd_skills_detected"])
        self.assertGreater(gap["partial_count"], 0)
        self.assertGreater(gap["match_percentage"], 0)
        self.assertIn("zoning analysis", gap["missing_skills"])

    def test_ai_skills_recover_empty_deterministic_vocabulary(self):
        resume = parse_resume_txt(b"JANE DOE\nOperations specialist with field experience.")
        jd = parse_job_description("SPECIALIST\nRole details and responsibilities")
        gap = analyze_skill_gap(
            resume,
            jd,
            ai_analysis={
                "matched_skills": ["field operations"],
                "partial_skills": ["stakeholder coordination"],
                "missing_skills": ["SAP EWM"],
            },
        )
        self.assertIn("field operations", gap["matched_skills"])
        self.assertIn("stakeholder coordination", gap["partial_skills"])
        self.assertIn("sap ewm", gap["missing_skills"])

    def test_partial_match_uses_word_boundaries(self):
        # 'go' in JD must not partially-match 'google' in resume prose
        resume = parse_resume_txt(b"SAM RAY\nSKILLS\nGoogle Workspace, Excel")
        jd = parse_job_description("ENGINEER\nSKILLS\nGo, Docker, Excel")
        gap = analyze_skill_gap(resume, jd)
        self.assertNotIn("go", [s.lower() for s in gap["partial_skills"]])
        self.assertIn("excel", [s.lower() for s in gap["matched_skills"]])

    def test_domain_fallback_skills_for_non_tech(self):
        # extract_skill_names must find nursing skills, not just tech
        from resumeiq.parser.section_extractor import extract_skill_names

        text = "Registered Nurse providing patient care, EHR documentation, HIPAA compliance."
        skills = [s.lower() for s in extract_skill_names(text)]
        self.assertIn("patient care", skills)
        self.assertIn("hipaa", skills)


if __name__ == "__main__":
    unittest.main()
