# ABOUTME: Rapid response workflow powered by Claude for event triage.
# ABOUTME: Assesses severity, assigns priority tiers, generates talking points and escalation guidance.
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .claude_client import assess_event

logger = logging.getLogger(__name__)

MAX_WORKERS = 5

ROUTING = {
    "P0": ["Comms Lead", "Legal", "Policy", "Executive On-Call"],
    "P1": ["Comms Lead", "Policy"],
    "P2": ["Comms Operations"],
}

SLA_HOURS = {"P0": 1, "P1": 4, "P2": 24}


def build_alerts(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Assess events with Claude and build prioritized alert output.

    Each event is sent to Claude for severity scoring, tier assignment,
    rationale, and response talking points.

    Args:
        input_path: Path to JSON file containing event objects.
        output_path: Path where the JSON alerts will be written.

    Returns:
        Summary dict with alert_count and per-tier counts.
    """
    with input_path.open("r", encoding="utf-8") as f:
        events = json.load(f)

    alerts: list[dict[str, Any]] = []
    error_count = 0

    def _assess_one(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        try:
            return event, assess_event(event)
        except Exception as e:
            logger.error("Failed to assess '%s': %s", event.get("event_id", "?"), e)
            return event, None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(_assess_one, event) for event in events]
        for future in as_completed(futures):
            event, assessment = future.result()
            if assessment is None:
                error_count += 1
                continue
            tier = assessment["tier"]

            alerts.append({
                "event_id": event["event_id"],
                "timestamp": event["timestamp"],
                "source": event["source"],
                "summary": event["summary"],
                "priority_score": assessment["priority_score"],
                "tier": tier,
                "owners": ROUTING[tier],
                "response_sla_hours": SLA_HOURS[tier],
                "human_review_required": tier in {"P0", "P1"},
                "rationale": assessment["rationale"],
                "talking_points": assessment["talking_points"],
                "escalation_note": assessment["escalation_note"],
            })

    alerts.sort(key=lambda a: a["priority_score"], reverse=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(alerts, indent=2) + "\n", encoding="utf-8")

    return {
        "alert_count": len(alerts),
        "error_count": error_count,
        "p0_count": sum(1 for a in alerts if a["tier"] == "P0"),
        "p1_count": sum(1 for a in alerts if a["tier"] == "P1"),
        "p2_count": sum(1 for a in alerts if a["tier"] == "P2"),
    }
