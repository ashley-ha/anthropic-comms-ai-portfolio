# Comms Automation Playbook

## 1) Workflow: Daily Press Digest

Problem:
Manual clip curation is slow, inconsistent, and hard to scale during high-volume cycles.

Design:
- Ingest coverage sources.
- Score relevance to Anthropic narratives.
- Tag topic and sentiment.
- Generate Slack-ready morning brief.

Rollout:
- Week 1: Shadow mode (no production distribution).
- Week 2: Team pilot with manual approval.
- Week 3+: Expand to full team with weekly quality review.

KPIs:
- Time spent on morning clips.
- Relevance precision at top 10 clips.
- Team satisfaction with digest usefulness.

## 2) Workflow: Rapid Response Alerting

Problem:
High-risk stories can be detected too late or routed inconsistently.

Design:
- Monitor inbound event streams.
- Score urgency and assign tier (P0/P1/P2).
- Route to owners with SLA expectations.

Rollout:
- Start with policy/legal-sensitive sources.
- Require human review for P0/P1 during initial launch.
- Add auto-routing after error rate stabilizes.

KPIs:
- Mean time to alert.
- Mean time to first response.
- Escalation accuracy.

## 3) Training and Enablement

- 45-minute onboarding session for comms stakeholders.
- 1-page quick-start guide per workflow.
- Weekly office hours during first 30 days.
- Feedback form linked in all outputs.

## 4) Governance and Safety

- Human-in-the-loop for high-severity outputs.
- Logged decisions for post-incident review.
- No external data ingestion without legal/terms review.
- Prompt/eval updates versioned with changelog.
