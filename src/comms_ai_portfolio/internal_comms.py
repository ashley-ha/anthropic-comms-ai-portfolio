# ABOUTME: Internal communications workflow tool powered by Claude.
# ABOUTME: Three-stage pipeline: draft generation, structured review, and channel-specific formatting.
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .claude_client import draft_internal_content, format_for_channel, review_internal_content

logger = logging.getLogger(__name__)


def build_internal_comms(
    request_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Run the full internal comms pipeline: draft, review, format.

    Stage 1 — Draft: Claude generates initial content from the brief.
    Stage 2 — Review: Claude reviews the draft with structured feedback
              (tone, clarity, alignment, sensitivity flags). This is where
              a human would approve/reject before proceeding.
    Stage 3 — Format: Claude adapts the reviewed content for each
              distribution channel (Slack, email).

    Args:
        request_path: Path to JSON file containing the comms brief.
        output_path: Path where the Markdown workflow report will be written.

    Returns:
        Summary dict with content_type, review scores, and recommendation.
    """
    with request_path.open("r", encoding="utf-8") as f:
        request = json.load(f)

    # Stage 1: Draft
    logger.info("Stage 1: Drafting %s content...", request["content_type"])
    draft = draft_internal_content(request)

    # Stage 2: Review
    logger.info("Stage 2: Reviewing draft...")
    review = review_internal_content(draft, request)

    # Stage 3: Format for distribution channels
    channels = request.get("distribution_channels", ["email"])
    logger.info("Stage 3: Formatting for channels: %s", ", ".join(channels))
    formatted = _format_channels(draft, channels, request["subject"])

    # Build output report
    lines = _format_report(request, draft, review, formatted)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "content_type": request["content_type"],
        "subject": request["subject"],
        "draft_word_count": len(draft.split()),
        "tone_score": review["tone_score"],
        "clarity_score": review["clarity_score"],
        "alignment_score": review["alignment_score"],
        "sensitivity_flags_count": len(review.get("sensitivity_flags", [])),
        "approval_recommendation": review["approval_recommendation"],
        "channels_formatted": list(formatted.keys()),
    }


def _format_channels(
    content: str,
    channels: list[str],
    subject: str,
) -> dict[str, str]:
    """Format content for multiple channels in parallel."""
    formatted: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=len(channels)) as pool:
        futures = {
            pool.submit(format_for_channel, content, ch, subject): ch
            for ch in channels
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                formatted[ch] = future.result()
            except Exception as e:
                logger.error("Failed to format for %s: %s", ch, e)
                formatted[ch] = f"[Formatting failed: {e}]"

    return formatted


def _format_report(
    request: dict[str, Any],
    draft: str,
    review: dict[str, Any],
    formatted: dict[str, str],
) -> list[str]:
    """Format the full workflow output as a Markdown report."""
    lines = [
        "# Internal Communications Workflow Report",
        "",
        f"**Content type:** {request['content_type'].replace('_', ' ').title()}",
        f"**Subject:** {request['subject']}",
        f"**Author:** {request.get('author', 'Communications Team')}",
        f"**Audience:** {request.get('audience', 'All employees')}",
        "",
        "---",
        "",
        "## Stage 1: Draft",
        "",
        draft,
        "",
        "---",
        "",
        "## Stage 2: Editorial Review",
        "",
        f"**Tone:** {review['tone_score']}/10",
        f"**Clarity:** {review['clarity_score']}/10",
        f"**Alignment:** {review['alignment_score']}/10",
        f"**Recommendation:** {review['approval_recommendation'].upper()}",
        "",
        f"> {review['rationale']}",
        "",
    ]

    if review.get("sensitivity_flags"):
        lines.extend(["### Sensitivity Flags", ""])
        for flag in review["sensitivity_flags"]:
            lines.append(f"- {flag}")
        lines.append("")

    if review.get("suggested_edits"):
        lines.extend(["### Suggested Edits", ""])
        for edit in review["suggested_edits"]:
            lines.append(f"- {edit}")
        lines.append("")

    lines.extend(["---", "", "## Stage 3: Channel Formatting", ""])

    for channel, content in sorted(formatted.items()):
        lines.extend([
            f"### {channel.title()}",
            "",
            "```",
            content,
            "```",
            "",
        ])

    return lines
