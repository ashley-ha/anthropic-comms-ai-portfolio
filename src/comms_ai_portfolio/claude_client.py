# ABOUTME: Thin wrapper around the Anthropic SDK for structured Claude calls.
# ABOUTME: Provides article analysis, event assessment, and briefing generation.
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def get_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")


# ---------------------------------------------------------------------------
# Article analysis: relevance, topic, sentiment
# ---------------------------------------------------------------------------

ARTICLE_ANALYSIS_TOOL = {
    "name": "record_article_analysis",
    "description": "Record the structured analysis of a press article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevance_score": {
                "type": "integer",
                "description": "1-10 relevance to Anthropic's communications interests. 10 = directly about Anthropic; 1 = unrelated.",
            },
            "topic": {
                "type": "string",
                "enum": ["policy", "product", "business", "safety", "competition", "general"],
                "description": "Primary topic category.",
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
                "description": "Overall sentiment toward Anthropic or the AI industry.",
            },
            "rationale": {
                "type": "string",
                "description": "1-2 sentence explanation of why this article matters (or doesn't) for the Comms team.",
            },
        },
        "required": ["relevance_score", "topic", "sentiment", "rationale"],
    },
}

ARTICLE_SYSTEM_PROMPT = """You are a communications intelligence analyst for Anthropic. Your job is to evaluate press articles for the daily digest.

When analyzing an article, consider:
- Direct mentions of Anthropic, Claude, or Anthropic's leadership
- AI policy, regulation, or safety discussions that affect Anthropic's positioning
- Competitive landscape (OpenAI, Google DeepMind, Meta AI, etc.)
- Enterprise AI adoption trends relevant to Claude's market
- Anything that the Comms team might need to brief leadership on or respond to

Score relevance 1-10 where:
- 9-10: Directly about Anthropic or requires immediate Comms attention
- 7-8: Highly relevant to Anthropic's market position or policy environment
- 5-6: Tangentially relevant industry news
- 3-4: General tech/AI news with weak connection
- 1-2: Irrelevant to Anthropic's communications needs"""


def analyze_article(article: dict[str, str], retries: int = 2) -> dict[str, Any]:
    """Analyze a single article for relevance, topic, sentiment, and rationale."""
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=300,
                system=ARTICLE_SYSTEM_PROMPT,
                tools=[ARTICLE_ANALYSIS_TOOL],
                tool_choice={"type": "tool", "name": "record_article_analysis"},
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze this article:\n\nTitle: {article['title']}\nSource: {article['source']}\nPublished: {article['published_at']}\n\nBody:\n{article['body']}",
                    }
                ],
            )
            for block in message.content:
                if block.type == "tool_use":
                    return block.input
            raise RuntimeError("Claude did not return a tool_use block for article analysis")
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error analyzing '%s' (attempt %d): %s", article.get("title", "?"), attempt + 1, e)
                continue
            raise
    raise last_err  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Event assessment: severity, tier, talking points
# ---------------------------------------------------------------------------

EVENT_ASSESSMENT_TOOL = {
    "name": "record_event_assessment",
    "description": "Record the structured assessment of an incoming communications event.",
    "input_schema": {
        "type": "object",
        "properties": {
            "priority_score": {
                "type": "integer",
                "description": "1-10 urgency score. 10 = existential crisis; 1 = routine noise.",
            },
            "tier": {
                "type": "string",
                "enum": ["P0", "P1", "P2"],
                "description": "P0 = immediate all-hands response; P1 = same-day response; P2 = monitor and prepare.",
            },
            "rationale": {
                "type": "string",
                "description": "Why this tier was assigned. Reference specific risk factors.",
            },
            "talking_points": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 recommended talking points if the Comms team needs to respond.",
            },
            "escalation_note": {
                "type": "string",
                "description": "Who should be looped in and what the first 30 minutes should look like.",
            },
        },
        "required": ["priority_score", "tier", "rationale", "talking_points", "escalation_note"],
    },
}

EVENT_SYSTEM_PROMPT = """You are a rapid-response analyst for Anthropic's Communications team. Your job is to assess incoming events and determine the appropriate response level.

Tier definitions:
- P0 (Critical): Immediate response required. Examples: data breach, safety incident, regulatory action against Anthropic, viral misinformation about Anthropic, executive controversy.
- P1 (High): Same-day response needed. Examples: negative trend in coverage, competitor announcement affecting positioning, policy development requiring a statement.
- P2 (Monitor): Track and prepare. Examples: routine competitor news, general industry commentary, minor social media chatter.

When generating talking points, be specific to Anthropic's values: safety, transparency, beneficial AI, and responsible development. Never generate talking points that are dishonest or dismissive."""


def assess_event(event: dict[str, str], retries: int = 2) -> dict[str, Any]:
    """Assess an event for priority, tier, and generate talking points."""
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=500,
                system=EVENT_SYSTEM_PROMPT,
                tools=[EVENT_ASSESSMENT_TOOL],
                tool_choice={"type": "tool", "name": "record_event_assessment"},
                messages=[
                    {
                        "role": "user",
                        "content": f"Assess this event:\n\nEvent ID: {event['event_id']}\nSource: {event['source']}\nTimestamp: {event['timestamp']}\n\nSummary:\n{event['summary']}",
                    }
                ],
            )
            for block in message.content:
                if block.type == "tool_use":
                    return block.input
            raise RuntimeError("Claude did not return a tool_use block for event assessment")
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error assessing '%s' (attempt %d): %s", event.get("event_id", "?"), attempt + 1, e)
                continue
            raise
    raise last_err


# ---------------------------------------------------------------------------
# Briefing generation: spokesperson prep document
# ---------------------------------------------------------------------------

BRIEFING_SYSTEM_PROMPT = """You are a senior communications strategist at Anthropic preparing spokesperson briefing documents.

Your briefings should be:
- Concise but thorough (executives are time-pressed)
- Grounded in recent coverage and actual key messages
- Honest about difficult questions the spokesperson might face
- Structured for quick scanning with clear headers

Output format:
1. ENGAGEMENT OVERVIEW (who, what, when, outlet)
2. KEY MESSAGES (3-5 core points to land)
3. RECENT COVERAGE CONTEXT (what's been written, what angles to expect)
4. ANTICIPATED QUESTIONS (tough questions + suggested framing)
5. LANDMINES TO AVOID (topics to redirect away from)
6. BRIDGING LANGUAGE (pivot phrases for difficult moments)"""


def generate_briefing(
    spokesperson: str,
    engagement_type: str,
    outlet: str,
    date: str,
    topics: list[str],
    key_messages: list[str],
    recent_coverage: list[dict[str, str]],
) -> str:
    """Generate a spokesperson prep briefing document."""
    coverage_text = "\n".join(
        f"- [{a['source']}] {a['title']} ({a['published_at']}): {a['body']}"
        for a in recent_coverage
    )

    client = get_client()
    message = client.messages.create(
        model=get_model(),
        max_tokens=2000,
        system=BRIEFING_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""Prepare a spokesperson briefing:

Spokesperson: {spokesperson}
Engagement: {engagement_type}
Outlet: {outlet}
Date: {date}
Topics: {', '.join(topics)}

Key messages to land:
{chr(10).join(f'- {m}' for m in key_messages)}

Recent relevant coverage:
{coverage_text}""",
            }
        ],
    )
    return message.content[0].text
