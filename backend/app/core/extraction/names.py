"""Deterministic name extraction + conservative normalization engine.

Locked behaviour:
    - organizations are detected ONLY by structural anchors: a legal
      designator suffix (Ltd / Pvt Ltd / Inc / Corp / LLC / LLP / Trust /
      Bank / University ...) or an org-type word (Solutions, Enterprises,
      Systems, Consultancy ...) closing a capitalized sequence. A bare
      brand word is never a fact.
    - a full organization name and its short form are BOTH kept as
      separate facts ("Tata Consultancy Services Ltd." AND "TCS"):
      the short form is emitted only when it is the initials of an
      organization seen in the same text or was defined in a
      parenthetical right after it — never guessed from a bare token.
    - persons are accepted only when the sequence is lexicon-anchored
      (first token in the given-name lexicon or an initial, last token
      in the surname lexicon or an initial) and contains no stop word,
      no designator and no org-type word.
    - normalized_name is conservative: casefolded, honorifics stripped,
      initials collapsed, legal designators canonicalized (Ltd/Limited ->
      "ltd", Pvt Ltd/Private Limited -> "pvt ltd"). Nothing else is
      rewritten, transliterated or translit-merged.
    - rapidfuzz similarity is EVIDENCE, never truth: a high similarity
      against a different earlier name is recorded as a conservative
      `match_candidate` with the score. Names are NEVER merged and no
      fact is dropped because of a fuzzy match.
    - everything here is a pure function of the input text: no LLM,
      no clock, no randomness.
"""

from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz

from app.core.extraction.base import CATEGORY_NAME, FactRecord, SpanClaims

ENGINE = "name"

# ---------------------------------------------------------------------------
# Legal designators (case-insensitive) closing an organization name
# ---------------------------------------------------------------------------

_DESIGNATORS: list[str] = [
    r"pvt\.?\s+ltd\.?",
    r"private\s+limited",
    r"ltd\.?",
    r"limited",
    r"inc\.?",
    r"incorporated",
    r"corp\.?",
    r"corporation",
    r"llc",
    r"llp",
    r"plc",
    r"gmbh",
    r"co\.?",
    r"company",
    r"trust",
    r"foundation",
    r"council",
    r"association",
    r"authority",
    r"board",
    r"bank",
    r"university",
    r"institute",
    r"college",
    r"school",
    r"hospital",
    r"laboratory",
    r"laboratories",
    r"labs\.?",
]
_DESIGNATOR_SOURCE = r"(?i:(?:" + "|".join(_DESIGNATORS) + r"))"

# Canonical form per designator word (normalized_name uses these).
_DESIGNATOR_CANON: dict[str, str] = {
    "ltd": "ltd",
    "ltd.": "ltd",
    "limited": "ltd",
    "pvt": "pvt",
    "pvt.": "pvt",
    "private": "pvt",
    "inc": "inc",
    "inc.": "inc",
    "incorporated": "inc",
    "corp": "corp",
    "corp.": "corp",
    "corporation": "corp",
    "co": "co",
    "co.": "co",
    "company": "co",
    "llc": "llc",
    "llp": "llp",
    "plc": "plc",
    "gmbh": "gmbh",
    "trust": "trust",
    "foundation": "foundation",
    "council": "council",
    "association": "association",
    "authority": "authority",
    "board": "board",
    "bank": "bank",
    "university": "university",
    "institute": "institute",
    "college": "college",
    "school": "school",
    "hospital": "hospital",
    "laboratory": "laboratory",
    "laboratories": "laboratories",
    "labs": "labs",
    "labs.": "labs",
}

# ---------------------------------------------------------------------------
# Org-type words that close a capitalized name WITHOUT a designator
# (Title-case only, so "orion solutions" in prose never matches)
# ---------------------------------------------------------------------------

_ORG_MID_WORDS: dict[str, str] = {
    "Solutions": "solutions",
    "Enterprises": "enterprises",
    "Technologies": "technologies",
    "Systems": "systems",
    "Services": "services",
    "Networks": "networks",
    "Consultancy": "consultancy",
    "Consultancies": "consultancies",
    "Software": "software",
    "Infotech": "infotech",
    "Industries": "industries",
    "Holdings": "holdings",
    "Ventures": "ventures",
}
_ORG_MID_SOURCE = "|".join(_ORG_MID_WORDS)

# Capitalized token: Title word ("Zenith"), ALL-CAPS word ("IBM") or
# ampersand ("AT&T" style is left to the ALL-CAPS arm).
_ORG_TOKEN = r"(?:[A-Z][a-z]+\.?|[A-Z]{2,}\.?)"

_ORG_WITH_DESIGNATOR = re.compile(
    rf"(?<![A-Za-z0-9&])"
    rf"(?P<name>(?:{_ORG_TOKEN}\s+){{0,4}}{_ORG_TOKEN}\s*)"
    rf"(?P<desig>{_DESIGNATOR_SOURCE})\.?"
    rf"(?![A-Za-z-])"
)
_ORG_MIDWORD = re.compile(
    rf"(?<![A-Za-z0-9&])"
    rf"(?P<name>(?:{_ORG_TOKEN}\s+){{1,3}}{_ORG_TOKEN}\s*)"
    rf"(?P<mid>{_ORG_MID_SOURCE})"
    rf"(?![A-Za-z-])"
)

# Bare short-form token: 2-6 ALL-CAPS letters, standalone.
_SHORT_TOKEN = re.compile(r"(?<![A-Za-z])(?P<ac>[A-Z]{2,6})(?![A-Za-z])")

# Common Indian-legal / tech acronyms that are never organization facts.
_SHORT_BLOCKLIST: frozenset[str] = frozenset(
    """AI IT ID IP PO PI FY FYI MSA NDA SLA KPI RFP RFQ ERP CRM HRM TAT
    GST TDS PAN ITR VAT GSTIN IEC RBI SEBI MCA ICSI NCLT NIRC ICAI
    API URL URI PDF DOCX XLSX CSV JSON XML HTTP HTTPS SSL TCP LAN WAN
    VPN CEO CFO CTO CIO COO MD VP USA UK UAE INR USD EUR GBP AED
    QA QC ABC XYZ LTD PVT INC CORP NGO GOV PSU SOE LLP LLC PLC KFC
    CC BCC SMS IVR OTP ATM PIN TAN DIN CIN ERP SAP IBM HP BJP INC
    NDA UPI NEFT RTGS IMPS SWIFT ISO IEEE SI CAG CVC DG PS KL""".split()
)

# ---------------------------------------------------------------------------
# Person lexicons (deterministic, conservative, replaceable)
# ---------------------------------------------------------------------------

_GIVEN_NAMES: frozenset[str] = frozenset(
    """Amit Anil Ashok Arjun Ananya Aisha Aditi Akash Alok Amrita Anand
    Aparna Arun Avinash Bhavna Chetan Deepak Divya Gaurav Hari Harsh
    Harshit Isha Kavya Kiran Lalit Mahesh Manish Meera Mohan Nandini
    Neha Nidhi Nikhil Nisha Pooja Prachi Prakash Pranav Priya Rahul
    Raj Rajesh Rakesh Ramesh Ravi Rohan Rohit Sanya Sapna Shreya Suresh
    Sushma Vikas Vikram Vinod Yogesh Aaron Adam Alan Albert Alexander
    Alice Amanda Andrew Anna Anthony Arthur Barbara Benjamin Brian
    Carol Carlos Charles Charlotte Christopher Daniel David Diana
    Donald Dorothy Edward Elizabeth Emily Emma Eric Eugene Frank
    George Hannah Henry Isabella James Jane Jennifer Jessica John
    Joseph Karen Kathleen Kevin Laura Lawrence Linda Lisa Maria Marie
    Mark Mary Matthew Megan Michael Michelle Nancy Natalie Nicholas
    Noah Oliver Olivia Patricia Paul Peter Rachel Ralph Richard Robert
    Ronald Ruth Samuel Sarah Sharon Sophia Susan Thomas Walter
    William""".split()
)

_SURNAMES: frozenset[str] = frozenset(
    """Sharma Verma Gupta Singh Kumar Das Rao Reddy Nair Menon Iyer
    Patel Shah Mehta Joshi Desai Kulkarni Chatterjee Banerjee
    Mukherjee Krishnan Pillai Naidu Varma Malhotra Kapoor Chopra Bhatt
    Bose Chauhan Rathore Yadav Mishra Pandey Tiwari Dubey Agarwal
    Bansal Goel Grover Sethi Aiyar Iyengar Bhat Kaur Sidhu Gill Sandhu
    Bedi Sood Thakur Pandit Trivedi Vaidya Saxena Srivastava Shukla
    Tandon Sengupta Ghosh Dutta Choudhury Saikia Barua Nambiar Warrier
    Kurup Shenoy Bhandari Hegde Kamath Nayak Naik Raut Deshpande Jadhav
    Pawar Kale Lele Bapat Gokhale Ranade Phadke Smith Johnson Brown
    Wilson Taylor Anderson Jackson White Harris Martin Thompson Garcia
    Martinez Robinson Clark Lewis Lee Walker Hall Allen Young King
    Wright Scott Green Baker Adams Nelson Hill Campbell Mitchell
    Roberts Carter Phillips Evans Turner Parker Edwards Collins Stewart
    Morris Rogers Reed Cook Morgan Bell Murphy Bailey Rivera Cooper
    Richardson Cox Howard Ward Brooks Watson Gray Sanders Price Bennett
    Wood Barnes Ross Henderson Coleman Jenkins Perry Powell Long
    Patterson Hughes Flores Washington Butler Simmons Foster Gonzales
    Bryant Russell Griffin Diaz Hayes Myers Ford Hamilton Graham
    Sullivan Wallace Woods Cole West Jordan Owens Reynolds Fisher
    Ellis Harrison Gibson Cruz Marshall Ortiz Gutierrez Schultz Webb
    Fuller Lynch Dean""".split()
)

# Tokens that can never appear inside a person name.
_PERSON_STOP: frozenset[str] = frozenset(
    """January February March April June July August September October
    November December Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec
    Monday Tuesday Wednesday Thursday Friday Saturday Sunday
    Agreement Contract Clause Section Schedule Annexure Exhibit Party
    Parties Buyer Vendor Seller Purchaser Customer Client Supplier
    Contractor Subcontractor Payment Invoice Delivery Warranty
    Liability Indemnity Termination Notice Dispute Arbitration
    Confidentiality Force Majeure Mobile Email Phone Fax Address Date
    Value Terms Conditions Officer Manager Director Lead Finance
    India Indian Rupees Lakh Lakhs Crore Percentage Limited Private
    Officer Sign Signature Witness Whereof Hereinafter Hereunder
    Between Whereas Schedule Approved Base Commercial Billing Terms""".split()
)

_HONORIFIC_SOURCE = r"(?:(?:Mr|Mrs|Ms|Miss|Dr|Prof|Shri|Smt|Sri)\.?\s+)?"
_PERSON_TOKEN = r"(?:[A-Z][a-z]+\.?|[A-Z]\.)"
_PERSON = re.compile(
    rf"(?<![A-Za-z0-9])"
    rf"{_HONORIFIC_SOURCE}"
    rf"(?P<name>{_PERSON_TOKEN}(?:\s+{_PERSON_TOKEN}){{1,3}})"
    rf"(?![A-Za-z-])"
)

# rapidfuzz similarity is evidence, never truth.
_SIMILARITY_THRESHOLD_ORG = 92
_SIMILARITY_THRESHOLD_PERSON = 95
_MATCH_NOTE = "similarity is not truth; names are never merged"

# ---------------------------------------------------------------------------
# Normalization (conservative)
# ---------------------------------------------------------------------------


def _norm_org(name: str) -> str:
    """Casefold, canonicalize designator words, collapse whitespace."""
    raw_tokens = name.replace(",", " ").split()
    out: list[str] = []
    for token in raw_tokens:
        canonical = _DESIGNATOR_CANON.get(token)
        out.append(canonical if canonical else token.casefold())
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def _norm_person(name: str) -> str:
    """Casefold, strip honorifics, collapse initials ('R. K.' -> 'r k')."""
    cleaned = re.sub(r"(?i)\b(?:mr|mrs|ms|miss|dr|prof|shri|smt|sri)\.?\s+", "", name)
    tokens = [t.replace(".", "").casefold() for t in cleaned.split()]
    return " ".join(tokens)


def _strip_trailing_period(raw: str) -> str:
    return raw[:-1] if raw.endswith(".") else raw


# ---------------------------------------------------------------------------
# Emit helper
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
        category=f"{CATEGORY_NAME}.{sub}",
        raw_text=raw,
        norm_start=start,
        norm_end=end,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Organization handlers
# ---------------------------------------------------------------------------


def _org_name_tokens(match: re.Match[str]) -> list[str]:
    """Content-word tokens of the org name (designator excluded)."""
    name = match.group("name").strip()
    return [t for t in name.split() if t]


def _on_org_designator(_text: str, match: re.Match[str]) -> FactRecord | None:
    name = match.group("name").strip()
    tokens = _org_name_tokens(match)
    # Reject when every content word is itself a designator word
    # ("Company Ltd", "Limited Corp"): that is not an organization name.
    if not tokens or all(
        _strip_trailing_period(t).casefold() in _DESIGNATOR_CANON for t in tokens
    ):
        return None
    desig_raw = _strip_trailing_period(match.group("desig"))
    desig_canon = " ".join(
        _DESIGNATOR_CANON.get(word, word.casefold()) for word in desig_raw.split()
    )
    raw = match.group()
    return _emit(
        "organization",
        raw,
        match.start(),
        match.end(),
        {
            "kind": "organization",
            "raw_name": raw,
            "normalized_name": _norm_org(f"{name} {desig_raw}"),
            "designator": desig_canon,
            "content_words": tokens,
            "source": "regex:org_designator",
        },
    )


def _on_org_midword(_text: str, match: re.Match[str]) -> FactRecord | None:
    name = match.group("name").strip()
    tokens = _org_name_tokens(match)
    if len(tokens) < 2:
        return None
    raw = match.group()
    return _emit(
        "organization",
        raw,
        match.start(),
        match.end(),
        {
            "kind": "organization",
            "raw_name": raw,
            "normalized_name": _norm_org(raw),
            "designator": None,
            "content_words": tokens,
            "source": "regex:org_midword",
        },
    )


# ---------------------------------------------------------------------------
# Person handler
# ---------------------------------------------------------------------------


def _on_person(_text: str, match: re.Match[str]) -> FactRecord | None:
    name = match.group("name").strip()
    tokens = name.split()
    if not 2 <= len(tokens) <= 4:
        return None
    cleaned: list[str] = []
    for token in tokens:
        bare = _strip_trailing_period(token)
        lowered = bare.casefold()
        if lowered in _PERSON_STOP:
            return None
        if bare in _ORG_MID_WORDS or lowered in {
            w.casefold() for w in _DESIGNATOR_CANON
        }:
            return None
        if not (len(bare) == 1 or bare.istitle()):
            return None
        cleaned.append(bare)
    first, last = cleaned[0], cleaned[-1]
    first_ok = len(first) == 1 or first in _GIVEN_NAMES
    last_ok = len(last) == 1 or last in _SURNAMES
    if not (first_ok and last_ok):
        return None
    raw = match.group()
    honorific_len = len(raw) - len(match.group("name"))
    honorific = raw[:honorific_len].strip() if honorific_len else None
    payload: dict[str, Any] = {
        "kind": "person",
        "raw_name": raw,
        "normalized_name": _norm_person(name),
        "source": "regex:person_lexicon",
    }
    if honorific:
        payload["honorific"] = _strip_trailing_period(honorific)
    return _emit("person", raw, match.start(), match.end(), payload)


# ---------------------------------------------------------------------------
# Short-form (acronym) handling
# ---------------------------------------------------------------------------


def _initials_of(content_words: list[str]) -> str:
    return "".join(word[0] for word in content_words if word)


def _collect_short_uses(
    text: str,
    claims: SpanClaims,
    initials_map: dict[str, tuple[str, str]],
) -> list[FactRecord]:
    """Emit org_short facts for ALL-CAPS tokens that are KNOWN short
    forms: either the initials of an organization in this text, or an
    acronym defined in a parenthetical after one. Never guessed."""
    records: list[FactRecord] = []
    for match in _SHORT_TOKEN.finditer(text):
        token = match.group("ac")
        if token in _SHORT_BLOCKLIST:
            continue
        known = initials_map.get(token)
        if known is None:
            continue
        if claims.overlaps(match.start(), match.end()):
            continue
        full_raw, evidence = known
        records.append(
            _emit(
                "org_short",
                token,
                match.start(),
                match.end(),
                {
                    "kind": "org_short",
                    "raw_name": token,
                    "normalized_name": token.casefold(),
                    "short_for": full_raw,
                    "evidence": evidence,
                    "source": "regex:org_short",
                },
            )
        )
        claims.claim(match.start(), match.end())
    return records


# ---------------------------------------------------------------------------
# Conservative match-candidate evidence (rapidfuzz, never a merge)
# ---------------------------------------------------------------------------


def _attach_match_candidates(records: list[FactRecord]) -> None:
    """Compare each name against earlier names of the same kind; attach a
    conservative match_candidate with the similarity score when above the
    threshold. Facts are never merged or dropped."""
    seen: list[tuple[str, str, str]] = []  # (kind, normalized, raw)
    for record in records:
        kind = record.payload.get("kind")
        if kind not in {"organization", "person"}:
            continue
        norm = record.payload.get("normalized_name")
        if not isinstance(norm, str) or len(norm) < 4:
            continue
        threshold = (
            _SIMILARITY_THRESHOLD_ORG if kind == "organization"
            else _SIMILARITY_THRESHOLD_PERSON
        )
        for prev_kind, prev_norm, prev_raw in seen:
            if prev_kind != kind or prev_norm == norm:
                continue
            score = fuzz.token_set_ratio(norm, prev_norm)
            if score >= threshold:
                record.payload["match_candidate"] = {
                    "raw": prev_raw,
                    "normalized": prev_norm,
                    "similarity": score,
                    "note": _MATCH_NOTE,
                }
                break
        seen.append((kind, norm, record.payload.get("raw_name", record.raw_text)))


# ---------------------------------------------------------------------------
# Engine entry point (fixed order = priority order)
# ---------------------------------------------------------------------------


def extract(text: str, claims: SpanClaims) -> list[FactRecord]:
    records: list[FactRecord] = []

    # 1. Organizations with a legal designator, then mid-word anchored
    #    organizations. Both claim their spans.
    for match in _ORG_WITH_DESIGNATOR.finditer(text):
        if claims.overlaps(match.start(), match.end()):
            continue
        record = _on_org_designator(text, match)
        if record is None:
            continue
        claims.claim(record.norm_start, record.norm_end)
        records.append(record)

        # Parenthetical acronym defined right after the org span.
        tail = text[record.norm_end : record.norm_end + 12]
        paren = re.match(r"\s*\(\s*[\"']?([A-Z]{2,6})[\"']?\s*\)", tail)
        if paren is not None:
            token = paren.group(1)
            if token not in _SHORT_BLOCKLIST:
                existing = records[-1].payload
                existing["short_forms"] = existing.get("short_forms", []) + [token]

    for match in _ORG_MIDWORD.finditer(text):
        if claims.overlaps(match.start(), match.end()):
            continue
        record = _on_org_midword(text, match)
        if record is None:
            continue
        claims.claim(record.norm_start, record.norm_end)
        records.append(record)

    # 2. Short forms: initials of the organizations seen above, plus any
    #    parenthetical-defined acronyms. Emitted as separate facts, never
    #    merged into the full name.
    initials_map: dict[str, tuple[str, str]] = {}
    for record in records:
        if record.payload.get("kind") != "organization":
            continue
        content_words = record.payload.get("content_words") or []
        full_raw = record.payload.get("raw_name", record.raw_text)
        initials = _initials_of(content_words)
        if 2 <= len(initials) <= 6 and initials not in _SHORT_BLOCKLIST:
            initials_map.setdefault(initials, (full_raw, "initials"))
        for short in record.payload.get("short_forms") or []:
            initials_map.setdefault(short, (full_raw, "parenthetical"))
    records.extend(_collect_short_uses(text, claims, initials_map))

    # 3. Persons (lexicon-anchored), after org spans are claimed.
    for match in _PERSON.finditer(text):
        if claims.overlaps(match.start(), match.end()):
            continue
        record = _on_person(text, match)
        if record is None:
            continue
        claims.claim(record.norm_start, record.norm_end)
        records.append(record)

    # 4. Conservative similarity evidence — never a merge.
    _attach_match_candidates(records)
    return records


__all__ = ["ENGINE", "extract"]
