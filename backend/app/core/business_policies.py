"""Versioned business rules evaluated against literal current document values."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlmodel import Session, select

from app.core.claims import claim_location
from app.core.extraction.base import SpanClaims
from app.core.extraction.dates import extract as extract_dates
from app.core.extraction.numeric import extract as extract_numeric
from app.core.source_fact_sheet import _canonical, build_source_fact_sheet
from app.core.source_verification import field_hint
from app.models import Audit, AuditLogEntry, Claim, Document, Flag, Policy

SCHEMA_VERSION = "business_policy_v1"
POLICY_FLAG_TYPES = ("policy_violation", "policy_uncertain")
NUMERIC_FIELDS = {"contract_value", "payment_terms_days", "warranty_months"}


class BusinessCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variable: Literal["contract_value", "payment_terms_days", "warranty_months", "delivery_date", "currency"]
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "exists"]
    value: float | str | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    reason: str = Field(default="", max_length=500)

    @field_validator("value", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("A boolean is not a business comparison value")
        return value

    @model_validator(mode="after")
    def typed_operand(self):
        if self.operator == "exists":
            if self.value is not None:
                raise ValueError("An exists rule does not take a comparison value")
        elif self.variable in NUMERIC_FIELDS:
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool) or not math.isfinite(self.value) or self.value < 0:
                raise ValueError("This field requires a non-negative numeric comparison value")
        elif self.variable == "delivery_date":
            if not isinstance(self.value, str) or date.fromisoformat(self.value).isoformat() != self.value:
                raise ValueError("Delivery dates must use YYYY-MM-DD")
        elif self.variable == "currency":
            if self.operator not in {"eq", "ne"} or not isinstance(self.value, str) or len(self.value) != 3 or not self.value.isalpha() or not self.value.isupper():
                raise ValueError("Currency rules compare an uppercase three-letter code with eq or ne")
        if self.variable == "contract_value" and self.operator != "exists" and not self.currency:
            raise ValueError("Contract amount rules require a currency; conversion is not automatic")
        if self.variable != "contract_value" and self.currency:
            raise ValueError("Only a contract amount condition takes a currency")
        return self


class BusinessRules(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: Literal["claim", "source"] = "claim"
    audit_id: UUID | None = None
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"] = "HIGH"
    conditions: list[BusinessCondition] = Field(min_length=1, max_length=20)


def _json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text or "{}")
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def rules_for(policy: Policy) -> BusinessRules | None:
    raw = _json(policy.rules_json)
    if raw.get("schema_version") != SCHEMA_VERSION:
        return None
    try:
        return BusinessRules.model_validate({k: raw[k] for k in ("target", "audit_id", "severity", "conditions") if k in raw})
    except ValueError:
        return None


def public_policy(policy: Policy) -> dict[str, Any]:
    raw = _json(policy.rules_json)
    rules = rules_for(policy)
    return {"id": str(policy.id), "name": policy.name, "description": policy.description, "is_active": policy.is_active,
            "version": raw.get("version", 1), "rules": rules.model_dump(mode="json") if rules else None,
            "supported": rules is not None, "history": raw.get("history", []), "updated_at": policy.updated_at}


def applicable_policies(session: Session, audit_id: UUID) -> list[tuple[Policy, BusinessRules]]:
    output = []
    for policy in session.exec(select(Policy).where(Policy.is_active.is_(True)).order_by(Policy.created_at, Policy.id)).all():
        rules = rules_for(policy)
        if rules and (rules.audit_id is None or rules.audit_id == audit_id):
            output.append((policy, rules))
    return output


def _fingerprint(session: Session, audit_id: UUID) -> dict[str, Any]:
    output = {"documents": {str(d.id): d.text_hash for d in session.exec(select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))).all()},
              "policies": {str(p.id): _json(p.rules_json).get("version", 1) for p, _ in applicable_policies(session, audit_id)}}
    from app.core.source_resolution import resolution_fingerprint
    resolutions = resolution_fingerprint(session, audit_id)
    if resolutions:
        output["resolutions"] = resolutions
    return output


def _claim_values(session: Session, audit_id: UUID) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    rows = session.exec(select(Claim, Document).join(Document, Claim.document_id == Document.id).where(Claim.audit_id == audit_id, Document.is_current.is_(True), Document.kind == "primary")).all()
    for claim, document in rows:
        location = claim_location(claim)
        start, end = location["start"], location["end"]
        if document.normalized_text[start:end].strip() != claim.text:
            continue
        field = field_hint(claim.text)
        spans = SpanClaims()
        records = extract_numeric(claim.text, spans) + extract_dates(claim.text, spans)
        for record in records:
            if record.raw_text != claim.text[record.norm_start:record.norm_end]:
                continue
            item = _canonical(field, record.payload)
            if not item:
                continue
            key, value, unit = item
            candidate = {"value": value, "unit": unit, "quote": claim.text, "document_id": str(document.id), "claim_id": str(claim.id), "location": location}
            candidates.setdefault(key, []).append(candidate)
            if key == "contract_value" and unit:
                candidates.setdefault("currency", []).append({**candidate, "value": unit, "unit": None})
    return candidates


def _source_values(sheet: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {}
    selections = {r["field"]: r for r in sheet.get("resolutions", []) if r["active"]}
    for fact in sheet["facts"]:
        if fact["field"] in selections and fact["document_id"] != selections[fact["field"]]["document_id"]:
            continue
        if not fact["grounded"] or fact["field"] not in NUMERIC_FIELDS | {"delivery_date"}:
            continue
        item = {"value": fact["value"], "unit": fact["unit"], "quote": fact["context_quote"] or fact["quote"], "document_id": fact["document_id"], "claim_id": None, "location": fact["location"], "fact_id": fact["id"]}
        candidates.setdefault(fact["field"], []).append(item)
        if fact["field"] == "contract_value" and fact["unit"]:
            candidates.setdefault("currency", []).append({**item, "value": fact["unit"], "unit": None})
    return candidates


def evaluate_rules(rules: BusinessRules, candidates: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    results = []
    for condition in rules.conditions:
        matches = candidates.get(condition.variable, [])
        distinct = {(str(m["value"]), m["unit"]) for m in matches}
        actual = matches[0]["value"] if len(distinct) == 1 else None
        unit = matches[0]["unit"] if len(distinct) == 1 else None
        state, explanation = "uncertain", "The required value is missing or conflicting in the current documents."
        if condition.operator == "exists":
            state = "satisfied" if matches else "uncertain"
            explanation = "The required field is present." if matches else "The required field could not be established from extracted business values; confirm extraction coverage before review."
            if condition.currency and (len(distinct) != 1 or unit != condition.currency):
                state, explanation = "uncertain", "The required contract currency could not be established unambiguously."
        elif actual is not None:
            if condition.currency and condition.currency != unit:
                explanation = f"Currency {unit} cannot be compared with {condition.currency} without an explicit conversion policy."
            else:
                expected = condition.value
                left, right = (Decimal(str(actual)), Decimal(str(expected))) if condition.variable in NUMERIC_FIELDS else (actual, expected)
                checks = {"eq": lambda: left == right, "ne": lambda: left != right, "gt": lambda: left > right, "gte": lambda: left >= right, "lt": lambda: left < right, "lte": lambda: left <= right}
                passed = checks[condition.operator]()
                state = "satisfied" if passed else "violation"
                field_label = {"contract_value": "Contract value", "payment_terms_days": "Payment terms", "warranty_months": "Warranty", "delivery_date": "Delivery date", "currency": "Contract currency"}[condition.variable]
                operator_label = {"eq": "equal to", "ne": "different from", "gt": "greater than", "gte": "at least", "lt": "less than", "lte": "at most"}[condition.operator]
                explanation = f"{field_label}: recorded {actual}{' ' + unit if unit else ''}; required {operator_label} {expected}{' ' + condition.currency if condition.currency else ''}."
        results.append({**condition.model_dump(mode="json"), "actual_value": actual, "actual_unit": unit, "state": state, "explanation": explanation, "evidence": matches[:12], "evidence_count": len(matches)})
    state = "violation" if any(r["state"] == "violation" for r in results) else "uncertain" if any(r["state"] == "uncertain" for r in results) else "satisfied"
    return {"state": state, "target": rules.target, "severity": rules.severity, "conditions": results}


def preview_rules(session: Session, audit_id: UUID, rules: BusinessRules) -> dict[str, Any]:
    if rules.audit_id is not None and rules.audit_id != audit_id:
        return {"state": "not_applicable", "target": rules.target, "severity": rules.severity, "conditions": []}
    candidates = _claim_values(session, audit_id) if rules.target == "claim" else _source_values(build_source_fact_sheet(session, audit_id))
    return evaluate_rules(rules, candidates)


def evaluate_audit_policies(session: Session, audit_id: UUID) -> dict[str, Any]:
    """Persist flags and a hash-chain evaluation snapshot before scoring."""
    audit = session.get(Audit, audit_id)
    if audit is None:
        raise ValueError("Audit not found")
    documents = session.exec(select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True)).order_by(Document.version_no)).all()
    document_fingerprint = {str(d.id): d.text_hash for d in documents}
    old_flags = session.exec(select(Flag).where(Flag.audit_id == audit_id, Flag.type.in_(POLICY_FLAG_TYPES))).all()
    old_status = {str(f.id): f.status for f in old_flags}
    existing = {_json(f.location_json).get("policy_evaluation_key"): f for f in old_flags}
    for flag in old_flags:
        flag.status = "superseded"
        session.add(flag)
    claims, sources = _claim_values(session, audit_id), _source_values(build_source_fact_sheet(session, audit_id))
    evaluations = []
    for policy, rules in applicable_policies(session, audit_id):
        result = evaluate_rules(rules, claims if rules.target == "claim" else sources)
        result.update(policy_id=str(policy.id), policy_name=policy.name, policy_version=_json(policy.rules_json).get("version", 1))
        if result["state"] in {"violation", "uncertain"} and documents:
            key = hashlib.sha256(json.dumps({"evaluation": result, "documents": document_fingerprint}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            conditions = [c for c in result["conditions"] if c["state"] != "satisfied"]
            evidence = next((c["evidence"][0] for c in conditions if c["evidence"]), None)
            document_id = UUID(evidence["document_id"]) if evidence else next((d.id for d in documents if d.kind == "primary"), documents[0].id)
            location = {**(evidence["location"] if evidence else {}), "policy_id": str(policy.id), "policy_version": result["policy_version"], "policy_evaluation_key": key}
            flag = existing.get(key)
            if flag is None or old_status.get(str(flag.id)) == "superseded":
                flag = Flag(audit_id=audit_id, document_id=document_id, claim_id=UUID(evidence["claim_id"]) if evidence and evidence["claim_id"] else None)
            else:
                flag.status = old_status[str(flag.id)]
            flag.type = "policy_violation" if result["state"] == "violation" else "policy_uncertain"
            flag.severity = rules.severity if result["state"] == "violation" else "LOW"
            flag.materiality = "MODERATE"
            flag.impact_score = 1.0 if result["state"] == "violation" else 0.0
            flag.reason = f"Policy '{policy.name}' v{result['policy_version']} ({rules.target}): " + " ".join(c["explanation"] for c in conditions)
            flag.suggested_fix = "Resolve the business rule violation or record a justified reviewer decision, then re-audit." if result["state"] == "violation" else "Supply a clear, grounded business value or clarify conflicting documents, then re-audit."
            flag.location_json = json.dumps(location)
            session.add(flag)
            session.flush()
            result["flag_id"] = str(flag.id)
        evaluations.append(result)
    snapshot = {"evaluations": evaluations, "fingerprint": {"documents": document_fingerprint, "policies": {r["policy_id"]: r["policy_version"] for r in evaluations}}}
    from app.core.source_resolution import resolution_fingerprint
    resolutions = resolution_fingerprint(session, audit_id)
    if resolutions:
        snapshot["fingerprint"]["resolutions"] = resolutions
    from app.core.pipeline import append_chain_entry
    append_chain_entry(session, audit_id=audit_id, actor_id=audit.owner_id, action="policies.evaluated", payload_json=json.dumps(snapshot, sort_keys=True))
    return snapshot


def recorded_policy_results(session: Session, audit_id: UUID) -> dict[str, Any]:
    entry = session.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id == audit_id, AuditLogEntry.action == "policies.evaluated").order_by(AuditLogEntry.created_at.desc())).first()
    current = _fingerprint(session, audit_id)
    if not entry:
        return {"evaluations": [], "stale": bool(current["policies"] or current.get("resolutions")), "evaluated_at": None, "documents_changed": False, "resolutions_changed": bool(current.get("resolutions")), "active_policy_count": len(current["policies"])}
    payload = _json(entry.payload_json)
    return {"evaluations": payload.get("evaluations", []), "stale": payload.get("fingerprint") != current, "evaluated_at": entry.created_at, "documents_changed": payload.get("fingerprint", {}).get("documents") != current["documents"], "resolutions_changed": payload.get("fingerprint", {}).get("resolutions", {}) != current.get("resolutions", {}), "active_policy_count": len(current["policies"])}
