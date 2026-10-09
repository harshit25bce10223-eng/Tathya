"""Source facts must remain grounded, versioned and permission-scoped."""
import json
import uuid

import pytest
from sqlmodel import select

from app.core.facts import extract_facts
from app.core.pipeline import ingest_document, save_upload
from app.core.source_fact_sheet import build_source_fact_sheet
from app.models import Audit, AuditLogEntry, Fact, User


@pytest.fixture
def source_set(db):
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="Fact sheet " + uuid.uuid4().hex, owner_id=owner.id, status="completed")
    db.add(audit)
    db.commit()
    def ingest(name, text):
        doc = ingest_document(db, audit, filename=name, path=save_upload(audit.id, name, text.encode()))
        extract_facts(db, doc)
        db.commit()
        return doc
    primary = ingest("generated.txt", "Contract value is INR 50 lakh.")
    source = ingest("approval.txt", "Contract value is INR 41.6 lakh.\nDelivery is on 22 December 2026.\nPayment is due within 45 days.\nWarranty is valid for 12 months.")
    return audit, primary, source, ingest


def test_canonical_values_use_only_grounded_source_facts(db, source_set):
    audit, primary, source, _ = source_set
    result = build_source_fact_sheet(db, audit.id)
    assert result["source_count"] == 1
    assert all(f["document_id"] == str(source.id) for f in result["facts"])
    assert result["canonical"]["contract_value"]["value"] == 4160000
    assert result["canonical"]["delivery_date"]["value"] == "2026-12-22"
    assert result["canonical"]["payment_terms_days"]["value"] == 45
    assert result["canonical"]["warranty_months"]["value"] == 12
    assert all(f["quote"] in source.normalized_text for f in result["facts"] if f["grounded"])
    assert not result["conflicts"]


def test_forged_normalized_value_is_not_canonical(db, source_set):
    audit, _, source, _ = source_set
    fact = db.exec(select(Fact).where(Fact.document_id == source.id, Fact.predicate == "amount")).first()
    metadata = json.loads(fact.metadata_json)
    metadata["normalized_payload"]["value"] = 99999999
    fact.metadata_json = json.dumps(metadata)
    db.add(fact)
    db.commit()
    result = build_source_fact_sheet(db, audit.id)
    assert "contract_value" not in result["canonical"]
    assert next(f for f in result["facts"] if f["id"] == str(fact.id))["grounded"] is False


@pytest.mark.parametrize("span", [{"norm_start": 0, "norm_end": 3}, {"norm_start": -1, "norm_end": 999999}])
def test_forged_quote_location_is_not_grounded(db, source_set, span):
    audit, _, source, _ = source_set
    fact = db.exec(select(Fact).where(Fact.document_id == source.id, Fact.predicate == "amount")).first()
    fact.location_json = json.dumps(span)
    db.add(fact)
    db.commit()
    result = build_source_fact_sheet(db, audit.id)
    assert "contract_value" not in result["canonical"]
    assert next(f for f in result["facts"] if f["id"] == str(fact.id))["grounded"] is False


def test_conflicting_current_sources_require_resolution(db, source_set):
    audit, _, _, ingest = source_set
    ingest("second-approval.txt", "Contract value is INR 42 lakh.")
    result = build_source_fact_sheet(db, audit.id)
    assert "contract_value" not in result["canonical"]
    assert result["conflicts"][0]["field"] == "contract_value"
    assert len(result["conflicts"][0]["fact_ids"]) == 2


def test_old_versions_cannot_contribute_facts(db, source_set):
    audit, _, old, ingest = source_set
    new = ingest("approval.txt", "Contract value is INR 42 lakh.")
    result = build_source_fact_sheet(db, audit.id)
    assert result["canonical"]["contract_value"]["value"] == 4200000
    assert all(f["document_id"] == str(new.id) for f in result["facts"])
    assert not result["conflicts"]


def test_source_context_permissions_and_chain(client, db, superuser_token_headers, normal_user_token_headers, source_set):
    audit, primary, source, _ = source_set
    base = f"/api/v1/audits/{audit.id}"
    path = f"{base}/documents/{source.id}/source-context"
    body = {"authority": "approved", "note": "Signed purchase approval supplied by the reviewer."}
    assert client.get(f"{base}/source-facts").status_code == 401
    assert client.get(f"{base}/source-facts", headers=normal_user_token_headers).status_code == 404
    assert client.patch(path, json=body, headers=normal_user_token_headers).status_code == 403
    assert client.patch(f"{base}/documents/{primary.id}/source-context", json=body, headers=superuser_token_headers).status_code == 404
    assert client.patch(path, json={**body, "authority": "automatically-verified"}, headers=superuser_token_headers).status_code == 422
    assert client.patch(path, json={**body, "note": "   "}, headers=superuser_token_headers).status_code == 422
    response = client.patch(path, json=body, headers=superuser_token_headers)
    assert response.status_code == 200
    result = client.get(f"{base}/source-facts", headers=superuser_token_headers)
    assert result.status_code == 200
    assert result.json()["sources"][0]["authority"] == "approved"
    assert result.json()["authority_is_reviewer_declared"] is True
    entry = db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit.id, AuditLogEntry.action == "source.context.updated")).first()
    assert json.loads(entry.payload_json)["context"]["note"] == body["note"]


def test_source_context_cannot_change_during_processing(client, db, superuser_token_headers, source_set):
    audit, _, source, _ = source_set
    audit.status = "processing"
    db.add(audit)
    db.commit()
    response = client.patch(f"/api/v1/audits/{audit.id}/documents/{source.id}/source-context", json={"authority": "reference", "note": "Reference only."}, headers=superuser_token_headers)
    assert response.status_code == 409


def test_context_change_refreshes_existing_passport(client, db, superuser_token_headers, source_set):
    from app.core.canonical import source_set_hash
    from app.core.pipeline import issue_passport
    audit, primary, source, _ = source_set
    audit.source_set_hash = source_set_hash([primary.text_hash, source.text_hash])
    db.add(audit)
    db.commit()
    passport = issue_passport(db, audit)
    token, revision, previous_head = passport.verify_token, passport.revision, passport.chain_head
    response = client.patch(f"/api/v1/audits/{audit.id}/documents/{source.id}/source-context", json={"authority": "reference", "note": "Reference document supplied for comparison."}, headers=superuser_token_headers)
    assert response.status_code == 200
    db.refresh(passport)
    assert passport.verify_token == token and passport.revision == revision + 1
    assert passport.chain_head != previous_head
    verification = client.get(f"/api/v1/verify/{token}")
    assert verification.status_code == 200
    assert verification.json()["signature_valid"] is True
