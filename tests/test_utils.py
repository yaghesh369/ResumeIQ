"""Tests for validators and section extraction utilities."""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resumeiq.utils.validators import validate_file, validate_text
from resumeiq.parser.section_extractor import extract_skill_names, extract_experience_years


class FakeUpload:
    def __init__(self, name, size=1000, mime="application/pdf"):
        self.name = name
        self.size = size
        self.type = mime
        self._buf = io.BytesIO(b"data")

    def read(self):
        return self._buf.read()


class TestFileValidation(unittest.TestCase):
    def test_pdf_accepted(self):
        ok, msg = validate_file(FakeUpload("resume.pdf"))
        self.assertTrue(ok)

    def test_txt_accepted(self):
        ok, _ = validate_file(FakeUpload("notes.txt", mime="text/plain"))
        self.assertTrue(ok)

    def test_exe_rejected(self):
        ok, msg = validate_file(FakeUpload("virus.exe", mime="application/x-msdownload"))
        self.assertFalse(ok)
        self.assertIn("Unsupported", msg)

    def test_none_rejected(self):
        ok, _ = validate_file(None)
        self.assertFalse(ok)

    def test_oversize_rejected(self):
        big = FakeUpload("big.pdf", size=50 * 1024 * 1024)
        ok, msg = validate_file(big)
        self.assertFalse(ok)


class TestTextValidation(unittest.TestCase):
    def test_valid_text(self):
        ok, _ = validate_text("x" * 200)
        self.assertTrue(ok)

    def test_empty_text_rejected(self):
        ok, _ = validate_text("")
        self.assertFalse(ok)

    def test_short_text_rejected(self):
        ok, _ = validate_text("hi")
        self.assertFalse(ok)


class TestSectionExtractor(unittest.TestCase):
    def test_skill_extraction(self):
        skills = extract_skill_names("Built APIs with Python, Docker and PostgreSQL on AWS")
        lowered = [s.lower() for s in skills]
        for expected in ["python", "docker", "postgresql", "aws"]:
            self.assertIn(expected, lowered)

    def test_no_duplicates_case_insensitive(self):
        skills = extract_skill_names("python Python PYTHON")
        self.assertEqual(len(skills), 1)

    def test_experience_years(self):
        self.assertEqual(extract_experience_years("over 6+ years of experience"), 6)
        self.assertIsNone(extract_experience_years(None))


if __name__ == "__main__":
    unittest.main()
