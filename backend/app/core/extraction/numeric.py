"""Deterministic numeric extraction engine.

Locked behaviour:
    - Indian formats are first-class: ₹ / Rs. / Rs / INR prefixes, lakh /
      lac / crore / Cr scale words; Indian comma groups (41,60,000) and
      Western groups (1,234,567) are ONE number — never split mid-digit
    - currency is preserved exactly (INR/USD/EUR/GBP) and NEVER
      converted: ₹41.6 lakh and USD 41.6 lakh are different facts and
      are never treated as equal
    - percentages preserve the written value (99.9 stays 99.9; a bare
      0.95 is never auto-converted into 95%)
    - durations: 30 days / 45 days / 12 months / 5 years / 90-day /
      five-year (word numbers, Hindi units) — value + unit preserved
    - ranges keep their semantics as {low, high} (10-12 days, 10-12%);
      qualifiers (approximately, ~, up to, at least, ...) are recorded
      on the payload and included in the quoted raw span
    - a bare number with no anchor (no currency, scale, percent, unit,
      ratio or qualifier) is NOT a fact: dates, IDs, phone numbers and
      clause numbers are protected from being shredded
    - every match claims its span in a fixed priority order, so one
      number is one fact ("99.9" inside "99.9%" is never re-extracted)

This engine runs AFTER the date engine: spans that belong to dates
("22 December 2026", "within 30 days") are already claimed, so the
numeric engine can never shred them.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from app.core.extraction.base import CATEGORY_NUMERIC, FactRecord, SpanClaims
from app.core.extraction.tokens import (
    DURATION_UNIT_SOURCE,
    NUMBER_SOURCE,
    WORD_NUM_ALT,
    duration_value,
    numeric_value,
    parse_duration_unit,
)

ENGINE = "numeric"

# ---------------------------------------------------------------------------
# Scale words (locked: lakh / lac / crore / Cr; never assume bare "L")
# ---------------------------------------------------------------------------

_SCALE_SOURCE = (
    r"(?i:crores?|lakhs?|lacs?|crs?\.?|millions?|mn|billions?|bn"
    r"|trillions?|thousands?|लाख|करोड़)"
)

_SCALE_FACTORS: dict[str, int] = {
    "lakh": 100000,
    "lakhs": 100000,
    "lac": 100000,
    "lacs": 100000,
    "लाख": 100000,
    "crore": 10000000,
    "crores": 10000000,
    "cr": 10000000,
    "crs": 10000000,
    "करोड़": 10000000,
    "million": 1000000,
    "millions": 1000000,
    "mn": 1000000,
    "billion": 1000000000,
    "billions": 1000000000,
    "bn": 1000000000,
    "trillion": 1000000000000,
    "trillions": 1000000000000,
    "thousand": 1000,
    "thousands": 1000,
}


def _scale_factor(raw: str) -> tuple[str, int] | None:
    key = raw.strip().rstrip(".").lower()
    factor = _SCALE_FACTORS.get(key)
    if factor is None:
        return None
    return key, factor


# ---------------------------------------------------------------------------
# Currency vocabulary (prefix and suffix forms; canonical codes only,
# conversion is never performed)
# ---------------------------------------------------------------------------

_CUR_TOKEN = r"(?:₹|US\$|\$|€|£|(?i:INR|USD|EUR|GBP|RS\.?))"
_CUR_SUFFIX_TOKEN = r"(?i:INR|USD|EUR|GBP|RS\.?|rupees?|rupaye|dollars?|euros?)"

_CURRENCY_CANON: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "inr": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "rupaye": "INR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}


def _currency(raw: str) -> str | None:
    return _CURRENCY_CANON.get(raw.strip().rstrip(".").lower())


# ---------------------------------------------------------------------------
# Patterns (fixed priority order — ranges before singles, currency before
# percent before duration before ratio before quantity before qualified
# bare numbers)
# ---------------------------------------------------------------------------

_RANGE_CURRENCY = re.compile(
    rf"(?<![A-Za-z0-9])(?P<cur>{_CUR_TOKEN})\s*(?P<lo>{NUMBER_SOURCE})"
    rf"\s*(?:-|–|—|to)\s*(?:{_CUR_TOKEN}\s*)?(?P<hi>{NUMBER_SOURCE})"
    rf"(?:\s*(?P<scale>{_SCALE_SOURCE}))?(?![A-Za-z0-9])"
)

_CURRENCY_PREFIX = re.compile(
    rf"(?<![A-Za-z0-9])(?P<cur>{_CUR_TOKEN})\s*(?P<num>{NUMBER_SOURCE})"
    rf"(?:\s*(?P<scale>{_SCALE_SOURCE}))?(?![A-Za-z0-9])"
)

_CURRENCY_SUFFIX = re.compile(
    rf"(?<![A-Za-z0-9])(?P<num>{NUMBER_SOURCE})(?:\s*(?P<scale>{_SCALE_SOURCE}))?"
    rf"\s*(?P<cur>{_CUR_SUFFIX_TOKEN})(?![A-Za-z0-9])"
)

_PCT_TAIL = r"(?:%|(?i:per\s*cent))"

_PERCENT_RANGE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<lo>{NUMBER_SOURCE})\s*(?:-|–|—|to)\s*"
    rf"(?P<hi>{NUMBER_SOURCE})\s*{_PCT_TAIL}(?![A-Za-z0-9])"
)

_PERCENT = re.compile(
    rf"(?<![A-Za-z0-9])(?P<num>{NUMBER_SOURCE})\s*{_PCT_TAIL}(?![A-Za-z0-9])"
)

_DURATION_RANGE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<lo>{NUMBER_SOURCE})\s*(?:-|–|—|to)\s*"
    rf"(?P<hi>{NUMBER_SOURCE})[\s-]{{0,2}}{DURATION_UNIT_SOURCE}(?![A-Za-z0-9])",
    re.IGNORECASE,
)

_DURATION = re.compile(
    rf"(?<![A-Za-z0-9])(?:(?P<num>{NUMBER_SOURCE})|(?P<word>{WORD_NUM_ALT}))"
    rf"[\s-]{{0,2}}{DURATION_UNIT_SOURCE}(?![A-Za-z0-9])",
    re.IGNORECASE,
)

_RATIO = re.compile(r"(?<![\d:])(?P<a>\d{1,4}):(?P<b>\d{1,4})(?![\d:])")
_AMPM_AFTER = re.compile(r"\s*(?i:am|pm)\b")
_AT_BEFORE = re.compile(r"(?i:\bat\s*$)")

_QTY_TOKEN = (
    r"(?i:units?|items?|pieces?|licenses?|licences?|seats?|users?|employees?"
    r"|people|customers?|clients?|servers?|gbs?|mbs?|tbs?|kbs?|kms?|kgs?"
    r"|cms?|litres?|liters?|metres?|meters?)"
)

_QUANTITY = re.compile(
    rf"(?<![A-Za-z0-9])(?P<num>{NUMBER_SOURCE})\s*(?P<qunit>{_QTY_TOKEN})(?![A-Za-z0-9-])"
)

_QUAL_SOURCE = (
    r"(?i:approximately|approx\.|about|around|roughly|nearly|almost|circa"
    r"|up\s+to|at\s+least|minimum\s+of|no\s+less\s+than|not\s+less\s+than"
    r"|at\s+most|maximum\s+of|no\s+more\s+than|not\s+more\s+than"
    r"|in\s+excess\s+of|more\s+than|less\s+than|exceeding)"
)

_QUALIFIED_NUMBER = re.compile(
    rf"(?<![A-Za-z0-9])(?P<qual>{_QUAL_SOURCE})\s+(?P<num>{NUMBER_SOURCE})(?![A-Za-z0-9])"
)

# A qualified bare number followed by a scale word is skipped: the scale
# would change the value and no other pattern owns it (conservative skip).
_SCALE_AFTER = re.compile(rf"\s*{_SCALE_SOURCE}(?![A-Za-z0-9])")

_QUAL_BEFORE = re.compile(rf"(?<![A-Za-z0-9])(?:(?P<qual>{_QUAL_SOURCE})|~)\s*$")


def _norm_qual(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.lower()).rstrip(".")


# ---------------------------------------------------------------------------
# Emit helpers
# ---------------------------------------------------------------------------


def _emit(
    sub: str,
    raw: str,
    start: int,
    end: int,
    payload: dict[str, Any],
) -> FactRecord:
    payload.setdefault("engine", ENGINE)
    payload.setdefault("raw", raw)
    return FactRecord(
        category=f"{CATEGORY_NUMERIC}.{sub}",
        raw_text=raw,
        norm_start=start,
        norm_end=end,
        payload=payload,
    )


def _qualifier_before(text: str, start: int) -> tuple[str, int] | None:
    """Qualifier word ending right before `start`, if any."""
    window = text[max(0, start - 30) : start]
    match = _QUAL_BEFORE.search(window)
    if match is None:
        return None
    # The "~" alternative has no named group: fall back to the tilde and
    # use the whole-match start (the pattern opens with the alternation).
    raw_qual = match.group("qual") or "~"
    qual = _norm_qual(raw_qual) if raw_qual != "~" else "~"
    qual_start = start - len(window) + match.start()
    return qual, qual_start


def _attach_qualifier(text: str, claims: SpanClaims, record: FactRecord) -> None:
    """Record a directly preceding qualifier and widen the quoted span.

    The qualifier is only included in the span when that extension does
    not collide with an already-claimed span; the payload qualifier is
    recorded either way so the semantics are never lost.
    """
    if record.payload.get("qualifier"):
        return
    found = _qualifier_before(text, record.norm_start)
    if found is None:
        return
    qual, qual_start = found
    if not claims.overlaps(qual_start, record.norm_start):
        record.norm_start = qual_start
        record.raw_text = text[qual_start:record.norm_end]
        record.payload["raw"] = record.raw_text
    record.payload["qualifier"] = qual


Handler = Callable[[str, re.Match[str]], FactRecord | None]


def _scan(
    pattern: re.Pattern[str],
    text: str,
    claims: SpanClaims,
    handler: Handler,
) -> list[FactRecord]:
    records: list[FactRecord] = []
    for match in pattern.finditer(text):
        if claims.overlaps(match.start(), match.end()):
            continue
        record = handler(text, match)
        if record is None:
            continue
        _attach_qualifier(text, claims, record)
        claims.claim(record.norm_start, record.norm_end)
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Pattern handlers
# ---------------------------------------------------------------------------


def _on_range_currency(_text: str, match: re.Match[str]) -> FactRecord | None:
    currency = _currency(match.group("cur"))
    if currency is None:
        return None
    factor = 1
    scale_raw = match.group("scale")
    scale_info: dict[str, Any] | None = None
    if scale_raw:
        got = _scale_factor(scale_raw)
        if got is None:
            return None
        scale_info = {"scale": got[0], "scale_factor": got[1]}
        factor = got[1]
    lo = numeric_value(match.group("lo"), factor)
    hi = numeric_value(match.group("hi"), factor)
    if lo is None or hi is None:
        return None
    payload: dict[str, Any] = {
        "type": "currency",
        "value": None,
        "range": {"low": lo, "high": hi},
        "currency": currency,
        "currency_raw": match.group("cur"),
        "number_raw": f"{match.group('lo')}-{match.group('hi')}",
        "source": "regex:currency_range",
    }
    if scale_info is not None:
        payload.update(scale_info)
    return _emit("currency", match.group(), match.start(), match.end(), payload)


def _on_currency_prefix(_text: str, match: re.Match[str]) -> FactRecord | None:
    currency = _currency(match.group("cur"))
    if currency is None:
        return None
    factor = 1
    payload: dict[str, Any] = {
        "type": "currency",
        "currency": currency,
        "currency_raw": match.group("cur"),
        "number_raw": match.group("num"),
        "source": "regex:currency_prefix",
    }
    scale_raw = match.group("scale")
    if scale_raw:
        got = _scale_factor(scale_raw)
        if got is None:
            return None
        payload["scale"] = got[0]
        payload["scale_factor"] = got[1]
        factor = got[1]
    value = numeric_value(match.group("num"), factor)
    if value is None:
        return None
    payload["value"] = value
    return _emit("currency", match.group(), match.start(), match.end(), payload)


def _on_currency_suffix(_text: str, match: re.Match[str]) -> FactRecord | None:
    currency = _currency(match.group("cur"))
    if currency is None:
        return None
    factor = 1
    payload: dict[str, Any] = {
        "type": "currency",
        "currency": currency,
        "currency_raw": match.group("cur"),
        "number_raw": match.group("num"),
        "source": "regex:currency_suffix",
    }
    scale_raw = match.group("scale")
    if scale_raw:
        got = _scale_factor(scale_raw)
        if got is None:
            return None
        payload["scale"] = got[0]
        payload["scale_factor"] = got[1]
        factor = got[1]
    value = numeric_value(match.group("num"), factor)
    if value is None:
        return None
    payload["value"] = value
    return _emit("currency", match.group(), match.start(), match.end(), payload)


def _on_percent_range(_text: str, match: re.Match[str]) -> FactRecord | None:
    lo = numeric_value(match.group("lo"))
    hi = numeric_value(match.group("hi"))
    if lo is None or hi is None:
        return None
    return _emit(
        "percentage",
        match.group(),
        match.start(),
        match.end(),
        {
            "type": "percentage",
            "value": None,
            "range": {"low": lo, "high": hi},
            "unit": "percent",
            "source": "regex:percent_range",
        },
    )


def _on_percent(_text: str, match: re.Match[str]) -> FactRecord | None:
    value = numeric_value(match.group("num"))
    if value is None:
        return None
    return _emit(
        "percentage",
        match.group(),
        match.start(),
        match.end(),
        {
            "type": "percentage",
            "value": value,
            "unit": "percent",
            "number_raw": match.group("num"),
            "source": "regex:percent",
        },
    )


def _on_duration_range(_text: str, match: re.Match[str]) -> FactRecord | None:
    lo = duration_value(match.group("lo"), None)
    hi = duration_value(match.group("hi"), None)
    if lo is None or hi is None:
        return None
    unit, calendar_mod = parse_duration_unit(match)
    payload: dict[str, Any] = {
        "type": "duration",
        "value": None,
        "range": {"low": lo, "high": hi},
        "unit": unit,
        "source": "regex:duration_range",
    }
    if calendar_mod:
        payload["calendar"] = calendar_mod
    return _emit("duration", match.group(), match.start(), match.end(), payload)


def _on_duration(_text: str, match: re.Match[str]) -> FactRecord | None:
    value = duration_value(match.group("num"), match.group("word"))
    if value is None:
        return None
    unit, calendar_mod = parse_duration_unit(match)
    payload: dict[str, Any] = {
        "type": "duration",
        "value": value,
        "unit": unit,
        "source": "regex:duration",
    }
    if match.group("word"):
        payload["number_form"] = "word"
    if calendar_mod:
        payload["calendar"] = calendar_mod
    return _emit("duration", match.group(), match.start(), match.end(), payload)


def _on_ratio(text: str, match: re.Match[str]) -> FactRecord | None:
    if _AMPM_AFTER.match(text, match.end()) is not None:
        return None
    window = text[max(0, match.start() - 8) : match.start()]
    if _AT_BEFORE.search(window) is not None:
        return None
    a, b = int(match.group("a")), int(match.group("b"))
    return _emit(
        "ratio",
        match.group(),
        match.start(),
        match.end(),
        {
            "type": "ratio",
            "value": f"{a}:{b}",
            "a": a,
            "b": b,
            "source": "regex:ratio",
        },
    )


def _on_quantity(_text: str, match: re.Match[str]) -> FactRecord | None:
    value = numeric_value(match.group("num"))
    if value is None:
        return None
    unit = match.group("qunit").lower()
    if len(unit) > 2 and unit.endswith("s"):
        unit = unit[:-1]
    return _emit(
        "quantity",
        match.group(),
        match.start(),
        match.end(),
        {
            "type": "quantity",
            "value": value,
            "unit": unit,
            "number_raw": match.group("num"),
            "source": "regex:quantity",
        },
    )


def _on_qualified_number(text: str, match: re.Match[str]) -> FactRecord | None:
    if _SCALE_AFTER.match(text, match.end()) is not None:
        return None
    value = numeric_value(match.group("num"))
    if value is None:
        return None
    sub = "integer" if isinstance(value, int) else "decimal"
    return _emit(
        sub,
        match.group(),
        match.start(),
        match.end(),
        {
            "type": sub,
            "value": value,
            "qualifier": _norm_qual(match.group("qual")),
            "number_raw": match.group("num"),
            "source": "regex:qualified_number",
        },
    )


# ---------------------------------------------------------------------------
# Engine entry point (fixed pattern order = priority order)
# ---------------------------------------------------------------------------


def extract(text: str, claims: SpanClaims) -> list[FactRecord]:
    records: list[FactRecord] = []
    for pattern, handler in (
        (_RANGE_CURRENCY, _on_range_currency),
        (_CURRENCY_PREFIX, _on_currency_prefix),
        (_CURRENCY_SUFFIX, _on_currency_suffix),
        (_PERCENT_RANGE, _on_percent_range),
        (_PERCENT, _on_percent),
        (_DURATION_RANGE, _on_duration_range),
        (_DURATION, _on_duration),
        (_RATIO, _on_ratio),
        (_QUANTITY, _on_quantity),
        (_QUALIFIED_NUMBER, _on_qualified_number),
    ):
        records.extend(_scan(pattern, text, claims, handler))
    return records


__all__ = ["ENGINE", "extract"]
