from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def _path(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return str(value.get("path", ""))
    return ""


def _paths(values: Iterable[object]) -> list[str]:
    return [path for value in values if (path := _path(value))]


def rank_score(expected: set[str], predicted: list[str]) -> tuple[bool, bool, float]:
    ranks = [index for index, path in enumerate(predicted, start=1) if path in expected]
    return bool(ranks and ranks[0] == 1), bool(ranks and ranks[0] <= 3), (
        1.0 / ranks[0] if ranks else 0.0
    )


def _accepted_sets(outcome: Mapping[str, Any]) -> list[set[str]]:
    explicit = outcome.get("expected_owner_sets")
    if explicit:
        return [{str(path) for path in owner_set} for owner_set in explicit]
    expected = {str(path) for path in outcome.get("expected_primary", [])}
    return [expected] if expected else []


def _predicted_owner_set(outcome: Mapping[str, Any]) -> set[str]:
    if "primary_owner" in outcome or "co_owners" in outcome:
        primary = _path(outcome.get("primary_owner"))
        return ({primary} if primary else set()) | set(_paths(outcome.get("co_owners", [])))
    return set(_paths(outcome.get("predicted_primary", [])))


def _ranked_candidates(outcome: Mapping[str, Any]) -> list[str]:
    if "primary_owner" in outcome or "alternatives" in outcome:
        owners = _predicted_owner_set(outcome)
        primary = _path(outcome.get("primary_owner"))
        ordered = ([primary] if primary else []) + sorted(owners - {primary})
        ordered.extend(_paths(outcome.get("alternatives", [])))
        return list(dict.fromkeys(ordered))
    return _paths(outcome.get("predicted_primary", []))


def _best_expected(predicted: set[str], accepted: list[set[str]]) -> set[str]:
    return max(
        accepted,
        key=lambda expected: (
            len(predicted & expected),
            -len(predicted ^ expected),
            tuple(sorted(expected)),
        ),
        default=set(),
    )


def aggregate_phase1_metrics(outcomes: list[Mapping[str, Any]]) -> dict[str, Any]:
    scored = [
        outcome
        for outcome in outcomes
        if not bool(outcome.get("expected_abstain"))
        and str(outcome.get("expected_status", "")) != "abstain"
    ]
    owner_tp = owner_fp = owner_fn = exact = false_primary = 0
    hit_one_total = hit_three_total = reciprocal_total = 0.0
    incorrect_high = 0
    bins: dict[str, list[bool]] = defaultdict(list)
    failure_ids: list[str] = []
    for outcome in outcomes:
        accepted = _accepted_sets(outcome)
        predicted = _predicted_owner_set(outcome)
        expected = _best_expected(predicted, accepted)
        owner_tp += len(predicted & expected)
        owner_fp += len(predicted - expected)
        owner_fn += len(expected - predicted)
        expected_abstain = bool(outcome.get("expected_abstain")) or str(
            outcome.get("expected_status", "")
        ) == "abstain"
        predicted_abstain = str(outcome.get("status", "")) == "abstain" or not predicted
        if (accepted and any(predicted == owner_set for owner_set in accepted)) or (
            expected_abstain and predicted_abstain
        ):
            exact += 1
        primary = _path(outcome.get("primary_owner"))
        if "primary_owner" not in outcome and not primary:
            legacy = _paths(outcome.get("predicted_primary", []))
            primary = legacy[0] if legacy else ""
        primary_correct = bool(primary and any(primary in item for item in accepted))
        if primary and not primary_correct:
            false_primary += 1
        confidence = str(
            outcome.get("confidence_level", outcome.get("confidence", "unknown"))
        ).casefold()
        confidence_correct = (
            predicted_abstain if expected_abstain else primary_correct
        )
        if confidence in {"high", "medium", "low"}:
            bins[confidence].append(confidence_correct)
        if confidence == "high" and primary and not primary_correct:
            incorrect_high += 1
        if expected and predicted != expected:
            failure_ids.append(str(outcome.get("task_id", outcome.get("id", "<unknown>"))))
        if outcome in scored:
            accepted_union = set().union(*accepted) if accepted else set()
            hit_one, hit_three, reciprocal = rank_score(
                accepted_union, _ranked_candidates(outcome)
            )
            hit_one_total += float(hit_one)
            hit_three_total += float(hit_three)
            reciprocal_total += reciprocal
    predicted_abstentions = [
        outcome
        for outcome in outcomes
        if str(outcome.get("status", "")) == "abstain"
        or bool(outcome.get("abstained"))
        or not _predicted_owner_set(outcome)
    ]
    expected_abstentions = [
        outcome
        for outcome in outcomes
        if bool(outcome.get("expected_abstain"))
        or str(outcome.get("expected_status", "")) == "abstain"
    ]
    abstention_tp = sum(outcome in expected_abstentions for outcome in predicted_abstentions)
    predicted_count = sum(bool(_predicted_owner_set(outcome)) for outcome in outcomes)
    false_primary_denominator = sum(
        bool(_path(outcome.get("primary_owner")))
        if "primary_owner" in outcome
        else bool(_paths(outcome.get("predicted_primary", [])))
        for outcome in outcomes
    )
    scored_count = len(scored)
    return {
        "cases": len(outcomes),
        "hit_at_1": hit_one_total / scored_count if scored_count else 0.0,
        "hit_at_3": hit_three_total / scored_count if scored_count else 0.0,
        "mrr": reciprocal_total / scored_count if scored_count else 0.0,
        "primary_owner_precision": owner_tp / (owner_tp + owner_fp) if owner_tp + owner_fp else 0.0,
        "primary_owner_recall": owner_tp / (owner_tp + owner_fn) if owner_tp + owner_fn else 0.0,
        "exact_owner_set_match": exact / len(outcomes) if outcomes else 0.0,
        "false_primary_rate": (
            false_primary / false_primary_denominator if false_primary_denominator else 0.0
        ),
        "abstention_precision": (
            abstention_tp / len(predicted_abstentions)
            if predicted_abstentions
            else (1.0 if not expected_abstentions else 0.0)
        ),
        "abstention_recall": (
            abstention_tp / len(expected_abstentions) if expected_abstentions else 1.0
        ),
        "confidence_bin_accuracy": {
            level: sum(results) / len(results) for level, results in sorted(bins.items())
        },
        "incorrect_high_confidence": incorrect_high,
        "unsafe_high_confidence_count": incorrect_high,
        "owner_true_positive": owner_tp,
        "owner_predicted": predicted_count,
        "owner_expected": owner_tp + owner_fn,
        "failure_ids": sorted(set(failure_ids)),
    }
