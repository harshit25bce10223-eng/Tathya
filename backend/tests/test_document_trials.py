"""Trial isolation, labels, authorization and conservative score regressions."""

import json
import uuid
import pytest
from sqlmodel import select
from app.models import Audit, AuditLogEntry, Claim, Document, User
from app.core.pipeline import ingest_document, save_upload
from app.core.challenge_runner import TrialRequest, start_trial, trial_results
from app.core.source_verification import compare_quote


@pytest.fixture
def trial_base(db):
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="Isolated trial", owner_id=owner.id, status="completed")
    db.add(audit)
    db.commit()
    docs = [
        ingest_document(
            db, audit, filename=name, path=save_upload(audit.id, name, text.encode())
        )
        for name, text in [
            ("generated.txt", "Warranty is valid for 12 months."),
            ("approved.txt", "Warranty is valid for 6 months."),
        ]
    ]
    return audit, docs


def body(status="contradicted"):
    return {
        "candidate_text": "Warranty is valid for 12 months.",
        "expected": [
            {
                "text": "Warranty is valid for 12 months.",
                "status": status,
                "category": "commitments",
            }
        ],
        "note": "Compare the approved warranty.",
    }


def test_trial_copies_sources_and_keeps_labels_out_of_candidate(
    db, trial_base, monkeypatch
):
    audit, originals = trial_base
    submitted = []

    def submit(id):
        candidate = db.get(Audit, id)
        assert candidate.status == "queued" and candidate.source_set_hash
        submitted.append(id)

    monkeypatch.setattr("app.core.challenge_runner.submit_audit_job", submit)
    result = start_trial(db, audit, audit.owner_id, TrialRequest(**body()))
    id = uuid.UUID(result["candidate_audit_id"])
    docs = db.exec(select(Document).where(Document.audit_id == id)).all()
    assert len(docs) == 2 and len(submitted) == 1
    source = next(d for d in docs if d.kind == "source")
    assert source.normalized_text == originals[1].normalized_text
    assert json.loads(source.metadata_json)["challenge_source"]["document_id"] == str(
        originals[1].id
    )
    assert all(d.is_current for d in originals)
    assert not db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == id)).all()
    candidate = db.get(Audit, id)
    candidate.status = "completed"
    db.add(candidate)
    primary = next(d for d in docs if d.kind == "primary")
    db.add(
        Claim(
            audit_id=id,
            document_id=primary.id,
            text=body()["candidate_text"],
            status="contradicted",
        )
    )
    db.commit()
    metrics = trial_results(db, audit.id)["metrics"]
    assert metrics["true_positives"] == 1 and metrics["f1"] == 1
    # Modifying the trial source invalidates the observation, not the originals.
    ingest_document(
        db,
        candidate,
        filename=source.filename,
        path=save_upload(id, source.filename, b"Warranty is valid for 24 months."),
    )
    report = trial_results(db, audit.id)
    assert (
        report["results"][0]["status"] == "documents_changed"
        and report["metrics"]["labelled_claims"] == 0
    )


def test_trial_validates_literal_labels_and_active_limit(db, trial_base, monkeypatch):
    audit, _ = trial_base
    monkeypatch.setattr("app.core.challenge_runner.submit_audit_job", lambda _: None)
    invalid = body()
    invalid["expected"][0]["text"] = "Fabricated expected passage."
    with pytest.raises(ValueError, match="literal"):
        start_trial(db, audit, audit.owner_id, TrialRequest(**invalid))
    for _ in range(5):
        start_trial(db, audit, audit.owner_id, TrialRequest(**body()))
    with pytest.raises(ValueError, match="five active"):
        start_trial(db, audit, audit.owner_id, TrialRequest(**body()))


def test_trial_route_permissions_and_validation(
    client, trial_base, superuser_token_headers, normal_user_token_headers, monkeypatch
):
    audit, _ = trial_base
    monkeypatch.setattr("app.core.challenge_runner.submit_audit_job", lambda _: None)
    url = f"/api/v1/challenges/{audit.id}/trials"
    assert client.post(url, json=body()).status_code == 401
    assert (
        client.post(url, json=body(), headers=normal_user_token_headers).status_code
        == 403
    )
    assert (
        client.post(
            url, json={**body(), "note": "   "}, headers=superuser_token_headers
        ).status_code
        == 422
    )
    assert (
        client.post(url, json=body(), headers=superuser_token_headers).status_code
        == 201
    )
    assert (
        client.get(url, headers=superuser_token_headers).json()["metrics"]["precision"]
        is None
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "not valid for",
        "valid for at least",
        "valid for up to",
        "may be valid for",
        "valid unless cancelled after",
    ],
)
def test_qualified_warranty_does_not_become_supported_from_equal_numbers(phrase):
    assert (
        compare_quote(
            "Warranty is valid for 12 months.", f"Warranty is {phrase} 12 months."
        )
        is None
    )


def test_unqualified_equivalent_units_are_supported():
    assert (
        compare_quote(
            "Warranty is valid for 12 months.", "Warranty is valid for 1 year."
        )
        == "supported"
    )


@pytest.mark.parametrize("field", ["candidate_text", "expected"])
def test_empty_trial_text_is_rejected_before_storage(field):
    invalid = body()
    if field == "expected":
        invalid["expected"][0]["text"] = "   "
    else:
        invalid[field] = "   "
    with pytest.raises(ValueError):
        TrialRequest(**invalid)
