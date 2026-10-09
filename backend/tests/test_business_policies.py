"""Business requirements must be typed, versioned, grounded and score-relevant."""
import json
import uuid

import pytest
from sqlmodel import select

from app.core.business_policies import BusinessRules, evaluate_audit_policies, preview_rules, recorded_policy_results
from app.core.claims import extract_claims
from app.core.facts import extract_facts
from app.core.grounding import ground_claims
from app.core.pipeline import ingest_document, save_upload
from app.core.trust_score import compute_score_breakdown
from app.models import Audit, AuditLogEntry, Evidence, Flag, Policy, User


@pytest.fixture
def policy_audit(db):
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="Policy regression " + uuid.uuid4().hex, owner_id=owner.id, status="completed")
    db.add(audit); db.commit()
    text = "Contract value is INR 41.6 lakh.\nDelivery is on 22 December 2026.\nPayment is due within 45 days.\nWarranty is valid for 6 months."
    primary = ingest_document(db, audit, filename="generated.txt", path=save_upload(audit.id, "generated.txt", text.encode()))
    source = ingest_document(db, audit, filename="approved.txt", path=save_upload(audit.id, "approved.txt", text.encode()))
    for document in (primary, source): extract_facts(db, document)
    for claim in extract_claims(db, primary):
        db.add(Evidence(claim_id=claim.id, source_document_id=source.id, quote=claim.text, score=1, support_type="supports"))
    db.commit()
    ground_claims(db, audit.id)
    db.commit()
    return audit, primary, source


def policy_body(audit_id, **patch):
    body = {"name": "Minimum warranty " + uuid.uuid4().hex, "description": "Business warranty requirement.", "is_active": True,
            "change_note": "Initial business rule for this synthetic audit.", "rules": {"target": "claim", "audit_id": str(audit_id), "severity": "HIGH", "conditions": [{"variable": "warranty_months", "operator": "gte", "value": 12, "currency": None, "reason": "At least one year of warranty is required."}]}}
    body.update(patch)
    return body


def create(client, headers, audit, **patch):
    body = policy_body(audit.id, **patch)
    response = client.post("/api/v1/policies", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), body


@pytest.mark.parametrize("condition", [
    {"variable": "arbitrary_attribute", "operator": "eq", "value": 1},
    {"variable": "warranty_months", "operator": "execute", "value": 1},
    {"variable": "warranty_months", "operator": "gte", "value": -1},
    {"variable": "warranty_months", "operator": "gte", "value": True},
    {"variable": "warranty_months", "operator": "gte", "value": float("nan")},
    {"variable": "contract_value", "operator": "lte", "value": 5000000},
    {"variable": "currency", "operator": "gte", "value": "INR"},
    {"variable": "delivery_date", "operator": "lte", "value": "2026-13-01"},
    {"variable": "warranty_months", "operator": "exists", "value": 12},
    {"variable": "payment_terms_days", "operator": "lte", "value": 30, "currency": "INR"},
])
def test_invalid_business_conditions_are_rejected(condition):
    with pytest.raises(ValueError): BusinessRules.model_validate({"conditions": [condition]})


def test_admin_authoring_and_optimistic_version_history(client, db, superuser_token_headers, normal_user_token_headers, policy_audit):
    audit, _, _ = policy_audit
    body = policy_body(audit.id)
    assert client.get("/api/v1/policies").status_code == 401
    assert client.get("/api/v1/policies", headers=normal_user_token_headers).status_code == 403
    assert client.post("/api/v1/policies", json=body, headers=normal_user_token_headers).status_code == 403
    record, body = create(client, superuser_token_headers, audit)
    assert record["version"] == 1 and len(record["history"]) == 1
    updated = {**body, "is_active": False, "change_note": "Disable the requirement for this test.", "expected_version": 1}
    response = client.put(f"/api/v1/policies/{record['id']}", json=updated, headers=superuser_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 2 and not data["is_active"]
    assert [h["version"] for h in data["history"]] == [1, 2]
    stale = client.put(f"/api/v1/policies/{record['id']}", json=updated, headers=superuser_token_headers)
    assert stale.status_code == 409
    duplicate = client.post("/api/v1/policies", json=body, headers=superuser_token_headers)
    assert duplicate.status_code == 409


def test_preview_has_real_values_and_no_writes(client, db, superuser_token_headers, policy_audit):
    audit, _, _ = policy_audit
    before_flags = len(db.exec(select(Flag).where(Flag.audit_id == audit.id)).all())
    before_entries = len(db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit.id)).all())
    body = {"audit_id": str(audit.id), "rules": policy_body(audit.id)["rules"]}
    response = client.post("/api/v1/policies/preview", json=body, headers=superuser_token_headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["state"] == "violation" and result["preview_only"] is True
    assert result["conditions"][0]["actual_value"] == 6
    assert result["conditions"][0]["evidence"][0]["quote"] == "Warranty is valid for 6 months."
    assert before_flags == len(db.exec(select(Flag).where(Flag.audit_id == audit.id)).all())
    assert before_entries == len(db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit.id)).all())


def test_policy_violation_reduces_real_score_and_records_version(client, db, superuser_token_headers, policy_audit):
    audit, _, _ = policy_audit
    assert compute_score_breakdown(db, str(audit.id)).reviewed_score == 100
    record, _ = create(client, superuser_token_headers, audit)
    # A new, unchecked requirement caps the current rating until evaluated.
    pending = compute_score_breakdown(db, str(audit.id))
    assert pending.score_status == "partial_verification" and pending.reviewed_score <= 79
    snapshot = evaluate_audit_policies(db, audit.id)
    result = snapshot["evaluations"][0]
    assert result["policy_id"] == record["id"] and result["policy_version"] == 1
    assert result["state"] == "violation"
    flags = db.exec(select(Flag).where(Flag.audit_id == audit.id, Flag.type == "policy_violation")).all()
    assert len(flags) == 1 and flags[0].claim_id is not None and flags[0].impact_score == 1
    score = compute_score_breakdown(db, str(audit.id))
    assert score.reviewed_score < 100 and score.sub_scores["policy_compliance"] == 0
    assert not recorded_policy_results(db, audit.id)["stale"]


def test_unchanged_rule_preserves_review_and_new_version_supersedes(client, db, superuser_token_headers, policy_audit):
    audit, _, _ = policy_audit
    record, body = create(client, superuser_token_headers, audit)
    first = evaluate_audit_policies(db, audit.id)["evaluations"][0]
    flag = db.get(Flag, uuid.UUID(first["flag_id"]))
    flag.status, flag.reviewer_note = "dismissed", "Approved exception recorded by the reviewer."
    db.add(flag); db.commit()
    second = evaluate_audit_policies(db, audit.id)["evaluations"][0]
    db.refresh(flag)
    assert second["flag_id"] == first["flag_id"] and flag.status == "dismissed"
    edit = {**body, "expected_version": 1, "is_active": False, "change_note": "Disable this requirement after review."}
    assert client.put(f"/api/v1/policies/{record['id']}", json=edit, headers=superuser_token_headers).status_code == 200
    assert recorded_policy_results(db, audit.id)["stale"] is True
    assert not evaluate_audit_policies(db, audit.id)["evaluations"]
    db.refresh(flag)
    assert flag.status == "superseded"
    response = client.post(f"/api/v1/audits/{audit.id}/flags/{flag.id}/decision", json={"action": "accept", "reason": "Attempt to resurrect an old finding."}, headers=superuser_token_headers)
    assert response.status_code == 409
    db.refresh(flag)
    assert flag.status == "superseded"
    assert compute_score_breakdown(db, str(audit.id)).reviewed_score == 100


def test_missing_business_value_remains_uncertain(client, db, superuser_token_headers, policy_audit):
    audit, _, _ = policy_audit
    body = policy_body(audit.id)
    body["rules"]["conditions"] = [{"variable": "warranty_months", "operator": "exists", "value": None}]
    # A forged claim span must not provide a business value to a rule.
    from app.models import Claim
    claim = db.exec(select(Claim).where(Claim.audit_id == audit.id, Claim.text.contains("Warranty"))).first()
    claim.metadata_json = json.dumps({"start_offset": -1, "end_offset": 99999})
    db.add(claim); db.commit()
    assert client.post("/api/v1/policies", json=body, headers=superuser_token_headers).status_code == 201
    result = evaluate_audit_policies(db, audit.id)["evaluations"][0]
    assert result["state"] == "uncertain"
    assert result["conditions"][0]["evidence"] == []
    score = compute_score_breakdown(db, str(audit.id))
    assert score.score_status == "partial_verification" and score.reviewed_score <= 79


def test_currency_mismatch_never_performs_implicit_conversion(db, policy_audit):
    audit, _, _ = policy_audit
    rules = BusinessRules.model_validate({"conditions": [{"variable": "contract_value", "operator": "lte", "value": 5000000, "currency": "USD"}]})
    result = preview_rules(db, audit.id, rules)
    assert result["state"] == "uncertain"
    assert result["conditions"][0]["actual_unit"] == "INR"


def test_source_target_and_dates_are_evaluated_on_literal_facts(db, policy_audit):
    audit, _, _ = policy_audit
    rules = BusinessRules.model_validate({"target": "source", "conditions": [{"variable": "delivery_date", "operator": "lte", "value": "2026-12-31"}, {"variable": "contract_value", "operator": "lte", "value": 4200000, "currency": "INR"}]})
    result = preview_rules(db, audit.id, rules)
    assert result["state"] == "satisfied"
    assert all(c["evidence"] and c["evidence"][0]["claim_id"] is None for c in result["conditions"])


def test_conflicting_source_values_cannot_pass_policy(db, policy_audit):
    audit, _, _ = policy_audit
    doc = ingest_document(db, audit, filename="conflicting.txt", path=save_upload(audit.id, "conflicting.txt", b"Warranty is valid for 24 months."))
    extract_facts(db, doc)
    rules = BusinessRules.model_validate({"target": "source", "conditions": [{"variable": "warranty_months", "operator": "gte", "value": 12}]})
    result = preview_rules(db, audit.id, rules)
    assert result["state"] == "uncertain" and result["conditions"][0]["evidence_count"] == 2


def test_pipeline_enforces_policy_before_signing_passport(client, db, superuser_token_headers, policy_audit, monkeypatch):
    from app.core import pipeline, retrieval
    from app.core.jobs import StageTracker
    from app.models import Passport
    audit, _, _ = policy_audit
    create(client, superuser_token_headers, audit)
    monkeypatch.setattr(pipeline, "scan_audit_risks", lambda *args: [])
    def no_semantic_model(*args, **kwargs): raise AssertionError("Exact source matches should not need semantic inference")
    monkeypatch.setattr(retrieval, "_encode", no_semantic_model)
    monkeypatch.setattr(retrieval, "_reranker", no_semantic_model)
    tracker = StageTracker()
    pipeline.run_audit_pipeline(db, audit.id, tracker)
    assert tracker.history.index("policy_check") < tracker.history.index("passport")
    passport = db.exec(select(Passport).where(Passport.audit_id == audit.id)).first()
    assert passport.trust_score < 100
    public = client.get(f"/api/v1/verify/{passport.verify_token}").json()
    assert public["signature_valid"] is True and public["requires_reassessment"] is False
    result = client.get(f"/api/v1/audits/{audit.id}/policy-results", headers=superuser_token_headers).json()
    assert result["evaluations"][0]["state"] == "violation" and result["stale"] is False


def test_policy_changes_mark_issued_passport_for_reassessment(client, db, superuser_token_headers, policy_audit):
    from app.core.pipeline import issue_passport
    from app.core.canonical import source_set_hash
    audit, primary, source = policy_audit
    audit.source_set_hash = source_set_hash([primary.text_hash, source.text_hash])
    db.add(audit); db.commit()
    passport = issue_passport(db, audit)
    create(client, superuser_token_headers, audit)
    response = client.get(f"/api/v1/verify/{passport.verify_token}").json()
    assert response["signature_valid"] is True
    assert response["requires_reassessment"] is True
    assert response["score_status"] == "partial_verification"


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_running_audit_cannot_be_reviewed_or_rescored(client, db, superuser_token_headers, policy_audit, status):
    audit, _, _ = policy_audit
    create(client, superuser_token_headers, audit)
    result = evaluate_audit_policies(db, audit.id)["evaluations"][0]
    audit.status = status
    db.add(audit); db.commit()
    response = client.post(f"/api/v1/audits/{audit.id}/flags/{result['flag_id']}/decision", json={"action": "accept", "reason": "Review while the audit is running."}, headers=superuser_token_headers)
    assert response.status_code == 409
    assert client.post(f"/api/v1/audits/{audit.id}/rescore", headers=superuser_token_headers).status_code == 409
    assert db.get(Flag, uuid.UUID(result["flag_id"])).status == "pending"


def test_reviewer_can_preview_but_cannot_author_policy(client, db, superuser_token_headers, policy_audit):
    from datetime import timedelta
    from app.core.security import create_access_token
    audit, _, _ = policy_audit
    reviewer = User(email=f"policy-reviewer-{uuid.uuid4().hex}@example.test", hashed_password="unused-test-hash", role="reviewer", is_active=True)
    db.add(reviewer); db.commit(); db.refresh(reviewer)
    headers = {"Authorization": "Bearer " + create_access_token(str(reviewer.id), timedelta(minutes=5))}
    record, body = create(client, superuser_token_headers, audit)
    assert client.get("/api/v1/policies", headers=headers).status_code == 200
    preview = client.post("/api/v1/policies/preview", json={"audit_id": str(audit.id), "rules": body["rules"]}, headers=headers)
    assert preview.status_code == 200 and preview.json()["preview_only"] is True
    assert client.post("/api/v1/policies", json=body, headers=headers).status_code == 403
    assert client.put(f"/api/v1/policies/{record['id']}", json={**body, "expected_version": 1}, headers=headers).status_code == 403
