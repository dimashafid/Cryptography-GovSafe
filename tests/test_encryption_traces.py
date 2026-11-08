import base64

from crypto.db_crypto import decrypt_column, encrypt_column_trace
from crypto.file_cipher import decrypt_bytes, encrypt_bytes_trace
from crypto.vigenere_aes import decrypt_message, encrypt_message_trace


def test_message_trace_produces_valid_ciphertext_without_exposing_keys():
    v_key = "GOVSAFE"
    aes_key = b"A" * 32
    hmac_key = b"B" * 32
    trace = encrypt_message_trace(
        "Pesan rahasia GOVSAFE",
        vigenere_key=v_key,
        aes_key=aes_key,
        hmac_key=hmac_key,
    )
    assert decrypt_message(
        trace["ciphertext"],
        vigenere_key=v_key,
        aes_key=aes_key,
        hmac_key=hmac_key,
    ) == "Pesan rahasia GOVSAFE"
    assert [stage["name"] for stage in trace["stages"]][-1] == "Token akhir"
    assert all("key" not in stage for stage in trace["stages"])


def test_database_aes_gcm_trace_can_be_decrypted():
    key = b"C" * 32
    trace = encrypt_column_trace("metadata", key, "table:column:1")
    assert decrypt_column(trace["blob"], key, "table:column:1") == b"metadata"
    assert trace["stages"][-1]["name"] == "Format penyimpanan"


def test_file_chacha_trace_can_be_decrypted():
    key = b"D" * 32
    trace = encrypt_bytes_trace(b"PNG sample", key)
    assert decrypt_bytes(trace["blob"], key) == b"PNG sample"
    assert trace["stages"][-1]["name"] == "Format file terenkripsi"
