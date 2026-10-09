"""Phase 1-3 audit pipeline.

Stages (persisted as audits.failed_stage on error):
    ingest         - parse + canonicalize every document of the audit
    canonical      - deterministic sentence/offset validation
    extract_facts  - structured fact extraction from documents
    grounding      - claim verification against evidence
    risk_scan      - deterministic risk detection (PII, secrets, URLs, commitments)
    hash_chain     - source_set_hash + chained audit_log entry
    passport       - issue ECDSA-signed passport with public verify token

No trust-core scoring here (later phases).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, func, select

from app.core.canonical import (
    build_blocks,
    build_sentences,
    normalize_text,
    source_set_hash,
    text_hash,
)
from app.core.claims import extract_claims_for_audit
from app.core.config import settings
from app.core.facts import extract_facts
from app.core.grounding import emit_grounding_flags, ground_claims
from app.core.retrieval import retrieve_evidence_for_audit
from app.core.jobs import StageError, StageTracker
from app.core.parsers import ParserError
from app.core.parse_worker import parse_bounded
from app.core.risk_scan import scan_audit_risks
from app.core.security import (
    GENESIS_HASH,
    compute_entry_hash,
    ensure_keypair,
    generate_verify_token,
    sign_message,
)
from app.core.trust_score import compute_score_breakdown, persist_scores
from app.models import Audit, AuditLogEntry, Document, Flag, Passport

logger = logging.getLogger("tathya.pipeline")


# ---------------------------------------------------------------------------
# Document ingest (used by upload routes and the ingest stage)
# ---------------------------------------------------------------------------


def _storage_root(audit_id: uuid.UUID) -> Path:
    return Path(settings.STORAGE_DIR).expanduser().resolve() / str(audit_id)


def save_upload(audit_id: uuid.UUID, filename: str, data: bytes) -> Path:
    directory = _storage_root(audit_id)
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or "upload.bin"
    path = directory / f"{uuid.uuid4().hex}_{safe_name}"
    path.write_bytes(data)
    return path


def next_version_no(session: Session, audit_id: uuid.UUID) -> int:
    current = session.exec(
        select(func.count()).select_from(Document).where(Document.audit_id == audit_id)
    ).one()
    return int(current) + 1


def _demote_previous_versions(
    session: Session, audit_id: uuid.UUID, filename: str
) -> None:
    rows = session.exec(
        select(Document).where(
            Document.audit_id == audit_id,
            Document.filename == filename,
            Document.is_current.is_(True),
        )
    ).all()
    for row in rows:
        row.is_current = False
        session.add(row)


def ingest_document(
    session: Session,
    audit: Audit,
    *,
    filename: str,
    path: Path,
    mime_type: str | None = None,
    commit: bool = True,
) -> Document:
    """Parse a stored file and create one immutable document version row."""
    try:
        parsed = parse_bounded(path, filename=filename)
    except ParserError as exc:
        raise StageError("ingest", str(exc)) from exc

    normalized, segments = normalize_text(parsed.raw_text)
    blocks = build_blocks(normalized)
    digest = text_hash(normalized)

    previous_kind = session.exec(select(Document.kind).where(Document.audit_id == audit.id, Document.filename == filename, Document.is_current.is_(True))).first()
    _demote_previous_versions(session, audit.id, filename)
    version_no = next_version_no(session, audit.id)

    try:
        relative_path = str(
            path.resolve().relative_to(
                Path(settings.STORAGE_DIR).expanduser().resolve()
            )
        )
    except ValueError:
        relative_path = str(path.resolve())

    current_kinds = session.exec(
        select(Document.kind).where(
            Document.audit_id == audit.id,
            Document.is_current.is_(True),
        )
    ).all()
    kind = previous_kind or ("primary" if "primary" not in current_kinds else "source")

    document = Document(
        audit_id=audit.id,
        kind=kind,
        filename=filename,
        mime_type=mime_type or parsed.mime_type,
        storage_path=relative_path,
        raw_text=parsed.raw_text,
        normalized_text=normalized,
        offset_map_json=json.dumps(segments, ensure_ascii=False),
        blocks_json=json.dumps([b.to_dict() for b in blocks], ensure_ascii=False),
        text_hash=digest,
        version_no=version_no,
        is_current=True,
        metadata_json=json.dumps(
            {
                "format": parsed.format,
                "parser_metadata": parsed.metadata,
                "locations": parsed.locations_json(),
            },
            ensure_ascii=False,
        ),
    )
    session.add(document)
    session.flush()
    if commit:
        session.commit()
    session.refresh(document)
    return document


# ---------------------------------------------------------------------------
# Audit pipeline
# ---------------------------------------------------------------------------


def run_audit_pipeline(
    session: Session, audit_id: uuid.UUID, tracker: StageTracker
) -> None:
    audit = session.get(Audit, audit_id)
    if audit is None:
        raise StageError("ingest", "audit disappeared")

    # ---- ingest ---------------------------------------------------------
    tracker.set("ingest")
    documents = session.exec(
        select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))
    ).all()
    for document in documents:
        if document.normalized_text:
            continue
        path = Path(settings.STORAGE_DIR).expanduser().resolve() / document.storage_path
        if not path.is_file():
            raise StageError("ingest", f"missing stored file: {document.filename}")
        try:
            parsed = parse_bounded(path, filename=document.filename)
        except ParserError as exc:
            raise StageError("ingest", str(exc)) from exc
        normalized, segments = normalize_text(parsed.raw_text)
        blocks = build_blocks(normalized)
        document.raw_text = parsed.raw_text
        document.normalized_text = normalized
        document.offset_map_json = json.dumps(segments, ensure_ascii=False)
        document.blocks_json = json.dumps(
            [b.to_dict() for b in blocks], ensure_ascii=False
        )
        document.text_hash = text_hash(normalized)
        session.add(document)
    session.commit()

    # ---- canonical validation ------------------------------------------
    tracker.set("canonical")
    documents = session.exec(
        select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))
    ).all()
    if not documents:
        raise StageError("canonical", "audit has no documents")
    for document in documents:
        blocks = build_blocks(document.normalized_text)
        sentences = build_sentences(document.id, blocks, document.normalized_text)
        for sentence in sentences:
            if len(sentence.sentence_id) != 64:
                raise StageError("canonical", "invalid sentence id produced")

    # ---- extract facts --------------------------------------------------
    tracker.set("extract_facts")
    documents = session.exec(
        select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))
    ).all()
    for document in documents:
        try:
            extract_facts(session, document)
        except Exception as exc:
            logger.exception("fact extraction failed for document %s", document.id)
            raise StageError("extract_facts", f"fact extraction failed: {exc}") from exc
    session.commit()

    # ---- extract claims -------------------------------------------------
    tracker.set("extract_claims")
    try:
        extract_claims_for_audit(session, audit_id)
    except Exception as exc:
        logger.exception("claim extraction failed for audit %s", audit_id)
        raise StageError("extract_claims", f"claim extraction failed: {exc}") from exc
    session.commit()

    # ---- retrieve evidence ----------------------------------------------
    tracker.set("retrieve")
    try:
        retrieve_evidence_for_audit(session, audit_id)
    except Exception as exc:
        logger.exception("retrieval failed for audit %s", audit_id)
        raise StageError("retrieve", f"retrieval failed: {exc}") from exc
    session.commit()

    # ---- grounding ------------------------------------------------------
    tracker.set("grounding")
    try:
        ground_claims(session, audit_id)
        emit_grounding_flags(session, audit_id)
    except Exception as exc:
        logger.exception("grounding failed for audit %s", audit_id)
        raise StageError("grounding", f"grounding failed: {exc}") from exc
    session.commit()

    # ---- risk scan ------------------------------------------------------
    tracker.set("risk_scan")
    try:
        scan_audit_risks(session, audit_id)
    except Exception as exc:
        logger.exception("risk scan failed for audit %s", audit_id)
        raise StageError("risk_scan", f"risk scan failed: {exc}") from exc
    session.commit()

    # ---- hash chain -----------------------------------------------------
    tracker.set("policy_check")
    try:
        from app.core.business_policies import evaluate_audit_policies
        evaluate_audit_policies(session, audit_id)
    except Exception as exc:
        logger.exception("policy evaluation failed for audit %s", audit_id)
        raise StageError("policy_check", f"policy evaluation failed: {exc}") from exc

    tracker.set("hash_chain")
    hashes = [d.text_hash for d in documents]
    audit.source_set_hash = source_set_hash(hashes)
    session.add(audit)
    session.commit()
    append_chain_entry(
        session,
        audit_id=audit.id,
        actor_id=audit.owner_id,
        action="audit.completed",
        payload_json=json.dumps(
            {
                "source_set_hash": audit.source_set_hash,
                "document_count": len(documents),
                "text_hashes": sorted(hashes),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    )

    # ---- passport -------------------------------------------------------
    tracker.set("passport")
    issue_passport(session, audit)


def _last_chain_hash(session: Session, audit_id: uuid.UUID) -> str:
    entry = session.exec(
        select(AuditLogEntry)
        .where(AuditLogEntry.audit_id == audit_id)
        .order_by(AuditLogEntry.created_at.desc())  # type: ignore[attr-defined]
    ).first()
    if entry is None:
        return GENESIS_HASH
    return entry.hash


def append_chain_entry(
    session: Session,
    *,
    audit_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    payload_json: str,
    commit: bool = True,
) -> AuditLogEntry:
    session.exec(select(Audit).where(Audit.id == audit_id).with_for_update()).one()
    previous_hash = _last_chain_hash(session, audit_id)
    entry_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    digest = compute_entry_hash(
        entry_id=entry_id,
        audit_id=audit_id,
        actor_id=actor_id,
        action=action,
        payload_json=payload_json,
        created_at=created_at,
        previous_hash=previous_hash,
    )
    entry = AuditLogEntry(
        id=entry_id,
        audit_id=audit_id,
        actor_id=actor_id,
        action=action,
        payload_json=payload_json,
        previous_hash=previous_hash,
        hash=digest,
        created_at=created_at,
    )
    session.add(entry)
    if commit:
        session.commit()
        session.refresh(entry)
    else:
        session.flush()
    return entry


def issue_passport(session: Session, audit: Audit) -> Passport:
    """Create (or return) the audit passport.

    Passport fields (locked):
        verify_token: 8-12 char URL-safe unique, public QR = /verify/{token}
        document_hash = source_set_hash
        chain_head = latest audit_log hash
        signature = ECDSA P-256 over document_hash + chain_head
    """
    existing = session.exec(
        select(Passport).where(Passport.audit_id == audit.id)
    ).first()
    if not audit.source_set_hash:
        raise StageError("passport", "source_set_hash missing before passport issue")

    # Capture identity before any commit expires the row.
    audit_id = audit.id
    try:
        breakdown = compute_score_breakdown(session, str(audit.id))
        persist_scores(session, audit, breakdown)
        session.commit()
        session.refresh(audit)
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("passport score computation failed for audit %s", audit_id)
        raise StageError("passport", f"score computation failed: {exc}") from exc

    chain_head = _last_chain_hash(session, audit.id)
    private_pem, _ = ensure_keypair(
        settings.ECDSA_PRIVATE_KEY_PATH, settings.ECDSA_PUBLIC_KEY_PATH
    )
    message = f"{audit.source_set_hash}:{chain_head}".encode()
    signature = sign_message(private_pem, message)

    # Build finding summary (consistent with audits.py create_passport helper)
    flags = session.exec(select(Flag).join(Document, Document.id == Flag.document_id).where(Flag.audit_id == audit.id, Document.is_current.is_(True), Flag.status != "superseded")).all()
    severity_counts: dict[str, int] = {}
    for f in flags:
        sev = (f.severity or "MEDIUM").upper()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    open_flags = [f for f in flags if f.status in ("pending", "accepted")]
    reviewed_score = float(getattr(audit, "reviewed_score") or 0.0)
    parts = [
        f"total={len(flags)}",
        f"open={len(open_flags)}",
        f"score={reviewed_score:.1f}",
    ]
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if sev in severity_counts:
            parts.append(f"{sev.lower()}={severity_counts[sev]}")
    finding_summary = "; ".join(parts)
    if len(finding_summary) > 500:
        finding_summary = finding_summary[:497] + "..."

    # Passport trust_score authoritative value = reviewed_score (after reviewer decisions)
    trust_score = reviewed_score
    ai_score = float(getattr(audit, "ai_score") or 0.0)
    score_band = str(getattr(audit, "score_band") or "trustworthy")
    critical_risk = bool(getattr(audit, "critical_risk") or False)
    review_status = str(getattr(audit, "review_status") or "pending")

    token = existing.verify_token if existing else _unique_token(session)
    passport = Passport(
        audit_id=audit.id,
        verify_token=token,
        document_hash=audit.source_set_hash,
        chain_head=chain_head,
        signature=signature,
        trust_score=trust_score,
        status="VERIFIED",
        ai_score=ai_score,
        reviewed_score=reviewed_score,
        score_band=score_band,
        critical_risk=critical_risk,
        finding_summary=finding_summary,
        review_status=review_status,
        revision=(existing.revision + 1) if existing else 1,
    )
    if existing:
        for field_name in ("document_hash", "chain_head", "signature", "trust_score", "status", "ai_score", "reviewed_score", "score_band", "critical_risk", "finding_summary", "review_status", "revision"):
            setattr(existing, field_name, getattr(passport, field_name))
        passport = existing
    from app.core.passport_payload import signed_payload
    passport.signature = "v2:" + sign_message(private_pem, signed_payload(passport))
    session.add(passport)
    session.commit()
    session.refresh(passport)
    return passport


def _unique_token(session: Session) -> str:
    for _ in range(20):
        token = generate_verify_token()
        taken = session.exec(
            select(Passport).where(Passport.verify_token == token)
        ).first()
        if taken is None:
            return token
    raise StageError("passport", "could not allocate unique verify token")


def verify_passport_token(
    session: Session, token: str
) -> tuple[Passport, Audit, bool, str] | None:
    """Resolve a public verify token.

    Returns (passport, audit, chain_ok, chain_reason) or None if unknown.
    Never requires or exposes the audit id from the caller side.
    """
    from app.core.security import verify_chain

    passport = session.exec(
        select(Passport).where(Passport.verify_token == token)
    ).first()
    if passport is None:
        return None
    audit = session.get(Audit, passport.audit_id)
    if audit is None:
        return None
    entries = session.exec(
        select(AuditLogEntry)
        .where(AuditLogEntry.audit_id == audit.id)
        .order_by(AuditLogEntry.created_at)  # type: ignore[attr-defined]
    ).all()
    chain_dicts = [
        {
            "id": str(e.id),
            "audit_id": str(e.audit_id),
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "action": e.action,
            "payload_json": e.payload_json,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "previous_hash": e.previous_hash,
            "hash": e.hash,
        }
        for e in entries
    ]
    ok, reason = verify_chain(chain_dicts)
    return passport, audit, ok, reason


def recompute_signature_message(document_hash: str, chain_head: str) -> bytes:
    return f"{document_hash}:{chain_head}".encode()


__all__ = [
    "ingest_document",
    "issue_passport",
    "recompute_signature_message",
    "run_audit_pipeline",
    "save_upload",
    "verify_passport_token",
]
