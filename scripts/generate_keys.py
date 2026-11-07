"""Buat file .env berisi secret acak; file .env tidak boleh di-commit."""
from pathlib import Path
import secrets
import string
from crypto.key_manager import generate_key_values

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    env_path = ROOT / ".env"
    if env_path.exists():
        raise SystemExit("File .env sudah ada. Backup dan kelola kunci lama secara terpisah; tidak ditimpa otomatis.")
    values = generate_key_values()
    lines = ["# Simpan file ini secara privat; jangan unggah ke GitHub."]
    lines.extend(f"{name}={value}" for name, value in values.items())
    lines.extend([
        "UNDERGRID_VIGENERE_KEY=" + "".join(secrets.choice(string.ascii_uppercase) for _ in range(32)),
        "UNDERGRID_DB_PATH=data/undergrid.db",
        "UNDERGRID_STORAGE_PATH=storage/products",
        "UNDERGRID_FACE_THRESHOLD=0.48",
        "UNDERGRID_DONGLE_REQUIRE_SERIAL=false",
    ])
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    print("Kunci berhasil dibuat pada .env. Simpan backup offline dan jangan pernah commit file tersebut.")
