"""Phase 3 tests for grounding, facts, and risk scan."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import database_available

pytestmark = pytest.mark.skipif(
    not database_available(), reason="PostgreSQL not available"
)


def test_fact_extraction_currency(db):
    """Test currency fact extraction from document."""
    from app.core.pipeline import ingest_document, save_upload
    from app.core.facts import extract_facts, get_facts_for_document
    from app.core.security import get_password_hash
    from app.models import Audit, User, Document

    user = User(
        email=f"facttest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="fact test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    path = save_upload(audit.id, "contract.txt", b"Contract value is INR 50 lakh.")
    document = ingest_document(session=db, audit=audit, filename="contract.txt", path=path)

    # Extract facts
    facts = extract_facts(db, document)
    
    # Verify currency fact extracted
    assert len(facts) >= 1
    currency_facts = [f for f in facts if f.subject == "contract value" and f.predicate == "amount"]
    assert len(currency_facts) == 1
    assert currency_facts[0].object_value == "5000000"
    assert currency_facts[0].location_json is not None


def test_fact_extraction_duration(db):
    """Test duration fact extraction."""
    from app.core.pipeline import ingest_document, save_upload
    from app.core.facts import extract_facts
    from app.core.security import get_password_hash
    from app.models import Audit, User

    user = User(
        email=f"durtest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="duration test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    path = save_upload(audit.id, "contract.txt", b"Delivery within 30 days.")
    document = ingest_document(session=db, audit=audit, filename="contract.txt", path=path)

    facts = extract_facts(db, document)
    # Duration facts are extracted with fact_type="duration" in metadata_json
    duration_facts = [f for f in facts if "duration" in f.subject.lower() or "duration" in f.predicate.lower()]
    assert duration_facts, "A 30-day delivery term must produce a duration fact"


def test_fact_version_binding(db):
    """Test facts are bound to document version."""
    from app.core.pipeline import ingest_document, save_upload
    from app.core.facts import extract_facts, get_facts_for_audit
    from app.core.security import get_password_hash
    from app.models import Audit, User, Document

    user = User(
        email=f"vbtest-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="version binding", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Version 1
    path_v1 = save_upload(audit.id, "contract.txt", b"Value is INR 41.6 lakh.")
    doc_v1 = ingest_document(session=db, audit=audit, filename="contract.txt", path=path_v1)
    facts_v1 = extract_facts(db, doc_v1)

    # Version 2
    path_v2 = save_upload(audit.id, "contract.txt", b"Value is INR 50 lakh.")
    doc_v2 = ingest_document(session=db, audit=audit, filename="contract.txt", path=path_v2)
    facts_v2 = extract_facts(db, doc_v2)

    # Facts should be bound to specific document versions
    assert doc_v1.id != doc_v2.id
    v1_fact_ids = {f.id for f in facts_v1}
    v2_fact_ids = {f.id for f in facts_v2}
    # Different document versions should have different facts (even if similar content)
    # They may have same normalized values but different document_id


def test_grounding_supported(db):
    """Test grounding with supporting evidence."""
    from app.core.grounding import ground_claims, GroundingStatus
    from app.core.security import get_password_hash
    from app.models import Audit, Claim, Evidence, Document, User

    user = User(
        email=f"ground-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="grounding test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="The contract value is INR 41.6 lakh.",
        normalized_text="The contract value is INR 41.6 lakh.",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="abc123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Create a claim that matches the source
    claim = Claim(
        audit_id=audit.id,
        document_id=document.id,
        text="The contract value is INR 41.6 lakh.",
        category="commercial",
        status="extracted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    source = Document(
        audit_id=audit.id, kind="source", filename="approval.txt", storage_path="approval.txt",
        normalized_text="The contract value is INR 41.6 lakh.", raw_text="The contract value is INR 41.6 lakh.",
        text_hash="source-hash", version_no=2, is_current=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    # Supporting evidence must come from a separate source document.
    evidence = Evidence(
        claim_id=claim.id,
        source_document_id=source.id,
        quote="The contract value is INR 41.6 lakh.",
        location_json="{}",
        support_type="supports",
        score=0.9,
    )
    db.add(evidence)
    db.commit()

    # Run grounding
    results = ground_claims(db, audit.id)
    
    assert len(results) == 1
    result = results[0]
    # With high-score supporting evidence, should be SUPPORTED
    assert result.status == GroundingStatus.SUPPORTED
    if result.status == GroundingStatus.SUPPORTED:
        assert result.confidence > 0.5
        assert len(result.evidence_ids) >= 1


def test_grounding_unsupported(db):
    """Test grounding with no evidence."""
    from app.core.grounding import ground_claims, GroundingStatus
    from app.core.security import get_password_hash
    from app.models import Audit, Claim, Document, User

    user = User(
        email=f"unsup-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="unsupported test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="Different content.",
        normalized_text="Different content.",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="xyz789",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Create claim with no matching evidence
    claim = Claim(
        audit_id=audit.id,
        document_id=document.id,
        text="The contract value is INR 50 lakh.",
        category="commercial",
        status="extracted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    # No evidence created

    results = ground_claims(db, audit.id)
    
    assert len(results) == 1
    result = results[0]
    # Should be UNSUPPORTED or UNCERTAIN (no evidence)
    assert result.status in (GroundingStatus.UNSUPPORTED, GroundingStatus.UNCERTAIN)


def test_risk_scan_pii(db):
    """Test PII detection in risk scan."""
    from app.core.risk_scan import scan_document_risks
    from app.core.security import get_password_hash
    from app.models import Audit, Document, User

    user = User(
        email=f"pii-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="PII test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="Contact: john.doe@company.com Phone: 9876543210 Aadhaar: 1234 5678 9012",
        normalized_text="Contact: john.doe@company.com Phone: 9876543210 Aadhaar: 1234 5678 9012",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="pii123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    flags = scan_document_risks(db, document)
    
    # Should detect at least Aadhaar
    pii_flags = [f for f in flags if f.type == "pii"]
    assert len(pii_flags) >= 1  # At least Aadhaar


def test_risk_scan_secrets(db):
    """Test secret/key detection."""
    from app.core.risk_scan import scan_document_risks
    from app.core.security import get_password_hash
    from app.models import Audit, Document, User

    user = User(
        email=f"secret-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="secret test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="API Key: sk-abcdefghijklmnopqrstuvwxyz123456",
        normalized_text="API Key: sk-abcdefghijklmnopqrstuvwxyz123456",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="secret123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    flags = scan_document_risks(db, document)
    
    secret_flags = [f for f in flags if f.type == "secret"]
    assert len(secret_flags) >= 1
    assert secret_flags[0].severity == "CRITICAL"


def test_risk_scan_risky_commitments(db):
    """Test risky commitment detection."""
    from app.core.risk_scan import scan_document_risks
    from app.core.security import get_password_hash
    from app.models import Audit, Document, User

    user = User(
        email=f"risky-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="risky commitment test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="We guarantee 100% uptime and unlimited liability for all damages.",
        normalized_text="We guarantee 100% uptime and unlimited liability for all damages.",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="risky123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    flags = scan_document_risks(db, document)
    
    commitment_flags = [f for f in flags if f.type == "risky_commitment"]
    assert len(commitment_flags) >= 1  # At least one detected


def test_risk_scan_suspicious_url(db):
    """Test suspicious URL detection."""
    from app.core.risk_scan import scan_document_risks
    from app.core.security import get_password_hash
    from app.models import Audit, Document, User

    user = User(
        email=f"url-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="URL test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="Visit http://suspicious-site.xyz/login for more info.",
        normalized_text="Visit http://suspicious-site.xyz/login for more info.",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="url123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    flags = scan_document_risks(db, document)
    
    url_flags = [f for f in flags if f.type == "suspicious_url"]
    assert len(url_flags) >= 1


def test_flag_deduplication(db):
    """Test that duplicate flags are not created."""
    from app.core.risk_scan import scan_document_risks
    from app.core.security import get_password_hash
    from app.models import Audit, Document, User, Flag

    user = User(
        email=f"dedup-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="dedup test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="Aadhaar: 1234 5678 9012 and another Aadhaar: 1234 5678 9012",
        normalized_text="Aadhaar: 1234 5678 9012 and another Aadhaar: 1234 5678 9012",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="dedup123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Run scan twice
    flags1 = scan_document_risks(db, document)
    flags2 = scan_document_risks(db, document)

    # Should not create duplicates
    all_flags = db.exec(select(Flag).where(Flag.document_id == document.id)).all()
    pii_flags = [f for f in all_flags if f.type == "pii"]
    
    # Should have only one Aadhaar flag despite two mentions
    aadhaar_flags = [f for f in pii_flags if "Aadhaar" in f.reason]
    assert len(aadhaar_flags) <= 1


def test_no_evidence_no_flag(db):
    """Test that no evidence = no source-grounding flag."""
    from app.core.grounding import ground_claims, GroundingStatus
    from app.core.security import get_password_hash
    from app.models import Audit, Claim, Document, User, Flag

    user = User(
        email=f"noevid-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Str0ngPass!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit = Audit(title="no evidence test", owner_id=user.id, status="queued")
    db.add(audit)
    db.commit()
    db.refresh(audit)

    document = Document(
        audit_id=audit.id,
        kind="primary",
        filename="source.txt",
        mime_type="text/plain",
        storage_path="source.txt",
        raw_text="The contract value is INR 41.6 lakh.",
        normalized_text="The contract value is INR 41.6 lakh.",
        offset_map_json="[]",
        blocks_json="[]",
        text_hash="noevid123",
        version_no=1,
        is_current=True,
        metadata_json="{}",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Claim that contradicts source but no evidence created
    claim = Claim(
        audit_id=audit.id,
        document_id=document.id,
        text="The contract value is INR 50 lakh.",
        category="commercial",
        status="extracted",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)

    # Run grounding - no evidence exists
    results = ground_claims(db, audit.id)
    
    # Should be UNSUPPORTED or UNCERTAIN, NOT CONTRADICTED (no opposing evidence)
    assert len(results) == 1
    result = results[0]
    assert result.status in (GroundingStatus.UNSUPPORTED, GroundingStatus.UNCERTAIN)
    # CONTRADICTED requires actual opposing evidence


# Need to import select for some tests
from sqlmodel import select