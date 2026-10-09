"""Explicit reviewer source selections, scoped to a field and immutable version."""
import json
from uuid import UUID
from sqlmodel import Session, select
from app.models import AuditLogEntry, Document

FIELDS = {"contract_value", "delivery_date", "payment_terms_days", "warranty_months"}


def latest_resolutions(session: Session, audit_id: UUID) -> dict:
    entries = session.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit_id, AuditLogEntry.action == "source.resolution.recorded").order_by(AuditLogEntry.created_at, AuditLogEntry.id)).all()
    output = {}
    for entry in entries:
        try:
            data = json.loads(entry.payload_json)
            if data.get("field") not in FIELDS:
                continue
            data = {**data, "revision": str(entry.id), "recorded_at": entry.created_at, "actor_id": str(entry.actor_id)}
            doc = session.get(Document, UUID(data["document_id"])) if data.get("document_id") else None
            data["active"] = bool(doc and doc.audit_id == audit_id and doc.is_current and doc.kind == "source" and doc.text_hash == data.get("text_hash"))
            data["state"] = "selected" if data["active"] else "expired" if data.get("document_id") else "cleared"
            output[data["field"]] = data
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    return output


def current_resolutions(session: Session, audit_id: UUID) -> dict:
    return {field: value for field, value in latest_resolutions(session, audit_id).items() if value["active"]}


def resolution_fingerprint(session: Session, audit_id: UUID) -> dict:
    return {field: item["revision"] for field, item in latest_resolutions(session, audit_id).items()}
