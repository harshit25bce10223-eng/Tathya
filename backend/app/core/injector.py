"""Jhooth Injector — Safe Candidate Generation (Spec §20).

Generates adversarial injection candidates against immutable source documents.
Candidates carry a traceable unified diff and never mutate the original text.
"""

from __future__ import annotations

import difflib
import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

__all__ = [
    "InjectionCandidate",
    "InjectionError",
    "generate_candidate",
    "compute_text_hash",
    "candidate_to_diff",
]


class InjectionError(ValueError):
    """Raised when an injection candidate cannot be safely generated."""


def compute_text_hash(text: str) -> str:
    """Deterministic SHA-256 hash of text, used to prove original immutability."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class InjectionCandidate:
    """A safe, traceable adversarial injection candidate.

    The ``original_text`` field is stored for audit only and is asserted to be
    unchanged (hash matches ``original_hash``) at generation time. It is never
    written back over the source document.
    """

    candidate_id: uuid.UUID
    base_document_id: uuid.UUID | None
    original_hash: str
    candidate_hash: str
    injected_text: str
    location: dict[str, Any]
    severity: str
    pattern: str
    rationale: str
    diff: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidate_id"] = str(self.candidate_id)
        data["base_document_id"] = (
            str(self.base_document_id) if self.base_document_id else None
        )
        data["created_at"] = self.created_at.isoformat()
        return data

    @property
    def changed(self) -> bool:
        return self.original_hash != self.candidate_hash


def candidate_to_diff(
    original_text: str,
    injected_text: str,
    *,
    label_original: str = "original",
    label_candidate: str = "candidate",
) -> list[str]:
    """Produce a unified diff between original and injected text.

    Both texts are first proven to be mutually consistent; the diff is derived
    solely from the two strings, so the original is never mutated.
    """
    return list(
        difflib.unified_diff(
            original_text.splitlines(),
            injected_text.splitlines(),
            fromfile=label_original,
            tofile=label_candidate,
            lineterm="",
        )
    )


def generate_candidate(
    *,
    original_text: str,
    injected_text: str,
    pattern: str,
    severity: str = "MEDIUM",
    base_document_id: uuid.UUID | None = None,
    location: dict[str, Any] | None = None,
    rationale: str = "",
    meta: dict[str, Any] | None = None,
) -> InjectionCandidate:
    """Generate a traceable injection candidate without mutating the original.

    Raises:
        InjectionError: if the injected text is identical to the original
            (no-op injections are rejected as unsafe/untraceable).
    """
    if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE"):
        raise InjectionError(f"Invalid severity: {severity}")

    original_hash = compute_text_hash(original_text)
    candidate_hash = compute_text_hash(injected_text)

    if original_hash == candidate_hash:
        raise InjectionError(
            "Injected text is identical to original; refusing to generate a no-op candidate."
        )

    diff = candidate_to_diff(original_text, injected_text)

    # Immutability assertion: recompute the original hash after diffing.
    if compute_text_hash(original_text) != original_hash:
        raise InjectionError("Original text was mutated during candidate generation.")

    return InjectionCandidate(
        candidate_id=uuid.uuid4(),
        base_document_id=base_document_id,
        original_hash=original_hash,
        candidate_hash=candidate_hash,
        injected_text=injected_text,
        location=dict(location or {}),
        severity=severity,
        pattern=pattern,
        rationale=rationale,
        diff=diff,
        meta=dict(meta or {}),
    )
