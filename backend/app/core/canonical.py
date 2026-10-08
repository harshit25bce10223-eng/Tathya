"""Canonical document text foundation.

Pipeline:
    raw extracted text
        -> safe normalization
        -> normalized text
        -> blocks
        -> sentences

Contracts (locked):
    text_hash = SHA256(normalized_text)
    document_version_id = documents.id
    sentence_id = SHA256(document_version_id + block_index + text + occurrence)
    offset_map  = compact segments, direction normalized -> raw
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_LINE_WRAP_HYPHEN = re.compile(r"(?<=[a-zA-Z])-\s*\n\s*(?=[a-z])")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def normalize_text(raw: str) -> tuple[str, list[dict]]:
    """Normalize raw text and return (normalized_text, offset_segments).

    Normalization rules (locked):
      - Unicode NFKC
      - NBSP -> regular space
      - CRLF / CR -> LF
      - safe whitespace collapse (runs of spaces/tabs -> single space)
      - line-wrap dehyphenation only (soft hyphens at line breaks)
      - NO global removal of meaningful hyphens
      - NO semantic content changes

    offset_segments map normalized ranges -> raw ranges:
      [{"norm_start", "norm_end", "raw_start", "raw_end"}, ...]
    """

    # Pass 1: character-level normalization, tracking raw positions.
    norm_chars: list[str] = []
    # Each entry: (norm_index_start_in_current_build, raw_index)
    raw_positions: list[int] = []

    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]

        # CRLF -> LF
        if ch == "\r":
            if i + 1 < n and raw[i + 1] == "\n":
                # consume both, emit one \n
                norm_chars.append("\n")
                raw_positions.append(i)
                i += 2
                continue
            else:
                # lone CR -> LF
                norm_chars.append("\n")
                raw_positions.append(i)
                i += 1
                continue

        # NBSP -> space
        if ch == "\u00a0":
            norm_chars.append(" ")
            raw_positions.append(i)
            i += 1
            continue

        # NFKC per character (safe: does not change length unpredictably for our use)
        if ch != "\n" and ch != " " and ch != "\t":
            normalized_ch = unicodedata.normalize("NFKC", ch)
            for nc in normalized_ch:
                norm_chars.append(nc)
                raw_positions.append(i)
            i += 1
            continue

        norm_chars.append(ch)
        raw_positions.append(i)
        i += 1

    # Pass 2: whitespace collapse on the normalized string.
    # We rebuild while tracking positions.
    norm = "".join(norm_chars)

    # Dehyphenation: "exam-\nple" -> "example" (line-wrap soft hyphens only)
    # We do this BEFORE whitespace collapse so the newline is consumed.
    dehyphenated_chars: list[str] = []
    dehyphenated_raw: list[int] = []
    j = 0
    while j < len(norm):
        if (
            j + 2 < len(norm)
            and norm[j] == "-"
            and norm[j + 1] == "\n"
            and norm[j + 2].islower()
            and j > 0
            and norm[j - 1].isalpha()
        ):
            # skip the hyphen and newline; keep the lowercase char next iteration
            j += 2
            continue
        dehyphenated_chars.append(norm[j])
        dehyphenated_raw.append(raw_positions[j])
        j += 1

    norm = "".join(dehyphenated_chars)
    raw_positions = dehyphenated_raw

    # Whitespace collapse: collapse runs of spaces/tabs into single space,
    # collapse 3+ newlines into exactly 2.
    # Each emitted char carries (raw_start, raw_end) so segments can be
    # derived without assuming raw position == normalized position.
    final_chars: list[str] = []
    final_raw_start: list[int] = []
    final_raw_end: list[int] = []
    k = 0
    while k < len(norm):
        ch = norm[k]
        if ch in (" ", "\t"):
            # consume run of spaces/tabs
            start_raw = raw_positions[k]
            while k < len(norm) and norm[k] in (" ", "\t"):
                k += 1
            end_raw = raw_positions[k - 1] + 1
            final_chars.append(" ")
            final_raw_start.append(start_raw)
            final_raw_end.append(end_raw)
            continue
        if ch == "\n":
            # consume run of newlines
            start_raw = raw_positions[k]
            nl_count = 0
            while k < len(norm) and norm[k] == "\n":
                nl_count += 1
                k += 1
            end_raw = raw_positions[k - 1] + 1
            emit = "\n\n" if nl_count >= 2 else "\n"
            for _ in range(len(emit)):
                final_chars.append("\n")
                final_raw_start.append(start_raw)
                final_raw_end.append(end_raw)
            continue

        final_chars.append(ch)
        final_raw_start.append(raw_positions[k])
        final_raw_end.append(raw_positions[k] + 1)
        k += 1

    normalized = "".join(final_chars)

    # Trim leading/trailing whitespace (and its raw mapping)
    text_start = len(normalized) - len(normalized.lstrip())
    if text_start:
        normalized = normalized[text_start:]
        final_raw_start = final_raw_start[text_start:]
        final_raw_end = final_raw_end[text_start:]
    text_end = len(normalized.rstrip())
    if text_end < len(normalized):
        normalized = normalized[:text_end]
        final_raw_start = final_raw_start[:text_end]
        final_raw_end = final_raw_end[:text_end]

    segments = _segments_from_raw(final_raw_start, final_raw_end)

    return normalized, segments


def _segments_from_raw(
    raw_starts: list[int], raw_ends: list[int]
) -> list[dict]:
    """Group normalized chars into compact [norm -> raw] segments.

    Chars join one segment only while the mapping stays 1:1 and the raw
    positions are contiguous. Collapsed / expanded chars (newline runs,
    NFKC expansions, absorbed whitespace) get their own segment so
    denormalize_span stays exact for ordinary text.
    """
    segments: list[dict] = []
    i = 0
    n = len(raw_starts)
    while i < n:
        if raw_ends[i] - raw_starts[i] != 1:
            segments.append(
                {
                    "norm_start": i,
                    "norm_end": i + 1,
                    "raw_start": raw_starts[i],
                    "raw_end": raw_ends[i],
                }
            )
            i += 1
            continue
        j = i + 1
        while (
            j < n
            and raw_starts[j] == raw_ends[j - 1]
            and raw_ends[j] - raw_starts[j] == 1
            and (raw_ends[j] - raw_starts[i]) == (j - i + 1)
        ):
            j += 1
        segments.append(
            {
                "norm_start": i,
                "norm_end": j,
                "raw_start": raw_starts[i],
                "raw_end": raw_ends[j - 1],
            }
        )
        i = j
    return segments


def _map_boundary(seg: dict, offset: int) -> int:
    """Map a normalized offset inside a segment to a raw offset."""
    span_n = seg["norm_end"] - seg["norm_start"]
    span_r = seg["raw_end"] - seg["raw_start"]
    if span_n == span_r:
        return seg["raw_start"] + offset
    if offset <= 0:
        return seg["raw_start"]
    if offset >= span_n:
        return seg["raw_end"]
    return seg["raw_start"] + min(offset, span_r)


def denormalize_span(
    segments: list[dict], norm_start: int, norm_end: int
) -> tuple[int, int]:
    """Map a normalized [start, end) range back to raw [start, end).

    Reverse mapping is derived from the same segments (direction: norm -> raw).
    """
    raw_start: int | None = None
    raw_end: int | None = None
    for seg in segments:
        if seg["norm_start"] <= norm_start < seg["norm_end"]:
            raw_start = _map_boundary(seg, norm_start - seg["norm_start"])
        if seg["norm_start"] < norm_end <= seg["norm_end"]:
            raw_end = _map_boundary(seg, norm_end - seg["norm_start"])
        if raw_start is not None and raw_end is not None:
            break
    if raw_start is None:
        raw_start = norm_start
    if raw_end is None:
        raw_end = norm_end
    return raw_start, raw_end


def _raw_to_norm_boundary(
    segments: list[dict], raw_pos: int, left: bool
) -> int:
    """Map one raw offset to a normalized offset (inverse direction).

    Boundary semantics (deterministic):
      - exact segment edges map to exact segment edges
      - 1:1 segments map linearly
      - collapsed segments (whitespace runs, newline collapses) map any
        interior raw position to the start edge (left boundary) or the
        end edge (right boundary) of the segment's normalized range
      - raw positions inside removed text (trimmed whitespace, absorbed
        hyphen+newline) snap to the neighbouring segment edge
    """
    previous_norm_end = 0
    for seg in segments:
        raw_start, raw_end = seg["raw_start"], seg["raw_end"]
        if raw_pos <= raw_start:
            if raw_pos == raw_start:
                return seg["norm_start"]
            return seg["norm_start"] if left else previous_norm_end
        if raw_pos < raw_end:
            span_n = seg["norm_end"] - seg["norm_start"]
            span_r = raw_end - raw_start
            if span_n == span_r:
                return seg["norm_start"] + (raw_pos - raw_start)
            return seg["norm_start"] if left else seg["norm_end"]
        if raw_pos == raw_end:
            return seg["norm_end"]
        previous_norm_end = seg["norm_end"]
    return previous_norm_end


def normalize_span(
    segments: list[dict], raw_start: int, raw_end: int
) -> tuple[int, int]:
    """Map a raw [start, end) range to normalized [start, end).

    Inverse of denormalize_span: direction raw -> norm.
    """
    if not segments:
        return raw_start, raw_end
    raw_start = max(0, raw_start)
    raw_end = max(raw_start, raw_end)
    norm_start = _raw_to_norm_boundary(segments, raw_start, left=True)
    norm_end = _raw_to_norm_boundary(segments, raw_end, left=False)
    return norm_start, max(norm_start, norm_end)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

BLOCK_TYPES = ("paragraph", "heading", "bullet", "table_cell")


@dataclass
class Block:
    block_id: str
    block_index: int
    start_offset: int
    end_offset: int
    type: str  # paragraph | heading | bullet | table_cell

    def to_dict(self) -> dict:
        return asdict(self)


def build_blocks(normalized_text: str) -> list[Block]:
    """Split normalized text into logical blocks.

    Rules:
      - Lines starting with '#', '##', ...  -> heading
      - Lines starting with '-', '*', '•'   -> bullet
      - Lines containing '|' with 2+ pipes  -> table_cell
      - Blank-line separated runs of text   -> paragraph
    """
    blocks: list[Block] = []
    lines = normalized_text.split("\n")

    offset = 0
    block_index = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        line_start = offset
        line_len = len(line)
        line_end = line_start + line_len

        stripped = line.strip()

        if not stripped:
            offset = line_end + 1  # +1 for the \n
            i += 1
            continue

        btype = "paragraph"

        if stripped.startswith("#"):
            btype = "heading"
            block_text = stripped
            blocks.append(
                Block(
                    block_id=f"blk-{block_index:04d}",
                    block_index=block_index,
                    start_offset=line_start + (len(line) - len(line.lstrip())),
                    end_offset=line_end - (len(line) - len(line.rstrip())),
                    type=btype,
                )
            )
            block_index += 1
            offset = line_end + 1
            i += 1
            continue

        if stripped[0] in ("-", "*", "•"):
            btype = "bullet"
            blocks.append(
                Block(
                    block_id=f"blk-{block_index:04d}",
                    block_index=block_index,
                    start_offset=line_start + (len(line) - len(line.lstrip())),
                    end_offset=line_end - (len(line) - len(line.rstrip())),
                    type=btype,
                )
            )
            block_index += 1
            offset = line_end + 1
            i += 1
            continue

        if stripped.count("|") >= 2:
            btype = "table_cell"
            blocks.append(
                Block(
                    block_id=f"blk-{block_index:04d}",
                    block_index=block_index,
                    start_offset=line_start + (len(line) - len(line.lstrip())),
                    end_offset=line_end - (len(line) - len(line.rstrip())),
                    type=btype,
                )
            )
            block_index += 1
            offset = line_end + 1
            i += 1
            continue

        # paragraph: accumulate until blank line
        para_start = line_start + (len(line) - len(line.lstrip()))
        para_end = line_end
        j = i + 1
        cur_offset = line_end + 1
        while j < len(lines) and lines[j].strip():
            para_end = cur_offset + len(lines[j].rstrip())
            cur_offset = cur_offset + len(lines[j]) + 1
            j += 1

        blocks.append(
            Block(
                block_id=f"blk-{block_index:04d}",
                block_index=block_index,
                start_offset=para_start,
                end_offset=para_end,
                type="paragraph",
            )
        )
        block_index += 1

        # Advance offset to just past the last line of this paragraph
        for m in range(i, j):
            offset += len(lines[m]) + 1
        i = j

    return blocks


# ---------------------------------------------------------------------------
# Sentences
# ---------------------------------------------------------------------------
#
# Deterministic, language-aware segmentation (English + Hindi/Hinglish):
#   - sentence enders: . ! ? and Devanagari danda (।) / double danda (॥)
#   - no split after known abbreviations ("Pvt. Ltd.", "e.g.", "Rs.", "No. 5")
#   - no split after initials ("J. R. D.") or list numbering ("1. Item")
#   - next sentence must start with an uppercase Latin / Devanagari letter
#     or an opening quote/bracket
#   - no giant NLP subsystem: a fixed scanner, fully replaceable

_SENTENCE_ENDER_WS = re.compile(r"[.!?।॥]\s+")
_SENTENCE_START = re.compile(r"[A-ZÀ-ÖØ-Þ\u0900-\u097F\"'“‘»«(\[{]")
_WORD_BEFORE = re.compile(r"([A-Za-z\u0900-\u097F][\w.\u0900-\u097F]{0,24})$")
_INITIALS = re.compile(r"(?:[A-Z]\.)+[A-Z]?$")

# compact (dot-free) forms are compared, so "e.g" and "eg" both match
_SENTENCE_ABBREVIATIONS = frozenset(
    {
        "no", "nos", "rs", "inr", "usd", "eur", "gbp", "pvt", "ltd", "inc",
        "co", "corp", "mr", "mrs", "ms", "dr", "prof", "st", "sr", "jr",
        "vs", "etc", "eg", "ie", "viz", "approx", "min", "max", "govt",
        "dept", "sec", "cl", "fig", "art", "para", "sub", "m/s", "bros",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sept", "sep",
        "oct", "nov", "dec", "vol", "pp", "ed", "al", "est", "ca", "cs",
    }
)


def _split_sentence_spans(text: str) -> list[tuple[int, int]]:
    """Split one block of normalized text into (start, end) sentence spans.

    Spans tile the input (separators stay attached to the preceding span)
    so sentence offsets never drift, even across newline separators.
    """
    cuts: list[int] = [0]
    for match in _SENTENCE_ENDER_WS.finditer(text):
        ender = match.group()[0]
        if ender == ".":
            token_match = _WORD_BEFORE.search(text, 0, match.start())
            if token_match is not None:
                token = token_match.group(1)
                compact = token.lower().replace(".", "")
                if (
                    token.isdigit()
                    or compact in _SENTENCE_ABBREVIATIONS
                    or _INITIALS.match(token) is not None
                ):
                    continue  # abbreviation / numbering: not a sentence end
        next_char = text[match.end()] if match.end() < len(text) else ""
        if next_char and _SENTENCE_START.match(next_char) is None:
            continue
        cuts.append(match.end())
    cuts.append(len(text))
    return [
        (cuts[i], cuts[i + 1])
        for i in range(len(cuts) - 1)
        if cuts[i] < cuts[i + 1]
    ]


@dataclass
class Sentence:
    sentence_id: str
    block_index: int
    text: str
    occurrence_index: int
    start_offset: int
    end_offset: int


def compute_sentence_id(
    document_version_id: uuid.UUID | str,
    block_index: int,
    sentence_text: str,
    occurrence_index: int,
) -> str:
    """Locked sentence ID contract:

    SHA256(document_version_id + block_index + normalized_sentence_text + occurrence)
    """
    payload = (
        f"{document_version_id}{block_index}{sentence_text}{occurrence_index}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_sentences(
    document_version_id: uuid.UUID | str,
    blocks: list[Block],
    normalized_text: str,
) -> list[Sentence]:
    """Split blocks into sentences and assign version-specific sentence IDs.

    Duplicate sentences are handled by:
      exact normalized match -> nearest position -> occurrence index
    """
    sentences: list[Sentence] = []
    seen_occurrence: dict[tuple[int, str], int] = {}

    for block in blocks:
        block_text = normalized_text[block.start_offset : block.end_offset]
        for span_start, span_end in _split_sentence_spans(block_text):
            part = block_text[span_start:span_end]
            sent_text = part.strip()
            if not sent_text:
                continue

            lead = len(part) - len(part.lstrip())
            trail = len(part) - len(part.rstrip())
            sent_start = block.start_offset + span_start + lead
            sent_end = block.start_offset + span_end - trail

            key = (block.block_index, sent_text)
            occurrence = seen_occurrence.get(key, 0)
            seen_occurrence[key] = occurrence + 1

            sid = compute_sentence_id(
                document_version_id, block.block_index, sent_text, occurrence
            )
            sentences.append(
                Sentence(
                    sentence_id=sid,
                    block_index=block.block_index,
                    text=sent_text,
                    occurrence_index=occurrence,
                    start_offset=sent_start,
                    end_offset=sent_end,
                )
            )

    return sentences


# ---------------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------------


def text_hash(normalized_text: str) -> str:
    """text_hash = SHA256(normalized_text)"""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def source_set_hash(text_hashes: list[str]) -> str:
    """source_set_hash = SHA256(sorted([text_hash of all source documents])).

    Sorting must be deterministic. If any source document changes,
    source_set_hash changes. Used for cache / re-audit invalidation.
    """
    sorted_hashes = sorted(text_hashes)
    payload = json.dumps(sorted_hashes, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Location contracts (structured, per format)
# ---------------------------------------------------------------------------


def location_pdf(page: int, bbox: list[float]) -> dict:
    return {"type": "pdf", "page": page, "bbox": bbox}


def location_docx(paragraph: int, char_start: int, char_end: int) -> dict:
    return {
        "type": "docx",
        "paragraph": paragraph,
        "char_start": char_start,
        "char_end": char_end,
    }


def location_xlsx(sheet: str, cell: str) -> dict:
    return {"type": "xlsx", "sheet": sheet, "cell": cell}


def location_text(char_start: int, char_end: int) -> dict:
    return {"type": "text", "char_start": char_start, "char_end": char_end}
