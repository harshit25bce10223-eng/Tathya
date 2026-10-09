"""Real Document Fact Verification Engine powered by RoPE Transformer.

Performs high-precision document auditing, extracting claims from draft documents,
cross-verifying them against baseline source contracts/documents using Rotary Position
Embedding (RoPE) neural representations, and issuing structured verification reports.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.parsers import parse_file
from app.core.rope_inference import verify_with_rope

logger = logging.getLogger("tathya.real_document_auditor")


def _split_into_sentences(text: str) -> List[str]:
    """Splits document text into distinct verifiable statements / clauses."""
    # Split by periods, bullet points, numbered lists, or newlines
    raw_lines = re.split(r"(?:\r?\n|(?<=[.!?])\s+|^\s*[-*•]\s+|^\s*\d+\.\s+)", text)
    sentences = []
    for line in raw_lines:
        cleaned = line.strip().strip("-*•#")
        if len(cleaned) > 15:  # Filter out trivial noise/headers
            sentences.append(cleaned)
    return sentences


def _find_best_candidate_evidence(claim: str, source_sentences: List[str]) -> Tuple[str, float]:
    """Finds the most relevant source sentence using lexical & token overlap."""
    claim_words = set(re.findall(r"\b\w{3,}\b", claim.lower()))
    if not claim_words:
        return ("", 0.0)

    best_match = ""
    best_score = 0.0

    for src in source_sentences:
        src_words = set(re.findall(r"\b\w{3,}\b", src.lower()))
        if not src_words:
            continue
        overlap = len(claim_words.intersection(src_words))
        score = overlap / max(len(claim_words), 1)
        if score > best_score:
            best_score = score
            best_match = src

    return best_match, best_score


class RealDocumentAuditReport:
    """Complete structured audit result for a document pair."""

    def __init__(self, audit_id: str, title: str):
        self.audit_id = audit_id
        self.title = title
        self.created_at = datetime.now(UTC).isoformat()
        self.findings: List[Dict[str, Any]] = []
        self.supported_count = 0
        self.contradicted_count = 0
        self.unsupported_count = 0
        self.overall_ai_score = 100.0
        self.risk_band = "LOW"
        self.source_hash = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "title": self.title,
            "created_at": self.created_at,
            "overall_ai_score": round(self.overall_ai_score, 2),
            "risk_band": self.risk_band,
            "summary": {
                "total_claims": len(self.findings),
                "supported": self.supported_count,
                "contradicted": self.contradicted_count,
                "unsupported": self.unsupported_count,
            },
            "findings": self.findings,
            "source_hash": self.source_hash,
        }


def audit_document_with_rope(
    target_doc_path: str,
    source_doc_paths: List[str],
    audit_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Audits a target document against one or more source documents using RoPE.

    Args:
        target_doc_path: Path to the draft/unverified document (e.g. AI draft contract)
        source_doc_paths: List of paths to baseline ground-truth documents (e.g. Approved PO, Baseline MSA)
        audit_title: Optional human-readable audit title

    Returns:
        Structured audit report dictionary with claims, statuses, RoPE confidences, and score.
    """
    target_path = Path(target_doc_path)
    if not target_path.exists():
        raise FileNotFoundError(f"Target document not found at: {target_doc_path}")

    # Parse target document
    parsed_target = parse_file(target_path)
    target_text = parsed_target.raw_text
    target_sentences = _split_into_sentences(target_text)

    # Parse all source documents
    all_source_sentences: List[str] = []
    source_hashes = []

    for src_p in source_doc_paths:
        p = Path(src_p)
        if p.exists():
            parsed_src = parse_file(p)
            all_source_sentences.extend(_split_into_sentences(parsed_src.raw_text))
            source_hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())

    # Create Audit Report
    audit_id = str(uuid.uuid4())
    report = RealDocumentAuditReport(
        audit_id=audit_id,
        title=audit_title or f"Audit of {target_path.name}",
    )
    report.source_hash = hashlib.sha256("".join(sorted(source_hashes)).encode("utf-8")).hexdigest()

    # Verify each sentence/claim in the target document
    for idx, claim in enumerate(target_sentences, 1):
        best_evidence, overlap_score = _find_best_candidate_evidence(claim, all_source_sentences)

        if not best_evidence or overlap_score < 0.15:
            # No relevant baseline source context found
            report.unsupported_count += 1
            finding = {
                "claim_index": idx,
                "claim_text": claim,
                "status": "unsupported",
                "confidence": 0.0,
                "risk_score": 0.4,
                "evidence_quote": None,
                "reason": "No relevant baseline contract clause found in source documents.",
            }
        else:
            # Run deep RoPE neural verification
            rope_res = verify_with_rope(claim_text=claim, evidence_text=best_evidence)
            status = rope_res["status"]
            confidence = rope_res["confidence"]
            risk = rope_res["risk_score"]

            if status == "supported":
                report.supported_count += 1
            elif status == "contradicted":
                report.contradicted_count += 1
            else:
                report.unsupported_count += 1

            finding = {
                "claim_index": idx,
                "claim_text": claim,
                "status": status,
                "confidence": confidence,
                "risk_score": risk,
                "probabilities": rope_res.get("probabilities", {}),
                "evidence_quote": best_evidence,
                "reason": rope_res["reason"],
            }

        report.findings.append(finding)

    # Compute overall trust score
    # Formula: Start at 100. Contradictions cost -25 pts, Unsupported cost -8 pts
    total_claims = max(len(report.findings), 1)
    score_penalty = (report.contradicted_count * 25.0) + (report.unsupported_count * 8.0)
    final_score = max(0.0, min(100.0, 100.0 - (score_penalty / total_claims * 10.0)))
    report.overall_ai_score = final_score

    # Determine Risk Band
    if report.contradicted_count > 0 or final_score < 60.0:
        report.risk_band = "CRITICAL"
    elif report.unsupported_count > 2 or final_score < 80.0:
        report.risk_band = "MODERATE"
    else:
        report.risk_band = "LOW"

    return report.to_dict()
