"""Admin authoring and reviewer preview of bounded, typed business rules."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.api.deps import AdminDep, ReviewerDep, SessionDep
from app.api.routes.audits import _get_audit
from app.core.business_policies import BusinessRules, SCHEMA_VERSION, preview_rules, public_policy
from app.models import Policy

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    is_active: bool = False
    rules: BusinessRules
    change_note: str = Field(min_length=3, max_length=2000)

    @field_validator("name", "change_note")
    @classmethod
    def trim_required(cls, value, info):
        value = value.strip()
        if len(value) < (3 if info.field_name == "change_note" else 1):
            raise ValueError("A name and meaningful change note are required")
        return value


class PolicyEdit(PolicyWrite):
    expected_version: int = Field(ge=1)


class PolicyPreview(BaseModel):
    audit_id: UUID
    rules: BusinessRules


def _revision(body: PolicyWrite, version: int, actor: AdminDep) -> dict:
    return {"version": version, "name": body.name, "description": body.description, "is_active": body.is_active, "rules": body.rules.model_dump(mode="json"), "change_note": body.change_note, "actor_id": str(actor.id), "changed_at": datetime.now(UTC).isoformat()}


def _save(session: SessionDep, policy: Policy) -> dict:
    session.add(policy)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="A policy with this name already exists")
    session.refresh(policy)
    return public_policy(policy)


@router.get("")
def list_policies(session: SessionDep, current_user: ReviewerDep) -> dict:
    policies = session.exec(select(Policy).order_by(Policy.created_at.desc(), Policy.id)).all()
    return {"data": [public_policy(p) for p in policies], "count": len(policies)}


@router.post("", status_code=201)
def create_policy(body: PolicyWrite, session: SessionDep, current_user: AdminDep) -> dict:
    if body.rules.audit_id is not None:
        _get_audit(session, body.rules.audit_id, current_user)
    revision = _revision(body, 1, current_user)
    raw = {**body.rules.model_dump(mode="json"), "schema_version": SCHEMA_VERSION, "version": 1, "history": [revision]}
    return _save(session, Policy(name=body.name, description=body.description, is_active=body.is_active, rules_json=json.dumps(raw)))


@router.put("/{policy_id}")
def edit_policy(policy_id: UUID, body: PolicyEdit, session: SessionDep, current_user: AdminDep) -> dict:
    # Serialize writers and reject stale editors rather than overwriting their changes.
    policy = session.exec(select(Policy).where(Policy.id == policy_id).with_for_update()).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    raw = json.loads(policy.rules_json or "{}")
    if not isinstance(raw, dict):
        raw = {}
    version = int(raw.get("version", 1))
    if version != body.expected_version:
        raise HTTPException(status_code=409, detail="This policy changed while you were editing. Reload the current version before saving.")
    if body.rules.audit_id is not None:
        _get_audit(session, body.rules.audit_id, current_user)
    history = raw.get("history", [])
    if not isinstance(history, list):
        history = []
    if not history:
        history = [{"version": version, "name": policy.name, "description": policy.description, "is_active": policy.is_active, "rules": {k: v for k, v in raw.items() if k != "history"}, "change_note": "Imported pre-existing policy record."}]
    next_version = version + 1
    history.append(_revision(body, next_version, current_user))
    policy.name, policy.description, policy.is_active = body.name, body.description, body.is_active
    policy.rules_json = json.dumps({**body.rules.model_dump(mode="json"), "schema_version": SCHEMA_VERSION, "version": next_version, "history": history})
    policy.updated_at = datetime.now(UTC)
    return _save(session, policy)


@router.post("/preview")
def preview_policy(body: PolicyPreview, session: SessionDep, current_user: ReviewerDep) -> dict:
    _get_audit(session, body.audit_id, current_user)
    return {"preview_only": True, **preview_rules(session, body.audit_id, body.rules)}
