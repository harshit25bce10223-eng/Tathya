"""Omission Detection Engine — Phase 5.

Detects potentially important information missing from a business document,
grounded in a specific expectation or requirement.

Rule: Absence alone is not proof of an omission.  A missing clause is a
meaningful potential omission only when there is an explicit expectation basis.

Supported expectation sources:
    • Configured business policy.
    • Document-type checklist.
    • User-provided required-clause list.
    • Approved template/process specification.
    • Source-supported requirement already stored in Tathya.
Do NOT assume every contract or business document must contain the same information.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlmodel import Session

from app.models import Claim, Document, Flag, Policy

logger = logging.getLogger("tathya.omission_detection_engine")

# ---------------------------------------------------------------------------
# Omission result contract
# ---------------------------------------------------------------------------

@dataclass
class OmissionResult:
    """Result of an omission detection run."""
    claim_id: str
    document_id: str
    omission_category: str  # "missing_clause" | "partial_information" | "expected_field"
    expected_information: str  # what was expected/required
    requirement_source: str  # policy ID, checklist name, template, etc.
    requirement_source_type: str  # "policy" | "checklist" | "user_list" | "template" | "db_source"
    presence_status: str  # "present" | "partial" | "absent" | "ambiguous"
    requirement_version: str | None = None  # policy version, checklist version, etc.
    evidence_supporting_expectation: list[dict[str, Any]] | None = None  # quotes, doc refs, policy refs
    document_section_searched: str | None = None  # e.g. "clause 4.2", "schedule A"
    confidence: float = 0.5  # 0-1, higher when basis is strong
    uncertainty_reason: str | None = None  # why we cannot classify with certainty
    materiality: str | None = None  # "low" | "medium" | "high" | "critical" (if calculated)
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    explanation: str = ""  # human-readable explanation


# ---------------------------------------------------------------------------
# Expectation basis sources
# ---------------------------------------------------------------------------

class ExpectationSource(str, Enum):
    POLICY = "policy"
    CHECKLIST = "checklist"
    USER_LIST = "user_provided_list"
    TEMPLATE = "approved_template"
    DB_SOURCE = "source_stored_in_tathya"


# ---------------------------------------------------------------------------
# Helper: inspect document content for expected information
# ---------------------------------------------------------------------------

def _search_document_text(
    document: Document,
    expected_keyword: str | list[str],
    case_sensitive: bool = False,
) -> bool:
    """Search the document's normalized text for a keyword or list of keywords.

    Returns True if the keyword(s) are found.  This is a simple substring search;
    a production system would use NLP/embedding-based similarity.
    """
    text = document.normalized_text or ""
    if not text:
        return False

    keywords = expected_keyword if isinstance(expected_keyword, list) else [expected_keyword]
    for kw in keywords:
        search_kw = kw if case_sensitive else kw.lower()
        if search_kw in text.lower():
            return True
    return False


def _search_document_blocks(
    document: Document,
    expected_keyword: str | list[str],
) -> bool:
    """Search document blocks_json for a keyword.

    The blocks_json stores parsed sentence/offset blocks from the canonical
    parser.  This is a best-effort substring search on the stored block text.
    """
    blocks = json.loads(document.blocks_json or "[]")
    if not blocks:
        return False
    text_snippets = []
    for block in blocks:
        # blocks have a 'text' field from the parser
        btext = block.get("text", "")
        if btext:
            text_snippets.append(btext.lower())
    combined = " ".join(text_snippets)
    keywords = expected_keyword if isinstance(expected_keyword, list) else [expected_keyword]
    for kw in keywords:
        if kw.lower() in combined:
            return True
    return False


# ---------------------------------------------------------------------------
# Omission detection engine
# ---------------------------------------------------------------------------

def detect_omission(
    session: Session,
    claim_id: str,
    expectation_source: ExpectationSource,
    expectation_identifier: str,  # policy ID, checklist name, etc.
    expected_information: str,
    document_id: str | None = None,
) -> OmissionResult:
    """Detect a potential omission in a document, grounded in an expectation basis.

    The omission is only classified as a potential finding when the expectation
    basis is defensible (a policy, checklist, template, or DB-stored requirement).

    Returns an OmissionResult with presence_status, confidence, explanation,
    and whether evidence supports the expectation.
    """
    # --- Look up the claim and document ---
    claim = session.get(Claim, claim_id)
    if claim is None:
        raise ValueError(f"Claim {claim_id} not found")

    doc_id = document_id or claim.document_id
    document = session.get(Document, doc_id)
    if document is None:
        raise ValueError(f"Document {doc_id} not found")

    # --- Determine presence status based on source type ---
    presence_status: str
    evidence_supporting: list[dict[str, Any]] | None = None
    uncertainty_reason: str | None = None
    confidence: float = 0.5

    if expectation_source == ExpectationSource.POLICY:
        # Policy-based expectation: look up the policy and check if the
        # expected information is referenced/required
        policy = session.get(Policy, expectation_identifier)
        if policy is None:
            # Policy not found → cannot defensibly claim omission
            presence_status = "ambiguous"
            uncertainty_reason = f"Policy {expectation_identifier} not found; cannot assess omission."
            confidence = 0.1
            evidence_supporting = None
        else:
            # Search the document for policy-relevant keywords
            # Use the policy's rules_json or name as keyword source
            rules = json.loads(policy.rules_json or "{}")
            keywords = rules.get("expected_clauses", [])
            found = _search_document_blocks(document, keywords) if keywords else _search_document_text(document, expected_information)

            if found:
                presence_status = "present"
                confidence = 0.8
                evidence_supporting = [
                    {
                        "source": "policy",
                        "policy_id": policy.id,
                        " rationale": f"Policy {policy.id} expected clauses found in document.",
                    }
                ]
            else:
                presence_status = "absent"
                confidence = 0.6
                uncertainty_reason = "Expected clauses not found in document per policy policy."
                evidence_supporting = [
                    {
                        "source": "policy",
                        "policy_id": policy.id,
                        "expected_information": expected_information,
                    }
                ]
    elif expectation_source == ExpectationSource.CHECKLIST:
        # Checklist-based: similar policy lookup pattern
        # For now, treat as policy-like but with checklist identifier
        policy = session.get(Policy, expectation_identifier)  # reuse Policy model
        if policy is None:
            presence_status = "ambiguous"
            uncertainty_reason = f"Checklist {expectation_identifier} not found as a policy record."
            confidence = 0.1
            evidence_supporting = None
        else:
            keywords = rules.get("expected_clauses", []) if isinstance(rules := json.loads(policy.rules_json or "{}"), dict) else []
            found = _search_document_blocks(document, keywords) if keywords else _search_document_text(document, expected_information)
            if found:
                presence_status = "present"
                confidence = 0.75
                evidence_supporting = [
                    {"source": "checklist", "checklist_id": expectation_identifier}
                ]
            else:
                presence_status = "absent"
                confidence = 0.55
                uncertainty_reason = "Expected checklist items not found in document."
                evidence_supporting = [
                    {"source": "checklist", "checklist_id": expectation_identifier, "expected": expected_information}
                ]
    elif expectation_source == ExpectationSource.USER_LIST:
        # User-provided required-clause list: we treat the identifier as a
        # free-form reference; since we cannot verify an external list, we
        # default to uncertain unless the user also provided text we can search.
        # If the identifier is a URL or path we could fetch, but that's out of scope.
        presence_status = "ambiguous"
        uncertainty_reason = "User-provided clause list; basis not verified against stored document content."
        confidence = 0.2
        evidence_supporting = None
    elif expectation_source == ExpectationSource.TEMPLATE:
        # Approved template: look for the template in the system
        # For now, default to ambiguous/uncertain since we don't have a
        # template registry integrated yet.
        presence_status = "ambiguous"
        uncertainty_reason = "Approved template reference; basis not yet verified against document."
        confidence = 0.3
        evidence_supporting = None
    elif expectation_source == ExpectationSource.DB_SOURCE:
        # Source-supported requirement already stored in Tathya:
        # Search for the expected information in related documents/evidence
        # linked to the claim/audit.
        # For now, default to uncertain with low confidence.
        presence_status = "ambiguous"
        uncertainty_reason = "Source-supported requirement from DB; specifics not mapped to document search."
        confidence = 0.3
        evidence_supporting = None
    else:
        presence_status = "ambiguous"
        uncertainty_reason = f"Unsupported expectation source: {expectation_source}"
        confidence = 0.1
        evidence_supporting = None

    # --- Build explanation ---
    explanation_parts: list[str] = []
    explanation_parts.append(f"expectation_source={expectation_source.value}")
    explanation_parts.append(f"presence_status={presence_status}")
    if evidence_supporting:
        explanation_parts.append(f"evidence_supporting_count={len(evidence_supporting)}")
    if uncertainty_reason:
        explanation_parts.append(f"uncertainty_reason={uncertainty_reason}")
    explanation_parts.append(f"expected_information={expected_information}")

    explanation = " | ".join(explanation_parts)

    # --- Build omission result ---
    result = OmissionResult(
        claim_id=claim.id,
        document_id=doc_id,
        omission_category="missing_clause" if presence_status in ("absent", "ambiguous") else "partial_information",
        expected_information=expected_information,
        requirement_source=expectation_identifier,
        requirement_source_type=expectation_source.value,
        requirement_version=None,  # could be populated from policy version etc.
        presence_status=presence_status,
        evidence_supporting_expectation=evidence_supporting,
        document_section_searched="blocks_text_search",
        confidence=confidence,
        uncertainty_reason=uncertainty_reason,
        materiality=None,  # will be calculated separately if needed
        explanation=explanation,
    )

    logger.info(
        "Omission detected for claim %s: presence=%s confidence=%.2f "
        "source=%s",
        claim.id,
        presence_status,
        confidence,
        expectation_source.value,
    )

    return result


# ---------------------------------------------------------------------------
# Convenience: assess omission for a flag
# ---------------------------------------------------------------------------

def assess_flag_omission(
    session: Session,
    flag_id: str,
    expectation_source: ExpectationSource,
    expectation_identifier: str,
) -> OmissionResult:
    """Assess omission for a flag, building the expectation from the flag's
    audit and document.

    Returns an OmissionResult.
    """
    flag = session.get(Flag, flag_id)
    if flag is None:
        raise ValueError(f"Flag {flag_id} not found")
    # Use the flag's claim and its document
    claim_id = str(flag.claim_id) if flag.claim_id else None
    # Use the claim's document
    doc_id = None
    if claim_id:
        claim = session.get(Claim, claim_id)
        if claim and claim.document_id:
            doc_id = str(claim.document_id)

    return detect_omission(
        session=session,
        claim_id=claim_id or "",
        expectation_source=expectation_source,
        expectation_identifier=expectation_identifier,
        expected_information="required clause or field per applicable basis",
        document_id=doc_id,
    )


__all__ = [
    "OmissionResult",
    "ExpectationSource",
    "detect_omission",
    "assess_flag_omission",
    "detect_omission",
]