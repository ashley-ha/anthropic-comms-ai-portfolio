# ABOUTME: Data models for articles, events, briefing requests, and pull-through analysis.
# ABOUTME: Used across press digest, rapid response, briefing generator, and pull-through tracker workflows.
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    title: str
    body: str
    source: str
    url: str
    published_at: str


@dataclass
class AnalyzedArticle:
    title: str
    body: str
    source: str
    url: str
    published_at: str
    relevance_score: int
    topic: str
    sentiment: str
    rationale: str


@dataclass
class Event:
    event_id: str
    summary: str
    source: str
    timestamp: str


@dataclass
class AlertAssessment:
    event_id: str
    timestamp: str
    source: str
    summary: str
    priority_score: int
    tier: str
    owners: list[str]
    response_sla_hours: int
    human_review_required: bool
    rationale: str
    talking_points: list[str]


@dataclass
class MessageMatch:
    message_id: str
    narrative: str
    match_type: str  # "verbatim", "paraphrased", "thematic", "distorted", "absent"
    confidence: int  # 1-10
    evidence: str  # Direct quote or passage from the article
    distortion_note: str  # If distorted, what changed


@dataclass
class PullThroughResult:
    title: str
    source: str
    url: str
    published_at: str
    overall_score: int  # 0-100 pull-through percentage
    matches: list[MessageMatch] = field(default_factory=list)
    narrative_gaps: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class BriefingRequest:
    spokesperson: str
    engagement_type: str
    outlet: str
    date: str
    topics: list[str]
    key_messages: list[str]
    recent_coverage: list[Article] = field(default_factory=list)


@dataclass
class ContentReview:
    tone_score: int  # 1-10
    clarity_score: int  # 1-10
    alignment_score: int  # 1-10
    sensitivity_flags: list[str]
    suggested_edits: list[str]
    approval_recommendation: str  # "approve", "revise", "escalate"
    rationale: str


@dataclass
class InternalCommsResult:
    content_type: str  # "all_hands", "faq", "leadership_message"
    subject: str
    draft: str
    review: ContentReview
    formatted_outputs: dict[str, str] = field(default_factory=dict)  # channel -> formatted text
