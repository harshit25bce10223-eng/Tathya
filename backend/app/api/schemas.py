"""API contracts consumed by the frontend.

These are the stable serialized shapes for:
Audit, Document, Fact, Claim, Evidence, Flag, Decision, Proof, Passport,
VerificationResult — the frontend never reverse-engineers backend responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import (  # noqa: F401 - re-exported contract types
    AuditPublic,
    AuditsPublic,
    ClaimPublic,
    DecisionPublic,
    DocumentPublic,
    EvidencePublic as EvidencePublicModel,
    FactPublic,
    FlagPublic,
    FlagsPublic,
    PassportPublic,
    PolicyPublic,
    ProofPublic,
)


class DocumentsPublic(BaseModel):
    data: list[DocumentPublic]
    count: int


class ClaimsPublic(BaseModel):
    data: list[ClaimPublic]
    count: int


class FactsPublic(BaseModel):
    data: list[FactPublic]
    count: int


class EvidencePublic(BaseModel):
    data: list[EvidencePublicModel]
    count: int


class DecisionsPublic(BaseModel):
    data: list[DecisionPublic]
    count: int


class ProofsPublic(BaseModel):
    data: list[ProofPublic]
    count: int


class DecisionRequest(BaseModel):
    action: str = Field(pattern="^(accept|dismiss|fix)$")
    note: str | None = None


class RescoreResult(BaseModel):
    audit: AuditPublic
    trust_score: float
    flag_count: int
    open_flag_count: int


class ChainVerification(BaseModel):
    ok: bool
    reason: str
    entry_count: int


class VerificationResult(BaseModel):
    """Public result of GET /api/v1/verify/{verify_token}.

    Never includes the audit id.
    """

    found: bool
    verify_token: str
    status: str
    trust_score: float
    issued_at: datetime | None = None
    document_count: int = 0
    document_hash: str = ""
    chain: ChainVerification | None = None
    signature_valid: bool | None = None
    verify_url: str = ""
    detail: str | None = None


class AuditSummary(BaseModel):
    audit: AuditPublic
    document_count: int
    flag_count: int
    open_flag_count: int
    claim_count: int
    passport: PassportPublic | None = None
    verify_token: str | None = None


class JobStatus(BaseModel):
    audit_id: uuid.UUID
    status: str
    failed_stage: str | None = None
    error_message: str | None = None
    source_set_hash: str | None = None
