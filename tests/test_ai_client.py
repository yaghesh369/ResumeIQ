import unittest
from unittest.mock import patch

from resumeiq.ai.gemini_client import (
    _extract_json,
    analyze_resume_against_jd,
    evaluate_voice_answer,
)


class TestAIClient(unittest.TestCase):
    def test_extract_json_rejects_non_object(self):
        self.assertIsNone(_extract_json("[]"))
        self.assertEqual(_extract_json('{"ok": true}'), {"ok": True})

    @patch("resumeiq.ai.gemini_client.call_gemini", return_value={})
    def test_analysis_reports_unavailable_provider(self, _call):
        result = analyze_resume_against_jd("resume", "job")
        self.assertFalse(result["ai_available"])
        self.assertEqual(result["job_match_score"], 0)

    @patch("resumeiq.ai.gemini_client._gemini_client", return_value=None)
    def test_voice_reports_unavailable_provider(self, _client):
        result = evaluate_voice_answer(b"audio", "question", "resume", "job")
        self.assertFalse(result["available"])
        self.assertEqual(result["overall"], 0.0)


if __name__ == "__main__":
    unittest.main()
