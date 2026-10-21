"""Describe whether a real-account evaluation could be run. Do not compute scores.

Thirty confirmed accounts is a count milestone only. It is not proof of reliability.
"""

from __future__ import annotations

from app.datasets import MIN_CONFIRMED_ACCOUNTS, evaluation_report, split_by_account


def readiness(observations: list[dict], labels: list[dict]) -> dict:
    report = evaluation_report(observations, labels)
    assigned = split_by_account(observations) if observations else {}
    groups = {"train": set(), "validation": set(), "test": set()}
    for key, name in assigned.items():
        groups[name].add(key)
    overlap = bool(groups["train"] & groups["test"] or groups["train"] & groups["validation"] or groups["validation"] & groups["test"])
    return {
        "schema_version": report["schema_version"],
        "model_status": "unvalidated_experimental",
        "observations": report["observations"],
        "unique_accounts": report["unique_accounts"],
        "confirmed_accounts": report["confirmed_accounts"],
        "confirmed_by_type": report["confirmed_by_type"],
        "count_milestone": MIN_CONFIRMED_ACCOUNTS,
        "count_milestone_met": report["confirmed_accounts"] >= MIN_CONFIRMED_ACCOUNTS,
        "count_milestone_is_not_reliability": True,
        "training_performed": False,
        "evaluation_performed": False,
        "metrics": None,
        "real_world_metrics": None,
        "class_metrics_available": False,
        "split_accounts": {name: len(keys) for name, keys in groups.items()},
        "split_leakage": overlap,
        "schema_compatibility": report.get("schema_compatibility"),
        "note": (
            f"{report['confirmed_accounts']} accounts have a confirmed label. "
            f"{MIN_CONFIRMED_ACCOUNTS} is only the minimum count before a later experiment may be considered. "
            "It does not show that a model is reliable. Diversity, evidence quality, and an untouched test set "
            "still have to be judged. No precision, recall, F1, or calibration figure is computed."
        ),
    }
