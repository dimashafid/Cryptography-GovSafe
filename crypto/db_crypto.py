"""Enkripsi tingkat kolom dengan AES-256-GCM dan AAD terikat record."""
from __future__ import annotations

import json
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"UGDB"
VERSION = 1
NONCE_SIZE = 12


def _aad_bytes(aad: str | bytes) -> bytes:
    return aad.encode("utf-8") if isinstance(aad, str) else aad


def encrypt_column(value: str | bytes, key: bytes, aad: str | bytes) -> bytes:
    """Enkripsi nilai satu kolom; AAD mengikat tabel, kolom, dan ID record."""
    if len(key) != 32:
        raise ValueError("Kunci AES-GCM harus 32 byte.")
    plaintext = value.encode("utf-8") if isinstance(value, str) else value
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _aad_bytes(aad))
    return MAGIC + bytes([VERSION]) + nonce + ciphertext


def decrypt_column(blob: bytes, key: bytes, aad: str | bytes) -> bytes:
    """Dekripsi dan autentikasi nilai kolom; gagal jika record/AAD berubah."""
    if len(key) != 32:
        raise ValueError("Kunci AES-GCM harus 32 byte.")
    if not isinstance(blob, (bytes, bytearray)) or len(blob) < len(MAGIC) + 1 + NONCE_SIZE + 16:
        raise ValueError("Ciphertext database tidak valid atau terpotong.")
    if blob[:4] != MAGIC or blob[4] != VERSION:
        raise ValueError("Header atau versi ciphertext database tidak dikenal.")
    nonce = bytes(blob[5:17])
    return AESGCM(key).decrypt(nonce, bytes(blob[17:]), _aad_bytes(aad))


def encrypt_json(value: object, key: bytes, aad: str | bytes) -> bytes:
    """Serialisasi JSON deterministik kemudian enkripsi."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return encrypt_column(payload, key, aad)


def decrypt_json(blob: bytes, key: bytes, aad: str | bytes) -> object:
    """Dekripsi dan parse JSON."""
    return json.loads(decrypt_column(blob, key, aad).decode("utf-8"))
