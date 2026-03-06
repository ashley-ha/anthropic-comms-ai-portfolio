#!/usr/bin/env python3
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.press_digest import build_digest


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    threshold = int(os.getenv("DIGEST_RELEVANCE_THRESHOLD", "2"))
    summary = build_digest(
        input_path=root / "data" / "mock_articles.json",
        output_path=root / "outputs" / "press_digest.md",
        threshold=threshold,
    )
    print(f"Press digest generated: {summary}")
