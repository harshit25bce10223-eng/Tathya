"""Golden regressions for measured source comparisons and honest score coverage."""
import uuid

import pytest
from sqlmodel import select

from app.core.source_verification import compare_quote


@pytest.mark.parametrize("claim,source,status", [
    ("Contract value is INR 50 lakh.", "Contract value is INR 41.6 lakh.", "contradicted"),
    ("Contract value is INR 1.2 crore.", "Contract value is INR 1,20,00,000.", "supported"),
    ("Payment is due within 30 days.", "Payment is due within 45 days.", "contradicted"),
    ("Warranty is valid for 5 years.", "Warranty is valid for 12 months.", "contradicted"),
    ("Warranty is valid for 1 year.", "Warranty is valid for 12 months.", "supported"),
    ("Delivery is on 15 December 2026.", "Delivery is on 22 December 2026.", "contradicted"),
    ("Contract value is INR 50 lakh.", "Liability is capped at INR 41.6 lakh.", None),
    ("Contract value is USD 50 lakh.", "Contract value is INR 50 lakh.", None),
])
def test_normalized_source_comparison(claim, source, status):
    assert compare_quote(claim, source) == status


def test_zero_claims_cannot_receive_perfect_trust(db):
    from app.models import Audit, User
    from app.core.trust_score import compute_score_breakdown
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="No claims regression", owner_id=owner.id)
    db.add(audit)
    db.commit()
    result = compute_score_breakdown(db, str(audit.id))
    assert result.score_status == "insufficient_verification"
    assert result.reviewed_score_band != "trustworthy"
    assert result.reviewed_score != 100
    assert result.coverage["checked_claims"] == 0
    assert result.sub_scores["factual_support"] is None


def test_golden_source_mismatches_reach_real_score(db, monkeypatch):
    from app.models import Audit, User, Claim, Document, Evidence
    from app.core.pipeline import ingest_document, save_upload
    from app.core.claims import extract_claims
    from app.core.grounding import ground_claims, emit_grounding_flags
    from app.core.trust_score import compute_score_breakdown
    from app.core.source_verification import field_hint
    from app.core.canonical import build_blocks, build_sentences
    owner = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit = Audit(title="Golden real scoring " + uuid.uuid4().hex, owner_id=owner.id)
    db.add(audit)
    db.commit()
    primary_text = "Contract value is INR 50 lakh.\nDelivery is on 15 December 2026.\nPayment is due within 30 days.\nWarranty is valid for 5 years."
    source_text = "Contract value is INR 41.6 lakh.\nDelivery is on 22 December 2026.\nPayment is due within 45 days.\nWarranty is valid for 12 months."
    primary = ingest_document(db, audit, filename="generated.txt", path=save_upload(audit.id, "generated.txt", primary_text.encode()))
    source = ingest_document(db, audit, filename="approval.txt", path=save_upload(audit.id, "approval.txt", source_text.encode()))
    assert primary.kind == "primary" and source.kind == "source"
    claims = extract_claims(db, primary)
    assert len(claims) == 4
    source_sentences = build_sentences(source.id, build_blocks(source.normalized_text), source.normalized_text)
    for claim in claims:
        quote = next(sentence.text for sentence in source_sentences if field_hint(sentence.text) == field_hint(claim.text))
        db.add(Evidence(claim_id=claim.id, source_document_id=source.id, quote=quote, support_type="unclassified", score=0))
    db.commit()
    outcomes = ground_claims(db, audit.id)
    assert len(outcomes) == 4 and all(item.status.value == "contradicted" for item in outcomes)
    flags = emit_grounding_flags(db, audit.id)
    assert len(flags) == 4
    score = compute_score_breakdown(db, str(audit.id))
    assert score.score_status == "assessed"
    assert score.coverage["contradicted"] == 4
    assert score.reviewed_score <= 49
    assert all(item.penalty > 0 for item in score.finding_contributions)
    assert score.sub_scores["factual_support"] == 0

    # A source amendment must replace old evidence/verdicts and change the score.
    updated = ingest_document(db, audit, filename="approval.txt", path=save_upload(audit.id, "approval.txt", primary_text.encode()))
    assert updated.kind == "source"
    db.refresh(source)
    assert not source.is_current
    from app.core.retrieval import retrieve_evidence_for_audit
    from app.core import retrieval
    def semantic_model_not_needed(*args, **kwargs):
        raise AssertionError("Deterministic comparisons must run before semantic models")
    monkeypatch.setattr(retrieval, "_encode", semantic_model_not_needed)
    monkeypatch.setattr(retrieval, "_reranker", semantic_model_not_needed)
    retrieve_evidence_for_audit(db, audit.id)
    outcomes = ground_claims(db, audit.id)
    assert all(item.status.value == "supported" for item in outcomes)
    emit_grounding_flags(db, audit.id)
    fresh = compute_score_breakdown(db, str(audit.id))
    assert fresh.total_findings == 0
    assert fresh.coverage["supported"] == 4
    assert fresh.reviewed_score == 100
    # Historical superseded findings must not leak into the newly signed passport.
    from app.core.canonical import source_set_hash
    from app.core.pipeline import issue_passport
    audit.source_set_hash = source_set_hash([primary.text_hash, updated.text_hash])
    db.add(audit)
    db.commit()
    passport = issue_passport(db, audit)
    assert "total=0" in passport.finding_summary and "open=0" in passport.finding_summary
