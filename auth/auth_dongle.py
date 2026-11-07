"""Validasi USB dongle berbasis token acak; dijalankan pada host Streamlit lokal."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import secrets
import ctypes
from pathlib import Path
import psutil
from crypto.key_manager import get_key
from config import DONGLE_FILENAME, DONGLE_REQUIRE_SERIAL


def _token_digest(token: str) -> str:
    secret = get_key("UNDERGRID_DONGLE_SECRET")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def _serial_digest(serial: str) -> str:
    secret = get_key("UNDERGRID_DONGLE_SECRET")
    return hmac.new(secret, serial.encode("utf-8"), hashlib.sha256).hexdigest()


def detect_removable_drives() -> list[str]:
    """Deteksi mount removable secara best-effort pada OS host."""
    drives: list[str] = []
    system = platform.system().lower()
    for partition in psutil.disk_partitions(all=False):
        mount = partition.mountpoint
        removable = "removable" in (partition.opts or "").lower()
        if system == "windows":
            try:
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{mount}\\")
                removable = drive_type == 2  # DRIVE_REMOVABLE
            except Exception:
                removable = removable or mount.upper().startswith(("E:\\", "F:\\", "G:\\"))
        elif system == "darwin":
            removable = removable or mount.startswith("/Volumes/")
        else:
            removable = removable or mount.startswith(("/media/", "/run/media/", "/mnt/usb"))
        if removable:
            drives.append(mount)
    return drives


def find_dongle_file(drives: list[str] | None = None) -> list[Path]:
    """Temukan file provisioning pada daftar mount removable."""
    candidates = drives if drives is not None else detect_removable_drives()
    return [Path(mount) / DONGLE_FILENAME for mount in candidates if (Path(mount) / DONGLE_FILENAME).is_file()]


def get_volume_serial(path: str | Path) -> str | None:
    """Ambil serial volume pada Windows; OS lain tidak dijamin mendukungnya."""
    if platform.system().lower() != "windows":
        return None
    root = str(Path(path).resolve())
    if not root.endswith("\\"):
        root += "\\"
    serial = ctypes.c_ulong()
    maximum = ctypes.c_ulong()
    flags = ctypes.c_ulong()
    filesystem = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), None, 0, ctypes.byref(serial), ctypes.byref(maximum),
        ctypes.byref(flags), filesystem, 261
    )
    return f"{serial.value:08X}" if ok else None


def generate_dongle_key(target_mount: str | Path, *, username: str) -> dict[str, str | None]:
    """Buat token acak ke USB dan kembalikan digest untuk disimpan di database."""
    mount = Path(target_mount)
    if not mount.exists() or not mount.is_dir():
        raise ValueError("Mount USB tujuan tidak ditemukan.")
    token = secrets.token_urlsafe(32)
    document = {"version": 1, "username": username.strip().lower(), "token": token}
    target = mount / DONGLE_FILENAME
    target.write_text(json.dumps(document, separators=(",", ":")), encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    serial = get_volume_serial(mount)
    return {"token_hash": _token_digest(token), "serial_hash": _serial_digest(serial) if serial else None, "serial": serial}


def verify_dongle(buyer_record, drives: list[str] | None = None) -> bool:
    """Verifikasi dongle token acak dan, bila dikonfigurasi, serial volume."""
    expected = buyer_record.get("dongle_token_hash") if buyer_record else None
    if not expected:
        return False
    for key_file in find_dongle_file(drives):
        try:
            data = json.loads(key_file.read_text(encoding="utf-8"))
            if data.get("username", "").lower() != buyer_record.get("username", "").lower():
                continue
            actual = _token_digest(str(data.get("token", "")))
            if not hmac.compare_digest(actual, expected):
                continue
            required = DONGLE_REQUIRE_SERIAL
            if required:
                serial = get_volume_serial(key_file.parent)
                stored_serial_hash = buyer_record.get("dongle_volume_serial_hash")
                if not serial or not stored_serial_hash or not hmac.compare_digest(_serial_digest(serial), stored_serial_hash):
                    continue
            return True
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return False
