from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEVERITY_TERMS = {
    "critical": {"data leak", "safety incident", "lawsuit", "regulator inquiry", "security breach"},
    "high": {"negative trend", "viral criticism", "misinformation", "policy pushback"},
    "medium": {"competitor launch", "analyst note", "pricing reaction"},
}

ROUTING = {
    "P0": ["Comms Lead", "Legal", "Policy", "Executive On-Call"],
    "P1": ["Comms Lead", "Policy"],
    "P2": ["Comms Operations"],
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def priority_score(summary: str) -> int:
    blob = _normalize(summary)
    score = 0
    score += 5 * sum(1 for kw in SEVERITY_TERMS["critical"] if kw in blob)
    score += 3 * sum(1 for kw in SEVERITY_TERMS["high"] if kw in blob)
    score += 1 * sum(1 for kw in SEVERITY_TERMS["medium"] if kw in blob)
    return score


def tier_from_score(score: int) -> str:
    if score >= 7:
        return "P0"
    if score >= 3:
        return "P1"
    return "P2"


def response_sla_hours(tier: str) -> int:
    return {"P0": 1, "P1": 4, "P2": 24}[tier]


def build_alerts(input_path: Path, output_path: Path) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8") as f:
        events = json.load(f)

    alerts: list[dict[str, Any]] = []

    for event in events:
        score = priority_score(event["summary"])
        tier = tier_from_score(score)
        alerts.append(
            {
                "event_id": event["event_id"],
                "timestamp": event["timestamp"],
                "source": event["source"],
                "summary": event["summary"],
                "priority_score": score,
                "tier": tier,
                "owners": ROUTING[tier],
                "response_sla_hours": response_sla_hours(tier),
                "human_review_required": tier in {"P0", "P1"},
            }
        )

    alerts.sort(key=lambda a: a["priority_score"], reverse=True)
    output_path.write_text(json.dumps(alerts, indent=2) + "\n", encoding="utf-8")

    return {
        "alert_count": len(alerts),
        "p0_count": sum(1 for a in alerts if a["tier"] == "P0"),
        "p1_count": sum(1 for a in alerts if a["tier"] == "P1"),
        "p2_count": sum(1 for a in alerts if a["tier"] == "P2"),
    }
