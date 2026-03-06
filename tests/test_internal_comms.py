# ABOUTME: Integration tests for the internal communications workflow tool.
# ABOUTME: Calls Claude API to verify draft generation, review, and channel formatting.
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.claude_client import (
    draft_internal_content,
    format_for_channel,
    review_internal_content,
)
from comms_ai_portfolio.internal_comms import build_internal_comms


SAMPLE_REQUEST = {
    "content_type": "all_hands",
    "subject": "Q1 2026 Company Update",
    "author": "Dario Amodei",
    "audience": "All Anthropic employees",
    "tone": "optimistic but grounded",
    "key_points": [
        "Claude Enterprise crossed 500 customers",
        "Responsible Scaling Policy v3 published",
        "FTC inquiry is ongoing; legal team cooperating",
    ],
    "sensitive_topics": [
        "FTC investigation — do not speculate on outcomes",
        "Avoid disparaging competitors by name",
    ],
    "context": "Q1 update with strong product momentum but regulatory uncertainty.",
    "distribution_channels": ["slack", "email"],
}


class TestDraftGeneration(unittest.TestCase):
    """Test Claude generates appropriate internal comms drafts."""

    def test_draft_all_hands_covers_key_points(self) -> None:
        draft = draft_internal_content(SAMPLE_REQUEST)
        self.assertIsInstance(draft, str)
        self.assertGreater(len(draft.split()), 50)
        # Draft should reference the core subject matter
        draft_lower = draft.lower()
        self.assertTrue(
            "enterprise" in draft_lower or "500" in draft_lower or "customer" in draft_lower,
            "Draft should reference enterprise milestone",
        )

    def test_draft_faq_produces_questions(self) -> None:
        faq_request = {**SAMPLE_REQUEST, "content_type": "faq"}
        draft = draft_internal_content(faq_request)
        self.assertIsInstance(draft, str)
        # FAQs should contain question marks
        self.assertIn("?", draft, "FAQ draft should contain questions")


class TestContentReview(unittest.TestCase):
    """Test Claude's structured review of internal content."""

    def test_review_returns_valid_structure(self) -> None:
        draft = draft_internal_content(SAMPLE_REQUEST)
        review = review_internal_content(draft, SAMPLE_REQUEST)

        self.assertIn("tone_score", review)
        self.assertIn("clarity_score", review)
        self.assertIn("alignment_score", review)
        self.assertIn("sensitivity_flags", review)
        self.assertIn("suggested_edits", review)
        self.assertIn("approval_recommendation", review)
        self.assertIn("rationale", review)

        # Scores should be in valid range
        for score_key in ["tone_score", "clarity_score", "alignment_score"]:
            self.assertGreaterEqual(review[score_key], 1)
            self.assertLessEqual(review[score_key], 10)

        self.assertIn(review["approval_recommendation"], ["approve", "revise", "escalate"])

    def test_review_flags_sensitive_content(self) -> None:
        # Draft with obviously problematic content about the FTC
        sensitive_draft = (
            "Team, great news — the FTC investigation is clearly baseless and we expect it to be "
            "dropped any day now. Our competitors at OpenAI would never survive this kind of scrutiny. "
            "We're confident the investigators will realize they're wasting their time."
        )
        sensitive_request = {
            **SAMPLE_REQUEST,
            "sensitive_topics": [
                "FTC investigation — must not speculate on outcomes or dismiss the inquiry",
                "Competitive positioning — never disparage competitors",
            ],
        }
        review = review_internal_content(sensitive_draft, sensitive_request)

        # Should recommend against approving this content
        self.assertIn(
            review["approval_recommendation"],
            ["revise", "escalate"],
            "Should not approve content that speculates about FTC outcome and disparages competitors",
        )
        # Should flag sensitivity issues
        self.assertTrue(
            len(review["sensitivity_flags"]) > 0 or len(review["suggested_edits"]) > 0,
            "Should flag or suggest edits for sensitive content",
        )


class TestChannelFormatting(unittest.TestCase):
    """Test Claude formats content appropriately for each channel."""

    def test_slack_formatting(self) -> None:
        content = "# Update\n\nWe crossed 500 enterprise customers this quarter."
        formatted = format_for_channel(content, "slack", "Q1 Update")
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 10)

    def test_email_formatting(self) -> None:
        content = "# Update\n\nWe crossed 500 enterprise customers this quarter."
        formatted = format_for_channel(content, "email", "Q1 Update")
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 10)


class TestBuildInternalComms(unittest.TestCase):
    """Test the full internal comms pipeline end-to-end."""

    def test_full_pipeline_integration(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "internal_comms_report.md"
            summary = build_internal_comms(
                repo_root / "data" / "internal_comms_request.json",
                output,
            )
            self.assertTrue(output.exists())
            self.assertEqual(summary["content_type"], "all_hands")
            self.assertGreater(summary["draft_word_count"], 50)
            self.assertIn(summary["approval_recommendation"], ["approve", "revise", "escalate"])
            self.assertGreater(len(summary["channels_formatted"]), 0)

            content = output.read_text()
            self.assertIn("Internal Communications Workflow Report", content)
            self.assertIn("Stage 1: Draft", content)
            self.assertIn("Stage 2: Editorial Review", content)
            self.assertIn("Stage 3: Channel Formatting", content)


if __name__ == "__main__":
    unittest.main()
