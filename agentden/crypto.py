"""AgentDen crypto layer: AES-256-GCM file encryption.

The key is the whole secret. Everything else (maze, audit, prenup)
only raises the cost of crossing the line -- it does not replace the key.
"""
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

KEY_BYTES = 32
NONCE_BYTES = 12
TAG_BYTES = 16


def generate_key() -> bytes:
    """Generate a fresh 256-bit den key."""
    return AESGCM.generate_key(bit_length=256)


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt; returns nonce || ciphertext. Output is indistinguishable
    from random bytes without the key (this is what makes decoys work)."""
    if len(key) != KEY_BYTES:
        raise ValueError("key must be 32 bytes")
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """Decrypt nonce || ciphertext. Raises on wrong key / tampered data."""
    if len(key) != KEY_BYTES:
        raise ValueError("key must be 32 bytes")
    nonce, ct = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
    return AESGCM(key).decrypt(nonce, ct, None)


def derive_slot(key: bytes, alphabet: str) -> str:
    """Derive the maze slot from the key: O(1) locate, no position file.

    The agent never stores "where the real file is" anywhere else --
    the key itself is the map. A new key means a new slot (rotation
    moves the room for free).
    """
    n = len(alphabet)
    raw = HKDF(
        algorithm=hashes.SHA256(),
        length=2,
        salt=None,
        info=b"agentden-slot-v1",
    ).derive(key)
    return alphabet[raw[0] % n] + alphabet[raw[1] % n]
