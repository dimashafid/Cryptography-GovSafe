import pytest
from crypto.file_cipher import encrypt_bytes, decrypt_bytes

def test_chacha20_poly1305_round_trip():
    key = b"K" * 32
    data = b"undergrid confidential image bytes"
    encrypted = encrypt_bytes(data, key)
    assert encrypted != data
    assert decrypt_bytes(encrypted, key) == data

def test_wrong_key_and_modified_ciphertext_fail():
    encrypted = encrypt_bytes(b"secret", b"K" * 32)
    with pytest.raises(Exception):
        decrypt_bytes(encrypted, b"Z" * 32)
    modified = bytearray(encrypted); modified[-1] ^= 1
    with pytest.raises(Exception):
        decrypt_bytes(bytes(modified), b"K" * 32)
