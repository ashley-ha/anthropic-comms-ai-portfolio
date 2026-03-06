# ABOUTME: Runnable evaluation harness for press digest and rapid response workflows.
# ABOUTME: Scores Claude outputs against human-labeled ground truth and reports metrics.
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from comms_ai_portfolio.claude_client import (
    analyze_article,
    analyze_pull_through,
    assess_event,
    draft_internal_content,
    review_internal_content,
)


def run_article_eval(data_path: Path) -> dict[str, Any]:
    """Evaluate Claude's article analysis against human labels.

    Metrics:
    - relevance_accuracy: % of articles where Claude's score is within 2 of label
    - topic_accuracy: % of articles where topic matches
    - sentiment_accuracy: % of articles where sentiment matches
    - relevance_mae: Mean absolute error on relevance scores
    """
    with data_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    results = []
    for article in articles:
        labels = article.pop("labels")
        analysis = analyze_article(article)
        results.append({
            "title": article["title"],
            "predicted": analysis,
            "labeled": labels,
        })

    relevance_within_2 = sum(
        1 for r in results
        if abs(r["predicted"]["relevance_score"] - r["labeled"]["relevance_score"]) <= 2
    )
    topic_matches = sum(
        1 for r in results if r["predicted"]["topic"] == r["labeled"]["topic"]
    )
    sentiment_matches = sum(
        1 for r in results if r["predicted"]["sentiment"] == r["labeled"]["sentiment"]
    )
    relevance_errors = [
        abs(r["predicted"]["relevance_score"] - r["labeled"]["relevance_score"])
        for r in results
    ]

    n = len(results)
    metrics = {
        "total_articles": n,
        "relevance_accuracy_within_2": round(relevance_within_2 / n, 3),
        "topic_accuracy": round(topic_matches / n, 3),
        "sentiment_accuracy": round(sentiment_matches / n, 3),
        "relevance_mae": round(sum(relevance_errors) / n, 2),
    }

    return {"metrics": metrics, "details": results}


def run_event_eval(data_path: Path) -> dict[str, Any]:
    """Evaluate Claude's event assessment against human labels.

    Metrics:
    - tier_accuracy: % of events where tier matches
    - tier_confusion: breakdown of mismatches
    - p0_recall: % of true P0 events correctly identified
    - p0_false_positive_rate: % of non-P0 events incorrectly labeled P0
    """
    with data_path.open("r", encoding="utf-8") as f:
        events = json.load(f)

    results = []
    for event in events:
        labels = event.pop("labels")
        assessment = assess_event(event)
        results.append({
            "event_id": event["event_id"],
            "predicted_tier": assessment["tier"],
            "labeled_tier": labels["tier"],
            "rationale": assessment["rationale"],
        })

    tier_matches = sum(1 for r in results if r["predicted_tier"] == r["labeled_tier"])
    true_p0 = [r for r in results if r["labeled_tier"] == "P0"]
    p0_recall = (
        sum(1 for r in true_p0 if r["predicted_tier"] == "P0") / len(true_p0)
        if true_p0
        else 0.0
    )
    non_p0 = [r for r in results if r["labeled_tier"] != "P0"]
    p0_fp_rate = (
        sum(1 for r in non_p0 if r["predicted_tier"] == "P0") / len(non_p0)
        if non_p0
        else 0.0
    )

    # Confusion breakdown
    confusion: dict[str, dict[str, int]] = {}
    for r in results:
        key = f"{r['labeled_tier']}->{r['predicted_tier']}"
        confusion[key] = confusion.get(key, 0) + 1

    n = len(results)
    metrics = {
        "total_events": n,
        "tier_accuracy": round(tier_matches / n, 3),
        "p0_recall": round(p0_recall, 3),
        "p0_false_positive_rate": round(p0_fp_rate, 3),
        "confusion": confusion,
    }

    return {"metrics": metrics, "details": results}


def run_pull_through_eval(data_path: Path, messages_path: Path) -> dict[str, Any]:
    """Evaluate Claude's pull-through analysis against human labels.

    Metrics:
    - score_range_accuracy: % of articles where overall_score falls within labeled range
    - match_type_accuracy: % of message matches where match_type is in the expected set
    - distortion_detection_recall: % of labeled distortions correctly identified
    """
    with data_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)
    with messages_path.open("r", encoding="utf-8") as f:
        framework = json.load(f)

    key_messages = framework["messages"]
    results = []

    for article in articles:
        labels = article.pop("labels")
        analysis = analyze_pull_through(article, key_messages)
        results.append({
            "title": article["title"],
            "predicted": analysis,
            "labeled": labels,
        })

    # Score range accuracy
    score_in_range = sum(
        1 for r in results
        if r["labeled"]["overall_score_range"][0] <= r["predicted"]["overall_score"] <= r["labeled"]["overall_score_range"][1]
    )

    # Match type accuracy
    match_correct = 0
    match_total = 0
    distortion_expected = 0
    distortion_detected = 0

    for r in results:
        expected_matches = r["labeled"]["expected_matches"]
        for m in r["predicted"].get("matches", []):
            msg_id = m["message_id"]
            if msg_id in expected_matches:
                match_total += 1
                if m["match_type"] in expected_matches[msg_id]["match_types"]:
                    match_correct += 1
                # Track distortion recall
                if "distorted" in expected_matches[msg_id]["match_types"]:
                    distortion_expected += 1
                    if m["match_type"] == "distorted":
                        distortion_detected += 1

    n = len(results)
    metrics = {
        "total_articles": n,
        "score_range_accuracy": round(score_in_range / n, 3) if n else 0,
        "match_type_accuracy": round(match_correct / match_total, 3) if match_total else 0,
        "distortion_detection_recall": round(distortion_detected / distortion_expected, 3) if distortion_expected else 0,
    }

    return {"metrics": metrics, "details": results}


def run_internal_comms_eval(data_path: Path) -> dict[str, Any]:
    """Evaluate Claude's internal comms drafting and review against human labels.

    Metrics:
    - recommendation_accuracy: % where approval_recommendation is in expected set
    - tone_floor_pass_rate: % where tone_score >= labeled minimum
    - clarity_floor_pass_rate: % where clarity_score >= labeled minimum
    - alignment_floor_pass_rate: % where alignment_score >= labeled minimum
    - sensitivity_detection_accuracy: % where sensitivity flags match expectation
    """
    with data_path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    for case in cases:
        labels = case.pop("labels")
        draft = draft_internal_content(case)
        review = review_internal_content(draft, case)
        results.append({
            "subject": case["subject"],
            "content_type": case["content_type"],
            "predicted": review,
            "labeled": labels,
        })

    n = len(results)
    rec_correct = sum(
        1 for r in results
        if r["predicted"]["approval_recommendation"] in r["labeled"]["expected_recommendation"]
    )
    tone_pass = sum(
        1 for r in results
        if r["predicted"]["tone_score"] >= r["labeled"]["min_tone_score"]
    )
    clarity_pass = sum(
        1 for r in results
        if r["predicted"]["clarity_score"] >= r["labeled"]["min_clarity_score"]
    )
    alignment_pass = sum(
        1 for r in results
        if r["predicted"]["alignment_score"] >= r["labeled"]["min_alignment_score"]
    )
    sensitivity_correct = sum(
        1 for r in results
        if (len(r["predicted"].get("sensitivity_flags", [])) > 0) == r["labeled"]["should_flag_sensitivity"]
    )

    metrics = {
        "total_cases": n,
        "recommendation_accuracy": round(rec_correct / n, 3) if n else 0,
        "tone_floor_pass_rate": round(tone_pass / n, 3) if n else 0,
        "clarity_floor_pass_rate": round(clarity_pass / n, 3) if n else 0,
        "alignment_floor_pass_rate": round(alignment_pass / n, 3) if n else 0,
        "sensitivity_detection_accuracy": round(sensitivity_correct / n, 3) if n else 0,
    }

    return {"metrics": metrics, "details": results}


def print_report(name: str, result: dict[str, Any]) -> None:
    """Pretty-print an eval report to stdout."""
    print(f"\n{'=' * 60}")
    print(f"  EVAL REPORT: {name}")
    print(f"{'=' * 60}")
    for key, value in result["metrics"].items():
        if isinstance(value, dict):
            print(f"\n  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    print(f"\n  Details:")
    for detail in result["details"]:
        if "title" in detail and "predicted" in detail and "labeled" in detail:
            pred = detail["predicted"]
            lab = detail["labeled"]
            if "relevance_score" in pred:
                match = "PASS" if abs(pred["relevance_score"] - lab["relevance_score"]) <= 2 else "FAIL"
                print(f"    [{match}] {detail['title'][:50]}...")
                print(f"          predicted: rel={pred['relevance_score']} topic={pred['topic']} sent={pred['sentiment']}")
                print(f"          labeled:   rel={lab['relevance_score']} topic={lab['topic']} sent={lab['sentiment']}")
            elif "overall_score" in pred:
                lo, hi = lab["overall_score_range"]
                match = "PASS" if lo <= pred["overall_score"] <= hi else "FAIL"
                print(f"    [{match}] {detail['title'][:50]}...")
                print(f"          predicted: score={pred['overall_score']}% (expected {lo}-{hi}%)")
        elif "event_id" in detail:
            match = "PASS" if detail["predicted_tier"] == detail["labeled_tier"] else "FAIL"
            print(f"    [{match}] {detail['event_id']}: predicted={detail['predicted_tier']} labeled={detail['labeled_tier']}")
        elif "content_type" in detail and "predicted" in detail and "labeled" in detail:
            pred = detail["predicted"]
            lab = detail["labeled"]
            rec_ok = pred["approval_recommendation"] in lab["expected_recommendation"]
            match = "PASS" if rec_ok else "FAIL"
            print(f"    [{match}] {detail['subject'][:50]}")
            print(f"          recommendation: {pred['approval_recommendation']} (expected: {lab['expected_recommendation']})")
            print(f"          scores: tone={pred['tone_score']} clarity={pred['clarity_score']} alignment={pred['alignment_score']}")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parents[1] / "data"

    print("Running article evaluation...")
    article_result = run_article_eval(data_dir / "eval_articles_labeled.json")
    print_report("Press Digest — Article Analysis", article_result)

    print("Running event evaluation...")
    event_result = run_event_eval(data_dir / "eval_events_labeled.json")
    print_report("Rapid Response — Event Triage", event_result)

    print("Running pull-through evaluation...")
    pull_through_result = run_pull_through_eval(
        data_dir / "eval_pull_through_labeled.json",
        data_dir / "key_messages.json",
    )
    print_report("Pull-Through Tracker — Message Analysis", pull_through_result)

    print("Running internal comms evaluation...")
    internal_comms_result = run_internal_comms_eval(
        data_dir / "eval_internal_comms_labeled.json",
    )
    print_report("Internal Comms — Draft & Review", internal_comms_result)

    # Save results
    output_dir = Path(__file__).resolve().parents[1] / "outputs"
    output_dir.mkdir(exist_ok=True)
    with (output_dir / "eval_results.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "article_eval": article_result["metrics"],
                "event_eval": event_result["metrics"],
                "pull_through_eval": pull_through_result["metrics"],
                "internal_comms_eval": internal_comms_result["metrics"],
            },
            f,
            indent=2,
        )
    print(f"Results saved to {output_dir / 'eval_results.json'}")
