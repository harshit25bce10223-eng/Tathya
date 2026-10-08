"""Phase 1 tests that require PostgreSQL (skipped automatically if absent)."""

from __future__ import annotations

import time
import uuid

import pytest

from tests.conftest import database_available

pytestmark = pytest.mark.skipif(
    not database_available(), reason="PostgreSQL not available"
)


# ---------------------------------------------------------------------------
# Document version binding: document_version_id == documents.id
# ---------------------------------------------------------------------------


def test_document_version_binding(db):
    from app.core.pipeline import ingest_document, save_upload
    from app.core.security import get_password_hash
    from app.models import Audit, Claim, Document, User

    user = User(
        email=f"dbtest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit = Audit(title="binding test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    path_v1 = save_upload(audit.id, "contract.txt", b"Version one text.")
    doc_v1 = ingest_document(
        session=db, audit=audit, filename="contract.txt", path=path_v1
    )
    path_v2 = save_upload(audit.id, "contract.txt", b"Version two text.")
    doc_v2 = ingest_document(
        session=db, audit=audit, filename="contract.txt", path=path_v2
    )

    assert doc_v2.id != doc_v1.id
    assert doc_v1.version_no == 1 and doc_v2.version_no == 2
    assert doc_v1.is_current is False
    assert doc_v2.is_current is True
    assert doc_v1.id != doc_v2.id  # document_version_id == documents.id

    # claims.document_id -> documents.id (mandatory, never audit_id alone)
    claim = Claim(
        audit_id=audit.id,
        document_id=doc_v2.id,
        text="Version two text.",
        status="extracted",
    )
    db.add(claim)
    db.commit()

    bound = db.get(Document, claim.document_id)
    assert bound is not None
    assert bound.id == doc_v2.id
    assert bound.audit_id == audit.id


# ---------------------------------------------------------------------------
# Job status flow: queued -> processing -> completed | failed
# ---------------------------------------------------------------------------


def _wait_for_terminal(audit_id: uuid.UUID, timeout: float = 60.0) -> str:
    from sqlmodel import Session

    from app.core.db import engine
    from app.models import Audit

    deadline = time.monotonic() + timeout
    last = "unknown"
    while time.monotonic() < deadline:
        with Session(engine) as session:
            audit = session.get(Audit, audit_id)
            if audit is not None:
                last = audit.status
                if last in ("completed", "failed", "cancelled"):
                    return last
        time.sleep(0.2)
    return last


def test_audit_job_completes_and_persists_chain(db):
    from sqlmodel import select

    from app.core.jobs import submit_audit_job
    from app.core.pipeline import save_upload, verify_passport_token
    from app.core.security import get_password_hash
    from app.models import Audit, AuditLogEntry, Passport, User

    user = User(
        email=f"jobtest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="job flow test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    path = save_upload(audit.id, "doc.txt", b"Job pipeline source text.")
    from app.core.pipeline import ingest_document

    ingest_document(session=db, audit=audit, filename="doc.txt", path=path)

    submit_audit_job(audit.id)
    status = _wait_for_terminal(audit.id)
    assert status == "completed", f"job ended as {status}"

    db.refresh(audit)
    assert audit.source_set_hash and len(audit.source_set_hash) == 64
    assert audit.failed_stage is None
    assert audit.error_message is None

    passport = db.exec(select(Passport).where(Passport.audit_id == audit.id)).first()
    assert passport is not None
    assert 8 <= len(passport.verify_token) <= 12
    assert passport.document_hash == audit.source_set_hash
    assert passport.signature

    entries = db.exec(
        select(AuditLogEntry).where(AuditLogEntry.audit_id == audit.id)
    ).all()
    assert entries, "hash chain must contain at least one entry"

    resolved = verify_passport_token(db, passport.verify_token)
    assert resolved is not None
    _, resolved_audit, chain_ok, chain_reason = resolved
    assert resolved_audit.id == audit.id
    assert chain_ok, chain_reason


def test_failed_job_persists_error_and_stage(db):
    from app.core.jobs import StageError, StageTracker, submit_audit_job
    from app.core.security import get_password_hash
    from app.models import Audit, User

    user = User(
        email=f"failtest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="failure test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    def exploding_pipeline(_session, _audit_id, tracker: StageTracker) -> None:
        tracker.set("canonical")
        raise StageError("canonical", "boom at canonical stage")

    submit_audit_job(audit.id, pipeline=exploding_pipeline)
    status = _wait_for_terminal(audit.id)
    assert status == "failed"

    db.refresh(audit)
    assert audit.failed_stage == "canonical"
    assert audit.error_message and "boom" in audit.error_message


# ---------------------------------------------------------------------------
# API serialization: stable contracts for the frontend
# ---------------------------------------------------------------------------


def test_api_audit_lifecycle_serialization(client, superuser_token_headers):
    files = [("files", ("contract.txt", b"API contract text.", "text/plain"))]
    response = client.post(
        "/api/v1/audits",
        data={"title": "API serialization audit"},
        files=files,
        headers=superuser_token_headers,
    )
    assert response.status_code == 201, response.text
    created = response.json()
    for key in (
        "id",
        "owner_id",
        "status",
        "title",
        "source_set_hash",
        "created_at",
        "updated_at",
        "error_message",
        "failed_stage",
    ):
        assert key in created
    audit_id = created["id"]
    assert created["status"] == "queued"

    final_status = _wait_for_terminal(uuid.UUID(audit_id))
    assert final_status == "completed"

    # GET /audits/{id} -> AuditSummary contract
    response = client.get(f"/api/v1/audits/{audit_id}", headers=superuser_token_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["audit"]["id"] == audit_id
    assert summary["audit"]["status"] == "completed"
    assert summary["document_count"] == 1
    assert summary["flag_count"] == 0
    assert summary["claim_count"] == 0
    assert summary["verify_token"]
    assert len(summary["verify_token"]) <= 12

    # documents contract: document_version_id == id
    response = client.get(
        f"/api/v1/audits/{audit_id}/documents", headers=superuser_token_headers
    )
    docs = response.json()
    assert docs["count"] == 1
    doc = docs["data"][0]
    assert doc["id"] and doc["text_hash"] and doc["version_no"] == 1
    assert doc["is_current"] is True

    # flags contract (empty in Phase 1)
    response = client.get(
        f"/api/v1/audits/{audit_id}/flags", headers=superuser_token_headers
    )
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}

    # passport contract
    response = client.get(
        f"/api/v1/audits/{audit_id}/passport", headers=superuser_token_headers
    )
    assert response.status_code == 200
    passport = response.json()
    assert passport["verify_token"] == summary["verify_token"]
    assert passport["document_hash"] == summary["audit"]["source_set_hash"]
    assert "merkle" not in str(passport).lower()

    # public verification: no auth, no audit id in the payload
    response = client.get(f"/api/v1/verify/{summary['verify_token']}")
    assert response.status_code == 200
    verification = response.json()
    assert verification["found"] is True
    assert verification["document_count"] == 1
    assert verification["chain"]["ok"] is True
    assert verification["signature_valid"] is True
    assert verification["verify_url"].endswith(f"/verify/{summary['verify_token']}")
    assert audit_id not in response.text
    assert "merkle" not in response.text.lower()

    # unknown token -> found=False
    response = client.get("/api/v1/verify/zzzzzzzzzz")
    assert response.status_code == 200
    assert response.json()["found"] is False


def test_api_requires_auth_for_audit_routes(client):
    response = client.get("/api/v1/audits")
    assert response.status_code == 401


def test_api_job_status_endpoint(client, superuser_token_headers):
    files = [("files", ("status.txt", b"Status endpoint text.", "text/plain"))]
    response = client.post(
        "/api/v1/audits",
        data={"title": "status audit"},
        files=files,
        headers=superuser_token_headers,
    )
    audit_id = response.json()["id"]
    final_status = _wait_for_terminal(uuid.UUID(audit_id))
    assert final_status in ("completed", "failed")

    response = client.get(
        f"/api/v1/audits/{audit_id}/status", headers=superuser_token_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["audit_id"] == audit_id
    assert payload["status"] == final_status
    assert "source_set_hash" in payload
