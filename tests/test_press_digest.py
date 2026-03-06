from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.press_digest import (
    classify_sentiment,
    classify_topic,
    relevance_score,
    build_digest,
)


class PressDigestTests(unittest.TestCase):
    def test_relevance_score(self) -> None:
        text = "Anthropic policy update for Claude enterprise release"
        self.assertGreaterEqual(relevance_score(text), 2)

    def test_topic_classification(self) -> None:
        text = "Senate regulation and policy debate around AI governance"
        self.assertEqual(classify_topic(text), "policy")

    def test_sentiment_classification(self) -> None:
        text = "Strong adoption and positive enterprise growth"
        self.assertEqual(classify_sentiment(text), "positive")

    def test_build_digest(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "digest.md"
            summary = build_digest(repo_root / "data" / "mock_articles.json", output, threshold=2)
            self.assertTrue(output.exists())
            self.assertGreaterEqual(summary["selected_count"], 1)


if __name__ == "__main__":
    unittest.main()
