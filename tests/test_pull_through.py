# ABOUTME: Integration tests for the message pull-through tracker.
# ABOUTME: Calls Claude API to verify pull-through analysis and report generation.
from pathlib import Path
import json
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.claude_client import analyze_pull_through
from comms_ai_portfolio.pull_through_tracker import build_pull_through_report


SAMPLE_KEY_MESSAGES = [
    {
        "id": "safety-leadership",
        "narrative": "Anthropic is the industry leader in AI safety.",
        "pillar": "Safety",
        "priority": "primary",
    },
    {
        "id": "enterprise-trust",
        "narrative": "Regulated industries choose Claude because of Anthropic's safety-first approach.",
        "pillar": "Product",
        "priority": "primary",
    },
]


class TestPullThroughAnalysis(unittest.TestCase):
    """Test Claude's pull-through analysis produces valid structured output."""

    def test_article_with_strong_pull_through(self) -> None:
        article = {
            "title": "Kaiser Permanente deploys Claude for clinical documentation",
            "body": (
                "Kaiser Permanente announced a pilot program using Claude to assist physicians "
                "with clinical documentation. The hospital system chose Anthropic specifically "
                "because of its industry-leading safety track record and responsible AI approach. "
                "'We needed the most trustworthy AI for our high-stakes healthcare environment,' "
                "said the CTO. Anthropic worked closely with Kaiser's compliance team to meet "
                "HIPAA requirements, reinforcing Claude's position as the top choice for regulated industries."
            ),
            "source": "STAT News",
            "url": "https://example.com/kaiser-claude",
            "published_at": "2026-03-05T14:00:00Z",
        }
        result = analyze_pull_through(article, SAMPLE_KEY_MESSAGES)

        self.assertIn("overall_score", result)
        self.assertIn("matches", result)
        self.assertIn("summary", result)
        self.assertIsInstance(result["overall_score"], int)
        self.assertGreaterEqual(result["overall_score"], 40)
        self.assertGreater(len(result["matches"]), 0)

        # Verify match structure
        for match in result["matches"]:
            self.assertIn("message_id", match)
            self.assertIn("match_type", match)
            self.assertIn(match["match_type"], ["verbatim", "paraphrased", "thematic", "distorted", "absent"])
            self.assertIn("confidence", match)
            self.assertIn("evidence", match)

    def test_article_with_no_pull_through(self) -> None:
        article = {
            "title": "Tesla announces fully autonomous rideshare service",
            "body": (
                "Tesla launched its autonomous rideshare service in San Francisco. "
                "The service uses Tesla's FSD v13 system. Early reviews are mixed."
            ),
            "source": "Wired",
            "url": "https://example.com/tesla",
            "published_at": "2026-03-04T14:00:00Z",
        }
        result = analyze_pull_through(article, SAMPLE_KEY_MESSAGES)

        self.assertLessEqual(result["overall_score"], 20)
        # Most or all messages should be absent
        absent_count = sum(1 for m in result["matches"] if m["match_type"] == "absent")
        self.assertGreater(absent_count, 0)

    def test_article_with_distorted_message(self) -> None:
        article = {
            "title": "AI safety is a marketing strategy, not research",
            "body": (
                "Critics argue that Anthropic's safety messaging is primarily a branding exercise. "
                "'They call themselves safety leaders, but their real goal is market differentiation,' "
                "said a former employee. The company's responsible scaling policy has been dismissed "
                "by some researchers as vague and unenforceable. Meanwhile, Anthropic continues to "
                "aggressively pursue enterprise deals in healthcare and finance."
            ),
            "source": "New York Times",
            "url": "https://example.com/nyt-safety",
            "published_at": "2026-03-05T15:00:00Z",
        }
        result = analyze_pull_through(article, SAMPLE_KEY_MESSAGES)

        # Should detect distortion — the safety narrative is present but twisted
        match_types = [m["match_type"] for m in result["matches"]]
        self.assertTrue(
            "distorted" in match_types or result["overall_score"] <= 30,
            "Should detect distortion or score low when messages are twisted",
        )


class TestBuildPullThroughReport(unittest.TestCase):
    """Test the full pull-through report workflow."""

    def test_build_report_integration(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pull_through_report.md"
            summary = build_pull_through_report(
                articles_path=repo_root / "data" / "mock_articles.json",
                messages_path=repo_root / "data" / "key_messages.json",
                output_path=output,
            )
            self.assertTrue(output.exists())
            self.assertIn("total_articles", summary)
            self.assertIn("aggregate_score", summary)
            self.assertIn("message_scores", summary)
            self.assertGreater(summary["total_articles"], 0)
            self.assertIsInstance(summary["aggregate_score"], (int, float))

            content = output.read_text()
            self.assertIn("Message Pull-Through Report", content)
            # Should contain per-message breakdown
            self.assertIn("safety-leadership", content)

    def test_report_contains_source_breakdown(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pull_through_report.md"
            summary = build_pull_through_report(
                articles_path=repo_root / "data" / "mock_articles.json",
                messages_path=repo_root / "data" / "key_messages.json",
                output_path=output,
            )
            # Should track per-source performance
            self.assertIn("source_scores", summary)
            self.assertIsInstance(summary["source_scores"], dict)
            self.assertGreater(len(summary["source_scores"]), 0)


if __name__ == "__main__":
    unittest.main()
