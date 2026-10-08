"""Deterministic Phase 1 tests: no network, no database, no model weights."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.canonical import (
    build_blocks,
    build_sentences,
    compute_sentence_id,
    denormalize_span,
    normalize_text,
    source_set_hash,
    text_hash,
)
from app.core.llm import LLMRequest, cache_key
from app.core.parsers import ParsedDocument, parse_file
from app.core.security import (
    GENESIS_HASH,
    compute_entry_hash,
    generate_keypair,
    generate_verify_token,
    sign_message,
    verify_chain,
    verify_signature,
    verify_token_is_valid,
)

# ---------------------------------------------------------------------------
# Document hash / source set hash
# ---------------------------------------------------------------------------


def test_text_hash_is_sha256_of_normalized_text():
    normalized = "Contract value is INR 42,00,000."
    assert text_hash(normalized) == __import__("hashlib").sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def test_text_hash_changes_when_text_changes():
    assert text_hash("alpha") != text_hash("alpha.")


def test_source_set_hash_is_order_independent():
    a, b, c = "aa" * 32, "bb" * 32, "cc" * 32
    assert source_set_hash([a, b, c]) == source_set_hash([c, a, b])


def test_source_set_hash_changes_when_any_document_changes():
    a, b, c = "aa" * 32, "bb" * 32, "cc" * 32
    assert source_set_hash([a, b, c]) != source_set_hash([a, b, "dd" * 32])


def test_source_set_hash_is_deterministic_sha256():
    hashes = ["11" * 32, "22" * 32]
    again = source_set_hash(hashes)
    assert source_set_hash(hashes) == again
    assert len(again) == 64


# ---------------------------------------------------------------------------
# Canonical text: normalization + offsets
# ---------------------------------------------------------------------------


def test_normalization_nfcs_and_converts_nbsp_and_crlf():
    raw = "Price\u00a0is\r\nINR\u00a0100"
    normalized, segments = normalize_text(raw)
    assert "\u00a0" not in normalized
    assert "\r" not in normalized
    assert "Price is\nINR 100" == normalized
    assert all(
        s["norm_end"] > s["norm_start"] and s["raw_end"] >= s["raw_start"]
        for s in segments
    )


def test_normalization_preserves_meaningful_hyphens():
    normalized, _ = normalize_text("The well-known clause stays intact.")
    assert "well-known" in normalized


def test_normalization_removes_line_wrap_hyphenation():
    normalized, _ = normalize_text("This is an exam-\nple of soft wrap.")
    assert "example" in normalized
    assert "exam-\nple" not in normalized


def test_denormalize_span_round_trips_through_segments():
    raw = "Hello   world\r\nsecond\tline"
    normalized, segments = normalize_text(raw)
    start = normalized.index("world")
    end = start + len("world")
    raw_start, raw_end = denormalize_span(segments, start, end)
    assert raw[raw_start:raw_end] == "world"


def test_offset_segments_cover_normalized_length():
    raw = "A  B\n\nC\tD"
    normalized, segments = normalize_text(raw)
    covered: set[int] = set()
    for seg in segments:
        covered.update(range(seg["norm_start"], seg["norm_end"]))
    assert covered == set(range(len(normalized)))


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


def test_block_types_and_serialization_contract():
    text = "# Heading\n\nA paragraph line.\n\n- bullet item\n\n| colA | colB |"
    blocks = build_blocks(text)
    types = {b.type for b in blocks}
    assert types == {"heading", "paragraph", "bullet", "table_cell"}
    for index, block in enumerate(blocks):
        payload = json.loads(json.dumps(block.to_dict()))
        assert payload["block_index"] == index
        assert set(payload) == {
            "block_id",
            "block_index",
            "start_offset",
            "end_offset",
            "type",
        }
        assert payload["end_offset"] > payload["start_offset"]
        assert text[payload["start_offset"] : payload["end_offset"]].strip()


# ---------------------------------------------------------------------------
# Sentence IDs
# ---------------------------------------------------------------------------

DOC_A = uuid.uuid4()
DOC_B = uuid.uuid4()


def test_sentence_id_is_deterministic():
    first = compute_sentence_id(DOC_A, 0, "Revenue grew 12%.", 0)
    second = compute_sentence_id(DOC_A, 0, "Revenue grew 12%.", 0)
    assert first == second
    assert len(first) == 64


def test_sentence_id_changes_with_every_component():
    base = compute_sentence_id(DOC_A, 0, "Revenue grew 12%.", 0)
    assert compute_sentence_id(DOC_B, 0, "Revenue grew 12%.", 0) != base
    assert compute_sentence_id(DOC_A, 1, "Revenue grew 12%.", 0) != base
    assert compute_sentence_id(DOC_A, 0, "Revenue grew 13%.", 0) != base
    assert compute_sentence_id(DOC_A, 0, "Revenue grew 12%.", 1) != base


def test_build_sentences_assigns_occurrence_index_for_duplicates():
    text = "Same line. Same line."
    blocks = build_blocks(text)
    sentences = build_sentences(DOC_A, blocks, text)
    duplicate = [s for s in sentences if s.text == "Same line."]
    assert len(duplicate) == 2
    assert {s.occurrence_index for s in duplicate} == {0, 1}
    assert duplicate[0].sentence_id != duplicate[1].sentence_id


# ---------------------------------------------------------------------------
# Verify token
# ---------------------------------------------------------------------------


def test_verify_token_is_8_to_12_url_safe_chars():
    for _ in range(50):
        token = generate_verify_token()
        assert 8 <= len(token) <= 12
        assert token.isascii()
        assert all(c.isalnum() or c in "-_" for c in token)
        assert verify_token_is_valid(token)


def test_verify_token_uniqueness_over_many_draws():
    tokens = {generate_verify_token() for _ in range(2000)}
    assert len(tokens) == 2000


def test_verify_token_length_bounds_enforced():
    with pytest.raises(ValueError):
        generate_verify_token(7)
    with pytest.raises(ValueError):
        generate_verify_token(13)


# ---------------------------------------------------------------------------
# Hash chain
# ---------------------------------------------------------------------------


def _entry(**overrides):
    base = {
        "entry_id": uuid.uuid4(),
        "audit_id": uuid.uuid4(),
        "actor_id": uuid.uuid4(),
        "action": "audit.completed",
        "payload_json": '{"k":"v"}',
        "created_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        "previous_hash": GENESIS_HASH,
    }
    base.update(overrides)
    return base


def test_hash_chain_same_entry_same_hash():
    entry = _entry()
    assert compute_entry_hash(**entry) == compute_entry_hash(**entry)


def test_hash_chain_modified_payload_changes_hash():
    entry = _entry()
    modified = _entry(payload_json='{"k":"v2"}', entry_id=entry["entry_id"])
    assert compute_entry_hash(**entry) != compute_entry_hash(**modified)


def test_hash_chain_tampered_payload_fails_verification():
    first = _entry()
    first_hash = compute_entry_hash(**first)
    second = _entry(
        previous_hash=first_hash,
        created_at=datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC),
    )
    second_hash = compute_entry_hash(**second)
    entries = [
        {**first, "hash": first_hash},
        {**second, "hash": second_hash},
    ]
    serialized = [
        {
            "id": str(e["entry_id"]),
            "audit_id": str(e["audit_id"]),
            "actor_id": str(e["actor_id"]),
            "action": e["action"],
            "payload_json": e["payload_json"],
            "created_at": e["created_at"].isoformat(),
            "previous_hash": e["previous_hash"],
            "hash": e["hash"],
        }
        for e in entries
    ]
    ok, _ = verify_chain(serialized)
    assert ok

    serialized[1]["payload_json"] = '{"k":"EVIL"}'
    ok, reason = verify_chain(serialized)
    assert not ok
    assert "TAMPERED" in reason


def test_hash_chain_broken_previous_hash_fails_verification():
    entry_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    created = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    # Entry is internally consistent but does not link to genesis.
    digest = compute_entry_hash(
        entry_id=entry_id,
        audit_id=audit_id,
        actor_id=None,
        action="x",
        payload_json="{}",
        created_at=created,
        previous_hash="f" * 64,
    )
    broken = [
        {
            "id": str(entry_id),
            "audit_id": str(audit_id),
            "actor_id": None,
            "action": "x",
            "payload_json": "{}",
            "created_at": created.isoformat(),
            "previous_hash": "f" * 64,  # not genesis
            "hash": digest,
        }
    ]
    ok, reason = verify_chain(broken)
    assert not ok
    assert "previous_hash" in reason


# ---------------------------------------------------------------------------
# ECDSA P-256
# ---------------------------------------------------------------------------


def test_ecdsa_sign_verify_and_tamper_detection():
    private_pem, public_pem = generate_keypair()
    message = b"source_set_hash:chain_head"
    signature = sign_message(private_pem, message)
    assert verify_signature(public_pem, message, signature)
    assert not verify_signature(public_pem, b"modified message", signature)


def test_ecdsa_rejects_non_p256_keys():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core.security import load_public_key

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_public = rsa_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with pytest.raises(ValueError, match="ECDSA|P-256"):
        load_public_key(rsa_public)
    assert verify_signature(rsa_public, b"msg", "00") is False


def test_ecdsa_no_secp256k1_in_codebase():
    root = Path(__file__).resolve().parents[1] / "app"
    for py in root.rglob("*.py"):
        content = py.read_text(encoding="utf-8")
        assert "SECP256K1" not in content, py
        assert "secp256k1" not in content, py


# ---------------------------------------------------------------------------
# LLM adapter cache key (no network)
# ---------------------------------------------------------------------------


def test_llm_cache_key_contract():
    request = LLMRequest(prompt="p", schema={"type": "object"})
    key1 = cache_key("openai", "gpt-5-mini", request)
    key2 = cache_key("openai", "gpt-5-mini", request)
    assert key1 == key2
    assert len(key1) == 64
    assert cache_key("gemini", "gemini-2.5-flash", request) != key1
    assert cache_key("openai", "other-model", request) != key1

    other = LLMRequest(prompt="p", schema={"type": "object"}, prompt_version="v2")
    assert cache_key("openai", "gpt-5-mini", other) != key1
    warmer = LLMRequest(prompt="p", schema={"type": "object"}, temperature=0.5)
    assert cache_key("openai", "gpt-5-mini", warmer) != key1


# ---------------------------------------------------------------------------
# Parser common representation
# ---------------------------------------------------------------------------


def test_txt_parser_returns_common_representation(tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_bytes(b"# Title\n\nBody text.")
    parsed = parse_file(path)
    assert isinstance(parsed, ParsedDocument)
    assert parsed.format == "text"
    assert parsed.raw_text == "# Title\n\nBody text."
    assert parsed.locations
    assert parsed.location_at(0)["type"] == "text"
    payload = json.loads(json.dumps(parsed.locations_json()))
    assert payload[0]["location"] == {
        "type": "text",
        "char_start": 0,
        "char_end": len(parsed.raw_text),
    }


def test_parser_rejects_missing_file(tmp_path: Path):
    from app.core.parsers import ParserError

    with pytest.raises(ParserError):
        parse_file(tmp_path / "missing.txt")
