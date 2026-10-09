"""Conservative deterministic comparisons against actual current source quotes."""
from __future__ import annotations

import re
from decimal import Decimal

from app.core.extraction.base import SpanClaims
from app.core.extraction.numeric import extract as numeric_records
from app.core.extraction.dates import extract as date_records


def field_hint(text: str) -> str | None:
    fields = {
        "contract_value": r"contract\s+(?:value|amount|price)|total\s+(?:value|price)|purchase\s+price",
        "delivery": r"deliver|completion|deadline",
        "payment": r"payment|\bnet\s+\d|payable",
        "warranty": r"warranty|guarantee\s+period",
        "liability": r"liability|indemn",
        "sla": r"uptime|\bsla\b|availability",
        "tax": r"\btax\b|\bgst\b",
    }
    matches = [field for field, pattern in fields.items() if re.search(pattern, text, re.I)]
    return matches[0] if len(matches) == 1 else None


def values(text: str) -> dict[str, tuple]:
    spans = SpanClaims()
    records = numeric_records(text, spans) + date_records(text, spans)
    output: dict[str, list] = {}
    for record in records:
        # Extraction must be grounded in the literal cited text.
        if record.raw_text != text[record.norm_start:record.norm_end]:
            continue
        p = record.payload
        kind = p.get("type")
        value = p.get("value")
        if kind == "currency" and value is not None:
            key, value = "currency:" + str(p.get("currency")), Decimal(str(value))
        elif kind == "duration" and value is not None:
            unit = str(p.get("unit", "")).lower().rstrip("s")
            value = Decimal(str(value))
            if unit == "year": unit, value = "month", value * 12
            if unit == "week": unit, value = "day", value * 7
            key = "duration:" + unit
        elif kind == "percentage" and value is not None:
            key, value = "percentage", Decimal(str(value))
        elif p.get("kind") == "absolute" and p.get("iso"):
            key, value = "date", p["iso"]
        else:
            continue
        output.setdefault(key, []).append(value)
    return {key: tuple(items) for key, items in output.items()}


def compare_quote(claim: str, quote: str) -> str | None:
    """Compare like business fields; never compare unrelated numbers or dates."""
    # Equality of a number cannot prove negation, conditional or bounded terms.
    qualifiers = r"\b(?:not|never|unless|except|without|may|might|up\s+to|at\s+least|at\s+most|more\s+than|less\s+than|minimum|maximum)\b|n't\b"
    if re.search(qualifiers, claim + " " + quote, re.I):
        return None
    claim_field, source_field = field_hint(claim), field_hint(quote)
    if not claim_field or claim_field != source_field:
        return None
    claim_values, source_values = values(claim), values(quote)
    shared = set(claim_values) & set(source_values)
    if not shared:
        return None
    # A sentence with multiple amounts/dates needs a more specific field match.
    if any(len(claim_values[k]) != 1 or len(source_values[k]) != 1 for k in shared):
        return None
    if any(claim_values[k] != source_values[k] for k in shared):
        return "contradicted"
    if set(claim_values) == shared:
        return "supported"
    return None
