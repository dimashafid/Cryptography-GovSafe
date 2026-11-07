"""Enkripsi file dengan ChaCha20-Poly1305."""
from __future__ import annotations

import secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

MAGIC = b"UGFILE"
VERSION = 1
NONCE_SIZE = 12


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """Enkripsi bytes dengan kunci 256-bit dan nonce acak 96-bit."""
    if len(key) != 32:
        raise ValueError("Kunci ChaCha20-Poly1305 harus 32 byte.")
    nonce = secrets.token_bytes(NONCE_SIZE)
    aad = MAGIC + bytes([VERSION])
    encrypted = ChaCha20Poly1305(key).encrypt(nonce, data, aad)
    return aad + nonce + encrypted


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    """Dekripsi bytes dan verifikasi authentication tag."""
    if len(key) != 32:
        raise ValueError("Kunci ChaCha20-Poly1305 harus 32 byte.")
    header_size = len(MAGIC) + 1
    if len(blob) < header_size + NONCE_SIZE + 16 or blob[:len(MAGIC)] != MAGIC or blob[len(MAGIC)] != VERSION:
        raise ValueError("Format file terenkripsi tidak valid.")
    nonce = blob[header_size:header_size + NONCE_SIZE]
    ciphertext = blob[header_size + NONCE_SIZE:]
    return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, blob[:header_size])


def encrypt_file(source: str | Path, destination: str | Path, key: bytes) -> Path:
    """Enkripsi file ke tujuan dan kembalikan path hasil."""
    src, dst = Path(source), Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(encrypt_bytes(src.read_bytes(), key))
    return dst


def decrypt_file(source: str | Path, destination: str | Path, key: bytes) -> Path:
    """Dekripsi file ke tujuan; untuk UI gunakan decrypt_bytes agar tetap di RAM."""
    src, dst = Path(source), Path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(decrypt_bytes(src.read_bytes(), key))
    return dst
