"""Materiality Engine — Phase 5.

Replaces the Phase 4 provisional materiality_factor = 1.0 with a dedicated,
explainable, versioned service.

Materiality is the potential business impact of a finding.  It is NOT the same
as severity or confidence.  Preserve those distinctions.

The default rule set below is rule-based and explicitly un-calibrated.  If an
empirically calibrated model is later trained/evaluated for materiality, the
rule set is replaced and the methodology version is incremented.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from app.core.trust_score import (
    SEVERITY_WEIGHTS,
    MATERIALITY_FACTOR,
)
from app.models import Flag

logger = logging.getLogger("tathya.materiality_engine")

# ---------------------------------------------------------------------------
# Materiality metadata
# ---------------------------------------------------------------------------

#: Methodology version string.  Increment when the rule set or calibration
#: changes.  Old score/Passport snapshots remain auditable under their
#: original methodology.
MATERIALITY_METHODOLOGY_VERSION: str = "5.0.0"

#: Rule-set label.  Marked "rule_based_un_calibrated" until a labelled
#: dataset and evaluation prove empirical calibration.
MATERIALITY_RULE_SET: str = "rule_based_un_calibrated"

# ---------------------------------------------------------------------------
# Datacontracts
# ---------------------------------------------------------------------------

@dataclass
class MaterialityInput:
    """Input factors for a materiality assessment.

    Keep separate from severity and confidence.  Only filled fields contribute;
    missing fields produce a partial/uncertain outcome.
    """
    finding_severity: str | None = None  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    monetary_amount: float | None = None  # e.g. 5000000.0
    currency: str | None = None  # e.g. "INR" | "USD"
    contract_value: float | None = None  # known contract exposure
    warranty_duration_days: int | None = None
    performance_guarantee: str | None = None  # e.g. "SLA 99.9%"
    liability_exposure: float | None = None  # known financial liability
    pii_exposure: bool | None = None  # personal data involved
    policy_result: str | None = None  # "compliant" | "violation" | "uncertain" | "not_applicable"
    proof_status: str | None = None  # "SAT" | "UNSAT" | "UNKNOWN"
    source_freshness_days: int | None = None  # days since document version
    other_factors: dict[str, Any] = field(default_factory=dict)  # free-form


@dataclass
class MaterialityOutput:
    """Output from a materiality assessment.

    The frontend receives these values; it does NOT recompute them.
    """
    materiality_classification: str  # "low" | "medium" | "high" | "critical"
    materiality_factor: float  # numeric factor injected into penalty
    reason: str  # explanation grounded in actual input factors
    contributing_factors: dict[str, Any]  # which inputs drove the result
    rule_version: str  # MATERIALITY_METHODOLOGY_VERSION
    rule_set: str  # MATERIALITY_RULE_SET
    calibrated: bool  # True if empirically calibrated, False if rule-based
    missing_input_limitations: list[str]  # what was not available
    captured_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ---------------------------------------------------------------------------
# Rule-based materiality assessment (default, un-calibrated)
# ---------------------------------------------------------------------------

# Configurable thresholds for the rule-based engine.
# These are explicitly un-calibrated: they are illustrative starting points.
# Change them only after a labelled dataset and evaluation procedure exists.
_MATERIALITY_THRESHOLDS: dict[str, float] = {
    "low": 0.8,       # penalty multiplier in [0.8, 1.2)
    "medium": 1.3,    # penalty multiplier in [1.3, 1.8)
    "high": 2.0,      # penalty multiplier in [2.0, 3.0)
    "critical": 3.5,  # penalty multiplier >= 3.5
}


def _classify_materiality_factor(factor: float) -> str:
    """Map a materiality factor to a classification band."""
    if factor >= _MATERIALITY_THRESHOLDS["critical"]:
        return "critical"
    if factor >= _MATERIALITY_THRESHOLDS["high"]:
        return "high"
    if factor >= _MATERIALITY_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _assess_missing_input_limitations(input_: MaterialityInput) -> list[str]:
    """List which expected inputs were not available."""
    limitations: list[str] = []
    if input_.finding_severity is None:
        limitations.append("finding_severity")
    if input_.monetary_amount is None and input_.contract_value is None:
        limitations.append("monetary_amount or contract_value")
    if input_.warranty_duration_days is None and input_.performance_guarantee is None:
        limitations.append("warranty_duration_days or performance_guarantee")
    if input_.liability_exposure is None:
        limitations.append("liability_exposure")
    if input_.pii_exposure is None:
        limitations.append("pii_exposure")
    if not input_.other_factors:
        limitations.append("other_factors")
    return limitations


def assess_materiality(input_: MaterialityInput) -> MaterialityOutput:
    """Assess materiality from the given inputs using the rule-based engine.

    This is the authoritative Phase 5 materiality service.  It is rule-based
    and un-calibrated by default.  The materiality_factor is the value that
    gets injected into the Phase 4 penalty formula:

        penalty = severity_weight × materiality_factor × confidence

    Returns a MaterialityOutput which the frontend receives.  The frontend
    must NOT recompute the factor itself.
    """
    started = datetime.now(UTC)

    # --- Collect contributing inputs ---
    contributing: dict[str, Any] = {
        "severity": input_.finding_severity,
        "monetary": input_.monetary_amount,
        "contract_value": input_.contract_value,
        "warranty_days": input_.warranty_duration_days,
        "liability": input_.liability_exposure,
        "pii": input_.pii_exposure,
        "policy": input_.policy_result,
        "proof": input_.proof_status,
        "source_freshness_days": input_.source_freshness_days,
        "other": input_.other_factors,
    }

    limitations = _assess_missing_input_limitations(input_)

    # --- Default: when essential inputs are missing, return uncertain ---
    # We do NOT invent a perfect materiality score just because some data is
    # absent.  The output must reflect what is actually known.
    essential_missing = [
        f.name for f in fields(input_) if getattr(input_, f.name) is None and f.name not in ("other_factors",)
    ]
    if "finding_severity" in essential_missing:
        # Without severity we cannot compute a meaningful factor
        output = MaterialityOutput(
            materiality_classification="uncertain",
            materiality_factor=MATERIALITY_FACTOR,  # 1.0 provisional
            reason="Cannot assess materiality: missing required finding_severity.",
            contributing_factors=contributing,
            rule_version=MATERIALITY_METHODOLOGY_VERSION,
            rule_set=MATERIALITY_RULE_SET,
            calibrated=False,
            missing_input_limitations=limitations,
            captured_at=datetime.now(UTC).isoformat(),
        )
        return output

    # --- Rule-based factor computation ---
    # Start from the provisional Phase 4 factor and adjust based on available
    # real inputs.  The formula is intentionally simple and transparent:
    #
    #   factor = 1.0  (base)
    #   * severity_adjustment  (if severity known)
    #   * amount_adjustment    (if monetary amount known)
    #   * policy_adjustment    (if policy result known)
    #   * proof_adjustment     (if proof status known)
    #
    # Each adjustment is derived from explicitly configured thresholds.
    factor = 1.0  # base

    # Severity adjustment
    sev = input_.finding_severity
    if sev and sev.upper() in SEVERITY_WEIGHTS:
        # Higher severity -> higher materiality factor
        severity_map: dict[str, float] = {
            "CRITICAL": 2.0,
            "HIGH": 1.5,
            "MEDIUM": 1.1,
            "LOW": 0.9,
        }
        factor *= severity_map[sev.upper()]

    # Monetary / contract amount adjustment
    amt = input_.monetary_amount if input_.monetary_amount is not None else input_.contract_value
    if amt is not None and amt > 0:
        # Scale: amounts > 10 lakh critical, > 1 crore high, etc.
        # These thresholds are illustrative and un-calibrated.
        if amt > 1_00_00_000:  # > 1 crore INR
            factor *= 2.5
        elif amt > 10_00_000:  # > 10 lakh INR
            factor *= 1.8
        elif amt > 1_00_000:  # > 1 lakh INR
            factor *= 1.3
        # else: factor stays at base 1.0

    # Liability exposure adjustment
    if input_.liability_exposure is not None and input_.liability_exposure > 0:
        factor *= 1.5

    # PII exposure adjustment
    if input_.pii_exposure is True:
        factor *= 1.3

    # Policy result adjustment
    if input_.policy_result and input_.policy_result == "violation":
        factor *= 1.8
    elif input_.policy_result and input_.policy_result == "compliant":
        factor *= 0.8  # compliant reduces materiality impact

    # Proof status adjustment
    if input_.proof_status == "UNSAT":
        factor *= 1.4  # unsatisfiable structured constraints increase materiality
    elif input_.proof_status == "SAT":
        factor *= 0.9  # satisfiable reduces materiality concern

    # Source freshness adjustment (newer = lower materiality risk)
    if input_.source_freshness_days is not None and input_.source_freshness_days > 0:
        # Very old documents (> 3 years) increase materiality
        if input_.source_freshness_days > 1095:  # > 3 years
            factor *= 1.2
        elif input_.source_freshness_days > 365:  # > 1 year
            factor *= 1.1

    # Clamp factor to reasonable bounds
    factor = max(0.5, min(5.0, factor))

    classification = _classify_materiality_factor(factor)

    # --- Build output ---
    output = MaterialityOutput(
        materiality_classification=classification,
        materiality_factor=round(factor, 4),
        reason=_build_reason(input_, factor, classification),
        contributing_factors=contributing,
        rule_version=MATERIALITY_METHODOLOGY_VERSION,
        rule_set=MATERIALITY_RULE_SET,
        calibrated=False,  # rule-based, not empirically calibrated
        missing_input_limitations=limitations,
        captured_at=datetime.now(UTC).isoformat(),
    )

    logger.info(
        "Materiality assessed: classification=%s factor=%.4f "
        "calibrated=%s limitations=%s",
        classification,
        factor,
        output.calibrated,
        limitations,
    )

    return output


def _build_reason(input_: MaterialityInput, factor: float, classification: str) -> str:
    """Build a human-readable explanation grounded in actual inputs."""
    reasons: list[str] = []

    sev = input_.finding_severity
    if sev:
        reasons.append(f"severity={sev}")

    amt = input_.monetary_amount if input_.monetary_amount is not None else input_.contract_value
    if amt is not None and amt > 0:
        reasons.append(f"amount≈₹{amt:,.0f}")

    if input_.liability_exposure is not None and input_.liability_exposure > 0:
        reasons.append(f"liability≈₹{input_.liability_exposure:,.0f}")

    if input_.pii_exposure is True:
        reasons.append("PII exposure")

    if input_.policy_result:
        reasons.append(f"policy={input_.policy_result}")

    if input_.proof_status:
        reasons.append(f"proof={input_.proof_status}")

    if input_.warranty_duration_days is not None:
        reasons.append(f"warranty={input_.warranty_duration_days}d")

    if not reasons:
        reasons.append("insufficient input data for detailed rationale")

    reasons.append(f"materiality_factor={factor:.4f} -> classification={classification}")

    return " | ".join(reasons)


# ---------------------------------------------------------------------------
# Integration: inject materiality factor into the trust score penalty
# ---------------------------------------------------------------------------

def inject_materiality_into_penalty(
    base_penalty: float,
    finding: Flag,
    materiality_output: MaterialityOutput,
) -> float:
    """Inject the materiality factor into a finding penalty.

    The Phase 4 penalty formula is:

        penalty = severity_weight × materiality_factor × confidence

    This function returns the updated penalty after applying the materiality
    factor from the engine, so callers replace their prior hard-coded factor.

    Args:
        base_penalty: penalty computed without materiality (i.e.
            severity_weight × confidence, i.e. the Phase 4 formula without
            the materiality multiplier).
        finding: the Flag record associated with the penalty.
        materiality_output: result from assess_materiality().

    Returns:
        Updated penalty incorporating the materiality factor.
    """
    # The materiality_factor from the engine is the multiplier.
    # We keep confidence from the Flag if available, else default to 0.5.
    from app.core.trust_score import _normalize_confidence
    confidence = _normalize_confidence(getattr(finding, "impact_score", None))

    # New penalty = severity_weight × materiality_factor × confidence
    # But base_penalty already contains severity_weight × (old) confidence.
    # We override the old materiality factor with the new one.
    severity_weight = SEVERITY_WEIGHTS.get(finding.severity.upper(), 0)

    new_penalty = severity_weight * materiality_output.materiality_factor * confidence
    return round(max(0.0, new_penalty), 2)


# ---------------------------------------------------------------------------
# Convenience: assess materiality for a single flag
# ---------------------------------------------------------------------------

def assess_flag_materiality(session: Session, flag: Flag) -> MaterialityOutput:
    """Assess materiality for a single Flag, building MaterialityInput from
    what is available in the flag and its related database records.

    This is a convenience wrapper so that callers don't have to manually
    construct MaterialityInput from DB data.
    """
    # Gather what we can from the flag and related entities
    input_ = MaterialityInput(
        finding_severity=flag.severity,
        monetary_amount=getattr(flag, "monetary_amount", None),
        currency=getattr(flag, "currency", None),
        contract_value=getattr(flag, "contract_value", None),
        warranty_duration_days=getattr(flag, "warranty_duration_days", None),
        liability_exposure=getattr(flag, "liability_exposure", None),
        pii_exposure=getattr(flag, "pii_exposure", None),
        policy_result=getattr(flag, "policy_result", None),
        proof_status=getattr(flag, "proof_status", None),
        source_freshness_days=getattr(flag, "source_freshness_days", None),
        other_factors={
            "flag_id": str(flag.id),
            "audit_id": str(flag.audit_id) if flag.audit_id else None,
        },
    )

    return assess_materiality(input_)


__all__ = [
    "MaterialityInput",
    "MaterialityOutput",
    "MATERIALITY_METHODOLOGY_VERSION",
    "MATERIALITY_RULE_SET",
    "assess_materiality",
    "assess_flag_materiality",
    "inject_materiality_into_penalty",
    "MaterialityOutput",
]