import json
from auth import auth_dongle

def test_dongle_token_is_not_stored_plaintext(tmp_path, monkeypatch):
    result = auth_dongle.generate_dongle_key(tmp_path, username="buyer1")
    data = json.loads((tmp_path / "undergrid.key").read_text())
    assert data["token"]
    assert result["token_hash"] != data["token"]
    monkeypatch.setattr(auth_dongle, "find_dongle_file", lambda drives=None: [tmp_path / "undergrid.key"])
    record = {"username":"buyer1", "dongle_token_hash":result["token_hash"], "dongle_volume_serial_hash":None}
    assert auth_dongle.verify_dongle(record)
