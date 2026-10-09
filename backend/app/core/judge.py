"""ML Judge — Phase 4.

Evidence-constrained LLM-based claim verification.
Supplements deterministic grounding; never overrides conclusive fact-based contradictions.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.llm import LLMError, LLMRequest, llm_adapter

logger = logging.getLogger("tathya.judge")


@dataclass
class JudgeResult:
    """Result of ML Judge verification."""
    status: str  # supported, contradicted, unsupported, uncertain
    confidence: float
    reason: str
    primary_evidence_id: uuid.UUID | None
    referenced_evidence_ids: list[uuid.UUID]
    uncertainty_reason: str | None = None
    provider: str | None = None
    model: str | None = None
    cached: bool = False
    validated: bool = True


class JudgeValidationError(ValueError):
    """Raised when Judge output fails validation."""
    pass


# Schema for structured Judge output
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["supported", "contradicted", "unsupported", "uncertain"],
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string", "minLength": 1, "maxLength": 500},
        "primary_evidence_id": {"type": ["string", "null"], "format": "uuid"},
        "referenced_evidence_ids": {
            "type": "array",
            "items": {"type": "string", "format": "uuid"},
        },
        "uncertainty_reason": {"type": ["string", "null"], "maxLength": 300},
    },
    "required": ["status", "confidence", "reason", "primary_evidence_id", "referenced_evidence_ids"],
    "additionalProperties": False,
}


def build_judge_prompt(claim_text: str, claim_category: str, evidence_context: list[dict]) -> str:
    """Build the prompt for ML Judge verification."""
    evidence_json = json.dumps(evidence_context, ensure_ascii=False, indent=2)
    return f"""Verify if the following claim is grounded in the provided evidence.

Claim: {claim_text}
Claim category: {claim_category}

Evidence (only these items are authorized for this verification):
{evidence_json}

Determine if the claim is SUPPORTED, CONTRADICTED, UNSUPPORTED, or UNCERTAIN based ONLY on the provided evidence.
- SUPPORTED: Evidence directly confirms the claim
- CONTRADICTED: Evidence explicitly contradicts the claim (requires opposing evidence with factual conflict)
- UNSUPPORTED: No evidence supports the claim, but no contradiction exists
- UNCERTAIN: Evidence is ambiguous, conflicting, or insufficient for a reliable verdict

Rules:
1. You MUST reference only the provided evidence IDs. Do not invent evidence.
2. If evidence is missing or insufficient, return UNSUPPORTED or UNCERTAIN - never guess.
3. A deterministic numeric/date contradiction in the evidence MUST be reported as CONTRADICTED.
4. Conflicting evidence that cannot be resolved MUST return UNCERTAIN.
5. The primary_evidence_id must be one of the referenced_evidence_ids (or null).

Return structured JSON with: status, confidence (0-1), reason, primary_evidence_id, referenced_evidence_ids, uncertainty_reason (if applicable)."""


def validate_judge_output(
    result: dict[str, Any],
    authorized_evidence_ids: set[uuid.UUID],
) -> JudgeResult:
    """Validate Judge output against schema and authorized evidence.
    
    Raises JudgeValidationError if validation fails.
    """
    # Schema validation
    status = result.get("status")
    if status not in ("supported", "contradicted", "unsupported", "uncertain"):
        raise JudgeValidationError(f"Invalid status: {status}")
    
    confidence = result.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        raise JudgeValidationError(f"Invalid confidence: {confidence}")
    
    reason = result.get("reason", "").strip()
    if not reason:
        raise JudgeValidationError("Missing or empty reason")
    
    # Validate primary_evidence_id
    primary_id_str = result.get("primary_evidence_id")
    primary_id = uuid.UUID(primary_id_str) if primary_id_str else None
    if primary_id and primary_id not in authorized_evidence_ids:
        raise JudgeValidationError(f"Primary evidence ID not in authorized set: {primary_id}")
    
    # Validate referenced_evidence_ids
    ref_ids_str = result.get("referenced_evidence_ids", [])
    if not isinstance(ref_ids_str, list):
        raise JudgeValidationError("referenced_evidence_ids must be a list")
    
    referenced_ids = []
    for rid_str in ref_ids_str:
        try:
            rid = uuid.UUID(rid_str)
        except ValueError:
            raise JudgeValidationError(f"Invalid UUID in referenced_evidence_ids: {rid_str}")
        if rid not in authorized_evidence_ids:
            raise JudgeValidationError(f"Referenced evidence ID not in authorized set: {rid}")
        referenced_ids.append(rid)
    
    # Primary must be in referenced (or null)
    if primary_id and primary_id not in referenced_ids:
        raise JudgeValidationError("primary_evidence_id must be in referenced_evidence_ids")
    
    # Uncertainty reason
    uncertainty_reason = result.get("uncertainty_reason")
    if uncertainty_reason and len(uncertainty_reason) > 300:
        raise JudgeValidationError("uncertainty_reason too long")
    
    return JudgeResult(
        status=status,
        confidence=float(confidence),
        reason=reason,
        primary_evidence_id=primary_id,
        referenced_evidence_ids=referenced_ids,
        uncertainty_reason=uncertainty_reason,
    )


def verify_with_judge(
    claim_text: str,
    claim_category: str,
    evidence_list: list[dict],  # list of {"id": uuid.UUID, "quote": str, "location": str, "support_type": str, "score": float}
    prompt_version: str = "v1",
) -> JudgeResult:
    """Invoke ML Judge with evidence-constrained verification.
    
    Returns validated JudgeResult. Raises LLMError on provider failure.
    Raises JudgeValidationError on validation failure.
    """
    if not llm_adapter.is_configured():
        raise LLMUnavailableError("No LLM provider configured for Judge")
    
    # Prepare authorized evidence IDs for validation
    authorized_ids = {ev["id"] for ev in evidence_list}
    
    # Build evidence context for prompt (no internal metadata)
    evidence_context = [
        {
            "id": str(ev["id"]),
            "quote": ev["quote"],
            "location": ev["location"],
            "support_type": ev["support_type"],
            "score": ev["score"],
        }
        for ev in evidence_list
    ]
    
    prompt = build_judge_prompt(claim_text, claim_category, evidence_context)
    
    request = LLMRequest(
        prompt=prompt,
        schema=JUDGE_SCHEMA,
        prompt_version=prompt_version,
        temperature=0.0,
        max_output_tokens=1024,
    )
    
    # The shared adapter owns provider fallback and canonical request caching.
    # Do not claim a specific provider when fallback metadata is unavailable.
    provider_used = None
    model_used = None
    cached = False

    # Live call with retry
    for attempt in range(2):  # 1 retry
        try:
            result = llm_adapter.complete_json(request)
            validated = validate_judge_output(result, authorized_ids)
            validated.provider = provider_used
            validated.model = model_used
            validated.cached = cached
            return validated
        except (LLMError, JudgeValidationError) as exc:
            if attempt == 0:
                logger.warning("Judge attempt %d failed: %s; retrying", attempt + 1, exc)
                continue
            raise
    
    raise LLMError("All Judge attempts failed")


class LLMUnavailableError(LLMError):
    """No LLM provider available for Judge."""
    pass


def judge_claim(
    claim_text: str,
    claim_category: str,
    evidence_list: list[dict],
    deterministic_result: JudgeResult | None = None,
) -> JudgeResult:
    """Main Judge entry point with deterministic-first logic.
    
    Args:
        claim_text: The claim to verify
        claim_category: Category of the claim
        evidence_list: List of authorized evidence dicts with id, quote, location, support_type, score
        deterministic_result: Optional pre-computed deterministic result. If conclusive (SUPPORTED/CONTRADICTED with high confidence), it takes precedence.
    
    Returns:
        JudgeResult with validated output
    
    Raises:
        LLMUnavailableError: If no LLM provider configured
        LLMError: If all provider attempts fail
    """
    # If deterministic check already gave a conclusive result, return it
    if deterministic_result and deterministic_result.status in ("supported", "contradicted") and deterministic_result.confidence >= 0.85:
        logger.debug("Deterministic result conclusive; skipping Judge")
        return deterministic_result
    
    # Otherwise invoke ML Judge
    return verify_with_judge(claim_text, claim_category, evidence_list)


__all__ = [
    "JudgeResult",
    "JudgeValidationError",
    "JUDGE_SCHEMA",
    "build_judge_prompt",
    "validate_judge_output",
    "verify_with_judge",
    "judge_claim",
    "LLMUnavailableError",
]