"""Challenge Results — Measured Performance Against Hidden Ground Truth (Spec §23-26).

Computes adversarial detection metrics with proper denominators, category breakdowns,
and deterministic comparison against hidden ground truth.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "ChallengeCategory",
    "ChallengeOutcome",
    "ChallengeResult",
    "ChallengeMetrics",
    "GroundTruthStore",
    "compute_challenge_metrics",
    "aggregate_challenge_results",
]


class ChallengeCategory(StrEnum):
    """Categories of adversarial challenges for metrics breakdown."""

    CLAIM_INJECTION = "claim_injection"
    EVIDENCE_TAMPERING = "evidence_tampering"
    DOCUMENT_REPLACEMENT = "document_replacement"
    NUMERIC_MANIPULATION = "numeric_manipulation"
    DATE_MANIPULATION = "date_manipulation"
    ENTITY_SWAP = "entity_swap"
    LOGIC_INVERSION = "logic_inversion"
    OMISSION_INDUCTION = "omission_induction"
    POLICY_VIOLATION_INJECTION = "policy_violation_injection"
    MATERIALITY_MASKING = "materiality_masking"


class ChallengeOutcome(StrEnum):
    """Outcome of a single challenge trial."""

    DETECTED = "detected"
    MISSED = "missed"
    FALSE_POSITIVE = "false_positive"
    ERROR = "error"


@dataclass
class ChallengeResult:
    """Single challenge trial result against hidden ground truth.

    The ground truth is hidden from the system under test. The result records
    whether the system detected the injected adversarial pattern.
    """

    trial_id: uuid.UUID
    challenge_id: uuid.UUID
    category: ChallengeCategory
    expected_outcome: ChallengeOutcome  # What SHOULD happen (ground truth)
    actual_outcome: ChallengeOutcome    # What the system DID
    system_score: float | None = None   # System's confidence/score
    detection_latency_ms: int | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    meta: dict[str, Any] = field(default_factory=dict)

    def is_correct(self) -> bool:
        """Whether the system's outcome matches ground truth."""
        if self.expected_outcome == ChallengeOutcome.DETECTED:
            return self.actual_outcome == ChallengeOutcome.DETECTED
        elif self.expected_outcome == ChallengeOutcome.MISSED:
            return self.actual_outcome == ChallengeOutcome.MISSED
        return False

    def is_true_positive(self) -> bool:
        return (
            self.expected_outcome == ChallengeOutcome.DETECTED
            and self.actual_outcome == ChallengeOutcome.DETECTED
        )

    def is_false_negative(self) -> bool:
        return (
            self.expected_outcome == ChallengeOutcome.DETECTED
            and self.actual_outcome == ChallengeOutcome.MISSED
        )

    def is_false_positive(self) -> bool:
        return self.actual_outcome == ChallengeOutcome.FALSE_POSITIVE

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trial_id"] = str(self.trial_id)
        data["challenge_id"] = str(self.challenge_id)
        data["category"] = self.category.value
        data["expected_outcome"] = self.expected_outcome.value
        data["actual_outcome"] = self.actual_outcome.value
        data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class ChallengeMetrics:
    """Aggregated metrics for a set of challenge results.

    All rates include explicit denominators.
    """

    total_trials: int = 0
    true_positives: int = 0
    false_negatives: int = 0
    false_positives: int = 0
    errors: int = 0

    # Per-category breakdown
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def true_positive_rate(self) -> float:
        """Sensitivity / Recall: TP / (TP + FN)"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        """FP / (FP + TN) - but TN not tracked, so FP / total_negatives_expected"""
        # In our setup, negatives are challenges that should NOT be detected
        # (expected_outcome == MISSED or FALSE_POSITIVE)
        # For simplicity: FP / (FP + actual_negatives)
        # But we track expected MISSED as the negative class
        expected_negatives = sum(
            c.get("expected_missed", 0) for c in self.by_category.values()
        )
        return self.false_positives / (self.false_positives + expected_negatives) if (self.false_positives + expected_negatives) > 0 else 0.0

    @property
    def precision(self) -> float:
        """TP / (TP + FP)"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """Harmonic mean of precision and recall"""
        p = self.precision
        r = self.true_positive_rate
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        """(TP + TN) / Total - but TN not directly tracked"""
        # Approximate: correct / total
        correct = self.true_positives + sum(
            c.get("true_negatives", 0) for c in self.by_category.values()
        )
        return correct / self.total_trials if self.total_trials > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_trials": self.total_trials,
            "true_positives": self.true_positives,
            "false_negatives": self.false_negatives,
            "false_positives": self.false_positives,
            "errors": self.errors,
            "true_positive_rate": self.true_positive_rate,
            "false_positive_rate": self.false_positive_rate,
            "precision": self.precision,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "by_category": self.by_category,
        }


class GroundTruthStore:
    """Hidden ground truth store for challenge evaluation.

    Ground truth is loaded once and never exposed to the system under test.
    """

    def __init__(self, ground_truth_path: str | None = None):
        self._truths: dict[str, ChallengeOutcome] = {}
        if ground_truth_path:
            self.load(ground_truth_path)

    def load(self, path: str) -> None:
        """Load ground truth from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("ground_truths", []):
            self._truths[item["challenge_id"]] = ChallengeOutcome(item["expected_outcome"])

    def get_expected(self, challenge_id: uuid.UUID) -> ChallengeOutcome | None:
        """Get expected outcome for a challenge (hidden from system)."""
        return self._truths.get(str(challenge_id))

    def record_result(
        self,
        challenge_id: uuid.UUID,
        category: ChallengeCategory,
        actual_outcome: ChallengeOutcome,
        system_score: float | None = None,
        latency_ms: int | None = None,
        notes: str = "",
    ) -> ChallengeResult:
        """Record a system result and compute correctness against ground truth."""
        expected = self.get_expected(challenge_id)
        if expected is None:
            # No ground truth - treat as unknown
            expected = ChallengeOutcome.ERROR

        result = ChallengeResult(
            trial_id=uuid.uuid4(),
            challenge_id=challenge_id,
            category=category,
            expected_outcome=expected,
            actual_outcome=actual_outcome,
            system_score=system_score,
            detection_latency_ms=latency_ms,
            notes=notes,
        )
        return result


def compute_challenge_metrics(results: list[ChallengeResult]) -> ChallengeMetrics:
    """Compute aggregate metrics from challenge results."""
    metrics = ChallengeMetrics()
    for r in results:
        metrics.total_trials += 1
        cat = r.category.value

        if cat not in metrics.by_category:
            metrics.by_category[cat] = {
                "total": 0,
                "true_positives": 0,
                "false_negatives": 0,
                "false_positives": 0,
                "expected_detected": 0,
                "expected_missed": 0,
                "true_negatives": 0,
            }

        cat_metrics = metrics.by_category[cat]
        cat_metrics["total"] += 1

        if r.is_true_positive():
            metrics.true_positives += 1
            cat_metrics["true_positives"] += 1
        elif r.is_false_negative():
            metrics.false_negatives += 1
            cat_metrics["false_negatives"] += 1
        elif r.is_false_positive():
            metrics.false_positives += 1
            cat_metrics["false_positives"] += 1
        else:
            # actual_outcome == MISSED and expected_outcome == MISSED = true negative
            metrics.errors += 1
            cat_metrics["true_negatives"] += 1

        # Track expected for denominator calculations
        if r.expected_outcome == ChallengeOutcome.DETECTED:
            cat_metrics["expected_detected"] += 1
        else:
            cat_metrics["expected_missed"] += 1
            # True negative: expected missed and actual was missed
            if r.actual_outcome == ChallengeOutcome.MISSED:
                cat_metrics["true_negatives"] += 1

    return metrics


def aggregate_challenge_results(
    results: list[ChallengeResult],
    *,
    min_trials_per_category: int = 5,
) -> tuple[ChallengeMetrics, dict[str, Any]]:
    """Aggregate results with quality checks.

    Returns (metrics, quality_report).
    """
    metrics = compute_challenge_metrics(results)

    quality_report = {
        "sufficient_trials": bool(results) and all(
            c["total"] >= min_trials_per_category
            for c in metrics.by_category.values()
        ),
        "categories_tested": list(metrics.by_category.keys()),
        "trials_per_category": {
            cat: m["total"] for cat, m in metrics.by_category.items()
        },
    }

    return metrics, quality_report
