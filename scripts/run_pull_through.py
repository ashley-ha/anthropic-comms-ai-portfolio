#!/usr/bin/env python3
# ABOUTME: Entry point for the message pull-through tracker.
# ABOUTME: Analyzes earned media coverage against Anthropic's key messaging framework.
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from comms_ai_portfolio.pull_through_tracker import build_pull_through_report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]

    live = "--live" in sys.argv
    if live:
        articles_path = root / "data" / "live_articles.json"
        if not articles_path.exists():
            print("No live articles found. Run `python scripts/run_fetch_articles.py` first.")
            sys.exit(1)
        print("Analyzing message pull-through in LIVE earned media...")
    else:
        articles_path = root / "data" / "mock_articles.json"
        print("Analyzing message pull-through in earned media...")

    output_path = root / "outputs" / "pull_through_report.md"
    summary = build_pull_through_report(
        articles_path=articles_path,
        messages_path=root / "data" / "key_messages.json",
        output_path=output_path,
    )
    print(f"\nPull-through analysis complete:")
    print(f"  Articles analyzed: {summary['total_articles']}")
    print(f"  Aggregate score: {summary['aggregate_score']}%")
    print(f"\n  Per-message scores:")
    for msg_id, data in summary["message_scores"].items():
        print(f"    {msg_id}: {data['score']}%")
    if summary.get("distortions"):
        print(f"\n  Distortions detected: {len(summary['distortions'])}")
        for d in summary["distortions"]:
            print(f"    - [{d['source']}] {d['message_id']}: {d['distortion_note'][:80]}")
    print(f"\nView full report at: {output_path}")
