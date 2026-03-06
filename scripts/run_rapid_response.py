#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from comms_ai_portfolio.rapid_response import build_alerts


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    summary = build_alerts(
        input_path=root / "data" / "mock_events.json",
        output_path=root / "outputs" / "rapid_response_alerts.json",
    )
    print(f"Rapid response alerts generated: {summary}")
