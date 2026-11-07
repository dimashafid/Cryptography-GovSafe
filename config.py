"""Konfigurasi aplikasi GOVSAFE; nama variabel rahasia lama dipertahankan."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
DB_PATH = Path(os.getenv("UNDERGRID_DB_PATH", "data/undergrid.db"))
STORAGE_PATH = Path(os.getenv("UNDERGRID_STORAGE_PATH", "storage/products"))
ASSET_STORAGE_PATH = Path(os.getenv("GOVSAFE_ASSET_STORAGE_PATH", "storage/govsafe_assets"))
for _name in ("DB_PATH", "STORAGE_PATH", "ASSET_STORAGE_PATH"):
    _value = globals()[_name]
    if not _value.is_absolute():
        globals()[_name] = PROJECT_ROOT / _value
FACE_THRESHOLD = float(os.getenv("UNDERGRID_FACE_THRESHOLD", "0.48"))
DONGLE_REQUIRE_SERIAL = os.getenv("UNDERGRID_DONGLE_REQUIRE_SERIAL", "false").strip().lower() in {"1", "true", "yes"}
DONGLE_FILENAME = "undergrid.key"  # kompatibel dengan USB yang sudah diprovisikan
APP_NAME = "GOVSAFE"
APP_TAGLINE = "Secure Government Asset Information & Communication."
