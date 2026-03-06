from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

RELEVANCE_KEYWORDS = {
    "anthropic",
    "claude",
    "ai safety",
    "policy",
    "model release",
    "enterprise",
    "partnership",
    "regulation",
}

TOPIC_KEYWORDS = {
    "policy": {"policy", "regulation", "senate", "eu ai act", "governance"},
    "product": {"claude", "release", "feature", "api", "enterprise"},
    "business": {"partnership", "customer", "revenue", "adoption", "market"},
    "safety": {"ai safety", "alignment", "evals", "risk", "security"},
}

POSITIVE_WORDS = {"improved", "trusted", "growth", "breakthrough", "strong", "positive"}
NEGATIVE_WORDS = {"risk", "concern", "controversy", "lawsuit", "outage", "negative"}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def relevance_score(text: str) -> int:
    blob = _normalize(text)
    return sum(1 for kw in RELEVANCE_KEYWORDS if kw in blob)


def classify_topic(text: str) -> str:
    blob = _normalize(text)
    scores = {topic: sum(1 for kw in kws if kw in blob) for topic, kws in TOPIC_KEYWORDS.items()}
    best_topic, score = max(scores.items(), key=lambda x: x[1])
    return best_topic if score > 0 else "general"


def classify_sentiment(text: str) -> str:
    blob = _normalize(text)
    positive = sum(1 for w in POSITIVE_WORDS if w in blob)
    negative = sum(1 for w in NEGATIVE_WORDS if w in blob)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def build_digest(input_path: Path, output_path: Path, threshold: int = 2) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    processed: list[dict[str, Any]] = []
    topic_counts = Counter()

    for raw in articles:
        text = f"{raw['title']} {raw['body']}"
        score = relevance_score(text)
        if score < threshold:
            continue
        topic = classify_topic(text)
        sentiment = classify_sentiment(text)
        topic_counts[topic] += 1
        processed.append(
            {
                **raw,
                "relevance_score": score,
                "topic": topic,
                "sentiment": sentiment,
            }
        )

    processed.sort(key=lambda a: (a["relevance_score"], a["published_at"]), reverse=True)

    lines = ["# Daily Press Digest", "", "## Top Coverage"]
    for i, article in enumerate(processed, start=1):
        lines.extend(
            [
                f"{i}. **{article['title']}** ({article['source']})",
                f"   - Topic: `{article['topic']}` | Sentiment: `{article['sentiment']}` | Score: `{article['relevance_score']}`",
                f"   - Why included: Contains high-signal references to Anthropic/Claude strategy or policy context.",
                f"   - Link: {article['url']}",
            ]
        )

    lines.extend(["", "## Topic Mix"])
    for topic, count in topic_counts.most_common():
        lines.append(f"- {topic}: {count}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "selected_count": len(processed),
        "topic_mix": dict(topic_counts),
    }
