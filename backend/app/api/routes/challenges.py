"""Phase 6 Adversarial Verification API Routes.

Wires together:
1. Jhooth Chhupao: Adversarial Scenario Catalogue
2. Jhooth Injector: Safe candidate generation & unified diffs
3. Judge WOW: Adversarial review with prompt-injection defense & evidence integrity
4. Proof Sandbox: Z3 deterministic formal constraint solver
5. Challenge Results: Ground truth performance metrics & evaluations
6. Platform Control Metrics: Aggregate trust & audit telemetry
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep, ReviewerDep
from app.core.challenge_results import (
    aggregate_challenge_results,
)
from app.core.injector import generate_candidate
from app.core.jhooth_chhupao import (
    AdversarialScenario,
    AdversarialScenarioCatalogue,
)
from app.core.judge_wow import (
    EvidenceIntegrityError,
    InstructionInjectionError,
    run_adversarial_review,
)
from app.core.z3_engine import solve_constraints
from app.models import Audit, Flag, Passport, User
from app.core.challenge_runner import TrialRequest, start_trial, trial_results

challenges_router = APIRouter(prefix="/challenges", tags=["challenges"])
inject_router = APIRouter(prefix="/inject", tags=["injection"])
judge_router = APIRouter(prefix="/judge", tags=["judge"])
proof_router = APIRouter(prefix="/proof", tags=["proof"])
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])

@challenges_router.post("/{audit_id}/trials", status_code=201)
def run_document_trial(audit_id: uuid.UUID, payload: TrialRequest, session: SessionDep, reviewer: ReviewerDep) -> dict:
    from app.api.routes.audits import _get_audit
    base = _get_audit(session, audit_id, reviewer)
    try:
        return start_trial(session, base, reviewer.id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@challenges_router.get("/{audit_id}/trials")
def read_document_trials(audit_id: uuid.UUID, session: SessionDep, reviewer: ReviewerDep) -> dict:
    from app.api.routes.audits import _get_audit
    _get_audit(session, audit_id, reviewer)
    return trial_results(session, audit_id)


# ---------------------------------------------------------------------------
# Default Scenario Catalogue (Phase 6 Deterministic Scenarios)
# ---------------------------------------------------------------------------

def _build_default_catalogue() -> AdversarialScenarioCatalogue:
    catalogue = AdversarialScenarioCatalogue()
    
    defaults = [
        AdversarialScenario(
            id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
            version="scenario_v001",
            name="Claim Polarity Inversion (Negation)",
            pattern_type="claim_negation",
            claim_modification="negate",
            evidence_undermine="none",
            injection_method="prefix_negation",
            severity="HIGH",
            description="Inverts the polarity of a factual assertion while preserving domain vocabulary.",
            meta={"category": "logic", "blast_radius": "HIGH"},
        ),
        AdversarialScenario(
            id=uuid.UUID("22222222-2222-4222-8222-222222222222"),
            version="scenario_v002",
            name="Metric Value Escalation (50L vs 41.6L)",
            pattern_type="numeric_manipulation",
            claim_modification="flip_domain",
            evidence_undermine="distort_quote",
            injection_method="numeric_substitution",
            severity="CRITICAL",
            description="Alters contract pricing, caps, or fiscal amounts to contradict official audited sheets.",
            meta={"category": "financial", "blast_radius": "CRITICAL"},
        ),
        AdversarialScenario(
            id=uuid.UUID("33333333-3333-4333-8333-333333333333"),
            version="scenario_v003",
            name="Delivery Date Acceleration",
            pattern_type="date_manipulation",
            claim_modification="add_exception",
            evidence_undermine="none",
            injection_method="date_shift",
            severity="HIGH",
            description="Shifts delivery milestones earlier than permitted by the master procurement schedule.",
            meta={"category": "logistics", "blast_radius": "HIGH"},
        ),
        AdversarialScenario(
            id=uuid.UUID("44444444-4444-4444-8444-444444444444"),
            version="scenario_v004",
            name="Authority & Department Entity Swap",
            pattern_type="entity_swap",
            claim_modification="flip_domain",
            evidence_undermine="swap_source",
            injection_method="entity_substitution",
            severity="MEDIUM",
            description="Swaps the governing department or ministry to attribute approvals to an unverified authority.",
            meta={"category": "governance", "blast_radius": "MEDIUM"},
        ),
        AdversarialScenario(
            id=uuid.UUID("55555555-5555-4555-8555-555555555555"),
            version="scenario_v005",
            name="Critical Late-Fee / Penalty Omission",
            pattern_type="omission_induction",
            claim_modification="remove_quantifier",
            evidence_undermine="suppress_clause",
            injection_method="clause_removal",
            severity="CRITICAL",
            description="Omits critical liability or penalty clauses (e.g. Net 45 without late fee) to create material exposure.",
            meta={"category": "legal", "blast_radius": "CRITICAL"},
        ),
        AdversarialScenario(
            id=uuid.UUID("66666666-6666-4666-8666-666666666666"),
            version="scenario_v006",
            name="Instruction Injection in Source Annotation",
            pattern_type="evidence_tampering",
            claim_modification="add_exception",
            evidence_undermine="inject_prompt",
            injection_method="prompt_override",
            severity="CRITICAL",
            description="Embeds 'ignore previous instructions' directives within citation text to attempt reviewer subversion.",
            meta={"category": "security", "blast_radius": "CRITICAL"},
        ),
    ]
    
    for s in defaults:
        catalogue.scenarios[s.version] = s
    catalogue._version_counter = len(defaults)
    return catalogue

_CATALOGUE = _build_default_catalogue()


# ---------------------------------------------------------------------------
# 1. Challenge Library Endpoints
# ---------------------------------------------------------------------------

@challenges_router.get("/scenarios")
def list_scenarios(current_user: CurrentUser) -> dict[str, Any]:
    scenarios_list = [s.to_dict() for s in _CATALOGUE.scenarios.values()]
    return {
        "data": scenarios_list,
        "count": len(scenarios_list),
    }


@challenges_router.get("/scenarios/{version}")
def get_scenario(version: str, current_user: CurrentUser) -> dict[str, Any]:
    scenario = _CATALOGUE.get_scenario(version)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario {version} not found")
    return scenario.to_dict()


# ---------------------------------------------------------------------------
# 2. Injector Endpoints
# ---------------------------------------------------------------------------

class InjectionPayload(BaseModel):
    original_text: str
    injected_text: str
    pattern: str = "negate"
    severity: str = "MEDIUM"
    base_document_id: str | None = None
    location: dict[str, Any] = {}
    rationale: str = ""
    meta: dict[str, Any] = {}


@inject_router.post("/candidate")
def generate_injection_candidate(payload: InjectionPayload, current_user: CurrentUser) -> dict[str, Any]:
    try:
        base_doc_uuid = uuid.UUID(payload.base_document_id) if payload.base_document_id else None
        candidate = generate_candidate(
            original_text=payload.original_text,
            injected_text=payload.injected_text,
            pattern=payload.pattern,
            severity=payload.severity,
            base_document_id=base_doc_uuid,
            location=payload.location,
            rationale=payload.rationale,
            meta=payload.meta,
        )
        return {
            "candidate": candidate.to_dict(),
            "changed": candidate.changed,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Injection generation failed: {str(e)}")


# ---------------------------------------------------------------------------
# 3. Judge WOW Adversarial Review Endpoints
# ---------------------------------------------------------------------------

class JudgeEvidenceItem(BaseModel):
    id: uuid.UUID
    quote: str = Field(min_length=1, max_length=100000)
    location: str = ""
    support_type: str = "supports"
    score: float = 0.95


class JudgeAdversarialPayload(BaseModel):
    claim_text: str
    claim_category: str = "general"
    evidence_list: list[JudgeEvidenceItem] = []
    strict_injection_check: bool = True


@judge_router.post("/adversarial")
def judge_adversarial_review(payload: JudgeAdversarialPayload, current_user: CurrentUser) -> dict[str, Any]:
    try:
        ev_dicts = []
        for ev in payload.evidence_list:
            ev_id = ev.id
            ev_dicts.append({
                "id": ev_id,
                "quote": ev.quote,
                "location": ev.location,
                "support_type": ev.support_type,
                "score": ev.score,
            })
        
        review = run_adversarial_review(
            claim_text=payload.claim_text,
            claim_category=payload.claim_category,
            evidence_list=ev_dicts,
            strict_injection_check=payload.strict_injection_check,
        )
        return {"review": review.to_dict()}
    except InstructionInjectionError as e:
        raise HTTPException(status_code=422, detail=f"Prompt injection detected: {str(e)}")
    except EvidenceIntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Evidence integrity failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adversarial review failed: {str(e)}")


# ---------------------------------------------------------------------------
# 4. Proof Sandbox (Z3 Deterministic Solver)
# ---------------------------------------------------------------------------

class SolveProofPayload(BaseModel):
    goals: list[str] = []
    assumptions: list[str] = []
    numeric_constraints: list[dict[str, Any]] = []
    max_timeout_seconds: int = Field(default=10, ge=1, le=30)


@proof_router.post("/solve")
def solve_proof(payload: SolveProofPayload, current_user: CurrentUser) -> dict[str, Any]:
    try:
        result = solve_constraints(
            goals=payload.goals,
            assumptions=payload.assumptions,
            numeric_constraints=payload.numeric_constraints,
            max_timeout_seconds=payload.max_timeout_seconds,
        )
        return result
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:
        return {
            "satisfiable": None,
            "error": str(e),
            "timed_out": False,
            "proof": None,
        }


# ---------------------------------------------------------------------------
# 5. Challenge Results & Ground Truth Evaluation
# ---------------------------------------------------------------------------

@challenges_router.get("/results")
def get_challenge_results(current_user: CurrentUser) -> dict[str, Any]:
    # No measurements are claimed before persisted evaluations are available.
    metrics, quality_report = aggregate_challenge_results([], min_trials_per_category=5)
    return {"metrics": metrics.to_dict(), "quality_report": quality_report, "results": []}


# ---------------------------------------------------------------------------
# 6. Platform Control Metrics
# ---------------------------------------------------------------------------

@metrics_router.get("")
def get_control_metrics(session: SessionDep, reviewer: ReviewerDep) -> dict[str, Any]:
    total_audits = int(session.exec(select(func.count(Audit.id))).one() or 0)
    
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    audits_last_7 = int(
        session.exec(
            select(func.count(Audit.id)).where(Audit.created_at >= seven_days_ago)
        ).one()
        or 0
    )
    
    total_findings = int(session.exec(select(func.count(Flag.id))).one() or 0)
    pending_review = int(
        session.exec(
            select(func.count(Flag.id)).where(Flag.status == "pending")
        ).one()
        or 0
    )
    
    passports_issued = int(session.exec(select(func.count(Passport.id))).one() or 0)
    critical_risk_count = int(
        session.exec(
            select(func.count(Audit.id)).where(Audit.critical_risk == True)  # noqa: E712
        ).one()
        or 0
    )
    
    audits = session.exec(select(Audit)).all()
    avg_ai_score = (
        sum(a.ai_score for a in audits if a.ai_score is not None) / max(1, len([a for a in audits if a.ai_score is not None]))
        if audits
        else 0.0
    )
    avg_reviewed_score = (
        sum(a.reviewed_score for a in audits if a.reviewed_score is not None) / max(1, len([a for a in audits if a.reviewed_score is not None]))
        if audits
        else 0.0
    )
    
    reviewers_count = int(
        session.exec(
            select(func.count(User.id)).where(User.role.in_(["reviewer", "admin"]))  # type: ignore[attr-defined]
        ).one()
        or 0
    )
    
    # Severity breakdown
    severities = session.exec(select(Flag.severity)).all()
    sev_counts: dict[str, int] = {}
    for s in severities:
        if s:
            sev_counts[s] = sev_counts.get(s, 0) + 1
            
    # Score bands
    bands: dict[str, int] = {}
    for a in audits:
        b = a.score_band or "unscored"
        bands[b] = bands.get(b, 0) + 1

    return {
        "total_audits": total_audits,
        "audits_last_7_days": audits_last_7,
        "total_findings": total_findings,
        "pending_review_count": pending_review,
        "avg_reviewed_score": round(avg_reviewed_score, 2),
        "avg_ai_score": round(avg_ai_score, 2),
        "critical_risk_count": critical_risk_count,
        "passports_issued": passports_issued,
        "verify_token_views_last_7_days": None,
        "challenge_count": 0,
        "users_with_reviewer_role": reviewers_count,
        "audits_by_score_band": bands,
        "top_severity_counts": sev_counts,
        "generated_at": datetime.now(UTC).isoformat(),
    }
