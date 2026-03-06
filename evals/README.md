# Evaluation Plan

This folder captures how quality is measured before rollout.

## Press Digest Evals

- Precision@TopN for relevant clips.
- Topic classification agreement vs. human labels.
- Sentiment agreement vs. human labels.
- Failure cases:
  - False positives on generic AI news.
  - Missed policy stories with uncommon phrasing.

## Rapid Response Evals

- Priority tier agreement vs. incident review labels.
- Alert routing accuracy.
- Time-to-alert and time-to-first-human-review.
- Failure cases:
  - Over-escalation for low-impact social chatter.
  - Under-escalation for subtle legal/regulatory risks.

## KPI Targets (Initial)

- 30-50% reduction in manual clipping time.
- <5% missed high-priority incidents.
- <15% false-positive P0 alerts.
