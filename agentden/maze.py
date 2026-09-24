"""AgentDen maze: 36 x 36 = 1296 files, 1 real + 1295 decoys.

Every file has the same size and the same format (nonce || payload),
so without the key no file can be told apart from any other.
The maze is a boundary marker, not a wall: it turns "happened to see"
into a deliberate, auditable act of crossing. It provides no
cryptographic strength -- the key does that.
"""
import json
import os
import time

from . import crypto

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"  # 36 chars
SECRET_CAPACITY = 512          # max secret bytes per den
DEN_VERSION = 1

# Fixed file layout: nonce(12) || AES-GCM( len(4) || secret(<=512, zero-padded) )
# GCM adds a 16-byte tag. Every file is exactly this size.
FILE_SIZE = crypto.NONCE_BYTES + 4 + SECRET_CAPACITY + crypto.TAG_BYTES


def _pack(secret: bytes) -> bytes:
    if len(secret) > SECRET_CAPACITY:
        raise ValueError(f"secret too large: {len(secret)} > {SECRET_CAPACITY} bytes")
    return len(secret).to_bytes(4, "big") + secret + b"\x00" * (SECRET_CAPACITY - len(secret))


def _unpack(raw: bytes) -> bytes:
    n = int.from_bytes(raw[:4], "big")
    if n > SECRET_CAPACITY:
        raise ValueError("corrupted den file")
    return raw[4:4 + n]


def _path(den_dir: str, slot: str) -> str:
    return os.path.join(den_dir, slot + ".den")


def build(den_dir: str, key: bytes, secret: bytes) -> str:
    """Create the maze. Returns the real slot (for the builder's eyes only)."""
    if os.path.exists(den_dir) and os.listdir(den_dir):
        raise FileExistsError(f"den dir not empty: {den_dir}")
    os.makedirs(den_dir, exist_ok=True)

    slot = crypto.derive_slot(key, ALPHABET)
    real_blob = crypto.encrypt(key, _pack(secret))
    assert len(real_blob) == FILE_SIZE, "real blob size drifted -- decoys would stand out"

    for a in ALPHABET:
        for b in ALPHABET:
            s = a + b
            with open(_path(den_dir, s), "wb") as f:
                f.write(real_blob if s == slot else os.urandom(FILE_SIZE))

    with open(os.path.join(den_dir, "den.json"), "w") as f:
        # No slot, no key, nothing sensitive -- just format metadata.
        json.dump({"v": DEN_VERSION, "file_size": FILE_SIZE,
                   "created": int(time.time())}, f)
    return slot


def read(den_dir: str, key: bytes) -> bytes:
    """O(1) locate by key-derived slot, then decrypt."""
    slot = crypto.derive_slot(key, ALPHABET)
    with open(_path(den_dir, slot), "rb") as f:
        blob = f.read()
    return _unpack(crypto.decrypt(key, blob))


def verify_layout(den_dir: str) -> dict:
    """Sanity check: 1296 files, all identical in size."""
    files = [n for n in os.listdir(den_dir) if n.endswith(".den")]
    sizes = {os.path.getsize(os.path.join(den_dir, n)) for n in files}
    return {"count": len(files), "distinct_sizes": len(sizes),
            "ok": len(files) == 1296 and len(sizes) == 1}
