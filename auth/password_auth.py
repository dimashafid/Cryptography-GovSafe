"""Password hashing Argon2id dan autentikasi Buyer."""
from __future__ import annotations
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)


def hash_password(password: str) -> str:
    """Hash password dengan Argon2id; password asli tidak disimpan."""
    if not isinstance(password, str) or len(password) < 10:
        raise ValueError("Password minimal 10 karakter.")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verifikasi password dengan API library Argon2."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError, TypeError):
        return False


def create_buyer_account(username: str, password: str, db_path=None) -> int:
    """Provision akun Buyer dari CLI/skrip tepercaya; tidak ada registrasi publik."""
    from database.db_manager import add_buyer
    normalized = username.strip().lower()
    if not normalized or len(normalized) > 64:
        raise ValueError("Username harus berisi 1-64 karakter.")
    return add_buyer(normalized, hash_password(password), db_path=db_path)


def authenticate_buyer(username: str, password: str, db_path=None):
    """Ambil akun dan verifikasi password; mengembalikan record atau None."""
    from database.db_manager import get_buyer_by_username
    record = get_buyer_by_username(username.strip().lower(), db_path=db_path)
    if record and record["account_status"] == "active" and verify_password(password, record["password_hash"]):
        return record
    return None
