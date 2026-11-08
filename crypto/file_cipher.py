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


def encrypt_bytes_trace(data: bytes, key: bytes) -> dict:
    """Enkripsi byte ChaCha20-Poly1305 dan tampilkan tahapan publik tanpa kunci."""
    if len(key) != 32:
        raise ValueError("Kunci ChaCha20-Poly1305 harus 32 byte.")
    nonce = secrets.token_bytes(NONCE_SIZE)
    aad = MAGIC + bytes([VERSION])
    authenticated = ChaCha20Poly1305(key).encrypt(nonce, data, aad)
    ciphertext, tag = authenticated[:-16], authenticated[-16:]
    blob = aad + nonce + authenticated
    return {
        "blob": blob,
        "stages": [
            {"name": "Input file", "detail": f"Data masukan berukuran {len(data)} byte.", "value": data[:128].hex(" ")},
            {"name": "Header dan AAD", "detail": "Header UGFILE dan versi diikat sebagai Additional Authenticated Data.", "value": aad.hex(" ")},
            {"name": "Nonce", "detail": "Nonce 96-bit acak untuk operasi ChaCha20-Poly1305.", "value": nonce.hex()},
            {"name": "ChaCha20", "detail": "Stream cipher menghasilkan ciphertext. Kunci tidak ditampilkan.", "value": ciphertext[:512].hex(" ")},
            {"name": "Poly1305 tag", "detail": "Tag autentikasi 128-bit melindungi integritas dan autentisitas data.", "value": tag.hex()},
            {"name": "Format file terenkripsi", "detail": "Header + nonce + ciphertext + tag.", "value": blob.hex()[:2048]},
        ],
    }
