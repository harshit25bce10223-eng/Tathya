"""Deterministic date extraction engine.

Locked behaviour:
    - enumerated absolute forms are parsed by explicit regexes, never by
      guessing: 22 December 2026 / 22 Dec 2026 / 22-12-2026 / 22/12/2026 /
      22.12.2026 / 2026-12-22 / Dec 22, 2026 / 15 December / December 2026
    - day-first/month-first is AMBIGUOUS when both parts are <= 12
      (03/04/2026): the fact is marked `ambiguous` with both readings and
      NO resolved date — never silently misinterpreted
    - partial dates (15 December, December 2026) keep the missing fields
      null; no year is ever invented
    - relative expressions (within 30 days, next month, end of FY2026)
      are stored as raw + semantic structure; no absolute date is
      fabricated from them
    - dateparser is the SECONDARY parser, for non-enumerated absolute
      forms only ("the 22nd of December 2026", lowercase "22 may 2026").
      It is pinned to two fixed reference bases and a candidate is
      accepted only when both bases agree — relative and partial parses
      structurally disagree across bases and are therefore refused.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

import dateparser
from dateparser.search import search_dates

from app.core.extraction.base import CATEGORY_DATE, FactRecord, SpanClaims
from app.core.extraction.tokens import (
    DURATION_UNIT_SOURCE,
    NUMBER_SOURCE,
    WORD_NUM_ALT,
    duration_value,
    parse_duration_unit,
)

ENGINE = "date"

# ---------------------------------------------------------------------------
# Month vocabulary (English + common Devanagari forms)
# ---------------------------------------------------------------------------

_MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "जनवरी": 1,
    "february": 2,
    "feb": 2,
    "फरवरी": 2,
    "फ़रवरी": 2,
    "march": 3,
    "mar": 3,
    "मार्च": 3,
    "april": 4,
    "apr": 4,
    "अप्रैल": 4,
    "may": 5,
    "मई": 5,
    "june": 6,
    "jun": 6,
    "जून": 6,
    "july": 7,
    "jul": 7,
    "जुलाई": 7,
    "august": 8,
    "aug": 8,
    "अगस्त": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "सितंबर": 9,
    "सितम्बर": 9,
    "october": 10,
    "oct": 10,
    "अक्टूबर": 10,
    "november": 11,
    "nov": 11,
    "नवंबर": 11,
    "नवम्बर": 11,
    "december": 12,
    "dec": 12,
    "दिसंबर": 12,
    "दिसम्बर": 12,
}

# "may" is matched case-sensitively (Title case) to avoid the modal verb;
# every other month name matches case-insensitively.
_months_no_may = sorted(
    (m for m in _MONTHS if m.lower() != "may"), key=len, reverse=True
)
_MONTH_ALT = (
    "(?i:(?:" + "|".join(re.escape(m) for m in _months_no_may) + "))|May"
)

_MONTH_LOOKUP: dict[str, int] = {m.lower(): n for m, n in _MONTHS.items()}


def _month_number(token: str) -> int | None:
    if token == "May":
        return 5
    return _MONTH_LOOKUP.get(token.lower())


# ---------------------------------------------------------------------------
# Enumerated absolute forms
# ---------------------------------------------------------------------------

_ORDINAL = r"(?i:st|nd|rd|th)?"

_DMONY = re.compile(
    rf"(?<!\d)(?P<day>\d{{1,2}}){_ORDINAL}\s+(?P<mon>{_MONTH_ALT})\.?"
    rf"\s*,?\s*(?P<year>\d{{4}})(?!\d)"
)
_MONDY = re.compile(
    rf"(?<![A-Za-z])(?P<mon>{_MONTH_ALT})\.?\s+(?P<day>\d{{1,2}}){_ORDINAL}"
    rf"\s*,?\s*(?P<year>\d{{4}})(?!\d)"
)
_ISO = re.compile(
    r"(?<![\d-])(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)"
)
# Day-first numeric with a consistent separator; a dot separator requires a
# 4-digit year so version strings like "1.2.34" are never read as dates.
_DMY = re.compile(
    r"(?<![\d])(?P<a>\d{1,2})(?P<sep>[./-])(?P<b>\d{1,2})(?P=sep)(?P<yr>\d{2,4})(?!\d)"
)
_FY = re.compile(
    r"(?<![A-Za-z0-9])FY[\s-]?(?P<y1>\d{2,4})(?:-(?P<y2>\d{2,4}))?(?!\d)"
)
_DMON = re.compile(
    rf"(?<!\d)(?P<day>\d{{1,2}}){_ORDINAL}\s+(?P<mon>{_MONTH_ALT})\.?"
    rf"(?!\s*,?\s*\d)"
)
_MONY = re.compile(
    rf"(?<![A-Za-z])(?P<mon>{_MONTH_ALT})\.?\s+(?P<year>\d{{4}})(?!\d)"
)

# ---------------------------------------------------------------------------
# Relative forms (structure only — no absolute date is ever fabricated)
# ---------------------------------------------------------------------------

_WITHIN = re.compile(
    rf"(?<![A-Za-z])(?:within|inside)(?:\s+the\s+next|\s+next)?\s+"
    rf"(?:(?P<num>{NUMBER_SOURCE})|(?P<word>{WORD_NUM_ALT}))"
    rf"[\s-]{{0,2}}{DURATION_UNIT_SOURCE}(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_NEXT = re.compile(
    r"(?<![A-Za-z])next\s+(?:(?P<num>\d{1,3})\s+)?"
    r"(?P<unit>week|month|quarter|year|fortnight|financial\s+year|fiscal\s+year)s?"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Qualifiers recorded on the payload (never silently resolved)
# ---------------------------------------------------------------------------

_PRECEDING_ANCHOR = re.compile(
    r"(?:\b(by|before|after|from|on|until|till|since)\s+"
    r"|\b(no\s+later\s+than|not\s+later\s+than|prior\s+to)\s+)$",
    re.IGNORECASE,
)
_FY_ANCHOR = re.compile(
    r"(?:\b(end\s+of|close\s+of|start\s+of|beginning\s+of)\s+)$", re.IGNORECASE
)


def _preceding_qualifier(text: str, start: int, pattern: re.Pattern[str]) -> str | None:
    window = text[max(0, start - 30) : start]
    match = pattern.search(window)
    if match is None:
        return None
    return next((g for g in match.groups() if g), None)


def _expand_year(raw: str) -> tuple[int, dict[str, Any]]:
    """4-digit years pass through; 2-digit years use the fixed pivot
    00-69 -> 2000s, 70-99 -> 1900s (recorded, deterministic)."""
    year = int(raw)
    if len(raw) == 4:
        return year, {}
    return (2000 + year if year <= 69 else 1900 + year), {
        "year_raw": raw,
        "year_pivot_rule": "00-69->2000s|70-99->1900s",
    }


def _valid(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


# ---------------------------------------------------------------------------
# dateparser fallback (dual fixed bases; only agreeing absolutes survive)
# ---------------------------------------------------------------------------

_BASE_A = datetime(2000, 1, 1, tzinfo=UTC)
_BASE_B = datetime(2010, 6, 15, tzinfo=UTC)
_PARSER_SETTINGS_BASE: dict[str, Any] = {"RETURN_AS_TIMEZONE_AWARE": False}
_MONTH_HINT = re.compile(r"(?<![A-Za-z])[A-Za-z]{3,9}\b")
_YEAR_MIN, _YEAR_MAX = 1900, 2100


def _search(window: str, base: datetime) -> list[tuple[str, datetime]]:
    settings = dict(_PARSER_SETTINGS_BASE)
    settings["RELATIVE_BASE"] = base
    try:
        found = search_dates(window, languages=["en"], settings=settings)
    except Exception:  # noqa: BLE001 - third-party parser must never crash a job
        return []
    return [(item[0], item[1]) for item in found or []]


def _dateparser_fallback(text: str, claims: SpanClaims) -> list[FactRecord]:
    records: list[FactRecord] = []
    for hint in _MONTH_HINT.finditer(text):
        token = hint.group()
        if _month_number(token) is None and token.lower() != "may":
            continue
        window_start = max(0, hint.start() - 24)
        window_end = min(len(text), hint.end() + 36)
        window = text[window_start:window_end]
        results_a = _search(window, _BASE_A)
        if not results_a:
            continue
        results_b = _search(window, _BASE_B)
        agreeing = {
            matched: parsed
            for matched, parsed in results_a
            if any(m == matched and p == parsed for m, p in results_b)
        }
        for matched, parsed in sorted(agreeing.items()):
            if not (_YEAR_MIN <= parsed.year <= _YEAR_MAX):
                continue
            index = window.find(matched)
            if index < 0:
                continue
            start = window_start + index
            end = start + len(matched)
            if claims.overlaps(start, end):
                continue
            qualifier = _preceding_qualifier(text, start, _PRECEDING_ANCHOR)
            payload: dict[str, Any] = {
                "engine": ENGINE,
                "raw": matched,
                "kind": "absolute",
                "iso": parsed.date().isoformat(),
                "day": parsed.day,
                "month": parsed.month,
                "year": parsed.year,
                "precision": "day",
                "ambiguous": False,
                "qualifier": qualifier,
                "source": "dateparser",
            }
            records.append(
                FactRecord(
                    category=f"{CATEGORY_DATE}.absolute",
                    raw_text=matched,
                    norm_start=start,
                    norm_end=end,
                    payload=payload,
                )
            )
            claims.claim(start, end)
    return records


# ---------------------------------------------------------------------------
# Pattern handlers
# ---------------------------------------------------------------------------


def _match_month(token: str) -> int | None:
    return _month_number(token)


def _emit(
    category: str,
    raw: str,
    start: int,
    end: int,
    payload: dict[str, Any],
) -> FactRecord:
    payload.setdefault("engine", ENGINE)
    payload.setdefault("raw", raw)
    return FactRecord(
        category=category,
        raw_text=raw,
        norm_start=start,
        norm_end=end,
        payload=payload,
    )


def _scan(
    pattern: re.Pattern[str],
    text: str,
    claims: SpanClaims,
    handler,
) -> list[FactRecord]:
    records: list[FactRecord] = []
    for match in pattern.finditer(text):
        if claims.overlaps(match.start(), match.end()):
            continue
        record = handler(text, match)
        if record is None:
            continue
        claims.claim(record.norm_start, record.norm_end)
        records.append(record)
    return records


def _on_dmony(text: str, match: re.Match[str]) -> FactRecord | None:
    day, month, year = int(match.group("day")), _match_month(match.group("mon")), int(
        match.group("year")
    )
    if month is None or not _valid(year, month, day):
        return None
    qualifier = _preceding_qualifier(text, match.start(), _PRECEDING_ANCHOR)
    return _emit(
        f"{CATEGORY_DATE}.absolute",
        match.group(),
        match.start(),
        match.end(),
        {
            "kind": "absolute",
            "iso": date(year, month, day).isoformat(),
            "day": day,
            "month": month,
            "year": year,
            "precision": "day",
            "ambiguous": False,
            "qualifier": qualifier,
            "source": "regex:dmonthyear",
        },
    )


def _on_mondy(text: str, match: re.Match[str]) -> FactRecord | None:
    return _on_dmony(text, match)


def _on_iso(text: str, match: re.Match[str]) -> FactRecord | None:
    year, month, day = (
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )
    if not _valid(year, month, day):
        return None
    qualifier = _preceding_qualifier(text, match.start(), _PRECEDING_ANCHOR)
    return _emit(
        f"{CATEGORY_DATE}.absolute",
        match.group(),
        match.start(),
        match.end(),
        {
            "kind": "absolute",
            "iso": date(year, month, day).isoformat(),
            "day": day,
            "month": month,
            "year": year,
            "precision": "day",
            "ambiguous": False,
            "qualifier": qualifier,
            "source": "regex:iso",
        },
    )


def _on_dmy(text: str, match: re.Match[str]) -> FactRecord | None:
    a, b = int(match.group("a")), int(match.group("b"))
    sep, yr_raw = match.group("sep"), match.group("yr")
    if sep == "." and len(yr_raw) != 4:
        return None
    year, year_extra = _expand_year(yr_raw)
    qualifier = _preceding_qualifier(text, match.start(), _PRECEDING_ANCHOR)
    base = {"kind": "absolute", "year": year, "precision": "day",
            "qualifier": qualifier, "source": "regex:dayfirst", **year_extra}
    if a > 12 >= b:
        # day-first is the only reading (22/12/2026)
        if not _valid(year, b, a):
            return None
        return _emit(
            f"{CATEGORY_DATE}.absolute",
            match.group(),
            match.start(),
            match.end(),
            {
                **base,
                "iso": date(year, b, a).isoformat(),
                "day": a,
                "month": b,
                "ambiguous": False,
            },
        )
    if b > 12 >= a:
        # month-first is the only reading (12/22/2026)
        if not _valid(year, a, b):
            return None
        return _emit(
            f"{CATEGORY_DATE}.absolute",
            match.group(),
            match.start(),
            match.end(),
            {
                **base,
                "iso": date(year, a, b).isoformat(),
                "day": b,
                "month": a,
                "ambiguous": False,
            },
        )
    if a <= 12 and b <= 12:
        # AMBIGUOUS (03/04/2026): both readings recorded, none resolved
        dmy_iso = (
            date(year, b, a).isoformat() if _valid(year, b, a) else None
        )
        mdy_iso = (
            date(year, a, b).isoformat() if _valid(year, a, b) else None
        )
        return _emit(
            f"{CATEGORY_DATE}.ambiguous",
            match.group(),
            match.start(),
            match.end(),
            {
                **base,
                "iso": None,
                "day": None,
                "month": None,
                "ambiguous": True,
                "interpretations": [
                    {"order": "dmy", "iso": dmy_iso},
                    {"order": "mdy", "iso": mdy_iso},
                ],
                "note": "day-first vs month-first undecidable; never resolved",
            },
        )
    return None


def _on_fy(text: str, match: re.Match[str]) -> FactRecord | None:
    y1_raw = match.group("y1")
    y1, extra = _expand_year(y1_raw)
    years = [y1]
    y2_raw = match.group("y2")
    if y2_raw:
        y2, _ = _expand_year(y2_raw)
        years.append(y2)
    qualifier = _preceding_qualifier(text, match.start(), _FY_ANCHOR)
    return _emit(
        f"{CATEGORY_DATE}.fiscal_year",
        match.group(),
        match.start(),
        match.end(),
        {
            "kind": "fiscal_year",
            "years": years,
            "year": y1,
            "precision": "fiscal_year",
            "iso": None,
            "qualifier": qualifier,
            "source": "regex:fy",
            **extra,
        },
    )


def _on_dmon(text: str, match: re.Match[str]) -> FactRecord | None:
    day, month = int(match.group("day")), _match_month(match.group("mon"))
    if month is None or not 1 <= day <= 31:
        return None
    qualifier = _preceding_qualifier(text, match.start(), _PRECEDING_ANCHOR)
    return _emit(
        f"{CATEGORY_DATE}.partial",
        match.group(),
        match.start(),
        match.end(),
        {
            "kind": "partial",
            "iso": None,
            "day": day,
            "month": month,
            "year": None,
            "precision": "day",
            "missing": ["year"],
            "ambiguous": False,
            "qualifier": qualifier,
            "source": "regex:daymonth",
        },
    )


def _on_mony(text: str, match: re.Match[str]) -> FactRecord | None:
    month, year = _match_month(match.group("mon")), int(match.group("year"))
    if month is None:
        return None
    return _emit(
        f"{CATEGORY_DATE}.partial",
        match.group(),
        match.start(),
        match.end(),
        {
            "kind": "partial",
            "iso": None,
            "day": None,
            "month": month,
            "year": year,
            "precision": "month",
            "missing": ["day"],
            "ambiguous": False,
            "qualifier": _preceding_qualifier(text, match.start(), _PRECEDING_ANCHOR),
            "source": "regex:monthyear",
        },
    )


def _on_within(text: str, match: re.Match[str]) -> FactRecord | None:
    value = duration_value(match.group("num"), match.group("word"))
    if value is None:
        return None
    unit, calendar_mod = parse_duration_unit(match)
    payload: dict[str, Any] = {
        "kind": "relative",
        "expression": "within",
        "iso": None,
        "duration": {"value": value, "unit": unit},
        "precision": "duration",
        "ambiguous": False,
        "qualifier": None,
        "source": "regex:within",
    }
    if calendar_mod:
        payload["duration"]["calendar"] = calendar_mod
    return _emit(
        f"{CATEGORY_DATE}.relative",
        match.group().strip(),
        match.start(),
        match.end(),
        payload,
    )


def _on_next(text: str, match: re.Match[str]) -> FactRecord | None:
    unit = re.sub(r"\s+", " ", match.group("unit").lower())
    payload: dict[str, Any] = {
        "kind": "relative",
        "expression": "next",
        "iso": None,
        "unit": unit,
        "precision": "unit",
        "ambiguous": False,
        "qualifier": None,
        "source": "regex:next",
    }
    num_raw = match.group("num")
    if num_raw:
        payload["count"] = int(num_raw)
    return _emit(
        f"{CATEGORY_DATE}.relative",
        match.group().strip(),
        match.start(),
        match.end(),
        payload,
    )


# ---------------------------------------------------------------------------
# Engine entry point (fixed pattern order = priority order)
# ---------------------------------------------------------------------------


def extract(text: str, claims: SpanClaims) -> list[FactRecord]:
    records: list[FactRecord] = []
    for pattern, handler in (
        (_DMONY, _on_dmony),
        (_MONDY, _on_mondy),
        (_ISO, _on_iso),
        (_DMY, _on_dmy),
        (_FY, _on_fy),
        (_DMON, _on_dmon),
        (_MONY, _on_mony),
        (_WITHIN, _on_within),
        (_NEXT, _on_next),
    ):
        records.extend(_scan(pattern, text, claims, handler))
    records.extend(_dateparser_fallback(text, claims))
    return records


__all__ = ["ENGINE", "extract"]
