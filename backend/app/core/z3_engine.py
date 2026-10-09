"""Z3 Formal Verification Engine — Phase 5.

Evaluates whether supported structured claims are mathematically consistent
with extracted facts and explicit business constraints.

Constraint inputs are typed and validated.  Arbitrary natural-language text
is NOT accepted as executable solver code.
"""

from __future__ import annotations

import json
import logging
import uuid
from z3 import Real, Int, Bool, unknown
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlmodel import Session

from app.models import Audit, Claim

logger = logging.getLogger("tathya.z3_engine")

# ---------------------------------------------------------------------------
# Solver configuration
# ---------------------------------------------------------------------------

SOLVER_TIMEOUT_SECONDS = 30  # bounded timeout
GENESIS_HASH = "0" * 64


# ---------------------------------------------------------------------------
# Constraint typed schema
# ---------------------------------------------------------------------------

class ConstraintType(str, Enum):
    """Typed constraint categories supported by the Z3 engine."""
    NUMERIC_EQ = "numeric_eq"       # n == value
    NUMERIC_NE = "numeric_ne"       # n != value
    NUMERIC_LT = "numeric_lt"       # n < value
    NUMERIC_LE = "numeric_le"       # n <= value
    NUMERIC_GT = "numeric_gt"       # n > value
    NUMERIC_GE = "numeric_ge"       # n >= value
    CURRENCY_EQ = "currency_eq"     # ₹ amount equality
    DURATION_EQ = "duration_eq"     # days/years equality
    DATE_EQ = "date_eq"             # unambiguous date equality
    DATE_LT = "date_lt"             # unambiguous date before
    DATE_LE = "date_le"             # unambiguous date on or before
    KEYWORD_EQ = "keyword_eq"       # text token equality


# ---------------------------------------------------------------------------
# Proof result contract
# ---------------------------------------------------------------------------

@dataclass
class Z3ProofResult:
    """Result of a Z3 verification run."""
    proof_id: str  # generated UUID string
    status: str    # "SAT", "UNSAT", "UNKNOWN"
    constraints: list[dict[str, Any]]  # the exact normalized constraints passed to solver
    solver_time_seconds: float
    explanation: str  # human-readable summary grounded in real inputs
    unsatisfiable_core: list[dict[str, Any]] | None = None  # conflicting constraints if UNSAT
    captured_at: str = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat())
    schema_version: str = "5.0"


# ---------------------------------------------------------------------------
# Core Z3 solving function
# ---------------------------------------------------------------------------

def _make_solver(timeout_seconds: int = SOLVER_TIMEOUT_SECONDS) -> Any:
    """Create a new Z3 solver instance with timeout."""
    from z3 import Solver
    s = Solver()
    s.set("timeout", timeout_seconds * 1000)  # Z3 uses milliseconds
    return s


def _parse_numeric_value(val: str | float | int | None) -> Any:
    """Parse a numeric value for Z3, returning a Z3 Real or Int."""
    from z3 import Real as Z3Real, Int as Z3Int
    try:
        f = float(val)
        return Z3Real(f"{f:.10f}")
    except (ValueError, TypeError):
        try:
            i = int(val)
            return Z3Int(str(i))
        except (ValueError, TypeError):
            return None


def _check_constraint_types(constraints: list[dict[str, Any]]) -> bool:
    """Validate that all constraint dicts have required fields and allowed types."""
    allowed_keys = {"type", "variable", "operator", "value"}
    for c in constraints:
        if not isinstance(c, dict):
            return False
        if not set(c.keys()).issubset(allowed_keys | {"reason"}):
            return False
        if c.get("type") not in {
            "numeric", "currency", "duration", "date", "keyword"
        }:
            return False
    return True


# ---------------------------------------------------------------------------
# Public API: solve_z3_proof
# ---------------------------------------------------------------------------

def solve_z3_proof(
    session: Session,
    audit_id: str,
    claim_id: str | None,
    constraints: list[dict[str, Any]],
    schema_version: str = "5.0",
) -> Z3ProofResult:
    """Run Z3 proof on typed constraints.

    Args:
        session: SQLModel session
        audit_id: audit identifier
        claim_id: optional claim identifier
        constraints: list of constraint dicts, each with keys:
            - type: "numeric" | "currency" | "duration" | "date" | "keyword"
            - variable: str  # Z3 variable name
            - operator: one of the numeric/currency/duration/date operators
            - value: numeric or string literal
            - reason: str  # optional human rationale
        schema_version: version string for the proof

    Returns:
        Z3ProofResult with status, constraints, explanation, etc.

    Raises:
        ValueError: if constraints fail schema validation
    """
    # --- Schema validation ---
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("constraints must be a non-empty list")

    if not _check_constraint_types(constraints):
        raise ValueError("constraints contain disallowed types or missing fields")

    # --- Record start ---
    import uuid as _uuid
    proof_id = _uuid.uuid4().hex[:16]
    started = __import__("datetime").datetime.now(__import__("datetime").UTC)

    # --- Build Z3 constraints ---
    s = _make_solver()

    z3_constraints: list[Any] = []
    explanation_parts: list[str] = []
    unsat_core_candidates: list[dict[str, Any]] = []

    for c in constraints:
        ctype = c.get("type", "")
        var_name = c.get("variable", "")
        operator = c.get("operator", "")
        value = c.get("value", "")
        reason = c.get("reason", "")

        # Create Z3 variable (Real for numeric, Bool for keyword)
        if ctype in ("numeric", "currency", "duration"):
            var = Real(f"z3_{var_name}")
            z3_val = _parse_numeric_value(value)
            if z3_val is None:
                logger.warning("Z3: could not parse numeric value %s for constraint %s", value, c)
                continue
        elif ctype == "date":
            # Date constraints use Int for day-count comparison simplified
            var = Int(f"z3_{var_name}")
            z3_val = _parse_numeric_value(value)
            if z3_val is None:
                logger.warning("Z3: could not parse date value %s for constraint %s", value, c)
                continue
        elif ctype == "keyword":
            var = Bool(f"z3_{var_name}")
            # keyword equality: treat as boolean proposition
            z3_val = value.lower() in ("true", "yes", "y", "1")
        else:
            logger.warning("Z3: unsupported constraint type %s", ctype)
            continue

        # Apply operator
        if operator == "eq":
            s.add(var == z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "eq", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} == {value} ({reason})" if reason else f"{var_name} == {value}")
        elif operator == "neq":
            s.add(var != z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "neq", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} != {value} ({reason})" if reason else f"{var_name} != {value}")
        elif operator == "lt":
            s.add(var < z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "lt", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} < {value} ({reason})" if reason else f"{var_name} < {value}")
        elif operator == "le":
            s.add(var <= z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "le", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} <= {value} ({reason})" if reason else f"{var_name} <= {value}")
        elif operator == "gt":
            s.add(var > z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "gt", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} > {value} ({reason})" if reason else f"{var_name} > {value}")
        elif operator == "ge":
            s.add(var >= z3_val)
            z3_constraints.append({"type": ctype, "variable": var_name, "operator": "ge", "value": str(value), "reason": reason})
            explanation_parts.append(f"{var_name} >= {value} ({reason})" if reason else f"{var_name} >= {value}")
        else:
            logger.warning("Z3: unsupported operator %s", operator)
            continue

    # --- Solve ---
    solve_start = __import__("time").time()
    try:
        result = s.check()
    except Exception as exc:
        logger.exception("Z3 solver exception")
        result = unknown

    solve_time = __import__("time").time() - solve_start

    # --- Interpret result ---
    from z3 import sat as _sat, unsat as _unsat

    if result == _sat:
        status = "SAT"
        explanation = f"Constraints are satisfiable together. {', '.join(explanation_parts) if explanation_parts else ''}"
    elif result == _unsat:
        status = "UNSAT"
        # Collect unsatisfiable core candidates from solver
        core = s.unsat_core() if hasattr(s, "unsat_core") else None
        if core:
            for c in core:
                unsat_core_candidates.append({
                    "variable": str(c).replace("z3_", ""),
                    "operator": "eq",
                    "value": str(c),
                    "reason": "core conflict",
                })
        explanation = f"Constraints are inconsistent together. {', '.join(explanation_parts) if explanation_parts else ''}"
    else:
        status = "UNKNOWN"
        explanation = f"Solver could not establish satisfiability or inconsistency within {SOLVER_TIMEOUT_SECONDS}s timeout. {', '.join(explanation_parts) if explanation_parts else ''}"

    # --- Build result ---
    from datetime import UTC as _UTC
    proof_result = Z3ProofResult(
        proof_id=proof_id,
        status=status,
        constraints=z3_constraints,
        solver_time_seconds=round(solve_time, 4),
        explanation=explanation.strip(),
        unsatisfiable_core=unsat_core_candidates if status == "UNSAT" else None,
        captured_at=__import__("datetime").datetime.now(_UTC).isoformat(),
        schema_version=schema_version,
    )

    # --- Persist proof to database ---
    try:
        from app.models import Proof, ProofCreate

        # Get audit and optional claim
        audit = session.get(Audit, audit_id) if audit_id else None
        claim = session.get(Claim, claim_id) if claim_id else None

        proof_create = ProofCreate(
            audit_id=audit.id if audit else uuid.UUID(int=0),
            claim_id=claim.id if claim else None,
            solver="z3",
            query=json.dumps(
                {"constraints": constraints, "schema_version": schema_version},
                ensure_ascii=False,
            ),
            result=proof_result.status,
            detail=proof_result.explanation,
        )

        proof = Proof(**proof_create.model_dump(), id=_uuid.uuid4())
        session.add(proof)
        session.commit()
        session.refresh(proof)
        logger.info("Z3 proof %s persisted to database (status=%s)", proof_id, proof_result.status)
    except Exception as exc:
        logger.warning("Failed to persist Z3 proof: %s", exc)

    return proof_result


# ---------------------------------------------------------------------------
# Convenience: numeric constraint builder
# ---------------------------------------------------------------------------

def build_numeric_constraint(
    variable: str,
    operator: str,
    value: float | int | str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a typed numeric constraint dict for Z3 engine."""
    return {
        "type": "numeric",
        "variable": variable,
        "operator": operator,
        "value": str(value),
        "reason": reason or "",
    }


# ---------------------------------------------------------------------------
# Convenience: currency constraint builder
# ---------------------------------------------------------------------------

def build_currency_constraint(
    variable: str,
    amount: float,
    currency: str = "INR",
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a typed currency constraint dict for Z3 engine."""
    return {
        "type": "currency",
        "variable": variable,
        "operator": "eq",
        "value": f"{currency} {amount:.2f}",
        "reason": reason or "",
    }


# ---------------------------------------------------------------------------
# Convenience: duration constraint builder
# ---------------------------------------------------------------------------

def build_duration_constraint(
    variable: str,
    value: int | float,
    unit: str = "days",
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a typed duration constraint dict for Z3 engine."""
    return {
        "type": "duration",
        "variable": variable,
        "operator": "eq",
        "value": f"{value} {unit}",
        "reason": reason or "",
    }


# ---------------------------------------------------------------------------
# Convenience: date constraint builder (unambiguous form)
# ---------------------------------------------------------------------------

def build_date_constraint(
    variable: str,
    year: int,
    month: int | None = None,
    day: int | None = None,
    operator: str = "eq",
    reason: str | None = None,
) -> dict[str, Any]:
    """Build a typed date constraint dict for Z3 engine.

    Only unambiguous dates (with year, and optionally month/day) are supported.
    """
    value_parts = [str(year)]
    if month is not None:
        value_parts.append(str(month))
    if day is not None:
        value_parts.append(str(day))
    value_str = "-".join(value_parts)

    return {
        "type": "date",
        "variable": variable,
        "operator": operator,
        "value": value_str,
        "reason": reason or "",
    }


def solve_constraints(
    goals: list[str] | None = None,
    assumptions: list[str] | None = None,
    numeric_constraints: list[dict[str, Any]] | None = None,
    max_timeout_seconds: int = 10,
) -> dict[str, Any]:
    """Standalone Z3 proof sandbox compatible with SolveProofRequest.

    Translates goals/assumptions/numeric_constraints into the internal
    constraint format and returns a dict matching SolveProofResult.
    """
    from app.core.proof_sandbox import solve
    return solve(goals or [], assumptions or [], numeric_constraints or [], max_timeout_seconds)



__all__ = [
    "Z3ProofResult",
    "ConstraintType",
    "solve_z3_proof",
    "solve_constraints",
    "build_numeric_constraint",
    "build_currency_constraint",
    "build_duration_constraint",
    "build_date_constraint",
]