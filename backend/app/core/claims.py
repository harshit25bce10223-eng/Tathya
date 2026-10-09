"""Claim extraction from canonical document sentences.

Claims are assertions the audit must verify — not verdicts.
Extraction is deterministic so a missing LLM never produces an empty audit.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.canonical import build_blocks, build_sentences
from app.models import Claim, Document

logger = logging.getLogger("tathya.claims")

MAX_CLAIMS_PER_DOCUMENT = 80
MIN_CLAIM_CHARS = 12
MAX_CLAIM_CHARS = 600

_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$|€)\s*[\d,]+(?:\.\d+)?|\b[\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore|million|billion)\b",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_DATE = re.compile(
    r"\b(?:\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}"
    r"|\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(
    r"\b(?:PO[-/]\d+|GSTIN|PAN|IFSC|UPI|Aadhaar|Net\s+\d+)\b",
    re.IGNORECASE,
)
_COMMITMENT = re.compile(
    r"\b(?:shall|must|warrants?|indemnif\w*|guarantees?|commits?|liable|penalty|sla|uptime|net\s+\d+)\b",
    re.IGNORECASE,
)


def classify_claim(text: str) -> str:
    lowered = text.lower()
    if _AMOUNT.search(text):
        return "commercial"
    if _PERCENT.search(text) or "sla" in lowered or "uptime" in lowered:
        return "sla"
    if _DATE.search(text) or any(w in lowered for w in ("delivery", "milestone", "commence")):
        return "timeline"
    if any(w in lowered for w in ("indemn", "liab", "penalty", "late fee")):
        return "liability"
    if _IDENTIFIER.search(text):
        return "identifier"
    if _COMMITMENT.search(text):
        return "commitment"
    return "general"


def is_claim_sentence(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < MIN_CLAIM_CHARS or len(stripped) > MAX_CLAIM_CHARS:
        return False
    if stripped.endswith(":"):
        return False
    return bool(
        _AMOUNT.search(stripped)
        or _PERCENT.search(stripped)
        or _DATE.search(stripped)
        or _IDENTIFIER.search(stripped)
        or _COMMITMENT.search(stripped)
        or re.search(r"\b(?:is|are|was|were|has|have|will|provides|includes|approved|achieved)\b", stripped, re.I)
    )


def extract_claims(session: Session, document: Document) -> list[Claim]:
    """Persist checkable claims for one document version. Idempotent per sentence."""
    existing = {
        row.sentence_id
        for row in session.exec(
            select(Claim).where(Claim.document_id == document.id)
        ).all()
        if row.sentence_id
    }
    blocks = build_blocks(document.normalized_text or "")
    sentences = build_sentences(document.id, blocks, document.normalized_text or "")
    created: list[Claim] = []

    for sentence in sentences:
        if len(created) >= MAX_CLAIMS_PER_DOCUMENT:
            break
        if sentence.sentence_id in existing:
            continue
        if not is_claim_sentence(sentence.text):
            continue
        claim = Claim(
            audit_id=document.audit_id,
            document_id=document.id,
            sentence_id=sentence.sentence_id,
            text=sentence.text.strip(),
            category=classify_claim(sentence.text),
            status="extracted",
            metadata_json=json.dumps(
                {
                    "start_offset": sentence.start_offset,
                    "end_offset": sentence.end_offset,
                    "block_index": sentence.block_index,
                    "extractor": "deterministic_v1",
                },
                ensure_ascii=False,
            ),
        )
        session.add(claim)
        created.append(claim)
        existing.add(sentence.sentence_id)

    if created:
        session.commit()
        for claim in created:
            session.refresh(claim)
    logger.info(
        "extracted %s claims from document %s",
        len(created),
        document.id,
    )
    return created


def extract_claims_for_audit(session: Session, audit_id: uuid.UUID) -> list[Claim]:
    documents = session.exec(
        select(Document).where(
            Document.audit_id == audit_id,
            Document.is_current.is_(True),
        )
    ).all()
    primary = [d for d in documents if d.kind == "primary"] or documents
    claims: list[Claim] = []
    for document in primary:
        claims.extend(extract_claims(session, document))
    return claims


def claim_location(claim: Claim) -> dict[str, Any]:
    try:
        meta = json.loads(claim.metadata_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    start = int(meta.get("start_offset") or 0)
    end = int(meta.get("end_offset") or start)
    return {
        "kind": "text",
        "start": start,
        "end": end,
        "sentence_id": claim.sentence_id,
    }


__all__ = [
    "classify_claim",
    "is_claim_sentence",
    "extract_claims",
    "extract_claims_for_audit",
    "claim_location",
]
