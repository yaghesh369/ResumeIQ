"""Tests for resume and JD parsing (run with: python -m unittest, or pytest)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resumeiq.parser.resume_parser import parse_resume_txt
from resumeiq.parser.jd_parser import parse_job_description
from resumeiq.utils.text_cleaner import clean_text, extract_sections

SAMPLE_RESUME = """JANE SMITH
SUMMARY
Backend developer with 4 years of experience.
SKILLS
Python, Django, PostgreSQL
EXPERIENCE
Software Engineer 4 years of experience building APIs
PROJECTS
Ecommerce API service
EDUCATION
Bachelor degree in Computer Science"""

SAMPLE_JD = """SENIOR BACKEND ENGINEER
SKILLS
Required: Python, Django, Docker, PostgreSQL
EXPERIENCE
5 years of experience required"""


class TestTextCleaner(unittest.TestCase):
    def test_clean_text_removes_extra_whitespace(self):
        self.assertEqual(clean_text("hello   world \n\n next"), "hello world\nnext")

    def test_extract_sections_finds_skills(self):
        sections = extract_sections(SAMPLE_RESUME)
        self.assertIn("python", sections["skills"].lower())

    def test_extract_sections_all_keys_present(self):
        sections = extract_sections("SUMMARY\nhello")
        for key in ["summary", "skills", "education", "experience", "projects", "certifications"]:
            self.assertIn(key, sections)


class TestResumeParser(unittest.TestCase):
    def test_parse_resume_txt_structured(self):
        data = parse_resume_txt(SAMPLE_RESUME.encode("utf-8"))
        self.assertIn("clean_text", data)
        self.assertIn("sections", data)
        self.assertIn("django", data["clean_text"].lower())

    def test_empty_resume_raises(self):
        with self.assertRaises(ValueError):
            parse_resume_txt(b"   ")

    def test_sample_pdf_parses(self):
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "sample_data", "sample_resume.pdf")
        if os.path.exists(pdf_path):
            from resumeiq.parser.resume_parser import parse_resume_pdf

            data = parse_resume_pdf(pdf_path)
            self.assertGreater(len(data["clean_text"]), 100)


class TestJDParser(unittest.TestCase):
    def test_parse_jd(self):
        data = parse_job_description(SAMPLE_JD)
        self.assertIn("docker", data["clean_text"].lower())

    def test_empty_jd_raises(self):
        with self.assertRaises(ValueError):
            parse_job_description("")


if __name__ == "__main__":
    unittest.main()
