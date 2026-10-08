"""Audit API routes — Phase 1 contracts.

Flow: POST /audits -> queued -> processing -> completed | failed
Every claim/flag/document references document_version_id = documents.id.
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, ReviewerDep, SessionDep
from app.api.schemas import (
    AuditsPublic,
    AuditSummary,
    ClaimsWithGroundingPublic,
    ClaimWithGrounding,
    DecisionPublic,
    DecisionRequest,
    DocumentsPublic,
    EvidencePublic,
    FactsPublic,
    FlagsWithEvidencePublic,
    FlagWithEvidence,
    JobStatus,
    PassportPublic,
    RescoreResult,
    VerificationResult,
)
from app.core import security
from app.core.config import settings
from app.core.facts import get_facts_for_audit
from app.core.jobs import submit_audit_job
from app.core.pipeline import (
    append_chain_entry,
    ingest_document,
    save_upload,
    verify_passport_token,
)
from app.models import (
    Audit,
    AuditLogEntry,
    AuditPublic,
    Claim,
    Decision,
    Document,
    Evidence,
    Fact,
    Flag,
    Passport,
    User,
)

router = APIRouter(prefix="/audits", tags=["audits"])
verify_router = APIRouter(tags=["verification"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _get_audit(session: Session, audit_id: uuid.UUID, user: User) -> Audit:
    audit = session.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    if not user.is_superuser and user.role not in ("reviewer", "admin"):
        if audit.owner_id != user.id:
            raise HTTPException(status_code=404, detail="Audit not found")
    return audit


def _public(audit: Audit) -> AuditPublic:
    return AuditPublic(
        id=audit.id,
        owner_id=audit.owner_id,
        status=audit.status,
        title=audit.title,
        error_message=audit.error_message,
        failed_stage=audit.failed_stage,
        source_set_hash=audit.source_set_hash,
        created_at=audit.created_at,
        updated_at=audit.updated_at,
    )


def _recompute_source_set_hash(session: Session, audit_id: uuid.UUID) -> str | None:
    from app.core.canonical import source_set_hash

    hashes = session.exec(
        select(Document.text_hash).where(Document.audit_id == audit_id)
    ).all()
    if not hashes:
        return None
    digest = source_set_hash(list(hashes))
    audit = session.get(Audit, audit_id)
    if audit is not None:
        audit.source_set_hash = digest
        session.add(audit)
        session.commit()
    return digest


async def _ingest_uploads(
    session: Session, audit: Audit, files: list[UploadFile]
) -> list[Document]:
    documents: list[Document] = []
    for upload in files:
        filename = upload.filename or "upload.bin"
        data = await upload.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{filename} exceeds {MAX_UPLOAD_BYTES} bytes",
            )
        if not data:
            raise HTTPException(status_code=400, detail=f"{filename} is empty")
        path = save_upload(audit.id, filename, data)
        documents.append(
            ingest_document(
                session,
                audit,
                filename=filename,
                path=path,
                mime_type=upload.content_type,
            )
        )
    return documents


def _job_status(audit: Audit) -> JobStatus:
    return JobStatus(
        audit_id=audit.id,
        status=audit.status,
        failed_stage=audit.failed_stage,
        error_message=audit.error_message,
        source_set_hash=audit.source_set_hash,
    )


# ---------------------------------------------------------------------------
# Create / list / get
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AuditPublic)
async def create_audit(
    session: SessionDep,
    current_user: CurrentUser,
    title: Annotated[str, Form()] = "Untitled audit",
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> AuditPublic:
    """Create an audit, ingest any uploaded documents, enqueue the job."""
    audit = Audit(title=title, owner_id=current_user.id, status="queued")
    session.add(audit)
    session.commit()
    session.refresh(audit)

    if files:
        await _ingest_uploads(session, audit, files)
    _recompute_source_set_hash(session, audit.id)
    submit_audit_job(audit.id)
    session.refresh(audit)
    return _public(audit)


@router.get("", response_model=AuditsPublic)
def list_audits(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> AuditsPublic:
    statement = select(Audit).order_by(Audit.created_at.desc())  # type: ignore[attr-defined]
    if not current_user.is_superuser and current_user.role not in (
        "reviewer",
        "admin",
    ):
        statement = statement.where(Audit.owner_id == current_user.id)
    audits = session.exec(statement.offset(skip).limit(limit)).all()
    return AuditsPublic(data=[_public(a) for a in audits], count=len(audits))


@router.get("/{audit_id}", response_model=AuditSummary)
def get_audit(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> AuditSummary:
    audit = _get_audit(session, audit_id, current_user)
    document_count = session.exec(
        select(func.count()).select_from(Document).where(Document.audit_id == audit_id)
    ).one()
    flag_rows = session.exec(
        select(Flag.status, func.count())
        .where(Flag.audit_id == audit_id)
        .group_by(Flag.status)
    ).all()
    flag_count = sum(c for _, c in flag_rows)
    open_count = sum(c for s, c in flag_rows if s in ("pending", "open"))
    claim_count = session.exec(
        select(func.count()).select_from(Claim).where(Claim.audit_id == audit_id)
    ).one()
    fact_count = session.exec(
        select(func.count())
        .select_from(Fact)
        .where(
            Fact.document_id.in_(
                select(Document.id).where(Document.audit_id == audit_id)
            )
        )
    ).one()
    passport = session.exec(
        select(Passport).where(Passport.audit_id == audit_id)
    ).first()
    return AuditSummary(
        audit=_public(audit),
        document_count=int(document_count),
        flag_count=int(flag_count),
        open_flag_count=int(open_count),
        claim_count=int(claim_count),
        fact_count=int(fact_count),
        passport=passport,
        verify_token=passport.verify_token if passport else None,
    )


@router.get("/{audit_id}/status", response_model=JobStatus)
def audit_job_status(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> JobStatus:
    return _job_status(_get_audit(session, audit_id, current_user))


# ---------------------------------------------------------------------------
# Documents (document_version_id == documents.id)
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/documents", response_model=DocumentsPublic)
def list_documents(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> DocumentsPublic:
    _get_audit(session, audit_id, current_user)
    documents = session.exec(
        select(Document)
        .where(Document.audit_id == audit_id)
        .order_by(Document.created_at)  # type: ignore[attr-defined]
    ).all()
    return DocumentsPublic(data=documents, count=len(documents))


@router.post("/{audit_id}/documents", response_model=DocumentsPublic)
async def upload_documents(
    audit_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    files: Annotated[list[UploadFile], File()],
) -> DocumentsPublic:
    audit = _get_audit(session, audit_id, current_user)
    await _ingest_uploads(session, audit, files)
    _recompute_source_set_hash(session, audit_id)
    submit_audit_job(audit.id)
    all_docs = session.exec(select(Document).where(Document.audit_id == audit_id)).all()
    return DocumentsPublic(data=all_docs, count=len(all_docs))


@router.post("/{audit_id}/run", response_model=JobStatus)
def run_audit(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> JobStatus:
    audit = _get_audit(session, audit_id, current_user)
    if audit.status == "processing":
        raise HTTPException(status_code=409, detail="Audit is already processing")
    audit.status = "queued"
    audit.error_message = None
    audit.failed_stage = None
    session.add(audit)
    session.commit()
    submit_audit_job(audit.id)
    return _job_status(audit)


# ---------------------------------------------------------------------------
# Facts (Phase 3)
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/facts", response_model=FactsPublic)
def list_facts(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> FactsPublic:
    _get_audit(session, audit_id, current_user)
    facts = get_facts_for_audit(session, audit_id)
    return FactsPublic(data=facts, count=len(facts))


# ---------------------------------------------------------------------------
# Claims with grounding (Phase 3)
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/claims", response_model=ClaimsWithGroundingPublic)
def list_claims_with_grounding(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> ClaimsWithGroundingPublic:
    _get_audit(session, audit_id, current_user)
    claims = session.exec(
        select(Claim).where(Claim.audit_id == audit_id).order_by(Claim.created_at)  # type: ignore[attr-defined]
    ).all()

    enriched_claims = []
    for claim in claims:
        # Get evidence for this claim
        evidence = session.exec(
            select(Evidence).where(Evidence.claim_id == claim.id)
        ).all()

        # Parse grounding from metadata
        grounding = None
        try:
            meta = json.loads(claim.metadata_json or "{}")
            g = meta.get("grounding")
            if g:
                from app.api.schemas import GroundingDetail

                grounding = GroundingDetail(**g)
        except Exception:
            pass

        enriched_claims.append(
            ClaimWithGrounding(
                id=claim.id,
                audit_id=claim.audit_id,
                document_id=claim.document_id,
                sentence_id=claim.sentence_id,
                text=claim.text,
                category=claim.category,
                status=claim.status,
                metadata_json=claim.metadata_json,
                created_at=claim.created_at,
                grounding=grounding,
                evidence=evidence,
            )
        )

    return ClaimsWithGroundingPublic(data=enriched_claims, count=len(enriched_claims))


# ---------------------------------------------------------------------------
# Evidence (Phase 3)
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/evidence", response_model=EvidencePublic)
def list_evidence(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> EvidencePublic:
    _get_audit(session, audit_id, current_user)
    # Get all claim IDs for this audit
    claim_ids = session.exec(select(Claim.id).where(Claim.audit_id == audit_id)).all()

    if not claim_ids:
        return EvidencePublic(data=[], count=0)

    evidence = session.exec(
        select(Evidence).where(Evidence.claim_id.in_(claim_ids))
    ).all()
    return EvidencePublic(data=evidence, count=len(evidence))


# ---------------------------------------------------------------------------
# Flags + decisions (reviewer workflow)
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/flags", response_model=FlagsWithEvidencePublic)
def list_flags(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> FlagsWithEvidencePublic:
    _get_audit(session, audit_id, current_user)
    flags = session.exec(
        select(Flag).where(Flag.audit_id == audit_id).order_by(Flag.created_at)  # type: ignore[attr-defined]
    ).all()

    enriched_flags = []
    for flag in flags:
        # Get evidence for this flag's claim (if any)
        evidence = []
        if flag.claim_id:
            evidence = session.exec(
                select(Evidence).where(Evidence.claim_id == flag.claim_id)
            ).all()

        # Get claim text
        claim_text = None
        if flag.claim_id:
            claim = session.get(Claim, flag.claim_id)
            if claim:
                claim_text = claim.text

        enriched_flags.append(
            FlagWithEvidence(
                id=flag.id,
                audit_id=flag.audit_id,
                document_id=flag.document_id,
                claim_id=flag.claim_id,
                type=flag.type,
                severity=flag.severity,
                materiality=flag.materiality,
                reason=flag.reason,
                suggested_fix=flag.suggested_fix,
                status=flag.status,
                reviewer_note=flag.reviewer_note,
                impact_score=flag.impact_score,
                sentence_id=flag.sentence_id,
                location_json=flag.location_json,
                created_at=flag.created_at,
                evidence=evidence,
                claim_text=claim_text,
            )
        )

    return FlagsWithEvidencePublic(data=enriched_flags, count=len(enriched_flags))


@router.post("/{audit_id}/flags/{flag_id}/decision", response_model=DecisionPublic)
def submit_decision(
    audit_id: uuid.UUID,
    flag_id: uuid.UUID,
    body: DecisionRequest,
    session: SessionDep,
    reviewer: ReviewerDep,
) -> Decision:
    audit = _get_audit(session, audit_id, reviewer)
    flag = session.get(Flag, flag_id)
    if flag is None or flag.audit_id != audit_id or flag.audit_id != audit.id:
        raise HTTPException(status_code=404, detail="Flag not found")

    decision = Decision(
        audit_id=audit_id,
        flag_id=flag_id,
        actor_id=reviewer.id,
        action=body.action,
        note=body.note,
    )
    session.add(decision)

    flag.status = {"accept": "accepted", "dismiss": "dismissed", "fix": "fixed"}[
        body.action
    ]
    if body.note:
        flag.reviewer_note = body.note
    session.add(flag)
    session.commit()
    session.refresh(decision)

    append_chain_entry(
        session,
        audit_id=audit_id,
        actor_id=reviewer.id,
        action="flag.decision",
        payload_json=_canonical_json(
            {
                "flag_id": str(flag_id),
                "decision_id": str(decision.id),
                "action": body.action,
            }
        ),
    )
    return decision


@router.post("/{audit_id}/rescore", response_model=RescoreResult)
def rescore_audit(
    audit_id: uuid.UUID, session: SessionDep, reviewer: ReviewerDep
) -> RescoreResult:
    audit = _get_audit(session, audit_id, reviewer)
    flags = session.exec(select(Flag).where(Flag.audit_id == audit_id)).all()
    open_flags = [f for f in flags if f.status in ("pending", "accepted")]
    penalty = sum(max(0.0, f.impact_score) for f in open_flags)
    trust_score = max(0.0, round(100.0 - penalty, 2))

    passport = session.exec(
        select(Passport).where(Passport.audit_id == audit_id)
    ).first()
    if passport is not None:
        passport.trust_score = trust_score
        session.add(passport)
        session.commit()
        session.refresh(passport)

    append_chain_entry(
        session,
        audit_id=audit_id,
        actor_id=reviewer.id,
        action="audit.rescored",
        payload_json=_canonical_json(
            {"trust_score": trust_score, "open_flags": len(open_flags)}
        ),
    )
    return RescoreResult(
        audit=_public(audit),
        trust_score=trust_score,
        flag_count=len(flags),
        open_flag_count=len(open_flags),
    )


# ---------------------------------------------------------------------------
# Passport
# ---------------------------------------------------------------------------


@router.get("/{audit_id}/passport", response_model=PassportPublic)
def get_passport(
    audit_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Passport:
    _get_audit(session, audit_id, current_user)
    passport = session.exec(
        select(Passport).where(Passport.audit_id == audit_id)
    ).first()
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport not issued yet")
    return passport


# ---------------------------------------------------------------------------
# Public verification (no auth, never exposes the audit id)
# ---------------------------------------------------------------------------


@verify_router.get("/verify/{verify_token}", response_model=VerificationResult)
def verify_passport(verify_token: str, session: SessionDep) -> VerificationResult:
    resolved = verify_passport_token(session, verify_token)
    if resolved is None:
        return VerificationResult(
            found=False,
            verify_token=verify_token,
            status="NOT_FOUND",
            trust_score=0.0,
            detail="Unknown verify token",
        )
    passport, audit, chain_ok, chain_reason = resolved

    document_count = int(
        session.exec(
            select(func.count())
            .select_from(Document)
            .where(Document.audit_id == audit.id)
        ).one()
    )
    entry_count = int(
        session.exec(
            select(func.count())
            .select_from(AuditLogEntry)
            .where(AuditLogEntry.audit_id == audit.id)
        ).one()
    )

    signature_valid: bool | None = None
    try:
        _, public_pem = security.ensure_keypair(
            settings.ECDSA_PRIVATE_KEY_PATH, settings.ECDSA_PUBLIC_KEY_PATH
        )
        message = f"{passport.document_hash}:{passport.chain_head}".encode()
        signature_valid = security.verify_signature(
            public_pem, message, passport.signature
        )
    except Exception:  # noqa: BLE001
        signature_valid = None

    base = str(settings.PUBLIC_BASE_URL).rstrip("/")
    return VerificationResult(
        found=True,
        verify_token=passport.verify_token,
        status=passport.status,
        trust_score=passport.trust_score,
        issued_at=passport.issued_at,
        document_count=document_count,
        document_hash=passport.document_hash,
        chain={"ok": chain_ok, "reason": chain_reason, "entry_count": entry_count},
        signature_valid=signature_valid,
        verify_url=f"{base}/verify/{passport.verify_token}",
    )


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
