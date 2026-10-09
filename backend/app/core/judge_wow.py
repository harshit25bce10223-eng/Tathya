"""Judge WOW — Adversarial Review Workflow (Spec §21-22).

Provides an adversarial review layer that validates evidence integrity,
protects against instruction injection, and produces a structured output contract.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.judge import JudgeResult, validate_judge_output

logger = logging.getLogger("tathya.judge_wow")

__all__ = [
    "AdversarialReview",
    "AdversarialReviewError",
    "InstructionInjectionError",
    "EvidenceIntegrityError",
    "run_adversarial_review",
]


class AdversarialReviewError(ValueError):
    """Base error for adversarial review failures."""


class InstructionInjectionError(AdversarialReviewError):
    """Raised when instruction injection is detected in inputs."""


class EvidenceIntegrityError(AdversarialReviewError):
    """Raised when evidence integrity checks fail."""


# Known instruction injection patterns to reject
INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+.*\s+instructions",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"<\s*system\s*>",
    r"<\s*user\s*>",
    r"<\s*assistant\s*>",
    r"override\s+the\s+prompt",
    r"forget\s+what\s+you\s+were\s+told",
    r"you\s+are\s+now\s+",
    r"act\s+as\s+if\s+",
    r"pretend\s+to\s+be\s+",
]


def detect_instruction_injection(text: str) -> list[str]:
    """Scan text for potential instruction injection patterns.

    Returns list of matched patterns (empty if clean).
    """
    matches = []
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches.append(pattern)
    return matches


def verify_evidence_integrity(
    evidence_list: list[dict],
    authorized_evidence_ids: set[uuid.UUID],
) -> tuple[bool, list[str]]:
    """Verify that all referenced evidence IDs are in the authorized set.

    Returns (is_valid, list_of_issues).
    """
    issues = []
    for ev in evidence_list:
        ev_id = ev.get("id")
        if ev_id:
            try:
                ev_uuid = uuid.UUID(str(ev_id))
                if ev_uuid not in authorized_evidence_ids:
                    issues.append(f"Evidence ID {ev_id} not in authorized set")
            except ValueError:
                issues.append(f"Invalid UUID format for evidence ID: {ev_id}")
    return len(issues) == 0, issues


@dataclass
class AdversarialReview:
    """Structured output contract for adversarial review.

    This is the canonical output that the Judge WOW produces and that
    downstream consumers (Challenge Results, UI) rely on.
    """

    review_id: uuid.UUID
    claim_text: str
    claim_category: str
    status: str  # "verified" | "rejected" | "uncertain" | "error"
    confidence: float
    reason: str
    primary_evidence_id: uuid.UUID | None
    referenced_evidence_ids: list[uuid.UUID]
    evidence_integrity_verified: bool
    instruction_injection_detected: bool
    injection_patterns: list[str]
    judge_result: JudgeResult | None = None
    uncertainty_reason: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["review_id"] = str(self.review_id)
        data["primary_evidence_id"] = (
            str(self.primary_evidence_id) if self.primary_evidence_id else None
        )
        data["referenced_evidence_ids"] = [str(e) for e in self.referenced_evidence_ids]
        data["created_at"] = self.created_at.isoformat()
        if self.judge_result:
            data["judge_result"] = {
                "status": self.judge_result.status,
                "confidence": self.judge_result.confidence,
                "reason": self.judge_result.reason,
                "primary_evidence_id": (
                    str(self.judge_result.primary_evidence_id)
                    if self.judge_result.primary_evidence_id
                    else None
                ),
                "referenced_evidence_ids": [
                    str(e) for e in self.judge_result.referenced_evidence_ids
                ],
                "uncertainty_reason": self.judge_result.uncertainty_reason,
                "provider": self.judge_result.provider,
                "model": self.judge_result.model,
                "cached": self.judge_result.cached,
                "validated": self.judge_result.validated,
            }
        return data


def run_adversarial_review(
    claim_text: str,
    claim_category: str,
    evidence_list: list[dict],
    *,
    judge_result: JudgeResult | None = None,
    strict_injection_check: bool = True,
) -> AdversarialReview:
    """Run adversarial review on a claim with evidence.

    This is the main entry point for Judge WOW. It performs:
    1. Instruction injection detection on claim and evidence
    2. Evidence integrity verification
    3. Judge validation (if judge_result provided, validates it; otherwise runs judge)
    4. Produces structured AdversarialReview output contract

    Args:
        claim_text: The claim to review
        claim_category: Category of the claim
        evidence_list: List of evidence dicts with id, quote, location, support_type, score
        judge_result: Optional pre-computed JudgeResult to validate
        strict_injection_check: If True, fail on injection detection

    Returns:
        AdversarialReview with full audit trail

    Raises:
        InstructionInjectionError: If injection detected and strict mode
        EvidenceIntegrityError: If evidence integrity fails
    """
    review_id = uuid.uuid4()
    authorized_ids = {ev["id"] for ev in evidence_list}

    # 1. Instruction injection detection
    injection_matches = detect_instruction_injection(claim_text)
    for ev in evidence_list:
        injection_matches.extend(detect_instruction_injection(ev.get("quote", "")))

    if injection_matches and strict_injection_check:
        raise InstructionInjectionError(
            f"Instruction injection detected: {injection_matches}"
        )

    # 2. Evidence integrity
    integrity_ok, integrity_issues = verify_evidence_integrity(evidence_list, authorized_ids)
    if not integrity_ok:
        raise EvidenceIntegrityError(
            f"Evidence integrity check failed: {integrity_issues}"
        )

    # 3. Judge validation or execution
    validated_judge = None
    if judge_result is not None:
        # Validate the provided judge result
        try:
            # Re-validate against the current authorized evidence
            _ = validate_judge_output(
                {
                    "status": judge_result.status,
                    "confidence": judge_result.confidence,
                    "reason": judge_result.reason,
                    "primary_evidence_id": (
                        str(judge_result.primary_evidence_id)
                        if judge_result.primary_evidence_id
                        else None
                    ),
                    "referenced_evidence_ids": [
                        str(e) for e in judge_result.referenced_evidence_ids
                    ],
                    "uncertainty_reason": judge_result.uncertainty_reason,
                },
                authorized_ids,
            )
            validated_judge = judge_result
        except Exception as exc:
            logger.warning("Provided JudgeResult failed validation: %s", exc)
            # Could fall through to running judge, but for now we record the failure
            validated_judge = None

    # 4. Determine final status
    if validated_judge:
        final_status = validated_judge.status
        confidence = validated_judge.confidence
        reason = validated_judge.reason
        primary_id = validated_judge.primary_evidence_id
        ref_ids = validated_judge.referenced_evidence_ids
        uncertainty = validated_judge.uncertainty_reason
        provider = validated_judge.provider
        model = validated_judge.model
    else:
        final_status = "uncertain"
        confidence = 0.0
        reason = "No validated judge result available"
        primary_id = None
        ref_ids = []
        uncertainty = "Judge unavailable or validation failed"
        provider = None
        model = None

    # Map judge status to review status
    status_map = {
        "supported": "verified",
        "contradicted": "rejected",
        "unsupported": "uncertain",
        "uncertain": "uncertain",
    }
    review_status = status_map.get(final_status, "uncertain")

    return AdversarialReview(
        review_id=review_id,
        claim_text=claim_text,
        claim_category=claim_category,
        status=review_status,
        confidence=confidence,
        reason=reason,
        primary_evidence_id=primary_id,
        referenced_evidence_ids=ref_ids,
        evidence_integrity_verified=integrity_ok,
        instruction_injection_detected=len(injection_matches) > 0,
        injection_patterns=injection_matches,
        judge_result=validated_judge,
        uncertainty_reason=uncertainty,
        provider=provider,
        model=model,
    )
