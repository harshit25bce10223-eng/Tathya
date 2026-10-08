import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

secrets_dir = Path("secrets")
secrets_dir.mkdir(parents=True, exist_ok=True)

backend_secrets_dir = Path("backend/secrets")
backend_secrets_dir.mkdir(parents=True, exist_ok=True)

private_key_path = secrets_dir / "passport_private.pem"
public_key_path = secrets_dir / "passport_public.pem"

# Generate ECDSA P-256 keypair if not present
if not private_key_path.exists():
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_path.write_bytes(private_pem)
    # Also write to backend/secrets for backend usage
    (backend_secrets_dir / "passport_private.pem").write_bytes(private_pem)
    print(f"Generated private key at {private_key_path}")
else:
    private_pem = private_key_path.read_bytes()
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    print(f"Loaded existing private key from {private_key_path}")

public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
public_key_path.write_bytes(public_pem)
(backend_secrets_dir / "passport_public.pem").write_bytes(public_pem)
print(f"Saved public key at {public_key_path}")

# Test Signing
test_message = b"Tathya Trust Passport: Claim Verification Token #41600"
signature = private_key.sign(test_message, ec.ECDSA(hashes.SHA256()))
print(f"Signature generated ({len(signature)} bytes)")

# Test Verification
try:
    public_key.verify(signature, test_message, ec.ECDSA(hashes.SHA256()))
    print("VERIFICATION: PASS (valid signature verified)")
except InvalidSignature:
    print("VERIFICATION: FAIL")

# Test Tamper Detection
tampered_message = b"Tathya Trust Passport: Claim Verification Token #41601 - TAMPERED"
try:
    public_key.verify(signature, tampered_message, ec.ECDSA(hashes.SHA256()))
    print("TAMPER TEST: FAIL (tampered message was wrongly accepted)")
except InvalidSignature:
    print("TAMPER TEST: PASS (tampered message was correctly rejected)")
