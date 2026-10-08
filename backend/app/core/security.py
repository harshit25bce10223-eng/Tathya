"""Security primitives for Tathya.

Base-template JWT / password helpers (kept from FastAPI Full-Stack Template)
+ Tathya locked crypto:

    ECDSA P-256 / prime256v1  +  SHA-256 hash chain  +  QR verify token

No Secp256k1. No Merkle tree. No blockchain.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# ---------------------------------------------------------------------------
# Base-template password + JWT helpers
# ---------------------------------------------------------------------------

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

# ---------------------------------------------------------------------------
# Hash chain
# ---------------------------------------------------------------------------

GENESIS_HASH = "0" * 64


def canonical_json(obj: dict) -> str:
    """Canonical JSON used for hashing.

    sort_keys=True, separators=(",", ":"), ensure_ascii=False
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_entry_hash(
    *,
    entry_id: uuid.UUID | str,
    audit_id: uuid.UUID | str,
    actor_id: uuid.UUID | str | None,
    action: str,
    payload_json: str,
    created_at: datetime,
    previous_hash: str,
) -> str:
    """hash = SHA256(entry_canonical).hexdigest()

    entry_canonical is built exactly per the locked contract with
    UTC ISO-8601 timestamps.
    """
    created_iso = created_at.strftime("%Y-%m-%dT%H:%M:%S.%f") + "+00:00"
    entry = {
        "id": str(entry_id),
        "audit_id": str(audit_id),
        "actor_id": str(actor_id) if actor_id else None,
        "action": action,
        "payload_json": payload_json,
        "created_at": created_iso,
        "previous_hash": previous_hash,
    }
    canonical = canonical_json(entry)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_chain(entries: list[dict]) -> tuple[bool, str]:
    """Verify a full chain of audit_log entries.

    Each entry dict must contain:
        id, audit_id, actor_id, action, payload_json, created_at, previous_hash, hash

    Returns (ok, reason).
    Recomputes every entry hash and verifies previous_hash links.
    Does NOT merely trust stored hashes.
    """
    prev = GENESIS_HASH
    for i, e in enumerate(entries):
        created = e["created_at"]
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                return False, f"entry {i}: invalid created_at"
        recomputed = compute_entry_hash(
            entry_id=e["id"],
            audit_id=e["audit_id"],
            actor_id=e.get("actor_id"),
            action=e["action"],
            payload_json=e["payload_json"],
            created_at=created,
            previous_hash=e["previous_hash"],
        )
        if recomputed != e["hash"]:
            return False, f"TAMPERED at entry {i}: hash mismatch"
        if e["previous_hash"] != prev:
            return False, f"TAMPERED at entry {i}: previous_hash link broken"
        prev = e["hash"]
    return True, "VERIFIED"


# ---------------------------------------------------------------------------
# ECDSA P-256 (prime256v1)
# ---------------------------------------------------------------------------


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate a new ECDSA P-256 keypair.

    Returns (private_pem, public_pem).
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def load_private_key(pem: bytes) -> ec.EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("Not an ECDSA private key")
    if not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("Not a P-256 / prime256v1 key")
    return key


def load_public_key(pem: bytes) -> ec.EllipticCurvePublicKey:
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("Not an ECDSA public key")
    if not isinstance(key.curve, ec.SECP256R1):
        raise ValueError("Not a P-256 / prime256v1 key")
    return key


def sign_message(private_key_pem: bytes, message: bytes) -> str:
    """Sign message with ECDSA P-256 + SHA-256.

    Returns DER-encoded signature as hex string.
    """
    key = load_private_key(private_key_pem)
    der_sig = key.sign(message, ec.ECDSA(hashes.SHA256()))
    return der_sig.hex()


def verify_signature(
    public_key_pem: bytes, message: bytes, signature_hex: str
) -> bool:
    """Verify ECDSA P-256 + SHA-256 signature. Returns True/False."""
    try:
        key = load_public_key(public_key_pem)
        der_sig = bytes.fromhex(signature_hex)
        key.verify(der_sig, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def _int_to_hex32(value: int) -> str:
    return format(value, "064x")


def der_to_r_s(signature_hex: str) -> tuple[str, str]:
    """Convert DER signature to fixed-width (r, s) hex pair."""
    r, s = decode_dss_signature(bytes.fromhex(signature_hex))
    return _int_to_hex32(r), _int_to_hex32(s)


def r_s_to_der(r_hex: str, s_hex: str) -> str:
    """Convert fixed-width (r, s) hex pair back to DER hex."""
    der = encode_dss_signature(int(r_hex, 16), int(s_hex, 16))
    return der.hex()


# ---------------------------------------------------------------------------
# Verify token (public QR URL)
# ---------------------------------------------------------------------------

_TOKEN_ALPHABET = string.ascii_letters + string.digits + "-_"
TOKEN_LENGTH = 12  # 8-12 character, URL-safe, unique


def generate_verify_token(length: int = TOKEN_LENGTH) -> str:
    """Generate a URL-safe random verify token.

    8-12 characters, unique, URL-safe.
    NEVER use the audit ID in the public QR URL.
    """
    if not (8 <= length <= 12):
        raise ValueError("verify token length must be 8-12 characters")
    return "".join(secrets.choice(_TOKEN_ALPHABET) for _ in range(length))


def verify_token_is_valid(token: str) -> bool:
    """Check a verify token matches the expected format."""
    if not (8 <= len(token) <= 12):
        return False
    return all(c in _TOKEN_ALPHABET for c in token)


# ---------------------------------------------------------------------------
# SHA-256 file / content helpers
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
