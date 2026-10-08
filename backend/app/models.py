from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import EmailStr
from sqlalchemy import DateTime, Index, Text, UniqueConstraint
from sqlmodel import Field, JSON, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Users + RBAC
# ---------------------------------------------------------------------------

# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    # RBAC role: user | reviewer | admin
    role: str = Field(default="user", max_length=32)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, max_length=32)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------

AUDIT_STATUSES = ("queued", "processing", "completed", "failed", "cancelled")


class AuditBase(SQLModel):
    status: str = Field(default="queued", max_length=32)
    title: str | None = Field(default=None, max_length=500)
    error_message: str | None = Field(default=None)
    failed_stage: str | None = Field(default=None, max_length=128)
    # Deterministic hash over sorted source document text_hashes
    source_set_hash: str | None = Field(default=None, max_length=64)


class AuditCreate(AuditBase):
    pass


class AuditUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=500)
    error_message: str | None = None
    failed_stage: str | None = Field(default=None, max_length=128)
    source_set_hash: str | None = Field(default=None, max_length=64)


class Audit(AuditBase, table=True):
    __tablename__ = "audits"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )


class AuditPublic(AuditBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditsPublic(SQLModel):
    data: list[AuditPublic]
    count: int


# ---------------------------------------------------------------------------
# Documents  (ONE ROW == ONE IMMUTABLE DOCUMENT VERSION)
#
# document_version_id == documents.id  (identity equivalence)
# Every claim / flag must reference document_id -> documents.id directly,
# never audit_id alone.
# ---------------------------------------------------------------------------

class DocumentBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    kind: str = Field(default="primary", max_length=64)  # primary | source
    filename: str = Field(max_length=500)
    mime_type: str = Field(default="application/octet-stream", max_length=255)
    storage_path: str = Field(max_length=1024)
    raw_text: str = Field(default="", sa_column=Text())
    normalized_text: str = Field(default="", sa_column=Text())
    offset_map_json: str = Field(default="[]", sa_column=Text())
    blocks_json: str = Field(default="[]", sa_column=Text())
    text_hash: str = Field(max_length=64)  # SHA256(normalized_text)
    mtime: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    version_no: int = Field(default=1)
    is_current: bool = Field(default=True)
    metadata_json: str = Field(default="{}", sa_column=Text())


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase, table=True):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_audit_current", "audit_id", "is_current"),
        UniqueConstraint("audit_id", "version_no", name="uq_documents_audit_version"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    


class DocumentPublic(SQLModel):
    id: uuid.UUID  # document_version_id == id
    audit_id: uuid.UUID
    kind: str
    filename: str
    mime_type: str
    text_hash: str
    version_no: int
    is_current: bool
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

FACT_STATUSES = ("active", "stale", "superseded", "rejected")


class FactBase(SQLModel):
    document_id: uuid.UUID = Field(foreign_key="documents.id", nullable=False, index=True)
    subject: str = Field(max_length=500)
    predicate: str = Field(max_length=255)
    object_value: str = Field(default="", sa_column=Text())
    location_json: str = Field(default="{}", sa_column=Text())
    status: str = Field(default="active", max_length=32)


class FactCreate(FactBase):
    pass


class Fact(FactBase, table=True):
    __tablename__ = "facts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class FactPublic(FactBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Claims
#
# claims.document_id -> documents.id  (MANDATORY – never audit_id alone)
# ---------------------------------------------------------------------------

CLAIM_STATUSES = ("extracted", "supported", "contradicted", "unsupported", "uncertain")


class ClaimBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    # document_version_id == documents.id
    document_id: uuid.UUID = Field(foreign_key="documents.id", nullable=False, index=True)
    sentence_id: str = Field(default="", max_length=128)
    text: str = Field(default="", sa_column=Text())
    category: str = Field(default="general", max_length=64)
    status: str = Field(default="extracted", max_length=32)
    metadata_json: str = Field(default="{}", sa_column=Text())


class ClaimCreate(ClaimBase):
    pass


class Claim(ClaimBase, table=True):
    __tablename__ = "claims"
    __table_args__ = (
        Index("ix_claims_audit_document", "audit_id", "document_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    


class ClaimPublic(ClaimBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class EvidenceBase(SQLModel):
    claim_id: uuid.UUID = Field(foreign_key="claims.id", nullable=False, index=True)
    source_document_id: uuid.UUID = Field(
        foreign_key="documents.id", nullable=False, index=True
    )
    quote: str = Field(default="", sa_column=Text())
    location_json: str = Field(default="{}", sa_column=Text())
    support_type: str = Field(default="supports", max_length=32)  # supports | refutes
    score: float = Field(default=0.0)


class EvidenceCreate(EvidenceBase):
    pass


class Evidence(EvidenceBase, table=True):
    __tablename__ = "evidence"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class EvidencePublic(EvidenceBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Flags
#
# flags.document_id -> documents.id  (MANDATORY – never audit_id alone)
# ---------------------------------------------------------------------------

FLAG_STATUSES = ("pending", "accepted", "dismissed", "fixed")


class FlagBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    # document_version_id == documents.id
    document_id: uuid.UUID = Field(foreign_key="documents.id", nullable=False, index=True)
    claim_id: uuid.UUID | None = Field(default=None, foreign_key="claims.id", nullable=True)
    type: str = Field(default="", max_length=255)
    severity: str = Field(default="MEDIUM", max_length=32)
    materiality: str = Field(default="MODERATE", max_length=32)
    reason: str = Field(default="", sa_column=Text())
    suggested_fix: str = Field(default="", sa_column=Text())
    status: str = Field(default="pending", max_length=32)
    reviewer_note: str | None = Field(default=None)
    impact_score: float = Field(default=0.0)
    sentence_id: str | None = Field(default=None, max_length=128)
    location_json: str = Field(default="{}", sa_column=Text())


class FlagCreate(FlagBase):
    pass


class FlagUpdate(SQLModel):
    status: str | None = Field(default=None, max_length=32)
    reviewer_note: str | None = None
    impact_score: float | None = None


class Flag(FlagBase, table=True):
    __tablename__ = "flags"
    __table_args__ = (
        Index("ix_flags_audit_document", "audit_id", "document_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    


class FlagPublic(FlagBase):
    id: uuid.UUID
    created_at: datetime | None = None


class FlagsPublic(SQLModel):
    data: list[FlagPublic]
    count: int


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------

DECISION_ACTIONS = ("accept", "dismiss", "fix")


class DecisionBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    flag_id: uuid.UUID = Field(foreign_key="flags.id", nullable=False, index=True)
    actor_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    action: str = Field(max_length=32)
    note: str | None = Field(default=None)


class DecisionCreate(DecisionBase):
    pass


class Decision(DecisionBase, table=True):
    __tablename__ = "decisions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class DecisionPublic(DecisionBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

class PolicyBase(SQLModel):
    name: str = Field(max_length=255, unique=True)
    description: str | None = Field(default=None)
    rules_json: str = Field(default="{}", sa_column=Text())
    is_active: bool = Field(default=True)


class PolicyCreate(PolicyBase):
    pass


class Policy(PolicyBase, table=True):
    __tablename__ = "policies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class PolicyPublic(PolicyBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Proofs  (Z3 / formal)
# ---------------------------------------------------------------------------

class ProofBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    claim_id: uuid.UUID | None = Field(default=None, foreign_key="claims.id", nullable=True)
    solver: str = Field(default="z3", max_length=64)
    query: str = Field(default="", sa_column=Text())
    result: str = Field(default="unknown", max_length=32)  # sat | unsat | unknown
    detail: str = Field(default="", sa_column=Text())


class ProofCreate(ProofBase):
    pass


class Proof(ProofBase, table=True):
    __tablename__ = "proofs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class ProofPublic(ProofBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Passports
#
# verify_token: 8-12 char unique URL-safe random token
# QR target: PUBLIC_BASE_URL/verify/{verify_token}
# NEVER expose audit_id in the public QR URL.
# ---------------------------------------------------------------------------

class PassportBase(SQLModel):
    audit_id: uuid.UUID = Field(
        foreign_key="audits.id", nullable=False, unique=True, index=True
    )
    verify_token: str = Field(
        max_length=16, unique=True, index=True, nullable=False
    )
    document_hash: str = Field(default="", max_length=64)
    chain_head: str = Field(default="", max_length=64)
    signature: str = Field(default="", sa_column=Text())
    trust_score: float = Field(default=0.0)
    status: str = Field(default="VERIFIED", max_length=32)
    issued_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class PassportCreate(PassportBase):
    pass


class Passport(PassportBase, table=True):
    __tablename__ = "passports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )

    


class PassportPublic(PassportBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Audit Log  (hash chain)
#
# entry_canonical = json.dumps({
#   id, audit_id, actor_id, action, payload_json, created_at, previous_hash
# }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
# hash = SHA256(entry_canonical)
# ---------------------------------------------------------------------------

class AuditLogBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    actor_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    action: str = Field(max_length=255)
    payload_json: str = Field(default="{}", sa_column=Text())
    previous_hash: str = Field(default="", max_length=64)
    hash: str = Field(max_length=64)


class AuditLogEntry(AuditLogBase, table=True):
    __tablename__ = "audit_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class AuditLogPublic(AuditLogBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Challenges  (reviewer challenge workflow)
# ---------------------------------------------------------------------------

class ChallengeBase(SQLModel):
    audit_id: uuid.UUID = Field(foreign_key="audits.id", nullable=False, index=True)
    flag_id: uuid.UUID | None = Field(default=None, foreign_key="flags.id", nullable=True)
    raised_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    message: str = Field(default="", sa_column=Text())
    status: str = Field(default="open", max_length=32)  # open | resolved | rejected
    resolution: str | None = Field(default=None)


class ChallengeCreate(ChallengeBase):
    pass


class Challenge(ChallengeBase, table=True):
    __tablename__ = "challenges"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class ChallengePublic(ChallengeBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    audit_id: uuid.UUID | None = Field(
        default=None, foreign_key="audits.id", nullable=True
    )
    title: str = Field(max_length=500)
    body: str = Field(default="", sa_column=Text())
    is_read: bool = Field(default=False)
    kind: str = Field(default="info", max_length=64)  # info | warning | error | success


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class NotificationPublic(NotificationBase):
    id: uuid.UUID
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Items  (base-template demo model – kept so template routes/tests still work)
# ---------------------------------------------------------------------------


class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


class Item(ItemBase, table=True):
    __tablename__ = "items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    owner_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, ondelete="CASCADE"
    )


class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# ---------------------------------------------------------------------------
# Generic message / token (kept from base template)
# ---------------------------------------------------------------------------

class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None
    role: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
