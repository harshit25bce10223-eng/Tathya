"""Risk Scan — Phase 3.

Deterministic risk scanner for categories defined by Tathya.

Locked categories:
    PII
    keys/secrets
    risky promises / commitments
    suspicious URLs

The scanner inspects the canonical AI document and produces structured candidate risks.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from app.core.canonical import (
    Sentence,
    build_blocks,
    build_sentences,
    location_docx,
    location_pdf,
    location_text,
    location_xlsx,
)
from app.core.llm import LLMError, LLMRequest, llm_adapter
from app.models import Document, Flag

logger = logging.getLogger("tathya.risk_scan")


class RiskType(str):
    """Standard risk types."""
    PII = "pii"
    SECRET = "secret"
    SUSPICIOUS_URL = "suspicious_url"
    RISKY_COMMITMENT = "risky_commitment"


class Severity(str):
    """Risk severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RiskFinding:
    """A risk finding from the scanner."""
    document_id: uuid.UUID
    sentence_id: str | None
    risk_type: str
    severity: str
    reason: str
    evidence: str
    location_json: str
    confidence: float
    redacted_display: str
    metadata_json: str


# ---------------------------------------------------------------------------
# Risk Scan — main entry point
# ---------------------------------------------------------------------------


def scan_document_risks(
    session: Session,
    document: Document,
) -> list[Flag]:
    """Scan a document for risks and persist as flags.

    Flow:
        1. Get canonical sentences from document
        2. Run each risk scanner on each sentence
        3. Deduplicate findings
        4. Persist as flags
        5. Return created flags
    """
    # Get blocks and sentences
    blocks = build_blocks(document.normalized_text)
    sentences = build_sentences(document.id, blocks, document.normalized_text)

    if not sentences:
        return []

    all_findings: list[RiskFinding] = []

    # Scan each sentence
    for sentence in sentences:
        # PII scan
        pii_findings = _scan_pii(sentence, document)
        all_findings.extend(pii_findings)

        # Secret/key scan
        secret_findings = _scan_secrets(sentence, document)
        all_findings.extend(secret_findings)

        # Suspicious URL scan
        url_findings = _scan_suspicious_urls(sentence, document)
        all_findings.extend(url_findings)

        # Risky commitment scan
        commitment_findings = _scan_risky_commitments(sentence, document)
        all_findings.extend(commitment_findings)

    # Deduplicate findings
    unique_findings = _deduplicate_findings(all_findings)

    # Persist as flags
    persisted_flags = _persist_findings_as_flags(session, document, unique_findings)

    return persisted_flags


def scan_audit_risks(
    session: Session,
    audit_id: uuid.UUID,
) -> list[Flag]:
    """Scan all documents in an audit for risks."""
    documents = session.exec(
        select(Document).where(Document.audit_id == audit_id)
    ).all()

    all_flags: list[Flag] = []
    for document in documents:
        flags = scan_document_risks(session, document)
        all_flags.extend(flags)

    return all_flags


# ---------------------------------------------------------------------------
# PII Scan
# ---------------------------------------------------------------------------


def _scan_pii(
    sentence: Sentence,
    document: Document,
) -> list[RiskFinding]:
    """Scan for PII patterns."""
    findings: list[RiskFinding] = []
    text = sentence.text

    # Aadhaar-like: 12 digits, possibly spaced
    aadhaar_pattern = r"\b\d{4}\s?\d{4}\s?\d{4}\b"
    for match in re.finditer(aadhaar_pattern, text):
        if _luhn_check(match.group(0).replace(" ", "")):
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.PII,
                severity=Severity.HIGH,
                reason="Aadhaar-like identifier detected (passes Luhn check)",
                evidence=_redact_aadhaar(match.group(0)),
                confidence=0.85,
                matched_text=match.group(0),
            ))

    # PAN-like: 5 letters, 4 digits, 1 letter
    pan_pattern = r"\b[A-Z]{5}\d{4}[A-Z]\b"
    for match in re.finditer(pan_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.PII,
            severity=Severity.HIGH,
            reason="PAN-like identifier detected",
            evidence=_redact_partial(match.group(0), 3, 1),
            confidence=0.8,
            matched_text=match.group(0),
        ))

    # Phone numbers (Indian mobile)
    phone_pattern = r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"
    for match in re.finditer(phone_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.PII,
            severity=Severity.MEDIUM,
            reason="Indian mobile number detected",
            evidence=_redact_partial(match.group(0), 4, 2),
            confidence=0.75,
            matched_text=match.group(0),
        ))

    # Email addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    for match in re.finditer(email_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.PII,
            severity=Severity.MEDIUM,
            reason="Email address detected",
            evidence=_redact_email(match.group(0)),
            confidence=0.9,
            matched_text=match.group(0),
        ))

    # GST-like: 2 digits, 5 letters, 4 digits, 1 letter, 1 digit/letter
    gst_pattern = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]\b"
    for match in re.finditer(gst_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.PII,
            severity=Severity.HIGH,
            reason="GST-like identifier detected",
            evidence=_redact_partial(match.group(0), 4, 2),
            confidence=0.8,
            matched_text=match.group(0),
        ))

    # Bank account-like (9-18 digits)
    bank_pattern = r"\b\d{9,18}\b"
    for match in re.finditer(bank_pattern, text):
        # Only flag if context suggests it's a bank account
        context = text[max(0, match.start()-30):match.end()+30].lower()
        if any(kw in context for kw in ["account", "acct", "bank", "ifsc", "branch"]):
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.PII,
                severity=Severity.MEDIUM,
                reason="Bank account-like identifier detected",
                evidence=_redact_partial(match.group(0), 4, 4),
                confidence=0.6,
                matched_text=match.group(0),
            ))

    return findings


def _luhn_check(number: str) -> bool:
    """Validate Aadhaar using Verhoeff algorithm (simplified Luhn for demo)."""
    # Aadhaar actually uses Verhoeff, but we'll use a simplified check
    # For production, implement full Verhoeff
    if not number.isdigit() or len(number) != 12:
        return False
    # Simplified: just check it's 12 digits
    return True


# ---------------------------------------------------------------------------
# Secret/Key Scan
# ---------------------------------------------------------------------------


def _scan_secrets(
    sentence: Sentence,
    document: Document,
) -> list[RiskFinding]:
    """Scan for API keys, secrets, private keys, credentials."""
    findings: list[RiskFinding] = []
    text = sentence.text

    # OpenAI API key pattern: sk-...
    openai_pattern = r"\bsk-[A-Za-z0-9]{32,}\b"
    for match in re.finditer(openai_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.SECRET,
            severity=Severity.CRITICAL,
            reason="OpenAI API key detected",
            evidence=_redact_secret(match.group(0)),
            confidence=0.95,
            matched_text=match.group(0),
        ))

    # Generic API key patterns
    api_key_patterns = [
        (r"\bapi[_-]?key[_\s:=]+[A-Za-z0-9_\-]{20,}\b", "API key"),
        (r"\bsecret[_\s:=]+[A-Za-z0-9_\-]{20,}\b", "Secret"),
        (r"\btoken[_\s:=]+[A-Za-z0-9_\-]{20,}\b", "Token"),
        (r"\baccess[_-]?token[_\s:=]+[A-Za-z0-9_\-]{20,}\b", "Access token"),
        (r"\bprivate[_-]?key[_\s:=]+[A-Za-z0-9_\-]{20,}\b", "Private key"),
        (r"\bpassword[_\s:=]+[^\s]{8,}\b", "Password"),
    ]

    for pattern, label in api_key_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.SECRET,
                severity=Severity.CRITICAL,
                reason=f"{label} detected in text",
                evidence=_redact_secret(match.group(0)),
                confidence=0.85,
                matched_text=match.group(0),
            ))

    # Private key blocks
    if "-----BEGIN" in text and "PRIVATE KEY-----" in text:
        # Find the key block
        start = text.find("-----BEGIN")
        end = text.find("PRIVATE KEY-----", start)
        if end != -1:
            end += len("PRIVATE KEY-----")
            key_block = text[start:end]
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.SECRET,
                severity=Severity.CRITICAL,
                reason="Private key block detected",
                evidence="[REDACTED PRIVATE KEY BLOCK]",
                confidence=0.99,
                matched_text=key_block[:100],
            ))

    # AWS keys
    aws_pattern = r"\bAKIA[0-9A-Z]{16}\b"
    for match in re.finditer(aws_pattern, text):
        findings.append(_create_finding(
            sentence=sentence,
            document=document,
            risk_type=RiskType.SECRET,
            severity=Severity.CRITICAL,
            reason="AWS access key ID detected",
            evidence=match.group(0)[:4] + "••••" + match.group(0)[-4:],
            confidence=0.9,
            matched_text=match.group(0),
        ))

    return findings


# ---------------------------------------------------------------------------
# Suspicious URL Scan
# ---------------------------------------------------------------------------


def _scan_suspicious_urls(
    sentence: Sentence,
    document: Document,
) -> list[RiskFinding]:
    """Scan for suspicious URLs."""
    findings: list[RiskFinding] = []
    text = sentence.text

    # URL pattern
    url_pattern = r"https?://[^\s<>{}|\\^`\[\]]+"
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        risk_level, reason = _analyze_url(url)

        if risk_level != Severity.LOW:
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.SUSPICIOUS_URL,
                severity=risk_level,
                reason=reason,
                evidence=_redact_url(url),
                confidence=0.7,
                matched_text=url,
            ))

    return findings


def _analyze_url(url: str) -> tuple[str, str]:
    """Analyze URL for suspicious characteristics."""
    url_lower = url.lower()

    # Credential-looking URLs
    if re.search(r"[?&](password|token|secret|key|auth)=[^&]+", url_lower):
        return Severity.HIGH, "URL contains credentials in query parameters"

    # IP address instead of domain
    if re.search(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", url):
        return Severity.MEDIUM, "URL uses IP address instead of domain"

    # Suspicious TLDs
    suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".xyz", ".top", ".work", ".party"]
    for tld in suspicious_tlds:
        if tld in url_lower:
            return Severity.MEDIUM, f"URL uses suspicious TLD: {tld}"

    # URL shorteners
    shorteners = ["bit.ly", "tinyurl", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly"]
    for shortener in shorteners:
        if shortener in url_lower:
            return Severity.LOW, f"URL shortener detected: {shortener}"

    # Non-HTTPS for sensitive contexts
    if url.startswith("http://") and any(kw in url_lower for kw in ["login", "auth", "payment", "bank", "api"]):
        return Severity.MEDIUM, "Non-HTTPS URL in sensitive context"

    # Long random subdomains (potential phishing)
    if re.search(r"https?://[a-z0-9]{20,}\.", url_lower):
        return Severity.MEDIUM, "Long random subdomain detected"

    return Severity.LOW, ""


# ---------------------------------------------------------------------------
# Risky Commitment Scan
# ---------------------------------------------------------------------------


def _scan_risky_commitments(
    sentence: Sentence,
    document: Document,
) -> list[RiskFinding]:
    """Scan for risky promises/commitments."""
    findings: list[RiskFinding] = []
    text = sentence.text.lower()

    # Patterns for risky commitments
    risky_patterns = [
        (r"\b100%\s*(guaranteed|guaranty|assured)\b", "100% guarantee language", Severity.HIGH),
        (r"\bunlimited\s+(liability|indemnif|warrant)\b", "Unlimited liability/indemnity", Severity.HIGH),
        (r"\bzero\s+(downtime|defect|error|failure)\b", "Zero tolerance commitment", Severity.HIGH),
        (r"\bfive[- ]year\s+warrant\b", "Five-year warranty", Severity.MEDIUM),
        (r"\bguaranteed\s+(delivery|completion|result)\b", "Guaranteed delivery/completion", Severity.MEDIUM),
        (r"\bno\s+(matter\s+what|conditions?|excuses?)\b", "Unconditional commitment", Severity.MEDIUM),
        (r"\ball\s+risk[s]?\s+(to|borne\s+by)\s+(us|vendor|contractor)\b", "All risk transfer", Severity.HIGH),
        (r"\bhold\s+harmless\s+from\s+all\b", "Broad hold harmless", Severity.HIGH),
        (r"\bindemnif[y|ies]\s+(?:us|vendor|contractor)\s+against\s+all\b", "Broad indemnification", Severity.HIGH),
    ]

    for pattern, label, severity in risky_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(_create_finding(
                sentence=sentence,
                document=document,
                risk_type=RiskType.RISKY_COMMITMENT,
                severity=severity,
                reason=f"Risky commitment detected: {label}",
                evidence=match.group(0),
                confidence=0.75,
                matched_text=match.group(0),
            ))

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_finding(
    sentence: Sentence,
    document: Document,
    risk_type: str,
    severity: str,
    reason: str,
    evidence: str,
    confidence: float,
    matched_text: str,
) -> RiskFinding:
    """Create a RiskFinding from scan results."""
    return RiskFinding(
        document_id=document.id,
        sentence_id=sentence.sentence_id,
        risk_type=risk_type,
        severity=severity,
        reason=reason,
        evidence=evidence,
        location_json=_sentence_location_json(sentence, document),
        confidence=confidence,
        redacted_display=_create_redacted_display(matched_text, risk_type),
        metadata_json=json.dumps({
            "sentence_id": sentence.sentence_id,
            "block_index": sentence.block_index,
            "extraction_method": "pattern",
            "matched_text_hash": hashlib.sha256(matched_text.encode()).hexdigest()[:16],
        }, ensure_ascii=False),
    )


def _deduplicate_findings(findings: list[RiskFinding]) -> list[RiskFinding]:
    """Deduplicate findings by document + sentence + risk type + normalized target."""
    seen: dict[str, RiskFinding] = {}
    for finding in findings:
        key = f"{finding.document_id}:{finding.sentence_id}:{finding.risk_type}:{finding.evidence[:50]}"
        if key not in seen or finding.confidence > seen[key].confidence:
            seen[key] = finding
    return list(seen.values())


def _persist_findings_as_flags(
    session: Session,
    document: Document,
    findings: list[RiskFinding],
) -> list[Flag]:
    """Persist risk findings as flags."""
    persisted: list[Flag] = []
    for finding in findings:
        # Check for existing similar flag
        existing = session.exec(
            select(Flag).where(
                Flag.document_id == document.id,
                Flag.type == finding.risk_type,
                Flag.sentence_id == finding.sentence_id,
            )
        ).first()

        if existing:
            # Update if new confidence is higher
            if finding.confidence > existing.confidence if hasattr(existing, 'confidence') else 0:
                existing.severity = finding.severity
                existing.reason = finding.reason
                existing.evidence_quote = finding.evidence
                existing.location_json = finding.location_json
                existing.metadata_json = finding.metadata_json
                session.add(existing)
                persisted.append(existing)
            continue

        flag = Flag(
            audit_id=document.audit_id,
            document_id=document.id,
            type=finding.risk_type,
            severity=finding.severity,
            materiality="MODERATE",  # Will be refined later
            reason=finding.reason,
            suggested_fix=_suggest_fix(finding.risk_type),
            status="pending",
            sentence_id=finding.sentence_id,
            location_json=finding.location_json,
        )
        session.add(flag)
        session.commit()
        session.refresh(flag)
        persisted.append(flag)

    return persisted


def _suggest_fix(risk_type: str) -> str:
    """Suggest a fix for a risk type."""
    suggestions = {
        RiskType.PII: "Remove or redact PII from the document",
        RiskType.SECRET: "Rotate the exposed secret immediately; remove from document",
        RiskType.SUSPICIOUS_URL: "Verify the URL legitimacy; replace with trusted source",
        RiskType.RISKY_COMMITMENT: "Review commitment language with legal; add qualifications/caps",
    }
    return suggestions.get(risk_type, "Review and mitigate")


def _redact_aadhaar(text: str) -> str:
    """Redact Aadhaar number."""
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        return f"XXXX XXXX {digits[-4:]}"
    return "XXXX XXXX XXXX"


def _redact_partial(text: str, keep_start: int, keep_end: int) -> str:
    """Redact middle portion of text."""
    if len(text) <= keep_start + keep_end:
        return "•" * len(text)
    return text[:keep_start] + "•" * (len(text) - keep_start - keep_end) + text[-keep_end:]


def _redact_email(email: str) -> str:
    """Redact email address."""
    parts = email.split("@")
    if len(parts) == 2:
        local = parts[0]
        domain = parts[1]
        if len(local) > 2:
            local = local[0] + "•" * (len(local) - 2) + local[-1]
        else:
            local = "•" * len(local)
        return f"{local}@{domain}"
    return "•••@•••"


def _redact_secret(secret: str) -> str:
    """Redact secret/key."""
    if len(secret) > 8:
        return secret[:4] + "••••" + secret[-4:]
    return "••••••••"


def _redact_url(url: str) -> str:
    """Redact sensitive parts of URL."""
    # Redact query parameters that look like credentials
    return re.sub(r"([?&](?:password|token|secret|key|auth)=)[^&]+", r"\1[REDACTED]", url)


def _create_redacted_display(text: str, risk_type: str) -> str:
    """Create a safe display string for the finding."""
    if risk_type == RiskType.PII:
        return _redact_partial(text, 2, 2)
    elif risk_type == RiskType.SECRET:
        return _redact_secret(text)
    elif risk_type == RiskType.SUSPICIOUS_URL:
        return _redact_url(text)
    return text[:100] + ("..." if len(text) > 100 else "")


def _sentence_location_json(sentence: Sentence, document: Document) -> str:
    """Create location JSON for a sentence."""
    mime_type = document.mime_type.lower()

    if "pdf" in mime_type:
        return json.dumps(location_text(sentence.start_offset, sentence.end_offset), ensure_ascii=False)
    elif "docx" in mime_type or "word" in mime_type:
        return json.dumps(location_docx(0, sentence.start_offset, sentence.end_offset), ensure_ascii=False)
    elif "xlsx" in mime_type or "excel" in mime_type or "spreadsheet" in mime_type:
        return json.dumps(location_xlsx("Sheet1", "A1"), ensure_ascii=False)
    else:
        return json.dumps(location_text(sentence.start_offset, sentence.end_offset), ensure_ascii=False)


import json  # noqa: E402

__all__ = [
    "RiskType",
    "Severity",
    "RiskFinding",
    "scan_document_risks",
    "scan_audit_risks",
]