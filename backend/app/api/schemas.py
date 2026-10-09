"""API contracts consumed by the frontend.

These are the stable serialized shapes for:
Audit, Document, Fact, Claim, Evidence, Flag, Decision, Proof, Passport,
VerificationResult — the frontend never reverse-engineers backend responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

from app.models import (  # noqa: F401 - re-exported contract types
    AuditPublic,
    AuditsPublic,
    ClaimPublic,
    DecisionPublic,
    DocumentPublic,
    FactPublic,
    FlagPublic,
    FlagsPublic,
    PassportPublic,
    PolicyPublic,
    ProofPublic,
)
from app.models import (
    EvidencePublic as EvidencePublicModel,
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


class SourceContextUpdate(BaseModel):
    authority: Literal["unspecified", "reference", "approved", "official"]
    note: str = Field(min_length=3, max_length=2000)


class EvidencePublic(BaseModel):
    data: list[EvidencePublicModel]
    count: int


class ScoreContribution(BaseModel):
    """Per-finding contribution to trust score."""
    flag_id: str
    severity: str
    materiality: str
    confidence: float
    penalty: float
    status: str
    included_in_reviewed: bool
    reason: str = ""


class ScoreBreakdown(BaseModel):
    """Complete score breakdown for an audit."""
    ai_score: float
    reviewed_score: float
    ai_score_band: str
    reviewed_score_band: str
    critical_risk: bool
    total_findings: int
    unresolved_findings: int
    severity_counts: dict[str, int]
    review_status_counts: dict[str, int]
    finding_contributions: list[ScoreContribution]
    scoring_version: str
    scoring_methodology: str
    calculated_at: str
    score_status: str
    coverage: dict[str, Any]
    sub_scores: dict[str, float | None]
    score_limit_reason: str | None = None


class DecisionsPublic(BaseModel):
    data: list[DecisionPublic]
    count: int


class ProofsPublic(BaseModel):
    data: list[ProofPublic]
    count: int


# Phase 3 - enriched contracts for frontend


class GroundingDetail(BaseModel):
    """Grounding verification detail for a claim."""

    status: str  # supported, contradicted, unsupported, uncertain
    evidence_ids: list[uuid.UUID] = []
    primary_evidence_id: uuid.UUID | None = None
    reason: str = ""
    confidence: float = 0.0
    source_metadata: dict[str, Any] = {}


class ClaimWithGrounding(ClaimPublic):
    """Claim with grounding verification detail."""

    grounding: GroundingDetail | None = None
    evidence: list[EvidencePublicModel] = []


class ClaimsWithGroundingPublic(BaseModel):
    data: list[ClaimWithGrounding]
    count: int


class FlagWithEvidence(FlagPublic):
    """Flag with associated evidence for frontend display."""

    evidence: list[EvidencePublicModel] = []
    claim_text: str | None = None


class FlagsWithEvidencePublic(BaseModel):
    data: list[FlagWithEvidence]
    count: int


class DecisionRequest(BaseModel):
    action: str = Field(pattern="^(accept|dismiss|fix)$")
    note: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=1, max_length=4000)
    remediation: str = Field(default="", max_length=4000)


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
    score_status: str = "insufficient_verification"
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
    fact_count: int
    passport: PassportPublic | None = None
    verify_token: str | None = None


class JobStatus(BaseModel):
    audit_id: uuid.UUID
    status: str
    failed_stage: str | None = None
    error_message: str | None = None
    source_set_hash: str | None = None
