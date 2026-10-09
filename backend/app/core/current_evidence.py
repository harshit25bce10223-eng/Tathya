"""Literal evidence from current, separate sources in the same audit."""
from __future__ import annotations

import json
from uuid import UUID
from sqlmodel import Session, select, func
from app.models import Claim, Document, Evidence


def current_evidence(session: Session, audit_id: UUID, claim_ids: list[UUID] | None = None) -> list[Evidence]:
    claims = select(Claim.id).join(Document, Claim.document_id == Document.id).where(
        Claim.audit_id == audit_id, Document.audit_id == audit_id,
        Document.is_current.is_(True), Document.kind == "primary",
        func.length(func.trim(Claim.text)) > 0, func.strpos(Document.normalized_text, Claim.text) > 0,
    )
    if claim_ids is not None:
        if not claim_ids:
            return []
        claims = claims.where(Claim.id.in_(claim_ids))
    rows = session.exec(select(Evidence, Document).join(Document, Evidence.source_document_id == Document.id).where(
        Evidence.claim_id.in_(claims), Document.audit_id == audit_id,
        Document.is_current.is_(True), Document.kind == "source",
    ).order_by(Evidence.created_at, Evidence.id)).all()
    unique = {}
    for evidence, source in rows:
        if not evidence.quote.strip() or evidence.quote not in (source.normalized_text or ""):
            continue
        try:
            location = json.dumps(json.loads(evidence.location_json), sort_keys=True)
        except (ValueError, TypeError):
            location = evidence.location_json
        key = (evidence.claim_id, source.id, evidence.quote, location, evidence.support_type)
        if key not in unique or evidence.score > unique[key].score:
            unique[key] = evidence
    return list(unique.values())
