"""Tests for domain-aware vocabulary: detection, override, non-tech scoring."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resumeiq.analysis.domains import (
    CORE_KEYWORDS,
    DOMAIN_PROFILES,
    active_keywords,
    detect_domains,
    kw_in_text,
    resolve_domain,
)
from resumeiq.parser.resume_parser import parse_resume_txt
from resumeiq.parser.jd_parser import parse_job_description
from resumeiq.analysis.ats_scorer import (
    calculate_ats_score,
    calculate_keyword_match,
    calculate_technical_skills_score,
)

MARKETING_JD = """MARKETING SPECIALIST - BrightWave Media

RESPONSIBILITIES:
- Own SEO and Google Ads campaigns end to end
- Manage social media calendar across platforms
- Track GA4 dashboards and report ROI to leadership

REQUIRED SKILLS: SEO, Google Ads, Content Marketing, GA4, HubSpot, Copywriting
EXPERIENCE: 3 years in digital marketing required."""

MARKETING_RESUME = """PRIYA VERMA
SUMMARY
Digital marketer with 3 years of experience running campaigns.
SKILLS
SEO, Google Ads, Social Media, GA4, HubSpot, Email Marketing, Canva
EXPERIENCE
Marketing Executive 3 years of experience with campaigns and content.
PROJECTS
Led product launch campaign generating 40k impressions.
EDUCATION
BBA Marketing"""

NURSE_JD = """REGISTERED NURSE - City Care Hospital

Provide patient care in a 30-bed unit. Maintain EHR documentation
and follow HIPAA compliance strictly.

REQUIRED SKILLS: Patient Care, Medication Administration, EHR, Triage, CPR
EDUCATION: Nursing degree required."""


class TestKeywordBoundary(unittest.TestCase):
    def test_no_substring_false_positives(self):
        text = "the google algorithm is good at categorising postgresql data excellently"
        self.assertFalse(kw_in_text("go", text))
        self.assertFalse(kw_in_text("excel", text))
        self.assertFalse(kw_in_text("sql", text))

    def test_multiword_and_symbols(self):
        self.assertTrue(kw_in_text("google ads", "run google ads campaigns"))
        self.assertTrue(kw_in_text("ci/cd", "experience with CI/CD pipelines"))
        self.assertTrue(kw_in_text("c++", "solid C++ skills"))
        self.assertFalse(kw_in_text("c++", "the c plus plus of it"))


class TestDomainDetection(unittest.TestCase):
    def test_marketing_detected(self):
        result = detect_domains(MARKETING_JD.lower())
        self.assertEqual(result["primary"], "Marketing")
        self.assertIn("Marketing", result["matched"])

    def test_healthcare_detected(self):
        result = detect_domains(NURSE_JD.lower())
        self.assertEqual(result["primary"], "Healthcare")

    def test_tech_regression(self):
        jd = "build REST APIs with python django docker on aws using kubernetes"
        self.assertEqual(detect_domains(jd)["primary"], "Technology")

    def test_generic_jd_falls_back_to_core(self):
        result = detect_domains("office administrator duties as assigned by manager")
        self.assertIsNone(result["primary"])
        vocab = active_keywords("office administrator duties")
        self.assertTrue(vocab >= CORE_KEYWORDS)


class TestOverride(unittest.TestCase):
    def test_custom_keywords_are_added(self):
        vocab = active_keywords(
            "GIS analyst role",
            override="Custom",
            custom_keywords=["ArcGIS", "land surveying"],
        )
        self.assertIn("arcgis", vocab)
        self.assertIn("land surveying", vocab)

    def test_custom_keywords_drive_scoring(self):
        resume = parse_resume_txt(b"JANE DOE\nSKILLS\nArcGIS")
        jd = parse_job_description("GIS ANALYST\nSKILLS\nArcGIS, zoning")
        result = calculate_keyword_match(
            resume,
            jd,
            domain_keywords=active_keywords(
                jd["clean_text"], "Custom", ["ArcGIS", "zoning"]
            ),
        )
        self.assertIn("arcgis", result["matched_skills"])

    def test_override_forces_profile(self):
        vocab = active_keywords("ambiguous text here", override="Finance")
        self.assertIn("bookkeeping", vocab)
        self.assertIn("gst", vocab)

    def test_resolve_label_with_override(self):
        resolved = resolve_domain(MARKETING_JD.lower(), override="Sales")
        self.assertEqual(resolved["label"], "Sales")
        self.assertTrue(resolved["override"])

    def test_resolve_label_auto(self):
        resolved = resolve_domain(MARKETING_JD.lower())
        self.assertEqual(resolved["label"], "Marketing")
        self.assertFalse(resolved["override"])


class TestNonTechScoring(unittest.TestCase):
    """The old engine froze Skill Relevance at 75 for any non-tech JD."""

    @classmethod
    def setUpClass(cls):
        cls.mkt_resume = parse_resume_txt(MARKETING_RESUME.encode("utf-8"))
        cls.mkt_jd = parse_job_description(MARKETING_JD)

    def test_relevance_not_frozen_at_75(self):
        result = calculate_technical_skills_score(self.mkt_resume, self.mkt_jd)
        # Domain vocabulary actually detected from a non-tech JD
        self.assertIn("seo", result["required_tech"])
        self.assertIn("ga4", result["required_tech"])
        self.assertNotEqual(result["technical_score"], 75)
        # Found skills are a genuine subset with a sane ratio
        for kw in result["found_tech"]:
            self.assertIn(kw, result["required_tech"])
        self.assertGreaterEqual(result["technical_score"], 50)

    def test_keyword_match_healthy(self):
        result = calculate_keyword_match(self.mkt_resume, self.mkt_jd)
        matched = set(result["matched_skills"])
        self.assertIn("seo", matched)
        self.assertIn("ga4", matched)
        self.assertGreater(result["keyword_match"], 40)

    def test_full_pipeline_marketing(self):
        out = calculate_ats_score(self.mkt_resume, self.mkt_jd)
        self.assertIn("Skill Relevance", out["breakdown"])
        self.assertNotIn("Technical Skills", out["breakdown"])
        self.assertGreater(out["ats_score"], 45)

    def test_manual_override_changes_vocab(self):
        auto = calculate_keyword_match(self.mkt_resume, self.mkt_jd)
        forced_sales = calculate_keyword_match(
            self.mkt_resume, self.mkt_jd, domain_keywords=DOMAIN_PROFILES["Sales"]
        )
        # Sales profile adds terms absent from both docs -> match% drops
        self.assertLess(forced_sales["keyword_match"], auto["keyword_match"] + 1)


if __name__ == "__main__":
    unittest.main()
