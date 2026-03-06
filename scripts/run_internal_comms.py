#!/usr/bin/env python3
# ABOUTME: Entry point for the internal communications workflow tool.
# ABOUTME: Runs the three-stage pipeline: draft, review, and channel formatting.
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from comms_ai_portfolio.internal_comms import build_internal_comms


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]

    print("Running internal communications workflow...")
    print("  Stage 1: Drafting content...")
    print("  Stage 2: Reviewing draft...")
    print("  Stage 3: Formatting for channels...")

    output_path = root / "outputs" / "internal_comms_report.md"
    summary = build_internal_comms(
        request_path=root / "data" / "internal_comms_request.json",
        output_path=output_path,
    )

    print(f"\nWorkflow complete:")
    print(f"  Content type: {summary['content_type']}")
    print(f"  Subject: {summary['subject']}")
    print(f"  Draft word count: {summary['draft_word_count']}")
    print(f"  Review scores: tone={summary['tone_score']}/10, clarity={summary['clarity_score']}/10, alignment={summary['alignment_score']}/10")
    print(f"  Sensitivity flags: {summary['sensitivity_flags_count']}")
    print(f"  Recommendation: {summary['approval_recommendation'].upper()}")
    print(f"  Channels: {', '.join(summary['channels_formatted'])}")
    print(f"\nView full report at: {output_path}")
