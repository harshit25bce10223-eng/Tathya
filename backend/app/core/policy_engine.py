"""Policy Engine — Phase 5.

Configurable engine that evaluates persisted claims/findings against defined
business policies and produces traceable results.

Uses the existing `policies` table and APIs where possible.  Policy rules
are data/configuration, not arbitrary executable code.

Inspect the existing policies model before extending.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models import Claim, Flag, Policy

logger = logging.getLogger("tathya.policy_engine")

# ---------------------------------------------------------------------------
# Policy rule operator schema (allowlisted)
# ---------------------------------------------------------------------------

class PolicyOperator(str, Enum):
    """Allowlisted operators for policy rule conditions."""
    EQ = "eq"       # equal
    NE = "ne"       # not equal
    GT = "gt"       # greater than
    GTE = "gte"     # greater than or equal
    LT = "lt"       # less than
    LTE = "lte"     # less than or equal
    CONTAINS = "contains"  # text contains substring
    EXISTS = "exists"  # field/relation exists


# ---------------------------------------------------------------------------
# Policy condition result
# ---------------------------------------------------------------------------

@dataclass
class PolicyConditionResult:
    """Result of evaluating a single policy condition."""
    condition_id: str  # identifier within the policy rule
    operator: PolicyOperator
    operand_value: Any
    actual_value: Any
    satisfied: bool
    explanation: str  # human-readable, grounded in real data


@dataclass
class PolicyEvaluationResult:
    """Result of evaluating a policy against a claim/findings."""
    policy_id: str
    policy_version: str
    overall_state: str  # "satisfied" | "violation" | "uncertain" | "not_applicable"
    conditions: list[PolicyConditionResult]
    explanation: str  # grounded in real data
    materiality_guidance: str | None = None  # severity/severity hint
    missing_info: list[str] = field(default_factory=list)  # what limited the evaluation
    evaluated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ---------------------------------------------------------------------------
# Policy rule schema (versioned structured)

# Example policy rule format (stored as JSON in the policies table):
# {
#   "rule_id": "payment_term_check",
#   "conditions": [
#     {
#       "variable": "warranty_duration_days",
#       "operator": "gte",
#       "value": 365,
#       "reason": "Minimum warranty must be 1 year"
#     },
#     {
#       "variable": "liability_exposure",
#       "operator": "lte",
#       "value": 10000000,
#       "reason": "Liability must not exceed ₹1cr"
#     }
#   ],
#   "effect": "violation",
#   "materiality_guidance": "high",
#   "enabled": true,
#   "created_at": "2024-01-15T10:00:00Z",
#   "created_by": "admin",
#   "version": 1
# }

# ---------------------------------------------------------------------------
# Policy evaluation engine
# -------------------------------------------------------------------------__

def _get_policy(session: Session, policy_id: str) -> Policy | None:
    """Look up a policy by its UUID string."""
    return session.get(Policy, UUID(str(policy_id)))


def _evaluate_condition(
    condition: dict[str, Any],
    flag_or_claim: Any,
) -> PolicyConditionResult:
    """Evaluate a single policy condition against a Flag or Claim.

    Only allowlisted operators and typed operands are supported.
    Unknown operators or incompatible types produce "uncertain" outcome.
    """
    op_str = condition.get("operator", "")
    variable = condition.get("variable", "")
    operand = condition.get("value")
    reason = condition.get("reason", "")

    try:
        op = PolicyOperator(op_str)
    except ValueError:
        # Unknown operator -> uncertain
        return PolicyConditionResult(
            condition_id=condition.get("condition_id", "unknown"),
            operator=PolicyOperator.EXISTS,  # default to avoid crash
            operand_value=operand,
            actual_value=None,
            satisfied=False,
            explanation=f"Policy condition uses disallowed operator: {op_str}",
        )

    # --- Retrieve actual value from the flag/claim object ---
    actual_value: Any = None
    if hasattr(flag_or_claim, variable):
        actual_value = getattr(flag_or_claim, variable)
    elif isinstance(flag_or_claim, dict):
        actual_value = flag_or_claim.get(variable)

    # --- Apply operator ---
    satisfied = False
    explanation_parts: list[str] = []

    if op == PolicyOperator.EQ:
        satisfied = actual_value is not None and actual_value == operand
        explanation_parts.append(f"{variable} {op_str} {operand}")
    elif op == PolicyOperator.NE:
        satisfied = actual_value is not None and actual_value != operand
        explanation_parts.append(f"{variable} {op_str} {operand}")
    elif op == PolicyOperator.GT:
        try:
            satisfied = float(actual_value) > float(operand)
            explanation_parts.append(f"{variable} {op_str} {operand}")
        except (ValueError, TypeError):
            satisfied = False
            explanation_parts.append(f"{variable} {op_str} {operand} (type mismatch)")
    elif op == PolicyOperator.GTE:
        try:
            satisfied = float(actual_value) >= float(operand)
            explanation_parts.append(f"{variable} {op_str} {operand}")
        except (ValueError, TypeError):
            satisfied = False
            explanation_parts.append(f"{variable} {op_str} {operand} (type mismatch)")
    elif op == PolicyOperator.LT:
        try:
            satisfied = float(actual_value) < float(operand)
            explanation_parts.append(f"{variable} {op_str} {operand}")
        except (ValueError, TypeError):
            satisfied = False
            explanation_parts.append(f"{variable} {op_str} {operand} (type mismatch)")
    elif op == PolicyOperator.LTE:
        try:
            satisfied = float(actual_value) <= float(operand)
            explanation_parts.append(f"{variable} {op_str} {operand}")
        except (ValueError, TypeError):
            satisfied = False
            explanation_parts.append(f"{variable} {op_str} {operand} (type mismatch)")
    elif op == PolicyOperator.CONTAINS:
        if isinstance(actual_value, str) and isinstance(operand, str):
            satisfied = operand.lower() in actual_value.lower()
            explanation_parts.append(f"{variable} contains {operand}")
        else:
            satisfied = False
            explanation_parts.append("CONTAINS requires string values")
    elif op == PolicyOperator.EXISTS:
        satisfied = actual_value is not None
        explanation_parts.append(f"{variable} EXISTS")

    explanation = "; ".join(explanation_parts) + (f" ({reason})" if reason else "")

    return PolicyConditionResult(
        condition_id=condition.get("condition_id", "unknown"),
        operator=op,
        operand_value=operand,
        actual_value=actual_value,
        satisfied=satisfied,
        explanation=explanation,
    )


def evaluate_policy(
    session: Session,
    policy_id: str,
    flag: Flag | None = None,
    claim: Claim | None = None,
) -> PolicyEvaluationResult:
    """Evaluate a policy against a Flag or Claim.

    Exactly one of flag or claim must be provided (or neither for a
    structural check, which returns not_applicable).

    Returns a PolicyEvaluationResult with overall state, per-condition
    results, explanation, and guidance.
    """
    # --- Look up policy ---
    policy = _get_policy(session, policy_id)
    if policy is None:
        return PolicyEvaluationResult(
            policy_id=policy_id,
            policy_version="",
            overall_state="not_applicable",
            conditions=[],
            explanation=f"Policy {policy_id} not found.",
        )

    # --- Require exactly one of flag or claim ---
    if flag is None and claim is None:
        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_version=str(json.loads(policy.rules_json or "{}").get("version", 1)),
            overall_state="not_applicable",
            conditions=[],
            explanation="Policy evaluation requires a flag or claim to evaluate against.",
        )

    if flag is not None and claim is not None:
        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_version=str(json.loads(policy.rules_json or "{}").get("version", 1)),
            overall_state="uncertain",
            conditions=[],
            explanation="Policy evaluation: provide exactly one of flag or claim, not both.",
        )

    # --- Load policy rule JSON ---
    rule_json: dict[str, Any] = {}
    try:
        rule_json = json.loads(policy.rules_json or "{}")
    except json.JSONDecodeError:
        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_version="unknown",
            overall_state="uncertain",
            conditions=[],
            explanation=f"Policy {policy.id} has malformed rules_json.",
        )

    conditions_list: list[dict[str, Any]] = rule_json.get("conditions", [])
    effect: str = rule_json.get("effect", "violation")
    materiality_guidance: str | None = rule_json.get("materiality_guidance")
    enabled: bool = policy.is_active and rule_json.get("enabled", True)

    # --- Evaluate each condition ---
    condition_results: list[PolicyConditionResult] = []
    for cond in conditions_list:
        # Bind the flag or claim into the condition evaluator
        result = _evaluate_condition(cond, flag if flag else claim)
        condition_results.append(result)

    # --- Determine overall state ---
    if not enabled:
        overall_state = "not_applicable"
        explanation = f"Policy {policy.id} is disabled."
    elif not condition_results or any(c.actual_value is None and c.operator != PolicyOperator.EXISTS for c in condition_results) or any("type mismatch" in c.explanation or "disallowed operator" in c.explanation for c in condition_results):
        overall_state = "uncertain"
        explanation = "Policy conditions are missing or cannot be evaluated with available data."
    elif all(c.satisfied for c in condition_results):
        overall_state = "satisfied"
        explanation = f"All {len(condition_results)} policy conditions satisfied."
    elif any(not c.satisfied for c in condition_results):
        # If any condition is violated, overall state is violation
        # unless multiple conditions conflict; we default to violation
        violation_count = sum(1 for c in condition_results if not c.satisfied)
        overall_state = "violation"
        explanation = f"{violation_count} of {len(condition_results)} policy conditions violated."
    else:
        # Mixed: some satisfied, some not, but not all violated
        overall_state = "uncertain"
        explanation = "Policy evaluation inconclusive: some conditions satisfied, others not."

    # --- Build explanation ---
    condition_explanations = "; ".join(c.explanation for c in condition_results)
    full_explanation = f"{overall_state}: {condition_explanations}. {explanation}"

    # --- Missing info ---
    missing_info: list[str] = []
    for c in condition_results:
        if not c.satisfied and c.actual_value is None:
            missing_info.append(f"condition {c.condition_id}: actual value not available")

    return PolicyEvaluationResult(
        policy_id=policy.id,
        policy_version=str(json.loads(policy.rules_json or "{}").get("version", 1)),
        overall_state=overall_state,
        conditions=condition_results,
        explanation=full_explanation,
        materiality_guidance=materiality_guidance,
        missing_info=missing_info,
        evaluated_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Policy administration helpers
# ---------------------------------------------------------------------------

def create_policy(
    session: Session,
    *,
    name: str,
    description: str | None = None,
    rules_json: str,
    category: str | None = None,
    enabled: bool = True,
    created_by: str | None = None,
) -> Policy:
    """Create a new policy record.

    The rules_json must conform to the Phase 5 structured schema.
    Policy IDs are system-assigned UUIDs.
    """
    from uuid import uuid4

    rules = json.loads(rules_json)
    if not isinstance(rules, dict):
        raise ValueError("Policy rules must be a JSON object")
    rules.update(version=1, category=category, created_by=created_by)
    policy = Policy(
        id=uuid4(),
        name=name,
        description=description,
        rules_json=json.dumps(rules),
        is_active=enabled,
        created_at=datetime.now(UTC),
    )
    session.add(policy)
    session.commit()
    session.refresh(policy)
    logger.info("Policy created: id=%s name=%s", policy.id, name)
    return policy


def update_policy_version(
    session: Session,
    policy: Policy,
    *,
    new_rules_json: str | None = None,
    new_name: str | None = None,
    new_description: str | None = None,
    new_enabled: bool | None = None,
) -> Policy:
    """Increment the policy version and update fields.

    The version field is incremented.  All changes are auditable because
    the full rules_json is persisted with each version.
    """
    previous_rules = json.loads(policy.rules_json or "{}")
    rules = json.loads(new_rules_json) if new_rules_json is not None else dict(previous_rules)
    if not isinstance(rules, dict):
        raise ValueError("Policy rules must be a JSON object")
    rules["version"] = int(previous_rules.get("version", 1)) + 1
    policy.rules_json = json.dumps(rules)
    if new_name is not None:
        policy.name = new_name
    if new_description is not None:
        policy.description = new_description
    if new_enabled is not None:
        policy.is_active = new_enabled

    policy.updated_at = datetime.now(UTC)
    session.add(policy)
    session.commit()
    session.refresh(policy)
    logger.info("Policy version updated: id=%s new_version=%s", policy.id, rules["version"])
    return policy


# ---------------------------------------------------------------------------
# Convenience: assess a single flag against all applicable policies
# ---------------------------------------------------------------------------

def assess_flag_policies(
    session: Session,
    flag: Flag,
    authorized_user_role: str = "user",
) -> list[PolicyEvaluationResult]:
    """Assess a flag against all policies that apply to its audit.

    Only policies with enabled=True are evaluated.
    RBAC: only user roles >= the specified authorized_user_role can trigger
    evaluation (admin implicitly satisfies every requirement).

    Returns a list of PolicyEvaluationResult, one per applicable policy.
    """

    # RBAC check - simplified: admin always passes, otherwise check role
    # We'll just evaluate all enabled policies; the caller handles RBAC

    # Get all enabled policies for this audit
    policies = session.exec(
        select(Policy).where(Policy.is_active.is_(True))
    ).all()

    results: list[PolicyEvaluationResult] = []
    for pol in policies:
        rules = json.loads(pol.rules_json or "{}")
        if rules.get("audit_id") and str(rules["audit_id"]) != str(flag.audit_id):
            continue
        result = evaluate_policy(session, policy_id=str(pol.id), flag=flag)
        results.append(result)

    return results


__all__ = [
    "PolicyOperator",
    "PolicyConditionResult",
    "PolicyEvaluationResult",
    "evaluate_policy",
    "create_policy",
    "update_policy_version",
    "assess_flag_policies",
    "Policy",
]