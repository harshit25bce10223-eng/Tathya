"""Fact Extraction & Storage — Phase 2/3.

Facts are extracted information, not truth verdicts.
Persisted in the existing `facts` table/model.

Each fact preserves:
    fact_id
    document_id (document_version_id == documents.id)
    type (numeric, date, name, duration, currency, etc.)
    raw_text (original text span)
    normalized value/payload (JSON)
    unit/currency
    location (structured per format)
    extraction metadata

Document version binding: Every fact tied to documents.id.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from app.core.canonical import (
    Sentence,
    build_blocks,
    build_sentences,
    denormalize_span,
    location_docx,
    location_pdf,
    location_text,
    location_xlsx,
    text_hash,
)
from app.core.extraction.base import (
    CATEGORY_DATE,
    CATEGORY_NAME,
    CATEGORY_NUMERIC,
    EXTRACTION_VERSION,
    LocationResolver,
    SentenceIndex,
    SpanClaims,
    canonical_json,
    resolve_location,
)
from app.core.extraction.dates import extract as extract_dates
from app.core.extraction.names import extract as extract_names
from app.core.extraction.numeric import extract as extract_numeric
from app.core.llm import LLMError, LLMRequest, llm_adapter
from app.models import Document, Fact

logger = logging.getLogger("tathya.facts")


class FactType(str):
    """Standard fact types."""
    NUMERIC = "numeric"
    DATE = "date"
    NAME = "name"
    DURATION = "duration"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    IDENTIFIER = "identifier"
    ADDRESS = "address"
    OTHER = "other"


@dataclass
class ExtractedFact:
    """A fact extracted from a document."""
    document_id: uuid.UUID
    fact_type: str
    subject: str
    predicate: str
    object_value: str
    normalized_payload: dict[str, Any]
    raw_text: str
    location_json: str
    confidence: float
    metadata_json: str


# ---------------------------------------------------------------------------
# Fact Extraction — main entry point
# ---------------------------------------------------------------------------


def extract_facts(
    session: Session,
    document: Document,
) -> list[Fact]:
    """Extract structured facts from a document using deterministic engines.

    Flow:
        1. Get canonical sentences from document
        2. Run deterministic extraction engines (numeric, date, name) on full text
        3. Map extracted spans to sentences for sentence_id binding
        4. Persist facts with document version binding
        5. Return created facts
    """
    # Get blocks and sentences for sentence_id binding
    blocks = build_blocks(document.normalized_text)
    sentences = build_sentences(document.id, blocks, document.normalized_text)

    if not sentences and not document.normalized_text.strip():
        return []

    all_facts: list[ExtractedFact] = []

    # Load location resolver from document metadata
    import json as json_module
    metadata = json_module.loads(document.metadata_json or "{}")
    char_locations = metadata.get("locations", [])
    resolver = LocationResolver(char_locations)
    sentence_index = SentenceIndex(sentences)

    # Load offset map for denormalization
    offset_segments = json_module.loads(document.offset_map_json or "[]")

    # Run extraction engines on full normalized text with span claims
    claims = SpanClaims()

    # 1. Numeric extraction (currency, percentages, durations, quantities, ratios)
    numeric_records = extract_numeric(document.normalized_text, claims)
    for record in numeric_records:
        sentence_id = sentence_index.sentence_id_for(record.norm_start, record.norm_end)
        location = resolve_location(resolver, offset_segments, record.norm_start, record.norm_end)
        fact = _record_to_extracted_fact(
            document_id=document.id,
            record=record,
            sentence_id=sentence_id,
            location=location,
            document=document,
        )
        if fact:
            all_facts.append(fact)

    # 2. Date extraction (absolute, partial, relative, fiscal year)
    date_records = extract_dates(document.normalized_text, claims)
    for record in date_records:
        sentence_id = sentence_index.sentence_id_for(record.norm_start, record.norm_end)
        location = resolve_location(resolver, offset_segments, record.norm_start, record.norm_end)
        fact = _record_to_extracted_fact(
            document_id=document.id,
            record=record,
            sentence_id=sentence_id,
            location=location,
            document=document,
        )
        if fact:
            all_facts.append(fact)

    # 3. Name extraction (organizations, persons, short forms)
    name_records = extract_names(document.normalized_text, claims)
    for record in name_records:
        sentence_id = sentence_index.sentence_id_for(record.norm_start, record.norm_end)
        location = resolve_location(resolver, offset_segments, record.norm_start, record.norm_end)
        fact = _record_to_extracted_fact(
            document_id=document.id,
            record=record,
            sentence_id=sentence_id,
            location=location,
            document=document,
        )
        if fact:
            all_facts.append(fact)

    # Deduplicate facts (same document + same normalized payload)
    unique_facts = _deduplicate_facts(all_facts)

    # Persist facts
    persisted_facts = _persist_facts(session, document.id, unique_facts)

    return persisted_facts


def _record_to_extracted_fact(
    document_id: uuid.UUID,
    record,
    sentence_id: str,
    location: dict[str, Any],
    document: Document,
) -> ExtractedFact | None:
    """Convert an extraction engine FactRecord to an ExtractedFact."""
    payload = dict(record.payload)
    payload["extraction_version"] = EXTRACTION_VERSION

    # Map category to fact_type and subject/predicate
    category = record.category
    if category.startswith(CATEGORY_NUMERIC):
        fact_type, subject, predicate, object_value = _map_numeric_category(category, payload)
    elif category.startswith(CATEGORY_DATE):
        fact_type, subject, predicate, object_value = _map_date_category(category, payload)
    elif category.startswith(CATEGORY_NAME):
        fact_type, subject, predicate, object_value = _map_name_category(category, payload)
    else:
        fact_type = FactType.OTHER
        subject = "unknown"
        predicate = "value"
        object_value = record.raw_text

    # Confidence based on extraction source
    confidence = 0.9 if payload.get("source", "").startswith("regex") else 0.7

    return ExtractedFact(
        document_id=document_id,
        fact_type=fact_type,
        subject=subject,
        predicate=predicate,
        object_value=object_value,
        normalized_payload=payload,
        raw_text=record.raw_text,
        location_json=json.dumps(location, ensure_ascii=False),
        confidence=confidence,
        metadata_json=json.dumps({
            "sentence_id": sentence_id,
            "extraction_method": "deterministic",
            "category": category,
        }, ensure_ascii=False),
    )


def _map_numeric_category(category: str, payload: dict[str, Any]) -> tuple[str, str, str, str]:
    """Map numeric subcategory to fact_type, subject, predicate, object_value."""
    ptype = payload.get("type", "unknown")
    if ptype == "currency":
        return FactType.CURRENCY, "contract value", "amount", str(payload.get("value", ""))
    elif ptype == "percentage":
        return FactType.PERCENTAGE, "percentage", "value", f"{payload.get('value', '')}%"
    elif ptype == "duration":
        val = payload.get("value")
        unit = payload.get("unit", "")
        return FactType.DURATION, "duration", "value", f"{val} {unit}" if val else ""
    elif ptype in ("integer", "decimal"):
        return FactType.NUMERIC, "quantity", "value", str(payload.get("value", ""))
    elif ptype == "ratio":
        return FactType.NUMERIC, "ratio", "value", payload.get("value", "")
    elif ptype == "quantity":
        return FactType.NUMERIC, "quantity", "value", f"{payload.get('value', '')} {payload.get('unit', '')}"
    return FactType.NUMERIC, "numeric", "value", str(payload.get("value", ""))


def _map_date_category(category: str, payload: dict[str, Any]) -> tuple[str, str, str, str]:
    """Map date subcategory to fact_type, subject, predicate, object_value."""
    kind = payload.get("kind", "unknown")
    if kind == "absolute":
        return FactType.DATE, "date", "value", payload.get("iso", "")
    elif kind == "partial":
        parts = []
        if payload.get("day"):
            parts.append(str(payload["day"]))
        if payload.get("month"):
            parts.append(str(payload["month"]))
        if payload.get("year"):
            parts.append(str(payload["year"]))
        return FactType.DATE, "date", "partial", "-".join(parts)
    elif kind == "fiscal_year":
        years = payload.get("years", [])
        return FactType.DATE, "fiscal_year", "value", ",".join(str(y) for y in years)
    elif kind == "relative":
        return FactType.DATE, "relative_date", "expression", payload.get("expression", "")
    return FactType.DATE, "date", "value", ""


def _map_name_category(category: str, payload: dict[str, Any]) -> tuple[str, str, str, str]:
    """Map name subcategory to fact_type, subject, predicate, object_value."""
    kind = payload.get("kind", "unknown")
    if kind == "organization":
        return FactType.NAME, "organization", "name", payload.get("normalized_name", "")
    elif kind == "person":
        return FactType.NAME, "person", "name", payload.get("normalized_name", "")
    elif kind == "org_short":
        return FactType.NAME, "organization_short", "name", payload.get("normalized_name", "")
    return FactType.NAME, "name", "value", payload.get("normalized_name", "")


def _deduplicate_facts(facts: list[ExtractedFact]) -> list[ExtractedFact]:
    """Deduplicate facts by document + normalized payload hash."""
    seen: dict[str, ExtractedFact] = {}
    for fact in facts:
        key_payload = {
            "document_id": str(fact.document_id),
            "fact_type": fact.fact_type,
            "subject": fact.subject,
            "predicate": fact.predicate,
            "normalized_payload": fact.normalized_payload,
        }
        key = hashlib.sha256(
            json.dumps(key_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()[:16]

        if key not in seen or fact.confidence > seen[key].confidence:
            seen[key] = fact

    return list(seen.values())


def _persist_facts(
    session: Session,
    document_id: uuid.UUID,
    facts: list[ExtractedFact],
) -> list[Fact]:
    """Persist extracted facts to database."""
    persisted: list[Fact] = []
    for extracted in facts:
        # Check if identical fact already exists for this document version
        existing = session.exec(
            select(Fact).where(
                Fact.document_id == document_id,
                Fact.subject == extracted.subject,
                Fact.predicate == extracted.predicate,
                Fact.object_value == extracted.object_value,
            )
        ).first()

        if existing:
            # Update if new confidence is higher
            if extracted.confidence > 0:
                existing.location_json = extracted.location_json
                existing.metadata_json = extracted.metadata_json
                existing.status = "active"
                session.add(existing)
                persisted.append(existing)
            continue

        fact = Fact(
            document_id=document_id,
            subject=extracted.subject,
            predicate=extracted.predicate,
            object_value=extracted.object_value,
            location_json=extracted.location_json,
            status="active",
        )
        session.add(fact)
        session.commit()
        session.refresh(fact)
        persisted.append(fact)

    return persisted


# ---------------------------------------------------------------------------
# Fact retrieval helpers
# ---------------------------------------------------------------------------


def get_facts_for_document(session: Session, document_id: uuid.UUID) -> list[Fact]:
    """Get all active facts for a document version."""
    return session.exec(
        select(Fact).where(
            Fact.document_id == document_id,
            Fact.status == "active",
        )
    ).all()


def get_facts_for_audit(session: Session, audit_id: uuid.UUID) -> list[Fact]:
    """Get all facts for an audit (across all document versions)."""
    # Join through documents
    document_ids = session.exec(
        select(Document.id).where(Document.audit_id == audit_id)
    ).all()

    if not document_ids:
        return []

    return session.exec(
        select(Fact).where(
            Fact.document_id.in_(document_ids),
            Fact.status == "active",
        )
    ).all()


__all__ = [
    "FactType",
    "ExtractedFact",
    "extract_facts",
    "get_facts_for_document",
    "get_facts_for_audit",
]