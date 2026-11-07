"""Pemuatan dan validasi kunci kriptografi dari environment."""
from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from typing import Iterable

KEY_ENV_VARS = (
    "UNDERGRID_DB_KEY",
    "UNDERGRID_FILE_KEY",
    "UNDERGRID_AES_KEY",
    "UNDERGRID_HMAC_KEY",
    "UNDERGRID_DONGLE_SECRET",
)


def _decode_key(value: str) -> bytes:
    """Mendekode kunci dari Base64 atau hex; hasil harus tepat 32 byte."""
    raw = value.strip()
    if not raw:
        raise ValueError("Nilai kunci kosong.")
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    try:
        decoded = bytes.fromhex(raw)
        if len(decoded) == 32:
            return decoded
    except ValueError:
        pass
    raise ValueError("Kunci harus berupa Base64 URL-safe atau hex sepanjang 32 byte.")


def get_key(name: str, *, required: bool = True) -> bytes | None:
    """Ambil kunci 256-bit dari environment variable."""
    value = os.getenv(name)
    if not value:
        if required:
            raise RuntimeError(f"Environment variable {name} belum diatur. Jalankan scripts/generate_keys.py.")
        return None
    return _decode_key(value)


def generate_key_values(names: Iterable[str] = KEY_ENV_VARS) -> dict[str, str]:
    """Buat kunci acak 256-bit dengan representasi Base64 URL-safe."""
    return {name: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii") for name in names}


def validate_environment(names: Iterable[str] = KEY_ENV_VARS) -> list[str]:
    """Kembalikan daftar masalah konfigurasi kunci tanpa membocorkan isinya."""
    errors: list[str] = []
    for name in names:
        try:
            get_key(name)
        except (RuntimeError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    return errors
