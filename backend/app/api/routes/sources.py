from typing import Literal
"""Permission-scoped source inbox configuration and change detection."""
import json
from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import select
from app.models import Audit
from app.api.deps import CurrentUser, ReviewerDep, SessionDep
from app.api.routes.audits import _get_audit
from app.core.pipeline import append_chain_entry
from app.core.source_watch import inbox, inspect_watch, check_watch

router = APIRouter(prefix="/sources", tags=["sources"])


class WatchSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audit_id: UUID
    enabled: bool
    auto_reaudit: bool = False
    note: str = Field(min_length=3, max_length=2000)

    @field_validator("note")
    @classmethod
    def meaningful_note(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Explain the source watch configuration.")
        return value


@router.post("/watch")
def configure_watch(body: WatchSettings, session: SessionDep, reviewer: ReviewerDep) -> dict:
    _get_audit(session, body.audit_id, reviewer)
    session.exec(select(Audit).where(Audit.id == body.audit_id).with_for_update()).one()
    try:
        inbox(body.audit_id, create=body.enabled)
    except (OSError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    append_chain_entry(session, audit_id=body.audit_id, actor_id=reviewer.id, action="source.watch.configured", payload_json=json.dumps(body.model_dump(mode="json"), sort_keys=True))
    return inspect_watch(session, body.audit_id)


@router.get("/{audit_id}/stale")
def source_changes(audit_id: UUID, session: SessionDep, user: CurrentUser) -> dict:
    _get_audit(session, audit_id, user)
    try:
        return inspect_watch(session, audit_id)
    except (OSError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{audit_id}/check")
def check_sources(audit_id: UUID, session: SessionDep, reviewer: ReviewerDep) -> dict:
    _get_audit(session, audit_id, reviewer)
    try:
        return check_watch(session, audit_id, reviewer.id)
    except (OSError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


class SourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["contract_value", "delivery_date", "payment_terms_days", "warranty_months"]
    document_id: UUID | None = None
    expected_revision: UUID | None = None
    note: str = Field(min_length=3, max_length=2000)

    @field_validator("note")
    @classmethod
    def meaningful_note(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Explain the source selection.")
        return value


@router.post("/{audit_id}/resolve")
def resolve_source(audit_id: UUID, body: SourceSelection, session: SessionDep, reviewer: ReviewerDep) -> dict:
    from app.core.source_resolution import latest_resolutions
    from app.core.source_fact_sheet import build_source_fact_sheet
    from app.models import Document
    _get_audit(session, audit_id, reviewer)
    audit = session.exec(select(Audit).where(Audit.id == audit_id).with_for_update().execution_options(populate_existing=True)).one()
    if audit.status in ("queued", "processing"):
        raise HTTPException(409, "Wait for the audit to finish before resolving source conflicts.")
    previous = latest_resolutions(session, audit_id).get(body.field, {})
    if previous.get("revision") != (str(body.expected_revision) if body.expected_revision else None):
        raise HTTPException(409, "This source selection changed while you were editing. Refresh before saving.")
    document = session.get(Document, body.document_id) if body.document_id else None
    if body.document_id:
        if not document or document.audit_id != audit_id or not document.is_current or document.kind != "source":
            raise HTTPException(422, "Choose a current source version from this audit.")
        facts = [f for f in build_source_fact_sheet(session, audit_id)["facts"] if f["document_id"] == str(document.id) and f["field"] == body.field and f["grounded"]]
        values = {(str(f["value"]), f["unit"]) for f in facts}
        if len(values) != 1:
            raise HTTPException(422, "This source does not establish one unambiguous grounded value for this business field.")
    payload = {"field": body.field, "document_id": str(document.id) if document else None, "text_hash": document.text_hash if document else None, "version": document.version_no if document else None, "note": body.note}
    append_chain_entry(session, audit_id=audit_id, actor_id=reviewer.id, action="source.resolution.recorded", payload_json=json.dumps(payload, sort_keys=True))
    return build_source_fact_sheet(session, audit_id)
