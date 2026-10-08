"""Background job foundation (Phase 1).

Locked requirements:
    ThreadPoolExecutor(max_workers=1)  — uvicorn runs with --workers 1
    POST /audits -> queued -> processing -> completed | failed
    every job opens its own DB session
    error_message + failed_stage are persisted on failure
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from sqlmodel import Session

from app.core.db import engine
from app.models import Audit

logger = logging.getLogger("tathya.jobs")

executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tathya-job")


@dataclass
class QueueState:
    pending: int = 0
    active_audit_id: str | None = None
    active_stage: str | None = None
    last_error: str | None = None
    completed: int = 0
    failed: int = 0

    def to_dict(self) -> dict:
        return {
            "pending": self.pending,
            "active_audit_id": self.active_audit_id,
            "active_stage": self.active_stage,
            "last_error": self.last_error,
            "completed": self.completed,
            "failed": self.failed,
        }


queue_state = QueueState()
_state_lock = threading.Lock()


class StageError(RuntimeError):
    """Pipeline failure annotated with the stage it occurred in."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass
class StageTracker:
    stage: str = "queued"
    history: list[str] = field(default_factory=list)

    def set(self, stage: str) -> None:
        self.stage = stage
        self.history.append(stage)
        with _state_lock:
            queue_state.active_stage = stage


PipelineFn = Callable[[Session, uuid.UUID, StageTracker], None]


def submit_audit_job(
    audit_id: uuid.UUID, pipeline: PipelineFn | None = None
) -> Future[None]:
    """Enqueue an audit job. Status transitions are persisted by the worker."""
    with _state_lock:
        queue_state.pending += 1
    return executor.submit(_run_job, audit_id, pipeline)


def _run_job(audit_id: uuid.UUID, pipeline: PipelineFn | None) -> None:
    from app.core.pipeline import run_audit_pipeline  # avoids import cycle

    with _state_lock:
        queue_state.pending = max(0, queue_state.pending - 1)
        queue_state.active_audit_id = str(audit_id)

    tracker = StageTracker()
    with Session(engine) as session:
        audit = session.get(Audit, audit_id)
        if audit is None:
            with _state_lock:
                queue_state.active_audit_id = None
                queue_state.active_stage = None
            return
        if audit.status == "cancelled":
            with _state_lock:
                queue_state.active_audit_id = None
                queue_state.active_stage = None
            return

        audit.status = "processing"
        audit.error_message = None
        audit.failed_stage = None
        session.add(audit)
        session.commit()

        try:
            tracker.set("ingest")
            (pipeline or run_audit_pipeline)(session, audit_id, tracker)
            tracker.set("completed")
            session.refresh(audit)
            audit.status = "completed"
            audit.failed_stage = None
            audit.error_message = None
            session.add(audit)
            session.commit()
            with _state_lock:
                queue_state.completed += 1
        except StageError as exc:
            session.rollback()
            _fail(session, audit, exc.stage, str(exc))
            with _state_lock:
                queue_state.failed += 1
                queue_state.last_error = str(exc)
        except Exception as exc:  # noqa: BLE001 - job boundary
            session.rollback()
            logger.exception("audit job %s crashed", audit_id)
            _fail(session, audit, tracker.stage, str(exc))
            with _state_lock:
                queue_state.failed += 1
                queue_state.last_error = str(exc)
        finally:
            with _state_lock:
                queue_state.active_audit_id = None
                queue_state.active_stage = None


def _fail(session: Session, audit: Audit, stage: str, message: str) -> None:
    try:
        session.refresh(audit)
        audit.status = "failed"
        audit.failed_stage = stage
        audit.error_message = message[:2000]
        session.add(audit)
        session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("failed to persist failure state for audit %s", audit.id)


def shutdown(wait: bool = True) -> None:
    executor.shutdown(wait=wait)
