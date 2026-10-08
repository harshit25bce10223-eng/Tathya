"""Shared token helpers for the deterministic extraction engines.

Everything here is a pure function of the input text: no LLM, no clock,
no randomness, so identical inputs always produce identical facts.

Number rules (locked):
    - Indian comma groups (41,60,000 / 4,16,00,000) and Western groups
      (1,234,567) both match as ONE number — never split mid-number
    - a bare number with no anchor (no currency/scale/percent/duration/
      qualifier) is NOT a fact: it protects dates and IDs from being
      shredded into meaningless integers
    - word numbers are used for DURATION expressions only; word-number
      currency is deliberately not extracted because a partial word span
      ("Forty-One Lakh" inside "Forty-One Lakh Sixty Thousand") would
      misstate the value
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# Digit-group number: Indian (2-3 digit groups) or Western (3-digit groups),
# optional decimal part. "41,60,000" / "1,234,567" / "41.6" / "7"
NUMBER_SOURCE = r"(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"

# ---------------------------------------------------------------------------
# Word numbers (English 1-99 + common Hindi units) — duration context only
# ---------------------------------------------------------------------------

_WORD_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_WORD_UNITS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_HINDI_NUMBERS: dict[str, int] = {
    "एक": 1,
    "दो": 2,
    "तीन": 3,
    "चार": 4,
    "पाँच": 5,
    "पांच": 5,
    "छह": 6,
    "छः": 6,
    "सात": 7,
    "आठ": 8,
    "नौ": 9,
    "दस": 10,
    "बारह": 12,
    "पंद्रह": 15,
}

_WORD_NUM_ALT = (
    r"(?:(?:ninety|eighty|seventy|sixty|fifty|forty|thirty|twenty)"
    r"(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?"
    r"|nineteen|eighteen|seventeen|sixteen|fifteen|fourteen|thirteen|twelve"
    r"|eleven|ten|nine|eight|seven|six|five|four|three|two|one"
    r"|एक|दो|तीन|चार|पाँच|पांच|छह|छः|सात|आठ|नौ|दस|बारह|पंद्रह)"
)

_WORD_NUM_RE = re.compile(_WORD_NUM_ALT, re.IGNORECASE)

# Public alias: engines embed this in their patterns.
WORD_NUM_ALT = _WORD_NUM_ALT


def parse_word_number(text: str) -> int | None:
    """Parse an English/Hindi word number (1-99). None when not a word number."""
    match = _WORD_NUM_RE.fullmatch(text.strip())
    if match is None:
        return None
    lowered = text.strip().lower()
    if lowered in _HINDI_NUMBERS:
        return _HINDI_NUMBERS[lowered]
    parts = re.split(r"[\s-]+", lowered)
    total = 0
    for part in parts:
        if part in _WORD_TENS:
            total += _WORD_TENS[part]
        elif part in _WORD_UNITS:
            total += _WORD_UNITS[part]
        else:
            return None
    return total


# ---------------------------------------------------------------------------
# Duration units (English + common Hindi forms)
# ---------------------------------------------------------------------------

DURATION_UNIT_SOURCE = (
    r"(?:(?P<cal>business|working|calendar)\s+)?"
    r"(?P<unit>days?|weeks?|months?|years?|hours?|hrs?|minutes?|mins?|quarters?"
    r"|fortnights?|दिन|हफ़्ते|हफ़्ता|हफ्ते|हफ्ता|सप्ताह|महीने|महीना|महिने|महिना"
    r"|साल|वर्ष)"
)

_UNIT_CANON: dict[str, str] = {
    "day": "day",
    "days": "day",
    "दिन": "day",
    "week": "week",
    "weeks": "week",
    "हफ़्ते": "week",
    "हफ़्ता": "week",
    "हफ्ते": "week",
    "हफ्ता": "week",
    "सप्ताह": "week",
    "month": "month",
    "months": "month",
    "महीने": "month",
    "महीना": "month",
    "महिने": "month",
    "महिना": "month",
    "year": "year",
    "years": "year",
    "साल": "year",
    "वर्ष": "year",
    "hour": "hour",
    "hours": "hour",
    "hr": "hour",
    "hrs": "hour",
    "minute": "minute",
    "minutes": "minute",
    "min": "minute",
    "mins": "minute",
    "quarter": "quarter",
    "quarters": "quarter",
    "fortnight": "fortnight",
    "fortnights": "fortnight",
}


def parse_duration_unit(match: re.Match[str]) -> tuple[str, str | None]:
    """Return (canonical unit, calendar modifier) from a duration match."""
    unit_raw = (match.group("unit") or "").lower()
    calendar_mod = (match.group("cal") or "").lower() or None
    return _UNIT_CANON.get(unit_raw, unit_raw), calendar_mod


# ---------------------------------------------------------------------------
# Digit-number parsing (Decimal-exact, no float drift)
# ---------------------------------------------------------------------------


def numeric_value(raw_number: str, multiplier: int | None = None) -> int | float | None:
    """Parse a matched digit token. Indian/Western commas stripped, exact
    Decimal arithmetic, int when integral. None when the token is malformed."""
    clean = raw_number.replace(",", "").strip()
    if not clean or not re.fullmatch(r"\d+(\.\d+)?", clean):
        return None
    try:
        dec = Decimal(clean)
    except InvalidOperation:
        return None
    if multiplier is not None:
        dec *= Decimal(multiplier)
    if dec == dec.to_integral_value():
        return int(dec)
    return float(dec)


def duration_value(raw_number: str | None, raw_word: str | None) -> int | None:
    """Duration amount from a digit token or a word number."""
    if raw_number:
        value = numeric_value(raw_number)
        return int(value) if isinstance(value, int) else None
    if raw_word:
        return parse_word_number(raw_word)
    return None


__all__ = [
    "DURATION_UNIT_SOURCE",
    "NUMBER_SOURCE",
    "WORD_NUM_ALT",
    "duration_value",
    "numeric_value",
    "parse_duration_unit",
    "parse_word_number",
]
