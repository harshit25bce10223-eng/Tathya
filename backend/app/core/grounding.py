"""Grounding Guard — Phase 3.

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

from app.core.llm import LLMError, LLMRequest, llm_adapter
from app.models import Claim, Document, Evidence, Fact

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
        select(Claim).where(Claim.audit_id == audit_id)
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

    # Get evidence linked to this claim
    evidence_list = session.exec(
        select(Evidence).where(Evidence.claim_id == claim.id)
    ).all()

    if not evidence_list:
        # No evidence at all -> UNSUPPORTED (not CONTRADICTED)
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

    # Try deterministic fact-based verification first
    fact_result = _verify_against_facts(session, claim, document, evidence_list)
    if fact_result is not None:
        return fact_result

    # Fall back to LLM-based semantic verification
    return _verify_with_llm(session, claim, document, evidence_list)


def _verify_against_facts(
    session: Session,
    claim: Claim,
    document: Document,
    evidence_list: list[Evidence],
) -> GroundingResult | None:
    """Try deterministic verification against structured facts.

    Returns None if no relevant facts exist or conflict is ambiguous.
    """
    # Get facts from the source document
    facts = session.exec(
        select(Fact).where(Fact.document_id == document.id)
    ).all()

    if not facts:
        return None

    # Try to match claim against facts
    # This is a simplified version - in production, would use more sophisticated matching
    claim_text = claim.text.lower()

    for fact in facts:
        fact_text = f"{fact.subject} {fact.predicate} {fact.object_value}".lower()

        # Simple numeric conflict detection
        numeric_conflict = _check_numeric_conflict(claim_text, fact_text)
        if numeric_conflict is not None:
            return GroundingResult(
                claim_id=claim.id,
                document_id=document.id,
                status=GroundingStatus.CONTRADICTED,
                evidence_ids=[e.id for e in evidence_list],
                primary_evidence_id=evidence_list[0].id,
                reason=f"Numeric conflict: claim '{claim.text}' contradicts fact '{fact.subject} {fact.predicate} {fact.object_value}'",
                confidence=0.9,
                source_metadata={
                    "fact_id": str(fact.id),
                    "fact_type": "numeric",
                    "document_id": str(document.id),
                },
            )

        # Date conflict detection
        date_conflict = _check_date_conflict(claim_text, fact_text)
        if date_conflict is not None:
            return GroundingResult(
                claim_id=claim.id,
                document_id=document.id,
                status=GroundingStatus.CONTRADICTED,
                evidence_ids=[e.id for e in evidence_list],
                primary_evidence_id=evidence_list[0].id,
                reason=f"Date conflict: claim '{claim.text}' contradicts fact '{fact.subject} {fact.predicate} {fact.object_value}'",
                confidence=0.85,
                source_metadata={
                    "fact_id": str(fact.id),
                    "fact_type": "date",
                    "document_id": str(document.id),
                },
            )

    # If we have supporting evidence with high score, consider supported
    supporting_evidence = [e for e in evidence_list if e.support_type == "supports" and e.score > 0.7]
    if supporting_evidence:
        return GroundingResult(
            claim_id=claim.id,
            document_id=document.id,
            status=GroundingStatus.SUPPORTED,
            evidence_ids=[e.id for e in supporting_evidence],
            primary_evidence_id=supporting_evidence[0].id,
            reason="Claim supported by evidence with high confidence",
            confidence=0.75,
            source_metadata={
                "document_id": str(document.id),
                "supporting_evidence_count": len(supporting_evidence),
            },
        )

    return None


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
    """Retrieve evidence for a claim (used by P1's fast verifier)."""
    # This is a placeholder for the actual retrieval logic
    # which would use embeddings/risk reranking from P1
    return session.exec(
        select(Evidence)
        .where(Evidence.claim_id == claim.id)
        .order_by(Evidence.score.desc())
        .limit(max_results)
    ).all()


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
