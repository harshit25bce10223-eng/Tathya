"""Evidence history must not leak into current review or semantic verification."""
import uuid
from sqlmodel import select
from app.models import Audit, Claim, Evidence, Flag, User
from app.core.pipeline import ingest_document, save_upload
from app.core.claims import extract_claims
from app.core.current_evidence import current_evidence


def make_audit(db):
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="Evidence regression " + uuid.uuid4().hex, owner_id=owner.id, status="completed")
    db.add(audit); db.commit()
    return audit


def document(db, audit, filename, text):
    return ingest_document(db, audit, filename=filename, path=save_upload(audit.id, filename, text.encode()))


def test_review_apis_show_only_current_literal_same_audit_evidence(client, db, superuser_token_headers):
    audit = make_audit(db)
    text = "Warranty is valid for 12 months."
    primary = document(db, audit, "generated.txt", text)
    claim = extract_claims(db, primary)[0]
    old_source = document(db, audit, "approved.txt", "Warranty is valid for 6 months.")
    source = document(db, audit, "approved.txt", text)
    foreign = document(db, make_audit(db), "generated.txt", "Other audit document.")
    foreign_source = document(db, db.get(Audit, foreign.audit_id), "approved.txt", text)
    rows = [Evidence(claim_id=claim.id, source_document_id=old_source.id, quote=old_source.normalized_text),
            Evidence(claim_id=claim.id, source_document_id=source.id, quote=text, score=0.5),
            Evidence(claim_id=claim.id, source_document_id=source.id, quote=text, score=0.9),
            Evidence(claim_id=claim.id, source_document_id=source.id, quote="Forged warranty is 99 months."),
            Evidence(claim_id=claim.id, source_document_id=foreign_source.id, quote=text),
            Evidence(claim_id=claim.id, source_document_id=primary.id, quote=text)]
    for row in rows: db.add(row)
    flag = Flag(audit_id=audit.id, document_id=primary.id, claim_id=claim.id, type="claim_contradiction")
    db.add(flag); db.commit()
    evidence = current_evidence(db, audit.id)
    assert len(evidence) == 1 and evidence[0].score == 0.9
    for suffix in ("evidence", "claims", "flags"):
        result = client.get(f"/api/v1/audits/{audit.id}/{suffix}", headers=superuser_token_headers)
        assert result.status_code == 200
        data = result.json()["data"]
        quotes = data if suffix == "evidence" else data[0]["evidence"]
        assert len(quotes) == 1 and quotes[0]["source_document_id"] == str(source.id)
    # Historical rows are preserved, while replacing the primary hides its claims and evidence.
    document(db, audit, "generated.txt", "Warranty is valid for 24 months.")
    assert not current_evidence(db, audit.id)
    assert client.get(f"/api/v1/audits/{audit.id}/evidence", headers=superuser_token_headers).json()["count"] == 0
    assert len(db.exec(select(Evidence).where(Evidence.claim_id == claim.id)).all()) == 6


def test_forged_quote_never_reaches_neural_or_semantic_verifiers(db, monkeypatch):
    from app.core import grounding
    audit = make_audit(db)
    primary = document(db, audit, "generated.txt", "Warranty is valid for 12 months.")
    source = document(db, audit, "approved.txt", "Warranty is valid for 6 months.")
    claim = extract_claims(db, primary)[0]
    db.add(Evidence(claim_id=claim.id, source_document_id=source.id, quote=claim.text)); db.commit()
    calls = []
    monkeypatch.setattr(grounding, "retrieve_for_claim", lambda *args: [])
    monkeypatch.setattr(grounding, "verify_with_rope", lambda **kwargs: calls.append("neural"))
    monkeypatch.setattr(grounding, "judge_claim", lambda **kwargs: calls.append("semantic"))
    result = grounding._ground_single_claim(db, claim)
    assert result.status.value == "unsupported" and not result.evidence_ids
    assert calls == []


def test_retrieval_rejects_cross_audit_forged_and_duplicate_chunks(db):
    from app.core.retrieval import RetrievedChunk, persist_evidence_for_claim
    audit = make_audit(db)
    text = "Warranty is valid for 12 months."
    primary = document(db, audit, "generated.txt", text)
    source = document(db, audit, "approved.txt", text)
    other = make_audit(db)
    document(db, other, "generated.txt", text)
    foreign = document(db, other, "approved.txt", text)
    claim = extract_claims(db, primary)[0]
    def chunk(doc, quote): return RetrievedChunk(doc.id, "sentence", quote, 0, len(quote), 1, "supports")
    valid = chunk(source, text)
    rows = persist_evidence_for_claim(db, claim, [chunk(foreign, text), chunk(source, "Forged quote"), chunk(primary, text), valid, valid])
    assert len(rows) == 1 and rows[0].source_document_id == source.id
    document(db, audit, "generated.txt", "Warranty is valid for 24 months.")
    assert persist_evidence_for_claim(db, claim, [valid]) == []


def test_document_changes_invalidate_coverage_even_without_business_policies(db):
    from app.core.grounding import ground_claims
    from app.core.business_policies import evaluate_audit_policies, recorded_policy_results
    from app.core.trust_score import compute_score_breakdown
    audit = make_audit(db)
    text = "Warranty is valid for 12 months."
    primary = document(db, audit, "generated.txt", text)
    source = document(db, audit, "approved.txt", text)
    claim = extract_claims(db, primary)[0]
    db.add(Evidence(claim_id=claim.id, source_document_id=source.id, quote=text)); db.commit()
    ground_claims(db, audit.id)
    evaluate_audit_policies(db, audit.id)
    assert compute_score_breakdown(db, str(audit.id)).reviewed_score == 100
    document(db, audit, "new-source.txt", "Warranty is valid for 24 months.")
    assert recorded_policy_results(db, audit.id)["documents_changed"] is True
    result = compute_score_breakdown(db, str(audit.id))
    assert result.score_status == "insufficient_verification" and result.reviewed_score == 0
    assert result.coverage["grounded_claims"] == 0 and result.coverage["supported"] == 0
    assert result.sub_scores["factual_support"] is None and "document set changed" in result.score_limit_reason.lower()


def test_source_amendment_projects_stale_grounding_without_rewriting_history(client, db, superuser_token_headers):
    from app.core.grounding import ground_claims
    audit = make_audit(db)
    text = "Warranty is valid for 12 months."
    primary = document(db, audit, "generated.txt", text)
    source = document(db, audit, "approved.txt", text)
    claim = extract_claims(db, primary)[0]
    db.add(Evidence(claim_id=claim.id, source_document_id=source.id, quote=text)); db.commit()
    ground_claims(db, audit.id)
    db.refresh(claim)
    original_metadata = claim.metadata_json
    document(db, audit, "approved.txt", "Warranty is valid for 24 months.")
    response = client.get(f"/api/v1/audits/{audit.id}/claims", headers=superuser_token_headers)
    assert response.status_code == 200
    current = response.json()["data"][0]
    assert current["status"] == "uncertain" and current["evidence"] == []
    assert current["grounding"]["confidence"] == 0 and current["grounding"]["primary_evidence_id"] is None
    assert current["grounding"]["source_metadata"]["requires_reassessment"] is True
    db.refresh(claim)
    assert claim.metadata_json == original_metadata and claim.status == "supported"
