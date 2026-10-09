"""Bounded source inbox watching. Only dedicated per-audit storage folders are read."""
from __future__ import annotations
import hashlib
import json
import logging
import threading
from pathlib import Path
from uuid import UUID
from sqlmodel import Session, select
from app.core.config import settings
from app.core.parsers import supported_suffixes
from app.models import Audit, AuditLogEntry, Document

logger = logging.getLogger("tathya.source_watch")
MAX_BYTES = 50 * 1024 * 1024
_lock = threading.Lock()


def inbox(audit_id: UUID, create: bool = False) -> Path:
    root = Path(settings.STORAGE_DIR).expanduser().resolve()
    parent = root / "source-inbox"
    folder = parent / str(audit_id)
    if parent.is_symlink() or folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError("The source inbox cannot be a symbolic link or leave storage.")
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def configuration(session: Session, audit_id: UUID) -> dict:
    entry = session.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit_id, AuditLogEntry.action == "source.watch.configured").order_by(AuditLogEntry.created_at.desc(), AuditLogEntry.id.desc())).first()
    if not entry:
        return {"enabled": False, "auto_reaudit": False}
    try:
        payload = json.loads(entry.payload_json)
        return {"enabled": payload.get("enabled") is True, "auto_reaudit": payload.get("auto_reaudit") is True}
    except (ValueError, TypeError, AttributeError):
        return {"enabled": False, "auto_reaudit": False}


def _fingerprints(session: Session, audit_id: UUID) -> dict:
    entries = session.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit_id, AuditLogEntry.action == "source.watch.imported").order_by(AuditLogEntry.created_at, AuditLogEntry.id)).all()
    fingerprints = {}
    for entry in entries:
        try:
            data = json.loads(entry.payload_json)
            fingerprints[data["filename"]] = data["raw_sha256"]
        except (ValueError, TypeError, KeyError):
            continue
    return fingerprints


def _failed_files(session: Session, audit_id: UUID) -> dict:
    entries = session.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit_id, AuditLogEntry.action == "source.watch.failed").order_by(AuditLogEntry.created_at, AuditLogEntry.id)).all()
    failed = {}
    for entry in entries:
        try:
            data = json.loads(entry.payload_json)
            failed[data["filename"]] = data
        except (ValueError, TypeError, KeyError):
            continue
    return failed


def _read(path: Path, folder: Path) -> bytes:
    if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError("Only regular files inside the source inbox can be checked.")
    before = path.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError("File exceeds the 50 MB limit.")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    after = path.stat()
    if not data:
        raise ValueError("The source file is empty.")
    if len(data) > MAX_BYTES or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("File is too large or still changing; finish saving it and try again.")
    return data


def inspect_watch(session: Session, audit_id: UUID) -> dict:
    config = configuration(session, audit_id)
    folder = inbox(audit_id)
    previous = _fingerprints(session, audit_id)
    failed = _failed_files(session, audit_id)
    files = []
    entries = sorted(folder.iterdir(), key=lambda p: p.name.casefold()) if folder.exists() else []
    read_bytes = 0
    for path in entries[:100]:
        if path.is_dir() and not path.is_symlink():
            continue
        try:
            if path.suffix.lower() not in supported_suffixes():
                raise ValueError("Unsupported file type.")
            if read_bytes + path.lstat().st_size > 100 * 1024 * 1024:
                files.append({"filename": path.name, "state": "deferred", "raw_sha256": None, "error": "This check reached the 100 MB scan budget."})
                continue
            data = _read(path, folder)
            read_bytes += len(data)
            digest = hashlib.sha256(data).hexdigest()
            state = "unchanged" if previous.get(path.name) == digest else "changed" if path.name in previous else "new"
            failure = failed.get(path.name, {})
            if state != "unchanged" and failure.get("raw_sha256") == digest:
                state = "failed"
            files.append({"filename": path.name, "state": state, "raw_sha256": digest, "error": failure.get("error") if state == "failed" else None})
        except (ValueError, OSError) as exc:
            files.append({"filename": path.name, "state": "invalid", "raw_sha256": None, "error": str(exc)})
    return {**config, "audit_id": str(audit_id), "inbox_path": str(folder), "files": files, "has_more_files": len(entries) > 100, "changed_count": sum(f["state"] in ("new", "changed") for f in files), "poll_seconds": 30}


def check_watch(session: Session, audit_id: UUID, actor_id: UUID, automatic: bool = False) -> dict:
    from app.core.pipeline import save_upload, ingest_document, append_chain_entry
    from app.core.jobs import submit_audit_job
    config = configuration(session, audit_id)
    if not config["enabled"]:
        raise ValueError("Enable this source inbox before checking files.")
    if not _lock.acquire(blocking=False):
        return {"imported": [], "errors": [], "busy": True, "reaudit_queued": False}
    imported, errors = [], []
    failed_recorded = False
    try:
        audit = session.exec(select(Audit).where(Audit.id == audit_id).with_for_update().execution_options(populate_existing=True)).first()
        if audit is None:
            raise ValueError("Audit not found.")
        if audit.status in ("queued", "processing"):
            return {"imported": [], "errors": [], "busy": True, "reaudit_queued": False}
        docs = session.exec(select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))).all()
        if not any(d.kind == "primary" for d in docs):
            raise ValueError("Upload an AI document before adding watched sources.")
        primary_names = {Path(d.filename).name.casefold() for d in docs if d.kind == "primary"}
        state = inspect_watch(session, audit_id)
        for item in [f for f in state["files"] if f["state"] in ("new", "changed") or (not automatic and f["state"] == "failed")][:5]:
            saved = None
            try:
                if item["filename"].casefold() in primary_names:
                    raise ValueError("A source file cannot replace the AI document; use a different filename.")
                data = _read(inbox(audit_id) / item["filename"], inbox(audit_id))
                digest = hashlib.sha256(data).hexdigest()
                if digest != item["raw_sha256"]:
                    raise ValueError("The source changed during the check. Try again after saving finishes.")
                with session.begin_nested():
                    saved = save_upload(audit_id, item["filename"], data)
                    doc = ingest_document(session, audit, filename=item["filename"], path=saved, commit=False)
                    session.flush()
                    append_chain_entry(session, audit_id=audit_id, actor_id=actor_id, action="source.watch.imported", payload_json=json.dumps({"filename": item["filename"], "raw_sha256": digest, "document_id": str(doc.id), "trigger": "scheduled" if automatic else "manual"}, sort_keys=True), commit=False)
                imported.append({"filename": item["filename"], "document_id": str(doc.id), "version": doc.version_no})
            except Exception as exc:
                if saved is not None:
                    saved.unlink(missing_ok=True)
                error = str(exc)
                errors.append({"filename": item["filename"], "error": error})
                append_chain_entry(session, audit_id=audit_id, actor_id=actor_id, action="source.watch.failed", payload_json=json.dumps({"filename": item["filename"], "raw_sha256": item["raw_sha256"], "error": error[:2000]}, sort_keys=True), commit=False)
                failed_recorded = True
        queued = bool(imported and config["auto_reaudit"])
        if queued:
            audit.status, audit.error_message, audit.failed_stage = "queued", None, None
            session.add(audit)
        if imported:
            from app.api.routes.audits import _recompute_source_set_hash
            _recompute_source_set_hash(session, audit_id)
        elif failed_recorded:
            session.commit()
        else:
            session.rollback()
        if queued:
            submit_audit_job(audit_id)
        return {"imported": imported, "errors": errors + [f for f in state["files"] if f["state"] == "invalid"], "busy": False, "reaudit_queued": queued}
    finally:
        _lock.release()


def watch_loop(stop: threading.Event) -> None:
    from app.core.db import engine
    while not stop.wait(30):
        try:
            with Session(engine) as session:
                ids = session.exec(select(AuditLogEntry.audit_id).where(AuditLogEntry.action == "source.watch.configured").distinct()).all()
            for audit_id in ids:
                if stop.is_set():
                    return
                try:
                    with Session(engine) as session:
                        audit = session.get(Audit, audit_id)
                        if audit and configuration(session, audit_id)["enabled"]:
                            check_watch(session, audit_id, audit.owner_id, automatic=True)
                except Exception:
                    logger.exception("Source inbox check failed for audit %s", audit_id)
        except Exception:
            logger.exception("Source inbox check failed; will retry on the next poll")
