# Architecture Notes

## Press Digest

1. Ingest articles from approved feeds.
2. Normalize content and metadata.
3. Score relevance and classify topic/sentiment.
4. Build formatted digest.
5. Publish to Slack/email.

## Rapid Response

1. Ingest event signals (news/social/policy).
2. Score urgency using risk vocabulary + heuristics.
3. Assign tier and owners.
4. Trigger alerts with response SLA.
5. Record outcomes for tuning.

## Reliability Principles

- Deterministic baseline logic before modelized routing.
- Transparent scoring to aid trust and debugging.
- Human review for high-impact actions.
