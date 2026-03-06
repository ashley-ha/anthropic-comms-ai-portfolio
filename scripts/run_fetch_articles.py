#!/usr/bin/env python3
# ABOUTME: Entry point for the live article fetcher.
# ABOUTME: Pulls real articles from RSS feeds and saves them for press_digest and pull_through_tracker.
from pathlib import Path
import logging
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sources.rss_fetcher import fetch_live_articles, save_articles

logging.basicConfig(level=logging.INFO, format="%(message)s")

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output_path = root / "data" / "live_articles.json"

    # Parse --limit N flag (default: no limit)
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    print("Fetching live articles from RSS feeds...")
    print()

    articles = fetch_live_articles()

    if limit and len(articles) > limit:
        articles = articles[:limit]
        print(f"(limited to {limit} most recent articles)")

    if not articles:
        print("No articles matched keywords. Check network connection and feed availability.")
        sys.exit(1)

    save_articles(articles, output_path)

    # Summary
    sources = {}
    for a in articles:
        sources[a["source"]] = sources.get(a["source"], 0) + 1

    print()
    print(f"Fetched {len(articles)} articles matching AI keywords")
    print()
    print("By source:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")
    print()
    print(f"Saved to: {output_path}")
    print()
    print("Run with live data:")
    print(f"  python scripts/run_press_digest.py --live")
    print(f"  python scripts/run_pull_through.py --live")
