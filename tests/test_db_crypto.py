import pytest
from crypto.db_crypto import encrypt_column, decrypt_column

def test_aes_gcm_round_trip_and_aad_binding():
    key = b"D" * 32
    encrypted = encrypt_column("sensitive data", key, "products:title:7")
    assert decrypt_column(encrypted, key, "products:title:7") == b"sensitive data"
    with pytest.raises(Exception):
        decrypt_column(encrypted, key, "products:title:8")
    with pytest.raises(Exception):
        decrypt_column(encrypted, b"X" * 32, "products:title:7")
