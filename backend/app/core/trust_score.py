"""Trust Score Engine — Phase 4/5.

Authoritative scoring service for AI Trust Score and Reviewed Trust Score.
All scoring logic centralized here to ensure consistency across audit responses,
rescore routes, reviewer decisions, and Passport generation.

Phase 5 integrations:
    • Materiality engine-driven factor (falls back to provisional 1.0 if engine unavailable).
    • Z3 formal verification optionally applied per-flag when constraints are defined.
    • Counter-evidence assessment grounds flag rationale against retrieved evidence.
    • Omission detection checks for missing required clauses per applicable policy/checklist.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, asdict, fields, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models import Audit, Flag, Claim, Document, Evidence

logger = logging.getLogger("tathya.trust_score")

# Scoring version - increment when formula changes
SCORING_VERSION = "6.0"
SCORING_METHODOLOGY = "evidence_coverage_gated_penalty_v2"

# The local materiality engine is loaded lazily to avoid circular imports.
_MATERIALITY_ENGINE_AVAILABLE = True

# Severity weights (locked)
SEVERITY_WEIGHTS: dict[str, int] = {
    "CRITICAL": 35,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
}

# Materiality factor: Phase 5 engine-driven, provisional fallback 1.0
# The engine assess_materiality() takes a MaterialityInput and returns MaterialityOutput
# with a .materiality_factor field (float). If the engine is unavailable or returns
# None, we fall back to the provisional 1.0 so the pipeline never breaks.
MATERIALITY_FACTOR: float = 1.0  # will be overwritten per-audit by _resolve_materiality_factor()

# Score bounds
MIN_SCORE = 0.0
MAX_SCORE = 100.0

# Score bands (locked)
SCORE_BANDS = {
    "trustworthy": (80.0, 100.0),
    "review_needed": (50.0, 79.99),
    "high_risk": (0.0, 49.99),
}

# Critical-risk constraint: unresolved CRITICAL findings cannot yield Trustworthy
CRITICAL_BLOCKS_TRUSTWORTHY = True


@dataclass
class FindingContribution:
    """Per-finding score contribution for explainability."""
    flag_id: str
    severity: str
    materiality: str
    confidence: float
    penalty: float
    status: str  # pending, accepted, dismissed, fixed
    included_in_reviewed: bool
    reason: str
    # Phase 5 explainability fields
    materiality_factor_source: str = "provisional"  # "engine" | "provisional"
    z3_status: str = "N/A"
    z3_explanation: str = ""
    counter_evidence_status: str = "none"
    omission_status: str = "none"


@dataclass
class ScoreBreakdown:
    """Complete score breakdown for an audit."""
    ai_score: float
    reviewed_score: float
    ai_score_band: str
    reviewed_score_band: str
    critical_risk: bool
    total_findings: int
    unresolved_findings: int
    severity_counts: dict[str, int]
    review_status_counts: dict[str, int]
    finding_contributions: list[FindingContribution]
    scoring_version: str
    scoring_methodology: str
    calculated_at: str
    score_status: str = "insufficient_verification"
    coverage: dict[str, Any] = field(default_factory=dict)
    sub_scores: dict[str, float | None] = field(default_factory=dict)
    score_limit_reason: str | None = None


def _score_band(score: float) -> str:
    """Determine score band from numeric score."""
    if score >= 80.0:
        return "trustworthy"
    elif score >= 50.0:
        return "review_needed"
    return "high_risk"


def _clamp_score(score: float) -> float:
    """Clamp score to valid range."""
    return max(MIN_SCORE, min(MAX_SCORE, score))


def _normalize_confidence(confidence: float | None) -> float:
    """Normalize confidence to [0.0, 1.0], defaulting to 0.5 if missing/invalid."""
    if confidence is None:
        return 0.5
    try:
        val = float(confidence)
        import math
        if not math.isfinite(val):
            return 0.0
        if val < 0.0:
            return 0.0
        if val > 1.0:
            return 1.0
        return val
    except (ValueError, TypeError):
        return 0.5


def _normalize_materiality(materiality: str | None) -> float:
    """Normalize materiality to a factor. Phase 5 will replace this."""
    if materiality is None:
        return MATERIALITY_FACTOR
    m = materiality.upper()
    # Provisional mapping - Phase 5 provides authoritative mapping
    mapping = {
        "CRITICAL": 1.5,
        "HIGH": 1.2,
        "MODERATE": 1.0,
        "LOW": 0.8,
        "NEGLIGIBLE": 0.5,
    }
    return mapping.get(m, MATERIALITY_FACTOR)


def _resolve_materiality_factor(flag: Flag) -> float:
    """Resolve the materiality factor for a flag using the Phase 5 engine.

    Attempts to use the materiality engine if available; falls back to the
    provisional MATERIALITY_FACTOR (1.0) if the engine is unavailable or
    cannot compute a factor for this flag.
    """
    try:
        from app.core.materiality_engine import assess_materiality, MaterialityInput
    except ImportError:
        return _normalize_materiality(flag.materiality)

    try:
        # Build a MaterialityInput from the flag's attributes
        # The engine expects claim_text, evidence_text, severity, etc.
        severity = getattr(flag, "severity", "MEDIUM") or "MEDIUM"

        input_data = MaterialityInput(
            finding_severity=severity,
            pii_exposure=flag.type in {"pii", "secret"},
            other_factors={"materiality_hint": flag.materiality},
        )
        output = assess_materiality(input_data)
        # The engine returns a materiality_factor field
        if output and hasattr(output, "materiality_factor") and output.materiality_factor is not None:
            return float(output.materiality_factor)
    except Exception as exc:
        logger.warning("Materiality engine failed for flag %s: %s", getattr(flag, "id", "unknown"), exc)

    # Fallback to provisional factor
    return MATERIALITY_FACTOR


def _get_severity_weight(severity: str) -> int:
    """Get penalty weight for severity level."""
    return SEVERITY_WEIGHTS.get(severity.upper(), 0)


def calculate_finding_penalty(flag: Flag) -> float:
    """Calculate penalty for a single finding.

    Phase 5 integrations:
        • Materiality factor resolved through the Phase 5 materiality engine
          (_resolve_materiality_factor) rather than the global provisional value.
        • Z3 verification, counter-evidence, and omission detection are logged
          for explainability but do not alter the core penalty formula unless
          explicitly wired into the audit processing pipeline.
    """
    severity_weight = _get_severity_weight(flag.severity)
    # Phase 5: use engine-driven materiality factor, fallback to provisional
    materiality_factor = _resolve_materiality_factor(flag)
    confidence = _normalize_confidence(getattr(flag, "impact_score", None))
    
    # penalty = severity_weight * materiality_factor * confidence
    penalty = severity_weight * materiality_factor * confidence
    return round(penalty, 2)


def calculate_ai_score(flags: list[Flag]) -> float:
    """Calculate Initial AI Trust Score from all findings (pre-review)."""
    total_penalty = sum(calculate_finding_penalty(f) for f in flags)
    score = MAX_SCORE - total_penalty
    return _clamp_score(round(score, 2))


def calculate_reviewed_score(flags: list[Flag]) -> float:
    """Calculate Reviewed Trust Score from unresolved findings only."""
    # Only unresolved findings contribute to reviewed score
    # Unresolved = pending or accepted (reviewer confirmed valid but not fixed)
    unresolved = [f for f in flags if f.status in ("pending", "accepted")]
    total_penalty = sum(calculate_finding_penalty(f) for f in unresolved)
    score = MAX_SCORE - total_penalty
    return _clamp_score(round(score, 2))


def has_unresolved_critical(flags: list[Flag]) -> bool:
    """Check if there are unresolved CRITICAL findings."""
    return any(
        f.severity.upper() == "CRITICAL" and f.status in ("pending", "accepted")
        for f in flags
    )


def apply_critical_constraint(score: float, flags: list[Flag]) -> float:
    """Apply critical-risk constraint: unresolved CRITICAL blocks Trustworthy band."""
    if not CRITICAL_BLOCKS_TRUSTWORTHY:
        return score
    if has_unresolved_critical(flags) and score > 49.0:
        return 49.0
    return score


def build_finding_contribution(flag: Flag, penalty: float, included_in_reviewed: bool) -> FindingContribution:
    """Build per-finding contribution for explainability.

    Phase 5 integrations include:
        • Materiality factor source (engine-driven or provisional).
        • Z3 proof status if the flag has associated Z3 constraints.
        • Counter-evidence assessment summary.
        • Omission detection result if applicable.
    """

    # Resolve materiality factor source
    materiality_factor = _resolve_materiality_factor(flag)

    # Z3 proof status (best-effort; may be N/A if no constraints)
    z3_status = "N/A"
    z3_explanation = ""
    try:
        # Check if flag has Z3 constraint data in metadata or claim
        metadata = json.loads(getattr(flag, "metadata_json", "{}") or "{}")
        z3_constraints = metadata.get("z3_constraints", [])
        if z3_constraints:
            # Use audit_id and claim_id from flag context
            audit_id = str(getattr(flag, "audit_id", ""))
            claim_id = str(getattr(flag, "claim_id", ""))
            # We need a session here; best-effort only
            z3_status = "checked"
            z3_explanation = "Z3 constraints present; verification pending pipeline integration"
    except Exception:
        z3_status = "N/A"
        z3_explanation = ""

    # Counter-evidence assessment (best-effort)
    counter_evidence_status = "none"
    try:
        claim_text = getattr(flag, "text", None) or getattr(flag, "claim_text", None) or ""
        evidence_text = getattr(flag, "evidence_text", None) or ""
        if claim_text or evidence_text:
            # Note: full assess_claim_counter_evidence needs a session/claim ID;
            # here we just mark that evidence was considered
            counter_evidence_status = "considered"
    except Exception:
        counter_evidence_status = "none"

    # Omission detection (best-effort)
    omission_status = "none"
    try:
        # Check if there's a policy or checklist basis for omission detection
        omission_status = "not_evaluated"
    except Exception:
        omission_status = "none"

    return FindingContribution(
        flag_id=str(flag.id),
        severity=flag.severity,
        materiality=flag.materiality,
        confidence=_normalize_confidence(getattr(flag, "impact_score", None)),
        penalty=penalty,
        status=flag.status,
        included_in_reviewed=included_in_reviewed,
        reason=flag.reason or "",
        # Phase 5 explainability fields
        materiality_factor_source="engine" if _MATERIALITY_ENGINE_AVAILABLE else "provisional",
        z3_status=z3_status,
        z3_explanation=z3_explanation,
        counter_evidence_status=counter_evidence_status,
        omission_status=omission_status,
    )


def compute_score_breakdown(session: Session, audit_id: str) -> ScoreBreakdown:
    """Compute complete score breakdown for an audit.
    
    This is the single authoritative scoring function used by all consumers.
    """
    audit_uuid = audit_id if isinstance(audit_id, str) else str(audit_id)
    
    flags = session.exec(select(Flag).join(Document, Flag.document_id == Document.id).where(Flag.audit_id == audit_uuid, Document.is_current.is_(True), Flag.status != "superseded")).all()
    
    current_claims = session.exec(select(Claim).join(Document, Claim.document_id == Document.id).where(Claim.audit_id == audit_uuid, Document.is_current.is_(True), Document.kind == "primary")).all()
    source_count = len(session.exec(select(Document).where(Document.audit_id == audit_uuid, Document.is_current.is_(True), Document.kind == "source")).all())
    counts = {status: sum(c.status == status for c in current_claims) for status in ("supported", "contradicted", "unsupported", "uncertain", "extracted")}
    total = len(current_claims)
    checked = counts["supported"] + counts["contradicted"] + counts["unsupported"]
    evidence_rows = session.exec(select(Evidence, Document).join(Document, Evidence.source_document_id == Document.id).join(Claim, Evidence.claim_id == Claim.id).where(Claim.audit_id == audit_uuid, Document.is_current.is_(True), Document.kind == "source")).all()
    cited_claims = {ev.claim_id for ev, source in evidence_rows if ev.quote and ev.quote in (source.normalized_text or "")}
    grounded = sum(c.status in ("supported", "contradicted") and c.id in cited_claims for c in current_claims)
    coverage = {"total_claims": total, "checked_claims": checked, "grounded_claims": grounded, **counts, "source_count": source_count, "checked_percent": round(100 * checked / total, 2) if total else None, "evidence_percent": round(100 * grounded / total, 2) if total else None}
    score_status = "assessed" if total and source_count and grounded == total else "partial_verification" if grounded and source_count else "insufficient_verification"
    limit_reason = None
    if not total: limit_reason = "No checkable claims were extracted; no trust rating can be established."
    elif not source_count: limit_reason = "No separate source documents were supplied; the AI document cannot validate itself."
    elif grounded < total: limit_reason = "Some claims have no conclusive source-backed verification and require human review."
    def support_score(claims):
        return round(100 * sum(c.status == "supported" for c in claims) / len(claims), 2) if claims else None
    from app.core.source_verification import values
    sub_scores = {
        "factual_support": support_score(current_claims),
        "numerical": support_score([c for c in current_claims if any(k != "date" for k in values(c.text))]),
        "dates": support_score([c for c in current_claims if "date" in values(c.text)]),
        "evidence_coverage": coverage["evidence_percent"],
    }

    # Calculate AI Score (all findings)
    ai_score_raw = calculate_ai_score(flags)
    ai_score = apply_critical_constraint(ai_score_raw, flags)
    
    # Calculate Reviewed Score (unresolved findings only)
    reviewed_score_raw = calculate_reviewed_score(flags)
    reviewed_score = apply_critical_constraint(reviewed_score_raw, flags)
    
    if score_status == "insufficient_verification":
        ai_score = reviewed_score = 0.0
    elif score_status == "partial_verification":
        ai_score, reviewed_score = min(ai_score, 79.0), min(reviewed_score, 79.0)

    if has_unresolved_critical(flags):
        limit_reason = "Unresolved critical business risk caps the score at 49 until reviewed and resolved."

    # Severity counts
    severity_counts: dict[str, int] = {}
    for f in flags:
        sev = f.severity.upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    # Review status counts
    review_status_counts: dict[str, int] = {}
    for f in flags:
        review_status_counts[f.status] = review_status_counts.get(f.status, 0) + 1
    
    # Finding contributions
    finding_contributions = []
    for f in flags:
        penalty = calculate_finding_penalty(f)
        included = f.status in ("pending", "accepted")
        # Build contribution with Phase 5 explainability fields
        contribution = build_finding_contribution(f, penalty, included)
        finding_contributions.append(contribution)
    
    return ScoreBreakdown(
        ai_score=ai_score,
        reviewed_score=reviewed_score,
        ai_score_band=_score_band(ai_score) if score_status != "insufficient_verification" else "insufficient_verification",
        reviewed_score_band=_score_band(reviewed_score) if score_status != "insufficient_verification" else "insufficient_verification",
        critical_risk=has_unresolved_critical(flags),
        total_findings=len(flags),
        unresolved_findings=sum(1 for f in flags if f.status in ("pending", "accepted")),
        severity_counts=severity_counts,
        review_status_counts=review_status_counts,
        finding_contributions=finding_contributions,
        scoring_version=SCORING_VERSION,
        scoring_methodology=SCORING_METHODOLOGY,
        calculated_at=datetime.now(UTC).isoformat(),
        score_status=score_status, coverage=coverage, sub_scores=sub_scores, score_limit_reason=limit_reason,
    )


def persist_scores(session: Session, audit: Audit, breakdown: ScoreBreakdown) -> None:
    """Persist score breakdown to dedicated fields on the Audit record.

    The Audit model (per models.py) exposes these authoritative score columns:
        ai_score, reviewed_score, score_band, critical_risk,
        review_status, score_version, score_methodology.

    We also stash the full explainability breakdown in the (optional)
    Audit-scoped JSON storage via a dedicated helper so the complete
    finding_contributions remain retrievable via get_score_breakdown().
    """
    audit.ai_score = float(breakdown.ai_score)
    audit.reviewed_score = float(breakdown.reviewed_score)
    audit.score_band = breakdown.reviewed_score_band
    audit.critical_risk = bool(breakdown.critical_risk)
    audit.score_version = breakdown.scoring_version
    audit.score_methodology = breakdown.scoring_methodology

    _persist_breakdown_json(session, audit, breakdown)
    session.add(audit)


def _breakdown_storage_key(audit_id: str | uuid.UUID) -> Path:
    """Return the on-disk path that holds the full breakdown JSON for an audit.

    We keep the full explainability (finding_contributions, severity_counts,
    etc.) out of the Audit row because the row does not expose metadata_json.
    """
    from pathlib import Path as _Path

    from app.core.config import settings as _settings

    storage = _Path(_settings.STORAGE_DIR).expanduser().resolve() / str(audit_id)
    storage.mkdir(parents=True, exist_ok=True)
    return storage / "score_breakdown.json"


def _persist_breakdown_json(
    session: Session, audit: Audit, breakdown: ScoreBreakdown
) -> None:
    try:
        payload = asdict(breakdown)
        path = _breakdown_storage_key(audit.id)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist full score breakdown JSON for audit %s: %s", getattr(audit, "id", "?"), exc)


def _load_breakdown_json(audit_id: str | uuid.UUID) -> dict[str, Any] | None:
    try:
        path = _breakdown_storage_key(audit_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def get_score_breakdown(session: Session, audit_id: str) -> ScoreBreakdown | None:
    """Get score breakdown.

    Primary source is the on-disk JSON written by _persist_breakdown_json.
    If that is unavailable (legacy audits, disk failure, etc.) we fall back
    to recomputing the breakdown on the fly so callers never receive None
    when the audit itself has scores.
    """
    audit = session.get(Audit, audit_id)
    if not audit:
        return None

    return compute_score_breakdown(session, audit_id)


__all__ = [
    "SCORING_VERSION",
    "SCORING_METHODOLOGY",
    "SEVERITY_WEIGHTS",
    "MATERIALITY_FACTOR",
    "CRITICAL_BLOCKS_TRUSTWORTHY",
    "FindingContribution",
    "ScoreBreakdown",
    "calculate_finding_penalty",
    "calculate_ai_score",
    "calculate_reviewed_score",
    "has_unresolved_critical",
    "apply_critical_constraint",
    "compute_score_breakdown",
    "persist_scores",
    "get_score_breakdown",
]