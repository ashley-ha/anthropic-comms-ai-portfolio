# ABOUTME: Message pull-through tracker powered by Claude.
# ABOUTME: Analyzes earned media to measure how faithfully Anthropic's key narratives appear in press coverage.
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .claude_client import analyze_pull_through

logger = logging.getLogger(__name__)

MAX_WORKERS = 5

# Match types ordered by quality of pull-through
MATCH_WEIGHTS = {
    "verbatim": 1.0,
    "paraphrased": 0.8,
    "thematic": 0.4,
    "absent": 0.0,
    "distorted": -0.3,
}


def build_pull_through_report(
    articles_path: Path,
    messages_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Analyze earned media coverage for message pull-through.

    Sends each article to Claude alongside Anthropic's key messaging
    framework. Claude assesses which messages were reflected, how
    faithfully, and flags distortions. Results are aggregated into
    per-message and per-source breakdowns.

    Args:
        articles_path: Path to JSON file containing article objects.
        messages_path: Path to JSON file containing key messaging framework.
        output_path: Path where the Markdown report will be written.

    Returns:
        Summary dict with aggregate_score, message_scores, and source_scores.
    """
    with articles_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)
    with messages_path.open("r", encoding="utf-8") as f:
        framework = json.load(f)

    key_messages = framework["messages"]

    results: list[dict[str, Any]] = []
    error_count = 0

    def _analyze_one(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        try:
            return raw, analyze_pull_through(raw, key_messages)
        except Exception as e:
            logger.error("Failed to analyze pull-through for '%s': %s", raw.get("title", "?"), e)
            return raw, None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(_analyze_one, raw) for raw in articles]
        for future in as_completed(futures):
            raw, analysis = future.result()
            if analysis is None:
                error_count += 1
                continue
            results.append({**raw, **analysis})

    results.sort(key=lambda r: r["overall_score"], reverse=True)

    summary = _compute_summary(results, key_messages)
    summary["total_articles"] = len(results)
    summary["error_count"] = error_count

    lines = _format_report(results, key_messages, summary, framework.get("framework_name", ""))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return summary


def _compute_summary(
    results: list[dict[str, Any]],
    key_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate metrics from individual article analyses."""
    if not results:
        return {
            "aggregate_score": 0,
            "message_scores": {},
            "source_scores": {},
            "match_type_distribution": {},
            "distortions": [],
        }

    # Aggregate score across all articles
    aggregate_score = round(sum(r["overall_score"] for r in results) / len(results), 1)

    # Per-message breakdown
    message_scores: dict[str, dict[str, Any]] = {}
    for msg in key_messages:
        msg_id = msg["id"]
        msg_matches = []
        for r in results:
            for m in r.get("matches", []):
                if m["message_id"] == msg_id:
                    msg_matches.append(m)
        if msg_matches:
            weighted = sum(MATCH_WEIGHTS.get(m["match_type"], 0) for m in msg_matches)
            score = round((weighted / len(msg_matches)) * 100, 1)
        else:
            score = 0.0
        type_dist = Counter(m["match_type"] for m in msg_matches)
        message_scores[msg_id] = {
            "score": score,
            "match_distribution": dict(type_dist),
            "total_appearances": len(msg_matches) - type_dist.get("absent", 0),
        }

    # Per-source breakdown
    source_data: dict[str, list[int]] = defaultdict(list)
    for r in results:
        source_data[r["source"]].append(r["overall_score"])
    source_scores = {
        source: round(sum(scores) / len(scores), 1)
        for source, scores in source_data.items()
    }

    # Match type distribution
    all_match_types: Counter[str] = Counter()
    for r in results:
        for m in r.get("matches", []):
            all_match_types[m["match_type"]] += 1

    # Distortions flagged
    distortions = []
    for r in results:
        for m in r.get("matches", []):
            if m["match_type"] == "distorted":
                distortions.append({
                    "article": r["title"],
                    "source": r["source"],
                    "message_id": m["message_id"],
                    "distortion_note": m.get("distortion_note", ""),
                    "evidence": m.get("evidence", ""),
                })

    return {
        "aggregate_score": aggregate_score,
        "message_scores": message_scores,
        "source_scores": source_scores,
        "match_type_distribution": dict(all_match_types),
        "distortions": distortions,
    }


def _format_report(
    results: list[dict[str, Any]],
    key_messages: list[dict[str, Any]],
    summary: dict[str, Any],
    framework_name: str,
) -> list[str]:
    """Format pull-through analysis into a Markdown report."""
    lines = [
        "# Message Pull-Through Report",
        "",
        f"**Framework:** {framework_name}" if framework_name else "",
        f"**Articles analyzed:** {summary['total_articles']}",
        f"**Aggregate pull-through score:** {summary['aggregate_score']}%",
        "",
        "---",
        "",
        "## Narrative Health Dashboard",
        "",
    ]

    # Per-message scoreboard
    msg_lookup = {m["id"]: m for m in key_messages}
    for msg_id, data in sorted(
        summary["message_scores"].items(),
        key=lambda x: x[1]["score"],
        reverse=True,
    ):
        msg = msg_lookup.get(msg_id, {})
        priority_tag = f"[{msg.get('priority', '?').upper()}]"
        bar = _score_bar(data["score"])
        lines.extend([
            f"### {msg_id} {priority_tag}",
            f"> {msg.get('narrative', '')}",
            "",
            f"**Score:** {data['score']}% {bar}",
            f"**Appearances:** {data['total_appearances']} articles",
            f"**Distribution:** {_format_distribution(data['match_distribution'])}",
            "",
        ])

    # Distortion alerts
    if summary["distortions"]:
        lines.extend(["---", "", "## Distortion Alerts", ""])
        for d in summary["distortions"]:
            lines.extend([
                f"**{d['source']}** — _{d['article']}_",
                f"- Message: `{d['message_id']}`",
                f"- Issue: {d['distortion_note']}",
                f"- Evidence: \"{d['evidence']}\"",
                "",
            ])

    # Per-source breakdown
    lines.extend(["---", "", "## Source Fidelity", ""])
    for source, score in sorted(
        summary["source_scores"].items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        bar = _score_bar(score)
        lines.append(f"- **{source}**: {score}% {bar}")

    lines.append("")

    # Top articles by pull-through
    lines.extend(["---", "", "## Top Articles by Pull-Through", ""])
    for i, r in enumerate(results[:10], start=1):
        lines.extend([
            f"### {i}. {r['title']}",
            f"**Source:** {r['source']} | **Score:** {r['overall_score']}%",
            f"> {r.get('summary', '')}",
            "",
        ])

    # Match type distribution
    lines.extend(["---", "", "## Overall Match Distribution", ""])
    for match_type, count in sorted(
        summary["match_type_distribution"].items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        lines.append(f"- {match_type}: {count}")

    return lines


def _score_bar(score: float) -> str:
    """Generate a simple text-based score bar."""
    filled = round(score / 10)
    return "[" + "=" * filled + " " * (10 - filled) + "]"


def _format_distribution(dist: dict[str, int]) -> str:
    """Format match type distribution inline."""
    return " | ".join(f"{k}: {v}" for k, v in sorted(dist.items()))
