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
    segments: list[dict] = []

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
    final_chars: list[str] = []
    final_raw: list[int] = []
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
            final_raw.append(start_raw)
            segments.append(
                {
                    "norm_start": len(final_chars) - 1,
                    "norm_end": len(final_chars),
                    "raw_start": start_raw,
                    "raw_end": end_raw,
                }
            )
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
                final_raw.append(start_raw)
            segments.append(
                {
                    "norm_start": len(final_chars) - len(emit),
                    "norm_end": len(final_chars),
                    "raw_start": start_raw,
                    "raw_end": end_raw,
                }
            )
            continue

        final_chars.append(ch)
        final_raw.append(raw_positions[k])
        k += 1

    normalized = "".join(final_chars)

    # Trim leading/trailing whitespace
    normalized = normalized.strip()

    # Build compact merge segments: group consecutive identical raw ranges.
    # We already emitted segments for whitespace runs; add identity segments
    # for the non-whitespace runs between them.
    segments = _merge_segments(segments, len(final_chars), len(raw))

    return normalized, segments


def _merge_segments(
    whitespace_segments: list[dict], norm_len: int, raw_len: int
) -> list[dict]:
    """Ensure every normalized range has a mapping by adding identity spans
    for ranges not covered by whitespace segments, then sort + merge."""
    covered: set[int] = set()
    for s in whitespace_segments:
        for idx in range(s["norm_start"], s["norm_end"]):
            covered.add(idx)

    identity: list[dict] = []
    run_start = None
    for idx in range(norm_len):
        if idx not in covered:
            if run_start is None:
                run_start = idx
        else:
            if run_start is not None:
                identity.append(
                    {
                        "norm_start": run_start,
                        "norm_end": idx,
                        "raw_start": run_start,
                        "raw_end": min(idx, raw_len),
                    }
                )
                run_start = None
    if run_start is not None:
        identity.append(
            {
                "norm_start": run_start,
                "norm_end": norm_len,
                "raw_start": run_start,
                "raw_end": min(norm_len, raw_len),
            }
        )

    all_segments = sorted(whitespace_segments + identity, key=lambda s: s["norm_start"])

    # Merge adjacent segments where raw mapping is contiguous
    merged: list[dict] = []
    for seg in all_segments:
        if (
            merged
            and merged[-1]["norm_end"] == seg["norm_start"]
            and merged[-1]["raw_end"] == seg["raw_start"]
        ):
            merged[-1]["norm_end"] = seg["norm_end"]
            merged[-1]["raw_end"] = seg["raw_end"]
        else:
            merged.append(dict(seg))
    return merged


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
            offset = norm_start - seg["norm_start"]
            raw_start = seg["raw_start"] + offset
        if seg["norm_start"] < norm_end <= seg["norm_end"]:
            offset = norm_end - seg["norm_start"]
            raw_end = seg["raw_start"] + offset
        if raw_start is not None and raw_end is not None:
            break
    if raw_start is None:
        raw_start = norm_start
    if raw_end is None:
        raw_end = norm_end
    return raw_start, raw_end


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

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])")


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
        parts = _SENTENCE_SPLIT.split(block_text)
        if not parts:
            parts = [block_text] if block_text.strip() else []

        local_offset = block.start_offset
        for part in parts:
            if not part.strip():
                local_offset += len(part)
                continue

            # Compute offsets within the block
            lead = len(part) - len(part.lstrip())
            trail = len(part) - len(part.rstrip())
            sent_start = local_offset + lead
            sent_end = local_offset + len(part) - trail
            sent_text = part.strip()

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
            local_offset += len(part)

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
