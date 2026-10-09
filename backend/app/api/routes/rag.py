"""Authenticated questions over current source documents in one audit."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.audits import _get_audit
from app.core.rag import RagAnswer, RagQuestion, answer_question

router = APIRouter(prefix="/audits", tags=["source-questions"])


@router.post("/{audit_id}/ask", response_model=RagAnswer)
def ask_sources(
    audit_id: uuid.UUID, body: RagQuestion, session: SessionDep, user: CurrentUser
) -> RagAnswer:
    _get_audit(session, audit_id, user)
    return answer_question(session, audit_id, body)
