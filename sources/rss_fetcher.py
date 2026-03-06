# ABOUTME: RSS feed fetcher for live article ingestion.
# ABOUTME: Pulls from AI-focused news feeds, keyword-filters, and outputs the article schema used by press_digest and pull_through_tracker.
from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx

logger = logging.getLogger(__name__)

# AI-focused RSS feeds — public, no auth required
DEFAULT_FEEDS: list[dict[str, str]] = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "The Guardian AI", "url": "https://www.theguardian.com/technology/artificialintelligenceai/rss"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
]

# Keywords for pre-filtering — generous list to catch obliquely relevant stories
KEYWORDS: list[str] = [
    "anthropic", "claude", "ai safety", "ai regulation", "ai policy",
    "openai", "gpt", "deepmind", "gemini", "frontier model", "frontier ai",
    "large language model", "llm", "chatbot", "generative ai",
    "ai act", "ai governance", "responsible ai", "ai ethics",
    "artificial intelligence",
]

# Compiled regex for fast keyword matching (case-insensitive)
_KEYWORD_PATTERN = re.compile(
    "|".join(re.escape(kw) for kw in KEYWORDS),
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _parse_published(entry: Any) -> str:
    """Extract and normalize the published timestamp from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc).isoformat()


def fetch_feed(feed_url: str, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS feed, returning raw entries."""
    try:
        resp = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s: %s", feed_url, e)
        return []

    parsed = feedparser.parse(resp.text)
    return parsed.entries


def entry_to_article(entry: Any, source_name: str) -> dict[str, str]:
    """Convert a feedparser entry to the article schema."""
    title = _strip_html(getattr(entry, "title", "Untitled"))

    # Prefer content over summary for body text
    body = ""
    if hasattr(entry, "content") and entry.content:
        body = _strip_html(entry.content[0].get("value", ""))
    if not body and hasattr(entry, "summary"):
        body = _strip_html(entry.summary or "")
    if not body and hasattr(entry, "description"):
        body = _strip_html(entry.description or "")

    return {
        "title": title,
        "body": body[:2000],  # Cap body length to keep Claude calls efficient
        "source": source_name,
        "url": getattr(entry, "link", ""),
        "published_at": _parse_published(entry),
    }


def matches_keywords(article: dict[str, str]) -> bool:
    """Check if an article's title or body matches any AI-related keywords."""
    text = f"{article['title']} {article['body']}"
    return bool(_KEYWORD_PATTERN.search(text))


def fetch_live_articles(
    feeds: list[dict[str, str]] | None = None,
    max_per_feed: int = 20,
) -> list[dict[str, str]]:
    """Fetch articles from all configured RSS feeds, filter by keywords.

    Args:
        feeds: List of feed dicts with 'name' and 'url'. Defaults to DEFAULT_FEEDS.
        max_per_feed: Maximum entries to process per feed.

    Returns:
        List of article dicts matching the project's article schema.
    """
    feeds = feeds or DEFAULT_FEEDS
    all_articles: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for feed in feeds:
        logger.info("Fetching %s...", feed["name"])
        entries = fetch_feed(feed["url"])
        count = 0

        for entry in entries[:max_per_feed]:
            article = entry_to_article(entry, feed["name"])

            # Deduplicate by URL
            if article["url"] in seen_urls:
                continue
            seen_urls.add(article["url"])

            # Keyword pre-filter
            if not matches_keywords(article):
                continue

            all_articles.append(article)
            count += 1

        logger.info("  %s: %d articles matched keywords (of %d entries)", feed["name"], count, len(entries))

    # Sort by published date, newest first
    all_articles.sort(key=lambda a: a["published_at"], reverse=True)

    return all_articles


def save_articles(articles: list[dict[str, str]], output_path: Path) -> None:
    """Save articles to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
