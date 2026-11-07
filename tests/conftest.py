import base64
import pytest

@pytest.fixture(autouse=True)
def test_keys(monkeypatch):
    for name, byte in {
        "UNDERGRID_DB_KEY": b"D" * 32,
        "UNDERGRID_FILE_KEY": b"F" * 32,
        "UNDERGRID_AES_KEY": b"A" * 32,
        "UNDERGRID_HMAC_KEY": b"H" * 32,
        "UNDERGRID_DONGLE_SECRET": b"S" * 32,
    }.items():
        monkeypatch.setenv(name, base64.urlsafe_b64encode(byte).decode("ascii"))
    monkeypatch.setenv("UNDERGRID_VIGENERE_KEY", "UNDERGRIDPRIVATEKEY")
