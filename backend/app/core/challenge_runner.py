"""Run document candidates through the real pipeline without mutating originals."""

from __future__ import annotations
import json
import uuid
from datetime import UTC, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session, select
from app.models import Audit, AuditLogEntry, Claim, Document
from app.core.pipeline import append_chain_entry, ingest_document, save_upload
from app.core.jobs import submit_audit_job
from app.core.canonical import source_set_hash


class ExpectedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=2000)
    status: Literal["supported", "contradicted", "unsupported"]
    category: Literal["numbers", "dates", "names", "pii", "commitments", "other"] = (
        "other"
    )

    @field_validator("text")
    @classmethod
    def check_text(cls, value: str) -> str:
        if len(value.strip()) < 3 or "\x00" in value:
            raise ValueError("Supply a non-empty literal claim passage.")
        return value


class TrialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_text: str = Field(min_length=3, max_length=200000)
    expected: list[ExpectedClaim] = Field(min_length=1, max_length=50)
    note: str = Field(min_length=3, max_length=2000)

    @field_validator("candidate_text")
    @classmethod
    def check_candidate(cls, value: str) -> str:
        if len(value.strip()) < 3 or "\x00" in value:
            raise ValueError("Supply a non-empty text candidate.")
        return value

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("A reviewer reason is required.")
        return value.strip()


def start_trial(
    session: Session, base: Audit, actor_id: uuid.UUID, request: TrialRequest
) -> dict:
    base = session.exec(
        select(Audit).where(Audit.id == base.id).with_for_update()
    ).one()
    documents = session.exec(
        select(Document).where(
            Document.audit_id == base.id, Document.is_current.is_(True)
        )
    ).all()
    if (
        len(documents) > 20
        or sum(len(d.normalized_text.encode("utf-8")) for d in documents)
        > 100 * 1024 * 1024
    ):
        raise ValueError(
            "A trial supports at most 20 current documents and 100 MB of source text."
        )
    previous = session.exec(
        select(AuditLogEntry).where(
            AuditLogEntry.audit_id == base.id,
            AuditLogEntry.action == "challenge.trial.started",
        )
    ).all()
    child_ids = [
        uuid.UUID(json.loads(e.payload_json)["candidate_audit_id"]) for e in previous
    ]
    pending = (
        session.exec(
            select(Audit)
            .where(Audit.id.in_(child_ids), Audit.status.in_(["queued", "processing"]))
            .limit(5)
        ).all()
        if child_ids
        else []
    )
    if len(pending) >= 5:
        raise ValueError("Finish the five active trials before starting another.")
    if not any(d.kind == "primary" for d in documents) or not any(
        d.kind == "source" for d in documents
    ):
        raise ValueError(
            "A challenge needs a current AI document and separate current sources."
        )
    if len({e.text for e in request.expected}) != len(request.expected) or any(
        e.text not in request.candidate_text for e in request.expected
    ):
        raise ValueError(
            "Expected claim texts must be unique literal passages in the candidate."
        )
    # Pipeline never receives expected labels: they are stored only on the parent.
    trial = Audit(
        title=f"Challenge — {base.title}"[:255], owner_id=actor_id, status="queued"
    )
    saved = []
    clones = []
    try:
        session.add(trial)
        session.flush()
        inputs = [("candidate.txt", request.candidate_text, None)] + [
            (f"source-{i}.txt", d.normalized_text, d)
            for i, d in enumerate(documents)
            if d.kind == "source"
        ]
        for filename, text, original in inputs:
            path = save_upload(trial.id, filename, text.encode("utf-8"))
            saved.append(path)
            clone = ingest_document(
                session, trial, filename=filename, path=path, commit=False
            )
            clones.append(clone)
            if original:
                clone.metadata_json = json.dumps(
                    {
                        "challenge_source": {
                            "document_id": str(original.id),
                            "text_hash": original.text_hash,
                            "version": original.version_no,
                        }
                    }
                )
                session.add(clone)
        trial.source_set_hash = source_set_hash([d.text_hash for d in clones])
        trial_id = uuid.uuid4()
        append_chain_entry(
            session,
            audit_id=base.id,
            actor_id=actor_id,
            action="challenge.trial.started",
            payload_json=json.dumps(
                {
                    "trial_id": str(trial_id),
                    "candidate_audit_id": str(trial.id),
                    "expected": [e.model_dump() for e in request.expected],
                    "note": request.note,
                    "candidate_documents": {str(d.id): d.text_hash for d in clones},
                    "sources": {str(d.id): d.text_hash for d in documents},
                    "started_at": datetime.now(UTC).isoformat(),
                    "label_origin": "reviewer_declared",
                    "scope": "canonical text copies; global enabled policies; no parent reviewer decisions",
                },
                sort_keys=True,
            ),
            commit=False,
        )
        session.commit()
    except Exception:
        session.rollback()
        for path in saved:
            path.unlink(missing_ok=True)
        raise
    submit_audit_job(trial.id)
    return {
        "trial_id": str(trial_id),
        "candidate_audit_id": str(trial.id),
        "status": trial.status,
    }


def trial_results(session: Session, audit_id: uuid.UUID) -> dict:
    entries = session.exec(
        select(AuditLogEntry)
        .where(
            AuditLogEntry.audit_id == audit_id,
            AuditLogEntry.action == "challenge.trial.started",
        )
        .order_by(AuditLogEntry.created_at.desc())
        .limit(100)
    ).all()
    results = []
    totals = {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "true_negatives": 0,
        "abstentions": 0,
        "labelled_claims": 0,
    }
    for entry in entries:
        payload = json.loads(entry.payload_json)
        candidate = session.get(Audit, uuid.UUID(payload["candidate_audit_id"]))
        row = {
            **payload,
            "status": candidate.status if candidate else "missing",
            "claims": [],
            "latency_ms": None,
        }
        if candidate and candidate.status == "completed":
            current = session.exec(
                select(Document).where(
                    Document.audit_id == candidate.id, Document.is_current.is_(True)
                )
            ).all()
            if {str(d.id): d.text_hash for d in current} != payload.get(
                "candidate_documents"
            ):
                row["status"] = "documents_changed"
                results.append(row)
                continue
            claims = session.exec(
                select(Claim)
                .join(Document, Claim.document_id == Document.id)
                .where(
                    Claim.audit_id == candidate.id,
                    Document.kind == "primary",
                    Document.is_current.is_(True),
                )
            ).all()
            by_text = {c.text: c.status for c in claims}
            completion = session.exec(
                select(AuditLogEntry)
                .where(
                    AuditLogEntry.audit_id == candidate.id,
                    AuditLogEntry.action == "audit.completed",
                )
                .order_by(AuditLogEntry.created_at.desc())
            ).first()
            if completion:
                row["latency_ms"] = max(
                    0,
                    int(
                        (completion.created_at - entry.created_at).total_seconds()
                        * 1000
                    ),
                )
            for expected in payload["expected"]:
                actual = by_text.get(expected["text"], "not_extracted")
                positive, detected = (
                    expected["status"] != "supported",
                    actual in ("contradicted", "unsupported"),
                )
                key = (
                    "true_positives"
                    if positive and detected
                    else "false_negatives"
                    if positive
                    else "false_positives"
                    if detected
                    else "true_negatives"
                    if actual == "supported"
                    else "abstentions"
                )
                totals[key] += 1
                totals["labelled_claims"] += 1
                row["claims"].append(
                    {
                        **expected,
                        "actual": actual,
                        "correct": expected["status"] == actual,
                        "outcome": key,
                    }
                )
        results.append(row)
    tp, fp, fn, tn = (
        totals[k]
        for k in (
            "true_positives",
            "false_positives",
            "false_negatives",
            "true_negatives",
        )
    )
    return {
        "results": results,
        "metrics": {
            **totals,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "false_alarm_rate": fp / (fp + tn) if fp + tn else None,
        },
        "label_origin": "reviewer_declared",
        "scope": "current trial observations; labelled claim detection only; not independent production calibration",
        "limit": 100,
    }
