"""Super encryption Vigenere -> AES-256-CBC dengan Encrypt-then-MAC."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from crypto.key_manager import get_key

MAGIC = b"UGMSG1"
IV_SIZE = 16
BLOCK_SIZE = 128


def vigenere_encrypt(text: str, key: str) -> str:
    """Enkripsi huruf ASCII A-Z; karakter lain dipertahankan apa adanya."""
    if not key or not key.isalpha() or not key.isascii():
        raise ValueError("Kunci Vigenere harus berisi huruf ASCII saja.")
    key_values = [ord(ch.upper()) - 65 for ch in key]
    out: list[str] = []
    index = 0
    for char in text:
        if "A" <= char <= "Z":
            out.append(chr((ord(char) - 65 + key_values[index % len(key_values)]) % 26 + 65))
            index += 1
        elif "a" <= char <= "z":
            out.append(chr((ord(char) - 97 + key_values[index % len(key_values)]) % 26 + 97))
            index += 1
        else:
            out.append(char)
    return "".join(out)


def vigenere_decrypt(text: str, key: str) -> str:
    """Dekripsi Vigenere dengan kunci yang sama."""
    if not key or not key.isalpha() or not key.isascii():
        raise ValueError("Kunci Vigenere harus berisi huruf ASCII saja.")
    key_values = [ord(ch.upper()) - 65 for ch in key]
    out: list[str] = []
    index = 0
    for char in text:
        if "A" <= char <= "Z":
            out.append(chr((ord(char) - 65 - key_values[index % len(key_values)]) % 26 + 65))
            index += 1
        elif "a" <= char <= "z":
            out.append(chr((ord(char) - 97 - key_values[index % len(key_values)]) % 26 + 97))
            index += 1
        else:
            out.append(char)
    return "".join(out)


def _load_keys(vigenere_key: str | None, aes_key: bytes | None, hmac_key: bytes | None) -> tuple[str, bytes, bytes]:
    vkey = vigenere_key or __import__("os").environ.get("UNDERGRID_VIGENERE_KEY", "")
    akey = aes_key if aes_key is not None else get_key("UNDERGRID_AES_KEY")
    mkey = hmac_key if hmac_key is not None else get_key("UNDERGRID_HMAC_KEY")
    if not vkey or not vkey.isascii() or not vkey.isalpha():
        raise RuntimeError("UNDERGRID_VIGENERE_KEY harus berupa huruf ASCII.")
    if len(akey) != 32 or len(mkey) < 32:
        raise ValueError("Kunci AES wajib 32 byte dan kunci HMAC minimal 32 byte.")
    if hmac.compare_digest(akey, mkey):
        raise ValueError("Kunci AES dan HMAC tidak boleh sama.")
    return vkey, akey, mkey


def encrypt_message(plaintext: str, *, vigenere_key: str | None = None,
                    aes_key: bytes | None = None, hmac_key: bytes | None = None) -> str:
    """Vigenere plaintext, lalu AES-CBC, lalu HMAC-SHA256 atas header/IV/ciphertext."""
    vkey, akey, mkey = _load_keys(vigenere_key, aes_key, hmac_key)
    intermediate = vigenere_encrypt(plaintext, vkey).encode("utf-8")
    padder = padding.PKCS7(BLOCK_SIZE).padder()
    padded = padder.update(intermediate) + padder.finalize()
    iv = secrets.token_bytes(IV_SIZE)
    encryptor = Cipher(algorithms.AES(akey), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    body = MAGIC + iv + ciphertext
    tag = hmac.new(mkey, body, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(body + tag).decode("ascii")


def decrypt_message(token: str, *, vigenere_key: str | None = None,
                    aes_key: bytes | None = None, hmac_key: bytes | None = None) -> str:
    """Verifikasi HMAC terlebih dahulu, kemudian AES-CBC dan Vigenere."""
    vkey, akey, mkey = _load_keys(vigenere_key, aes_key, hmac_key)
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception as exc:
        raise ValueError("Format ciphertext pesan tidak valid.") from exc
    min_len = len(MAGIC) + IV_SIZE + 16 + 32
    if len(raw) < min_len or raw[:len(MAGIC)] != MAGIC:
        raise ValueError("Header ciphertext pesan tidak valid.")
    body, supplied_tag = raw[:-32], raw[-32:]
    expected_tag = hmac.new(mkey, body, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise ValueError("Integritas pesan gagal diverifikasi.")
    iv = raw[len(MAGIC):len(MAGIC) + IV_SIZE]
    ciphertext = raw[len(MAGIC) + IV_SIZE:-32]
    if not ciphertext or len(ciphertext) % 16:
        raise ValueError("Panjang ciphertext AES-CBC tidak valid.")
    decryptor = Cipher(algorithms.AES(akey), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(BLOCK_SIZE).unpadder()
    intermediate = unpadder.update(padded) + unpadder.finalize()
    return vigenere_decrypt(intermediate.decode("utf-8"), vkey)


def encrypt_message_trace(plaintext: str, *, vigenere_key: str | None = None,
                          aes_key: bytes | None = None, hmac_key: bytes | None = None) -> dict:
    """Jalankan enkripsi pesan dan kembalikan tahapan demonstrasi tanpa membuka kunci."""
    vkey, akey, mkey = _load_keys(vigenere_key, aes_key, hmac_key)
    vigenere_text = vigenere_encrypt(plaintext, vkey)
    intermediate = vigenere_text.encode("utf-8")
    padder = padding.PKCS7(BLOCK_SIZE).padder()
    padded = padder.update(intermediate) + padder.finalize()
    iv = secrets.token_bytes(IV_SIZE)
    encryptor = Cipher(algorithms.AES(akey), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    body = MAGIC + iv + ciphertext
    tag = hmac.new(mkey, body, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(body + tag).decode("ascii")
    return {
        "ciphertext": token,
        "stages": [
            {"name": "Plaintext", "detail": f"{len(plaintext.encode('utf-8'))} byte UTF-8 sebelum transformasi.", "value": plaintext},
            {"name": "Vigenere", "detail": "Substitusi polialfabetik diterapkan pada huruf ASCII; karakter non-huruf dipertahankan.", "value": vigenere_text},
            {"name": "Encoding UTF-8", "detail": f"{len(intermediate)} byte hasil Vigenere.", "value": intermediate.hex(" ")},
            {"name": "Padding PKCS7", "detail": f"Data dipadding ke kelipatan blok AES 16 byte; panjang akhir {len(padded)} byte.", "value": padded.hex(" ")},
            {"name": "AES-256-CBC", "detail": "Ciphertext dibuat dengan IV acak 16 byte. Kunci AES tidak ditampilkan.", "value": f"IV: {iv.hex()}\nCiphertext: {ciphertext.hex()}"},
            {"name": "HMAC-SHA256", "detail": "Tag autentikasi dihitung atas header, IV, dan ciphertext (Encrypt-then-MAC). Kunci HMAC tidak ditampilkan.", "value": tag.hex()},
            {"name": "Token akhir", "detail": "Header + IV + ciphertext + tag dikodekan dengan Base64 URL-safe.", "value": token},
        ],
    }
