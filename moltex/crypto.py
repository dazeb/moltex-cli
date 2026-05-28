"""Ed25519 cryptographic operations for MOLTEX RPC signing."""

import json
from pathlib import Path

import nacl.signing

KEY_FILE = Path.home() / ".moltex" / "agent_key.json"


def sort_keys(obj):
    """Recursively sort JSON object keys alphabetically for deterministic signing.
    MUST match server's sortKeys() exactly."""
    if obj is None or not isinstance(obj, (dict, list)):
        return obj
    if isinstance(obj, list):
        return [sort_keys(item) for item in obj]
    return {k: sort_keys(v) for k, v in sorted(obj.items())}


def generate_keypair():
    """Generate a new Ed25519 keypair. Returns (public_key_hex, secret_key_hex)."""
    sk = nacl.signing.SigningKey.generate()
    vk = sk.verify_key
    return (
        vk.encode(encoder=nacl.encoding.HexEncoder).decode(),
        sk.encode(encoder=nacl.encoding.HexEncoder).decode(),
    )


def load_or_create_keypair(key_file: Path | None = None):
    """Load existing keypair from disk, or create and save a new one."""
    kf = key_file or KEY_FILE
    kf.parent.mkdir(parents=True, exist_ok=True)
    if kf.exists():
        data = json.loads(kf.read_text())
        return data["public_key"], data["secret_key"]
    pk, sk = generate_keypair()
    kf.write_text(json.dumps({"public_key": pk, "secret_key": sk}, indent=2))
    return pk, sk


def sign_payload(payload: dict, secret_key_hex: str) -> str:
    """Sign a payload dict with Ed25519, returning hex signature.
    Uses alphabetically sorted keys for deterministic signing."""
    sorted_payload = sort_keys(payload)
    message = json.dumps(sorted_payload, separators=(",", ":")).encode()
    sk = nacl.signing.SigningKey(secret_key_hex, encoder=nacl.encoding.HexEncoder)
    signed = sk.sign(message)
    return signed.signature.hex()
