from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.rapid_response import (
    priority_score,
    tier_from_score,
    build_alerts,
)


class RapidResponseTests(unittest.TestCase):
    def test_priority_score(self) -> None:
        summary = "Regulator inquiry and safety incident reported"
        self.assertGreaterEqual(priority_score(summary), 5)

    def test_tier_mapping(self) -> None:
        self.assertEqual(tier_from_score(8), "P0")
        self.assertEqual(tier_from_score(3), "P1")
        self.assertEqual(tier_from_score(1), "P2")

    def test_build_alerts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "alerts.json"
            summary = build_alerts(repo_root / "data" / "mock_events.json", output)
            self.assertTrue(output.exists())
            self.assertEqual(summary["alert_count"], 3)


if __name__ == "__main__":
    unittest.main()
