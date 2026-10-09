"""Canonical signed Passport v2 snapshot, including scores and reviewer state."""
import json


def signed_payload(passport) -> bytes:
    fields = ("audit_id", "verify_token", "document_hash", "chain_head", "trust_score", "ai_score", "reviewed_score", "score_band", "critical_risk", "finding_summary", "review_status", "revision", "status")
    payload = {key: getattr(passport, key) for key in fields}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
