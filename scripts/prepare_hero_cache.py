import json
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization

cache_dir = Path("data/cache")
cache_dir.mkdir(parents=True, exist_ok=True)

hero_dir = Path("storage/hero_pack")
hero_manifest = json.loads((hero_dir / "hero_manifest.json").read_text(encoding="utf-8"))

# Sign the cached result with ECDSA private key
private_key_path = Path("secrets/passport_private.pem")
private_key = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)

cached_response = {
    "mode": "CACHED_FALLBACK",
    "document_id": "hero_contract_ai_draft",
    "status": "FLAGGED",
    "trust_score": 42.5,
    "total_claims": 7,
    "verified_claims": 0,
    "flagged_claims": 7,
    "issues": hero_manifest["planted_issues"],
    "summary": "Tathya Fact Verification Engine detected 7 major discrepancies between the AI draft contract and approved source documents."
}

payload_bytes = json.dumps(cached_response, sort_keys=True).encode("utf-8")
signature = private_key.sign(payload_bytes, ec.ECDSA(hashes.SHA256()))

cached_result = {
    "payload": cached_response,
    "signature_hex": signature.hex(),
    "hash_sha256": hashlib.sha256(payload_bytes).hexdigest()
}

out_file = cache_dir / "hero_cached_result.json"
out_file.write_text(json.dumps(cached_result, indent=2), encoding="utf-8")
print(f"[PASS] Pre-cached hero response generated at {out_file} (offline fallback ready)")
