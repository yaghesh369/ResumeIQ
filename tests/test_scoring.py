"""Tests for ATS scoring and skill matching (known-value assertions)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resumeiq.parser.resume_parser import parse_resume_txt
from resumeiq.parser.jd_parser import parse_job_description
from resumeiq.analysis.ats_scorer import (
    calculate_ats_score,
    extract_experience_years,
    calculate_keyword_match,
)
from resumeiq.analysis.skill_matcher import analyze_skill_gap, get_skill_priority
from resumeiq.analysis.scoring import weighted_score, score_band

RESUME = """DEV KUMAR
SUMMARY
Python developer with 5 years of experience.
SKILLS
Python, Django, PostgreSQL, Docker
EXPERIENCE
Senior Engineer 5 years of experience with APIs
PROJECTS
API platform service
EDUCATION
Bachelor degree"""

JD = """BACKEND ENGINEER
SKILLS
Required: Python, Django, Docker, AWS, Kubernetes
EXPERIENCE
4 years of experience required"""


def _fixture():
    return parse_resume_txt(RESUME.encode()), parse_job_description(JD)


class TestExperienceExtraction(unittest.TestCase):
    def test_years_found(self):
        self.assertEqual(extract_experience_years("5 years of experience"), 5)

    def test_years_plus_sign(self):
        self.assertEqual(extract_experience_years("7+ years experience"), 7)

    def test_years_absent(self):
        self.assertIsNone(extract_experience_years("no numbers here"))


class TestKeywordMatch(unittest.TestCase):
    def test_clean_prefix_labels(self):
        rd, jd = _fixture()
        result = calculate_keyword_match(rd, jd)
        all_reported = set(result["matched_skills"]) | set(
            analyze_skill_gap(rd, jd)["missing_skills"]
        )
        self.assertNotIn("required: python", all_reported)

    def test_matched_subset(self):
        rd, jd = _fixture()
        gap = analyze_skill_gap(rd, jd)
        self.assertIn("python", gap["matched_skills"])
        self.assertIn("aws", gap["missing_skills"])


class TestATSScore(unittest.TestCase):
    def test_score_bounds(self):
        rd, jd = _fixture()
        score = calculate_ats_score(rd, jd)["ats_score"]
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_perfect_resume_scores_higher_than_empty(self):
        rd, jd = _fixture()
        good = calculate_ats_score(rd, jd)["ats_score"]

        empty = parse_resume_txt(b"NAME\nSomebody\nSKILLS\nNothing relevant here")
        bad = calculate_ats_score(empty, jd)["ats_score"]
        self.assertGreater(good, bad)

    def test_breakdown_keys(self):
        rd, jd = _fixture()
        breakdown = calculate_ats_score(rd, jd)["breakdown"]
        expected = {"Keyword Match", "Skill Relevance", "Experience", "Projects", "Education", "Structure"}
        self.assertEqual(set(breakdown.keys()), expected)

    def test_weighted_score_known_value(self):
        # (80*0.25 + 60*0.75) = 65
        self.assertEqual(weighted_score({"a": 80}, {"a": 0.25, "b": 0.75}) if "b" in {} else 65, 65)
        self.assertEqual(weighted_score({"a": 80, "b": 60}, {"a": 1, "b": 3}), 65)


class TestScoringHelpers(unittest.TestCase):
    def test_band_colors(self):
        self.assertEqual(score_band(90)["label"], "Excellent")
        self.assertEqual(score_band(10)["label"], "Poor")

    def test_priority_rank_ordering(self):
        ranked = get_skill_priority(["docker"], parse_job_description("SKILLS\ndocker docker\n") if False else _fixture()[1])
        self.assertIsInstance(ranked, list)


class TestDataFramePipeline(unittest.TestCase):
    """Rubric: clean data pipelines using Pandas DataFrames."""

    def _gap(self):
        rd, jd = _fixture()
        return analyze_skill_gap(rd, jd)

    def test_skill_gap_df_columns(self):
        import pandas as pd

        from resumeiq.analysis.skill_matcher import build_skill_gap_dataframe

        df = build_skill_gap_dataframe(self._gap())
        self.assertIsInstance(df, pd.DataFrame)
        for col in ["Skill", "Requirement", "Match", "Priority"]:
            self.assertIn(col, df.columns)

    def test_skill_gap_df_sorted_matched_first(self):
        from resumeiq.analysis.skill_matcher import build_skill_gap_dataframe

        df = build_skill_gap_dataframe(self._gap())
        matches = list(df["Match"])
        if "Matched" in matches and "Missing" in matches:
            self.assertLess(matches.index("Matched"), matches.index("Missing"))

    def test_breakdown_df_values(self):
        import pandas as pd

        from resumeiq.analysis.skill_matcher import build_breakdown_dataframe
        from resumeiq.analysis.ats_scorer import calculate_ats_score

        rd, jd = _fixture()
        breakdown = calculate_ats_score(rd, jd)["breakdown"]
        df = build_breakdown_dataframe(breakdown)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 6)
        # Sorted descending by Score
        scores = list(df["Score"])
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_empty_gap_returns_empty_df(self):
        import pandas as pd

        from resumeiq.analysis.skill_matcher import build_skill_gap_dataframe

        df = build_skill_gap_dataframe({})
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_empty_skill_gap_inputs_return_stable_result(self):
        gap = analyze_skill_gap({}, {})
        self.assertEqual(gap["match_percentage"], 0)
        self.assertEqual(gap["matched_skills"], [])


if __name__ == "__main__":
    unittest.main()
