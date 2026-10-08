"""Shared extraction foundation.

A fact is EXTRACTED information only — it never carries a verification
verdict (verification is a later, separate operation).

Every extracted fact carries:
    - category        (stable, typed: numeric.* / date.* / name.* / identifier.*)
    - raw_text        (exact slice of the canonical normalized text)
    - payload         (normalized value, unit/currency, qualifiers, ranges,
                       extraction engine + version — structured JSON)
    - location        (format-level location contract + raw/norm char spans)
    - sentence_id     (locked SHA256 sentence contract, when inside a sentence)
"""

from __future__ import annotations

import bisect
import json
from dataclasses import dataclass, field
from typing import Any

from app.core.canonical import (
    Sentence,
    denormalize_span,
    location_text,
)

EXTRACTION_VERSION = "2"

CATEGORY_NUMERIC = "numeric"
CATEGORY_DATE = "date"
CATEGORY_NAME = "name"
CATEGORY_IDENTIFIER = "identifier"


@dataclass
class FactRecord:
    category: str
    raw_text: str
    norm_start: int
    norm_end: int
    payload: dict[str, Any] = field(default_factory=dict)
    sentence_id: str = ""
    location: dict[str, Any] = field(default_factory=dict)


class LocationResolver:
    """Resolves raw-text char offsets to format-level location contracts.

    Wraps the ordered char-location entries stored in document metadata.
    Never invents geometry: unknown spans fall back to text char offsets.
    """

    def __init__(self, char_locations: list[dict[str, Any]] | None) -> None:
        entries: list[tuple[int, int, dict[str, Any]]] = []
        for entry in char_locations or []:
            try:
                start = int(entry["start"])
                end = int(entry["end"])
            except (KeyError, TypeError, ValueError):
                continue
            entries.append((start, end, dict(entry.get("location") or {})))
        entries.sort(key=lambda e: e[0])
        self._entries = entries
        self._starts = [e[0] for e in entries]

    def resolve(self, raw_start: int, raw_end: int) -> dict[str, Any]:
        index = bisect.bisect_right(self._starts, raw_start) - 1
        if index >= 0:
            start, end, location = self._entries[index]
            if start <= raw_start < end:
                return dict(location)
        # between entries or beyond the last one: honest text fallback
        return location_text(raw_start, raw_end)


class SentenceIndex:
    """Maps fact spans to the locked sentence IDs of a document version."""

    def __init__(self, sentences: list[Sentence]) -> None:
        self._sentences = sentences
        self._starts = [s.start_offset for s in sentences]

    def sentence_id_for(self, norm_start: int, norm_end: int) -> str:
        index = bisect.bisect_right(self._starts, norm_start) - 1
        if index >= 0:
            sentence = self._sentences[index]
            if sentence.start_offset <= norm_start < sentence.end_offset:
                return sentence.sentence_id
        for sentence in self._sentences:
            if sentence.start_offset <= norm_start and norm_end <= sentence.end_offset:
                return sentence.sentence_id
        return ""


def resolve_location(
    resolver: LocationResolver,
    segments: list[dict],
    norm_start: int,
    norm_end: int,
) -> dict[str, Any]:
    """Compose the full location contract for a normalized span.

    Format contract (pdf/docx/xlsx/text) + raw/norm char spans, derived
    deterministically from the segment offset map. No LLM, no guessing.
    """
    raw_start, raw_end = denormalize_span(segments, norm_start, norm_end)
    location = dict(resolver.resolve(raw_start, raw_end))
    location["raw_start"] = raw_start
    location["raw_end"] = raw_end
    location["norm_start"] = norm_start
    location["norm_end"] = norm_end
    return location


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic JSON (sorted keys, compact) for stored fact payloads."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


class SpanClaims:
    """Priority-ordered span claiming so one number is one fact.

    Engines run in a fixed order; each claims its match span. Later
    engines skip spans that overlap an earlier claim (e.g. the "99.9"
    inside "99.9%" is never re-extracted as a bare decimal).
    """

    def __init__(self) -> None:
        self._spans: list[tuple[int, int]] = []

    def claim(self, start: int, end: int) -> None:
        bisect.insort(self._spans, (start, end))

    def overlaps(self, start: int, end: int) -> bool:
        for claimed_start, claimed_end in self._spans:
            if claimed_start >= end:
                break
            if start < claimed_end and claimed_start < end:
                return True
        return False


__all__ = [
    "CATEGORY_DATE",
    "CATEGORY_IDENTIFIER",
    "CATEGORY_NAME",
    "CATEGORY_NUMERIC",
    "EXTRACTION_VERSION",
    "FactRecord",
    "LocationResolver",
    "SentenceIndex",
    "SpanClaims",
    "canonical_json",
    "resolve_location",
]
