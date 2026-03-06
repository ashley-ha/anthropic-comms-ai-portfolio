# ABOUTME: Press digest workflow powered by Claude for article analysis.
# ABOUTME: Scores relevance, classifies topic/sentiment, and builds a formatted daily brief.
from __future__ import annotations

import json
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .claude_client import analyze_article

logger = logging.getLogger(__name__)

MAX_WORKERS = 5


def build_digest(
    input_path: Path,
    output_path: Path,
    threshold: int = 6,
) -> dict[str, Any]:
    """Build a daily press digest by analyzing articles with Claude.

    Each article is sent to Claude for relevance scoring, topic classification,
    sentiment analysis, and a rationale for inclusion/exclusion. Articles are
    analyzed in parallel for faster throughput.

    Args:
        input_path: Path to JSON file containing article objects.
        output_path: Path where the Markdown digest will be written.
        threshold: Minimum relevance_score (1-10) for inclusion.

    Returns:
        Summary dict with selected_count, filtered_count, and topic_mix.
    """
    with input_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    analyzed: list[dict[str, Any]] = []
    filtered_count = 0
    error_count = 0

    def _analyze_one(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        try:
            return raw, analyze_article(raw)
        except Exception as e:
            logger.error("Failed to analyze '%s': %s", raw.get("title", "?"), e)
            return raw, None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(_analyze_one, raw) for raw in articles]
        for future in as_completed(futures):
            raw, analysis = future.result()
            if analysis is None:
                error_count += 1
                continue
            entry = {**raw, **analysis}
            if analysis["relevance_score"] >= threshold:
                analyzed.append(entry)
            else:
                filtered_count += 1

    analyzed.sort(key=lambda a: a["relevance_score"], reverse=True)

    topic_counts: Counter[str] = Counter()
    sentiment_counts: Counter[str] = Counter()
    for a in analyzed:
        topic_counts[a["topic"]] += 1
        sentiment_counts[a["sentiment"]] += 1

    lines = _format_digest(analyzed, topic_counts, sentiment_counts, filtered_count)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "selected_count": len(analyzed),
        "filtered_count": filtered_count,
        "error_count": error_count,
        "topic_mix": dict(topic_counts),
        "sentiment_mix": dict(sentiment_counts),
    }


def _format_digest(
    articles: list[dict[str, Any]],
    topic_counts: Counter[str],
    sentiment_counts: Counter[str],
    filtered_count: int,
) -> list[str]:
    """Format analyzed articles into a Markdown digest."""
    lines = [
        "# Daily Press Digest",
        "",
        f"**{len(articles)} articles selected** | {filtered_count} filtered out",
        "",
        "---",
        "",
        "## Top Coverage",
        "",
    ]

    for i, article in enumerate(articles, start=1):
        lines.extend([
            f"### {i}. {article['title']}",
            f"**Source:** {article['source']} | **Published:** {article['published_at']}",
            f"**Relevance:** {article['relevance_score']}/10 | **Topic:** {article['topic']} | **Sentiment:** {article['sentiment']}",
            "",
            f"> {article['rationale']}",
            "",
            f"[Read full article]({article['url']})",
            "",
        ])

    lines.extend(["---", "", "## Distribution"])

    lines.append("")
    lines.append("**Topics:**")
    for topic, count in topic_counts.most_common():
        lines.append(f"- {topic}: {count}")

    lines.append("")
    lines.append("**Sentiment:**")
    for sentiment, count in sentiment_counts.most_common():
        lines.append(f"- {sentiment}: {count}")

    return lines
