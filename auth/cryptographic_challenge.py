"""Puzzle verifikasi Vigenere sekali pakai untuk demonstrasi kriptografi klasik."""
from __future__ import annotations

import hmac
import secrets
import string
import time
import uuid
from crypto.vigenere_aes import vigenere_encrypt, vigenere_decrypt

ALPHABET = string.ascii_uppercase


def generate_challenge(length: int = 12, key_length: int = 5) -> dict[str, object]:
    """Buat plaintext/key acak; plaintext hanya disimpan pada state server."""
    if length < 8 or key_length < 3:
        raise ValueError("Panjang challenge terlalu pendek.")
    answer = "".join(secrets.choice(ALPHABET) for _ in range(length))
    key = "".join(secrets.choice(ALPHABET) for _ in range(key_length))
    return {
        "id": uuid.uuid4().hex,
        "ciphertext": vigenere_encrypt(answer, key),
        "key": key,
        "answer": answer,
        "created_at": time.time(),
        "used": False,
    }


def vigenere_decrypt_challenge(ciphertext: str, key: str) -> str:
    """Helper dekripsi untuk pengujian dan pembelajaran."""
    return vigenere_decrypt(ciphertext, key)


def consume_challenge(challenge: dict[str, object] | None, answer: str) -> bool:
    """Konsumsi challenge sebelum hasil dikembalikan; jawaban dibanding konstan."""
    if not challenge or challenge.get("used"):
        return False
    challenge["used"] = True
    expected = str(challenge.get("answer", ""))
    candidate = (answer or "").strip().upper()
    return bool(expected) and hmac.compare_digest(candidate, expected)


def verify_challenge(challenge: dict[str, object] | None, answer: str) -> bool:
    """Nama API sesuai spesifikasi; setiap submit otomatis menghabiskan challenge."""
    return consume_challenge(challenge, answer)


def regenerate_challenge(challenge: dict[str, object] | None = None) -> dict[str, object]:
    """Tandai challenge lama tidak berlaku dan buat yang baru."""
    if challenge is not None:
        challenge["used"] = True
    return generate_challenge()
