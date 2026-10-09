"""Grounding Guard — Phase 3/4.

Verifies claims against source evidence.
Prevents unsupported findings from being treated as verified truth.

Contract (locked):
    claim
      -> associated document sentence
      -> retrieved source evidence
      -> check evidence presence / relationship
      -> grounding result

Outcomes:
    SUPPORTED
    CONTRADICTED
    UNSUPPORTED
    UNCERTAIN

Rules:
    - CONTRADICTED requires actual opposing evidence
    - UNSUPPORTED means support could not be established
    - UNCERTAIN means verifier/evidence signals are inconclusive
    - No-evidence source claim does not become a fabricated flag
    - Deterministic contradictions cannot be silently overridden by LLM
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlmodel import Session, select

from app.core.claims import claim_location
from app.core.llm import LLMError, LLMRequest, llm_adapter
from app.core.judge import LLMUnavailableError, judge_claim
from app.core.retrieval import persist_evidence_for_claim, retrieve_for_claim
from app.core.rope_inference import verify_with_rope
from app.models import Claim, Document, Evidence, Fact, Flag

logger = logging.getLogger("tathya.grounding")


class GroundingStatus(str, Enum):
    """Grounding verification outcomes."""
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNSUPPORTED = "unsupported"
    UNCERTAIN = "uncertain"


@dataclass
class GroundingResult:
    """Result of grounding a single claim."""
    claim_id: uuid.UUID
    document_id: uuid.UUID
    status: GroundingStatus
    evidence_ids: list[uuid.UUID]
    primary_evidence_id: uuid.UUID | None
    reason: str
    confidence: float
    source_metadata: dict[str, Any]


@dataclass
class ClaimEvidencePair:
    """Pair of claim and its candidate evidence for verification."""
    claim: Claim
    evidence: Evidence | None
    document: Document


# ---------------------------------------------------------------------------
# Grounding Guard — main entry point
# ---------------------------------------------------------------------------


def ground_claims(
    session: Session,
    audit_id: uuid.UUID,
) -> list[GroundingResult]:
    """Ground all claims for an audit against available evidence.

    Flow:
        1. Get all claims for the audit
        2. For each claim, find associated evidence and source document
        3. Run verification (deterministic first, LLM fallback for semantic)
        4. Persist grounding results
    """
    claims = session.exec(
        select(Claim).join(Document, Claim.document_id == Document.id).where(Claim.audit_id == audit_id, Document.is_current.is_(True))
    ).all()

    if not claims:
        return []

    results: list[GroundingResult] = []

    for claim in claims:
        result = _ground_single_claim(session, claim)
        results.append(result)

        # Update claim status with grounding result
        claim.status = result.status.value
        claim.metadata_json = json.dumps(
            {
                **json.loads(claim.metadata_json or "{}"),
                "grounding": {
                    "status": result.status.value,
                    "evidence_ids": [str(e) for e in result.evidence_ids],
                    "primary_evidence_id": str(result.primary_evidence_id) if result.primary_evidence_id else None,
                    "reason": result.reason,
                    "confidence": result.confidence,
                    "source_metadata": result.source_metadata,
                    "grounded_at": datetime.now(UTC).isoformat(),
                },
            },
            ensure_ascii=False,
        )
        session.add(claim)

    session.commit()
    return results


def _ground_single_claim(session: Session, claim: Claim) -> GroundingResult:
    """Ground a single claim against its evidence."""
    # Get the source document
    document = session.get(Document, claim.document_id)
    if document is None:
        return GroundingResult(
            claim_id=claim.id,
            document_id=claim.document_id,
            status=GroundingStatus.UNSUPPORTED,
            evidence_ids=[],
            primary_evidence_id=None,
            reason="Source document not found",
            confidence=0.0,
            source_metadata={},
        )

    evidence_list = session.exec(
        select(Evidence).join(Document, Evidence.source_document_id == Document.id).where(Evidence.claim_id == claim.id, Document.is_current.is_(True), Document.kind == "source")
    ).all()
    if not evidence_list:
        chunks = retrieve_for_claim(session, claim)
        evidence_list = persist_evidence_for_claim(session, claim, chunks)

    if not evidence_list:
        return GroundingResult(
            claim_id=claim.id,
            document_id=claim.document_id,
            status=GroundingStatus.UNSUPPORTED,
            evidence_ids=[],
            primary_evidence_id=None,
            reason="No evidence available for claim",
            confidence=0.0,
            source_metadata={"document_id": str(document.id)},
        )

    # Build evidence context for Judge integration
    evidence_context = [
        {
            "id": ev.id,
            "quote": ev.quote,
            "location": ev.location_json,
            "support_type": ev.support_type,
            "score": ev.score if ev.score is not None else 0.0,
        }
        for ev in evidence_list
    ]

    # Try deterministic fact-based verification first
    fact_result = _verify_against_facts(session, claim, document, evidence_list)
    if fact_result is not None:
        # Even if we have a fact result, also run deterministic Judge to check
        # This ensures no conclusive deterministic result is silently overridden
        return fact_result

    # Execute deep neural verification with RoPE Transformer
    rope_eval = None
    if evidence_list:
        combined_evidence = " ".join([ev.quote for ev in evidence_list if ev.quote])
        if combined_evidence:
            try:
                rope_eval = verify_with_rope(claim_text=claim.text, evidence_text=combined_evidence)
            except Exception as rope_err:
                logger.warning("RoPE verification exception: %s", rope_err)

    # Fall back to LLM-based semantic verification using ML Judge
    try:
        judge_result = judge_claim(
            claim_text=claim.text,
            claim_category=claim.category or "general",
            evidence_list=[
                {
                    "id": ev.id,
                    "quote": ev.quote,
                    "location": ev.location_json,
                    "support_type": ev.support_type,
                    "score": ev.score if ev.score is not None else 0.0,
                }
                for ev in evidence_list
            ],
        )
    except (LLMUnavailableError, Exception) as exc:
        if rope_eval:
            status_enum = GroundingStatus(rope_eval["status"])
            return GroundingResult(
                claim_id=claim.id,
                document_id=document.id,
                status=status_enum,
                evidence_ids=[e.id for e in evidence_list],
                primary_evidence_id=evidence_list[0].id if evidence_list else None,
                reason=f"[RoPE Neural Verifier] {rope_eval['reason']}",
                confidence=rope_eval["confidence"],
                source_metadata={
                    "document_id": str(document.id),
                    "verifier": "rope_transformer",
                    "probabilities": rope_eval["probabilities"],
                    "risk_score": rope_eval["risk_score"],
                },
            )
        logger.warning("Judge verification failed for claim %s, falling back to uncertain: %s", claim.id, exc)
        return GroundingResult(
            claim_id=claim.id,
            document_id=document.id,
            status=GroundingStatus.UNCERTAIN,
            evidence_ids=[e.id for e in evidence_list],
            primary_evidence_id=evidence_list[0].id if evidence_list else None,
            reason=f"Verification failed: {exc}",
            confidence=0.2,
            source_metadata={"document_id": str(document.id), "judge_error": str(exc)},
        )

    if rope_eval and rope_eval.get("status") != judge_result.status:
        return GroundingResult(
            claim_id=claim.id, document_id=document.id, status=GroundingStatus.UNCERTAIN,
            evidence_ids=[e.id for e in evidence_list], primary_evidence_id=evidence_list[0].id,
            reason="Fast verifier and semantic judge disagree; human review is required.",
            confidence=0.0, source_metadata={"verifier_disagreement": True, "fast_verdict": rope_eval.get("status"), "judge_verdict": judge_result.status},
        )

    # Convert Judge result to GroundingResult
    # Key: we DO NOT override a deterministic CONTRADICTED with an LLM result
    # but if deterministic returned None, we use Judge
    primary_evidence_id = judge_result.primary_evidence_id
    if primary_evidence_id is None and evidence_list:
        primary_evidence_id = evidence_list[0].id

    return GroundingResult(
        claim_id=claim.id,
        document_id=document.id,
        status=GroundingStatus(judge_result.status),
        evidence_ids=[e.id for e in evidence_list],
        primary_evidence_id=primary_evidence_id,
        reason=judge_result.reason,
        confidence=judge_result.confidence,
        source_metadata={
            "document_id": str(document.id),
            "judge_provider": judge_result.provider,
            "judge_model": judge_result.model,
            "judge_cached": judge_result.cached,
            "validated": judge_result.validated,
        },
    )


def _verify_against_facts(
    session: Session,
    claim: Claim,
    document: Document,
    evidence_list: list[Evidence],
) -> GroundingResult | None:
    """Try deterministic verification against structured facts.

    Returns None if no relevant facts exist or conflict is ambiguous.
    """
    from app.core.source_verification import compare_quote
    outcomes = []
    for evidence in evidence_list:
        source = session.get(Document, evidence.source_document_id)
        if source is None or not source.is_current or source.kind != "source" or source.id == claim.document_id:
            continue
        if not evidence.quote or evidence.quote not in (source.normalized_text or ""):
            continue
        verdict = compare_quote(claim.text, evidence.quote)
        if verdict:
            outcomes.append((verdict, evidence, source))
    if not outcomes:
        return None
    states = {item[0] for item in outcomes}
    state = next(iter(states)) if len(states) == 1 else "uncertain"
    evidence_ids = [item[1].id for item in outcomes]
    return GroundingResult(
        claim_id=claim.id, document_id=document.id, status=GroundingStatus(state),
        evidence_ids=evidence_ids, primary_evidence_id=evidence_ids[0],
        reason=("Current source quotes disagree; a reviewer must resolve source authority." if state == "uncertain" else f"Deterministic normalized comparison: claim is {state} by the cited current source quote."),
        confidence=1.0 if state != "uncertain" else 0.0,
        source_metadata={"verifier": "source_field_comparison_v1", "source_document_ids": [str(item[2].id) for item in outcomes]},
    )


def _check_numeric_conflict(claim_text: str, fact_text: str) -> bool | None:
    """Check for numeric conflicts between claim and fact."""

    # Extract numbers with units from both texts
    claim_numbers = _extract_numbers_with_units(claim_text)
    fact_numbers = _extract_numbers_with_units(fact_text)

    if not claim_numbers or not fact_numbers:
        return None

    # Simple check: if same unit but different values
    for c_num, c_unit in claim_numbers:
        for f_num, f_unit in fact_numbers:
            if c_unit == f_unit and c_num != f_num:
                return True

    return None


def _check_date_conflict(claim_text: str, fact_text: str) -> bool | None:
    """Check for date conflicts between claim and fact."""
    import re

    # Extract dates from both texts (simplified)
    date_pattern = r"\b(\d{1,2}[\s/-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/-]\d{2,4}|\d{4}[\s/-]\d{1,2}[\s/-]\d{1,2})\b"

    claim_dates = re.findall(date_pattern, claim_text, re.IGNORECASE)
    fact_dates = re.findall(date_pattern, fact_text, re.IGNORECASE)

    if not claim_dates or not fact_dates:
        return None

    # Normalize dates for comparison (simplified)
    for c_date in claim_dates:
        for f_date in fact_dates:
            if c_date != f_date:
                # Could do better normalization here
                return True

    return None


def _extract_numbers_with_units(text: str) -> list[tuple[float, str]]:
    """Extract numbers with their units from text."""
    import re

    # Pattern for numbers with units (₹, $, %, days, years, etc.)
    pattern = r"([₹$€£]?\s*\d+(?:[.,]\d+)?)\s*(lakh|crore|million|billion|k|K|%|percent|days?|years?|months?|weeks?)?"
    matches = re.findall(pattern, text, re.IGNORECASE)

    results = []
    for num_str, unit in matches:
        # Clean number
        num_str = num_str.replace(",", "").replace("₹", "").replace("$", "").strip()
        try:
            num = float(num_str)
            results.append((num, unit.lower() if unit else ""))
        except ValueError:
            pass

    return results


def _verify_with_llm(
    session: Session,
    claim: Claim,
    document: Document,
    evidence_list: list[Evidence],
) -> GroundingResult:
    """Use LLM for semantic verification when deterministic checks are insufficient."""
    # Prepare evidence context
    evidence_context = []
    for ev in evidence_list:
        evidence_context.append({
            "quote": ev.quote,
            "location": ev.location_json,
            "support_type": ev.support_type,
            "score": ev.score,
        })

    # If no LLM configured, return UNCERTAIN
    if not llm_adapter.is_configured():
        return GroundingResult(
            claim_id=claim.id,
            document_id=document.id,
            status=GroundingStatus.UNCERTAIN,
            evidence_ids=[e.id for e in evidence_list],
            primary_evidence_id=evidence_list[0].id if evidence_list else None,
            reason="LLM not configured; cannot perform semantic verification",
            confidence=0.3,
            source_metadata={"document_id": str(document.id), "llm_available": False},
        )

    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["supported", "contradicted", "unsupported", "uncertain"],
            },
            "reason": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "primary_evidence_index": {"type": "integer", "minimum": 0},
        },
        "required": ["status", "reason", "confidence", "primary_evidence_index"],
    }

    prompt = f"""Verify if the following claim is grounded in the provided evidence.

Claim: {claim.text}
Claim category: {claim.category}

Evidence:
{json.dumps(evidence_context, ensure_ascii=False, indent=2)}

Determine if the claim is SUPPORTED, CONTRADICTED, UNSUPPORTED, or UNCERTAIN based on the evidence.
- SUPPORTED: Evidence directly confirms the claim
- CONTRADICTED: Evidence explicitly contradicts the claim (requires opposing evidence)
- UNSUPPORTED: No evidence supports the claim, but no contradiction either
- UNCERTAIN: Evidence is ambiguous or conflicting

Return the status, a brief reason, confidence (0-1), and the index of the primary evidence (0-based)."""

    try:
        request = LLMRequest(prompt=prompt, schema=schema, temperature=0.0)
        result = llm_adapter.complete_json(request)

        status = GroundingStatus(result["status"])
        primary_idx = result.get("primary_evidence_index", 0)
        primary_evidence_id = (
            evidence_list[primary_idx].id
            if evidence_list and 0 <= primary_idx < len(evidence_list)
            else (evidence_list[0].id if evidence_list else None)
        )

        return GroundingResult(
            claim_id=claim.id,
            document_id=document.id,
            status=status,
            evidence_ids=[e.id for e in evidence_list],
            primary_evidence_id=primary_evidence_id,
            reason=result["reason"],
            confidence=result["confidence"],
            source_metadata={
                "document_id": str(document.id),
                "llm_verified": True,
                "evidence_count": len(evidence_list),
            },
        )
    except (LLMError, Exception) as exc:
        logger.warning("LLM verification failed for claim %s: %s", claim.id, exc)
        return GroundingResult(
            claim_id=claim.id,
            document_id=document.id,
            status=GroundingStatus.UNCERTAIN,
            evidence_ids=[e.id for e in evidence_list],
            primary_evidence_id=evidence_list[0].id if evidence_list else None,
            reason=f"Verification failed: {exc}",
            confidence=0.2,
            source_metadata={"document_id": str(document.id), "error": str(exc)},
        )


# ---------------------------------------------------------------------------
# Evidence retrieval for claims (P1 interface)
# ---------------------------------------------------------------------------


def find_evidence_for_claim(
    session: Session,
    claim: Claim,
    max_results: int = 5,
) -> list[Evidence]:
    """Return stored evidence, retrieving it first if the claim has none."""
    rows = session.exec(
        select(Evidence)
        .where(Evidence.claim_id == claim.id)
        .order_by(Evidence.score.desc())
        .limit(max_results)
    ).all()
    if rows:
        return list(rows)
    chunks = retrieve_for_claim(session, claim, top_k=max_results)
    return persist_evidence_for_claim(session, claim, chunks)


def emit_grounding_flags(session: Session, audit_id: uuid.UUID) -> list[Flag]:
    """Turn contradicted / material unsupported claims into reviewer flags."""
    claims = session.exec(select(Claim).join(Document, Claim.document_id == Document.id).where(Claim.audit_id == audit_id, Document.is_current.is_(True))).all()
    # A re-audit replaces current grounding verdicts without destroying history.
    previous_flags = session.exec(select(Flag).where(Flag.audit_id == audit_id, Flag.type.in_(["claim_contradiction", "unsupported_claim", "verification_uncertain"]), Flag.status != "superseded")).all()
    for previous in previous_flags:
        previous.status = "superseded"
        session.add(previous)
    existing = set()
    created: list[Flag] = []
    for claim in claims:
        status = (claim.status or "").lower()
        if status not in {GroundingStatus.CONTRADICTED.value, GroundingStatus.UNSUPPORTED.value, GroundingStatus.UNCERTAIN.value}:
            continue
        if status == GroundingStatus.UNSUPPORTED.value and claim.category not in {
            "commercial",
            "sla",
            "timeline",
            "liability",
        }:
            continue
        flag_type = (
            "claim_contradiction"
            if status == GroundingStatus.CONTRADICTED.value
            else "verification_uncertain" if status == "uncertain" else "unsupported_claim"
        )
        if (claim.id, flag_type) in existing:
            continue
        try:
            meta = json.loads(claim.metadata_json or "{}")
        except json.JSONDecodeError:
            meta = {}
        grounding = meta.get("grounding") or {}
        severity = "HIGH" if status == GroundingStatus.CONTRADICTED.value else "MEDIUM"
        if claim.category == "commercial":
            severity = "CRITICAL" if status == GroundingStatus.CONTRADICTED.value else "HIGH"
        flag = Flag(
            audit_id=audit_id,
            document_id=claim.document_id,
            claim_id=claim.id,
            type=flag_type,
            severity=severity,
            materiality="MATERIAL" if claim.category == "commercial" else "MODERATE",
            reason=str(grounding.get("reason") or f"Claim is {status}: {claim.text}"),
            suggested_fix="Compare the claim sentence with retrieved source excerpts before accepting.",
            status="pending",
            impact_score=0.0 if status == "uncertain" else float(grounding.get("confidence", 0.5)),
            sentence_id=claim.sentence_id,
            location_json=json.dumps(claim_location(claim), ensure_ascii=False),
        )
        session.add(flag)
        created.append(flag)
        existing.add((claim.id, flag_type))
    if created or previous_flags:
        session.commit()
    return created


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


__all__ = [
    "GroundingStatus",
    "GroundingResult",
    "ClaimEvidencePair",
    "ground_claims",
    "find_evidence_for_claim",
]
