"""Current source facts with literal grounding and conservative canonical fields."""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.core.canonical import build_blocks, build_sentences
from app.core.extraction.base import SpanClaims
from app.core.extraction.dates import extract as extract_dates
from app.core.extraction.names import extract as extract_names
from app.core.extraction.numeric import extract as extract_numeric
from app.core.source_verification import field_hint
from app.models import Document, Fact


def _object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def _grounded(quote: str, payload: dict[str, Any], text: str, location: dict[str, Any]) -> bool:
    if not quote or quote not in text or not payload:
        return False
    start, end = location.get("norm_start"), location.get("norm_end")
    if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(text)) or text[start:end] != quote:
        return False
    spans = SpanClaims()
    records = extract_numeric(quote, spans) + extract_dates(quote, spans) + extract_names(quote, spans)
    # Re-extract the exact cited quote, then compare all value-bearing payload keys.
    keys = {"type", "kind", "value", "currency", "unit", "iso", "normalized_name", "years", "expression", "day", "month", "year", "lower", "upper"}
    expected = {k: v for k, v in payload.items() if k in keys}
    if not expected:
        return False
    return any(record.raw_text == quote and all(record.payload.get(k) == v for k, v in expected.items()) for record in records)


def _canonical(field: str | None, payload: dict[str, Any]) -> tuple[str, Any, str | None] | None:
    kind = payload.get("type")
    if field == "contract_value" and kind == "currency":
        return "contract_value", payload.get("value"), payload.get("currency")
    if field == "delivery" and payload.get("kind") == "absolute":
        return "delivery_date", payload.get("iso"), None
    if field in {"payment", "warranty"} and kind == "duration":
        try:
            value = Decimal(str(payload.get("value")))
        except InvalidOperation:
            return None
        unit = str(payload.get("unit", "")).lower().rstrip("s")
        if unit == "year":
            unit, value = "month", value * 12
        if unit == "week":
            unit, value = "day", value * 7
        key = {("payment", "day"): "payment_terms_days", ("warranty", "month"): "warranty_months"}.get((field, unit))
        if key:
            return key, int(value) if value == int(value) else float(value), unit
    return None


def build_source_fact_sheet(session: Session, audit_id: UUID) -> dict[str, Any]:
    documents = session.exec(select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True), Document.kind == "source").order_by(Document.version_no)).all()
    sources, items, candidates = [], [], {}
    for document in documents:
        context = _object(document.metadata_json).get("source_context", {})
        if not isinstance(context, dict):
            context = {}
        sources.append({"document_id": str(document.id), "filename": document.filename, "version_no": document.version_no, "text_hash": document.text_hash, "uploaded_at": document.created_at,
                        "authority": context.get("authority", "unspecified"), "note": context.get("note", ""), "context_updated_at": context.get("updated_at")})
        sentences = build_sentences(document.id, build_blocks(document.normalized_text), document.normalized_text)
        sentence_map = {s.sentence_id: s for s in sentences}
        facts = session.exec(select(Fact).where(Fact.document_id == document.id, Fact.status == "active").order_by(Fact.created_at, Fact.id)).all()
        for fact in facts:
            meta = _object(fact.metadata_json)
            payload = meta.get("normalized_payload", {})
            if not isinstance(payload, dict):
                payload = {}
            quote = meta.get("quote", "")
            quote = quote if isinstance(quote, str) else ""
            location = _object(fact.location_json)
            grounded = _grounded(quote, payload, document.normalized_text, location)
            bound_sentence = sentence_map.get(meta.get("sentence_id"))
            sentence = bound_sentence.text if grounded and bound_sentence and bound_sentence.start_offset <= location["norm_start"] and location["norm_end"] <= bound_sentence.end_offset else ""
            field = field_hint(sentence) if sentence else None
            normalized = _canonical(field, payload) if grounded else None
            item = {"id": str(fact.id), "document_id": str(document.id), "filename": document.filename, "version_no": document.version_no, "text_hash": document.text_hash,
                    "field": normalized[0] if normalized else field, "subject": "monetary value" if not field and payload.get("type") == "currency" else fact.subject, "predicate": fact.predicate, "value": normalized[1] if normalized else fact.object_value,
                    "unit": normalized[2] if normalized else payload.get("currency") or payload.get("unit"), "quote": quote, "context_quote": sentence,
                    "location": location, "grounded": grounded, "authority": context.get("authority", "unspecified"), "uploaded_at": document.created_at}
            items.append(item)
            if normalized:
                candidates.setdefault(normalized[0], []).append(item)
    canonical, conflicts = {}, []
    for key, facts in candidates.items():
        distinct = {(str(f["value"]), f["unit"]) for f in facts}
        if len(distinct) == 1:
            canonical[key] = {"value": facts[0]["value"], "unit": facts[0]["unit"], "fact_ids": [f["id"] for f in facts]}
        else:
            conflicts.append({"field": key, "fact_ids": [f["id"] for f in facts], "reason": "Current sources contain different values or units. Reviewer resolution is required."})
    return {"sources": sources, "facts": items, "canonical": canonical, "conflicts": conflicts, "source_count": len(sources), "fact_count": len(items), "grounded_count": sum(f["grounded"] for f in items), "authority_is_reviewer_declared": True}
