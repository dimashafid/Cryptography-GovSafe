import pytest
from crypto.vigenere_aes import vigenere_encrypt, vigenere_decrypt, encrypt_message, decrypt_message

def test_vigenere_preserves_symbols_and_case():
    message = "Attack at dawn! 123"
    assert vigenere_decrypt(vigenere_encrypt(message, "LEMON"), "LEMON") == message

def test_super_encryption_round_trip_and_mac():
    token = encrypt_message("Pesan rahasia Undergrid.")
    assert decrypt_message(token) == "Pesan rahasia Undergrid."
    raw = bytearray(token.encode("ascii")); raw[-4] = ord("A") if raw[-4] != ord("A") else ord("B")
    with pytest.raises(Exception):
        decrypt_message(raw.decode("ascii"))
