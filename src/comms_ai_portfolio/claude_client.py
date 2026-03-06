# ABOUTME: Thin wrapper around the Anthropic SDK for structured Claude calls.
# ABOUTME: Provides article analysis, event assessment, briefing generation, and internal comms workflows.
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
# Pull-through analysis: message reflection in earned media
# ---------------------------------------------------------------------------

PULL_THROUGH_TOOL = {
    "name": "record_pull_through_analysis",
    "description": "Record how well an article reflects Anthropic's key messages.",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_score": {
                "type": "integer",
                "description": "0-100 overall pull-through percentage. 100 = every key message faithfully reflected; 0 = no messages present.",
            },
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "ID of the key message being evaluated.",
                        },
                        "match_type": {
                            "type": "string",
                            "enum": ["verbatim", "paraphrased", "thematic", "distorted", "absent"],
                            "description": "How the message appeared: verbatim (direct quote), paraphrased (same meaning, different words), thematic (general alignment), distorted (twisted or misrepresented), absent (not present).",
                        },
                        "confidence": {
                            "type": "integer",
                            "description": "1-10 confidence in this match assessment.",
                        },
                        "evidence": {
                            "type": "string",
                            "description": "Direct quote or passage from the article supporting this assessment. Use empty string if absent.",
                        },
                        "distortion_note": {
                            "type": "string",
                            "description": "If match_type is 'distorted', explain what was changed or misrepresented. Empty string otherwise.",
                        },
                    },
                    "required": ["message_id", "match_type", "confidence", "evidence", "distortion_note"],
                },
                "description": "Assessment for each key message.",
            },
            "narrative_gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key messages that were completely absent and represent missed opportunities.",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence summary of how well this article serves Anthropic's messaging goals.",
            },
        },
        "required": ["overall_score", "matches", "narrative_gaps", "summary"],
    },
}

PULL_THROUGH_SYSTEM_PROMPT = """You are a communications analyst measuring message pull-through in earned media coverage about Anthropic.

"Message pull-through" means: did the journalist reflect Anthropic's intended key messages in their reporting? This is a core PR effectiveness metric.

For each article, you will be given Anthropic's key messaging framework and the article text. Your job is to assess each key message:

Match types:
- verbatim: The article directly quotes or very closely mirrors the key message language.
- paraphrased: The article conveys the same meaning using different words.
- thematic: The article's framing generally aligns with the narrative direction, but doesn't specifically convey the message.
- distorted: The article references the narrative but twists, undermines, or misrepresents it. THIS IS IMPORTANT TO FLAG.
- absent: The message is not reflected in the article at all.

Scoring guidelines:
- overall_score represents what percentage of the messaging framework was effectively reflected.
- A "verbatim" or "paraphrased" match on a primary message contributes more than a "thematic" match on a secondary message.
- Distorted messages should REDUCE the overall score — a twisted message is worse than an absent one.
- Articles not about Anthropic will naturally have low scores; that's expected, not a failure.

Be rigorous. Comms teams use this data to refine their media strategy."""


def analyze_pull_through(
    article: dict[str, str],
    key_messages: list[dict[str, str]],
    retries: int = 2,
) -> dict[str, Any]:
    """Analyze how well an article reflects Anthropic's key messages."""
    messages_text = "\n".join(
        f"- [{m['id']}] ({m['priority']}) {m['narrative']}"
        for m in key_messages
    )

    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=1000,
                system=PULL_THROUGH_SYSTEM_PROMPT,
                tools=[PULL_THROUGH_TOOL],
                tool_choice={"type": "tool", "name": "record_pull_through_analysis"},
                messages=[
                    {
                        "role": "user",
                        "content": f"""Analyze this article for message pull-through:

Title: {article['title']}
Source: {article['source']}
Published: {article['published_at']}

Body:
{article['body']}

---

KEY MESSAGING FRAMEWORK:
{messages_text}""",
                    }
                ],
            )
            for block in message.content:
                if block.type == "tool_use":
                    return block.input
            raise RuntimeError("Claude did not return a tool_use block for pull-through analysis")
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error analyzing pull-through for '%s' (attempt %d): %s", article.get("title", "?"), attempt + 1, e)
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


# ---------------------------------------------------------------------------
# Internal comms: draft, review, format
# ---------------------------------------------------------------------------

DRAFT_SYSTEM_PROMPT = """You are a senior internal communications writer at Anthropic. You draft content for all-hands updates, FAQs, and leadership messages.

Your writing should be:
- Authentic to the author's voice — executives at Anthropic are direct, thoughtful, and honest
- Transparent about challenges — employees see through spin, so acknowledge difficulties plainly
- Concise — busy employees scan, so use clear headers and short paragraphs
- Sensitive to confidential matters — flag language that could be problematic if leaked

Content types:
- all_hands: Company-wide update from leadership. Structured with clear sections, forward-looking.
- faq: Q&A format anticipating employee questions. Direct, honest answers.
- leadership_message: Personal communication from an executive. More conversational tone.

Always write as if this content could appear on the front page of the New York Times tomorrow. Internal comms at high-profile AI companies frequently leak."""

DRAFT_FAQ_SYSTEM_PROMPT = """You are a senior internal communications writer at Anthropic. You draft FAQ documents that anticipate employee questions.

Your FAQs should:
- Anticipate the hardest questions employees will ask — don't just cover softballs
- Give direct, honest answers — employees see through corporate deflection
- Address emotional concerns (job security, company reputation) alongside factual ones
- Include a "what we don't know yet" section when appropriate
- Be concise — 2-4 sentences per answer

Write as if this FAQ could appear on the front page of the New York Times tomorrow."""


CONTENT_REVIEW_TOOL = {
    "name": "record_content_review",
    "description": "Record a structured review of internal communications content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tone_score": {
                "type": "integer",
                "description": "1-10 score for tone appropriateness. 10 = perfectly calibrated for audience and context; 1 = severely off-tone.",
            },
            "clarity_score": {
                "type": "integer",
                "description": "1-10 score for clarity and readability. 10 = crystal clear; 1 = confusing or jargon-heavy.",
            },
            "alignment_score": {
                "type": "integer",
                "description": "1-10 score for alignment with the stated key points and messaging goals. 10 = all points covered faithfully; 1 = off-message.",
            },
            "sensitivity_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific phrases or sections that could be problematic if leaked, misinterpreted, or that touch sensitive topics inappropriately. Empty array if none.",
            },
            "suggested_edits": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete, actionable edit suggestions. Each should specify what to change and why.",
            },
            "approval_recommendation": {
                "type": "string",
                "enum": ["approve", "revise", "escalate"],
                "description": "approve = ready to send; revise = needs edits before sending; escalate = contains sensitive content requiring leadership/legal sign-off.",
            },
            "rationale": {
                "type": "string",
                "description": "2-3 sentence summary of the review findings and recommendation.",
            },
        },
        "required": [
            "tone_score",
            "clarity_score",
            "alignment_score",
            "sensitivity_flags",
            "suggested_edits",
            "approval_recommendation",
            "rationale",
        ],
    },
}

REVIEW_SYSTEM_PROMPT = """You are a communications review editor at Anthropic. You review internal content before it's distributed to employees.

Your review should evaluate:
1. TONE: Is the content appropriately calibrated for the audience? Too corporate? Too casual? Appropriately empathetic about difficult topics?
2. CLARITY: Is the content easy to scan and understand? Are there jargon or ambiguities?
3. ALIGNMENT: Does the content faithfully cover the stated key points? Are any points missing or misrepresented?
4. SENSITIVITY: Could any phrases be damaging if leaked? Are sensitive topics handled with appropriate care?

Recommendation guidelines:
- approve: Content is ready to distribute. Minor imperfections are acceptable.
- revise: Content has specific issues that should be fixed before distribution. Always include concrete edit suggestions.
- escalate: Content touches on legal, regulatory, or reputational matters that need leadership or legal review before distribution.

Be constructive but honest. A weak all-hands message from the CEO is worse than a delayed one."""


def draft_internal_content(request: dict[str, Any], retries: int = 2) -> str:
    """Generate a draft of internal communications content."""
    content_type = request["content_type"]
    system = DRAFT_FAQ_SYSTEM_PROMPT if content_type == "faq" else DRAFT_SYSTEM_PROMPT

    key_points_text = "\n".join(f"- {p}" for p in request["key_points"])
    sensitive_text = "\n".join(f"- {s}" for s in request.get("sensitive_topics", []))
    channels_text = ", ".join(request.get("distribution_channels", ["email"]))

    user_prompt = f"""Draft a {content_type.replace('_', ' ')} communication:

Subject: {request['subject']}
Author: {request.get('author', 'Communications Team')}
Audience: {request.get('audience', 'All employees')}
Desired tone: {request.get('tone', 'professional and transparent')}

Key points to cover:
{key_points_text}

Sensitive topics to handle carefully:
{sensitive_text}

Context:
{request.get('context', '')}

Distribution channels: {channels_text}"""

    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=2000,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error drafting content (attempt %d): %s", attempt + 1, e)
                continue
            raise
    raise last_err


def review_internal_content(
    draft: str,
    request: dict[str, Any],
    retries: int = 2,
) -> dict[str, Any]:
    """Review a draft of internal communications content for tone, clarity, and sensitivity."""
    key_points_text = "\n".join(f"- {p}" for p in request["key_points"])
    sensitive_text = "\n".join(f"- {s}" for s in request.get("sensitive_topics", []))

    user_prompt = f"""Review this internal communications draft:

CONTENT TYPE: {request['content_type'].replace('_', ' ')}
SUBJECT: {request['subject']}
AUDIENCE: {request.get('audience', 'All employees')}
DESIRED TONE: {request.get('tone', 'professional and transparent')}

KEY POINTS THAT SHOULD BE COVERED:
{key_points_text}

SENSITIVE TOPICS TO HANDLE CAREFULLY:
{sensitive_text}

---

DRAFT TO REVIEW:
{draft}"""

    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=800,
                system=REVIEW_SYSTEM_PROMPT,
                tools=[CONTENT_REVIEW_TOOL],
                tool_choice={"type": "tool", "name": "record_content_review"},
                messages=[{"role": "user", "content": user_prompt}],
            )
            for block in message.content:
                if block.type == "tool_use":
                    return block.input
            raise RuntimeError("Claude did not return a tool_use block for content review")
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error reviewing content (attempt %d): %s", attempt + 1, e)
                continue
            raise
    raise last_err


FORMAT_SYSTEM_PROMPT = """You are a communications formatter at Anthropic. You adapt internal content for specific distribution channels.

Channel formatting rules:
- slack: Use Slack mrkdwn syntax. Break into digestible blocks. Use *bold* for headers, bullet points for lists. Keep total length under 3000 characters. Add a tl;dr at the top.
- email: Use clean HTML-safe plain text. Include a subject line. Professional but warm formatting. Full content with proper paragraphs.

Preserve the content faithfully — formatting changes only, no substantive edits."""


def format_for_channel(
    content: str,
    channel: str,
    subject: str,
    retries: int = 2,
) -> str:
    """Format internal communications content for a specific distribution channel."""
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            message = client.messages.create(
                model=get_model(),
                max_tokens=2000,
                system=FORMAT_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Format this content for the '{channel}' channel:\n\nSubject: {subject}\n\n---\n\n{content}",
                    }
                ],
            )
            return message.content[0].text
        except anthropic.APIStatusError as e:
            last_err = e
            if attempt < retries and e.status_code in {429, 500, 502, 503, 529}:
                logger.warning("Retryable error formatting for %s (attempt %d): %s", channel, attempt + 1, e)
                continue
            raise
    raise last_err
