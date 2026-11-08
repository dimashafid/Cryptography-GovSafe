"""Layanan bisnis GOVSAFE: aset, permohonan, pesan terenkripsi, dan audit."""
from __future__ import annotations

import json
import re
import secrets
from io import BytesIO

from PIL import Image
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from blockchain.blockchain import add_block
from config import ASSET_STORAGE_PATH
from crypto.db_crypto import encrypt_column, decrypt_column
from crypto.file_cipher import decrypt_bytes
from crypto.key_manager import get_key
from crypto.steganography import decode_message, encode_message
from crypto.vigenere_aes import encrypt_message, decrypt_message
from database.db_manager import get_connection, get_buyer_by_id
from database.govsafe_schema import ensure_govsafe_schema

VALID_ROLES = {"pemohon", "petugas"}
REQUEST_STATUSES = ("Menunggu", "Diproses", "Dijawab", "Ditutup")
LEGAL_STATUSES = ("Barang sitaan", "Barang rampasan negara", "Barang bukti", "Status dalam verifikasi")
ASSET_CATEGORIES = ("Kendaraan", "Elektronik", "Properti", "Mesin dan peralatan", "Barang bernilai", "Lainnya")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db_key() -> bytes:
    return get_key("UNDERGRID_DB_KEY")


def _enc(table: str, column: str, record_id: int, value: str) -> bytes:
    return encrypt_column(value, _db_key(), f"{table}:{column}:{record_id}")


def _dec(table: str, column: str, record_id: int, value: bytes) -> str:
    return decrypt_column(value, _db_key(), f"{table}:{column}:{record_id}").decode("utf-8")


def _user_role(user_id: int) -> str:
    user = get_buyer_by_id(int(user_id))
    if not user:
        raise LookupError("Akun GOVSAFE tidak ditemukan.")
    role = user.get("role") or "pemohon"
    if role not in VALID_ROLES:
        raise PermissionError("Peran akun tidak valid.")
    return role


def set_user_role(user_id: int, role: str, display_name: str | None = None) -> None:
    ensure_govsafe_schema()
    if role not in VALID_ROLES:
        raise ValueError("Peran harus 'pemohon' atau 'petugas'.")
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE buyers SET role=?, display_name=COALESCE(?, display_name) WHERE id=?",
            (role, display_name.strip() if display_name else None, int(user_id)),
        )
        if cursor.rowcount != 1:
            raise LookupError("Akun GOVSAFE tidak ditemukan.")


def get_user(user_id: int) -> dict[str, Any]:
    user = get_buyer_by_id(int(user_id))
    if not user:
        raise LookupError("Akun GOVSAFE tidak ditemukan.")
    user["role"] = user.get("role") or "pemohon"
    user["display_name"] = user.get("display_name") or user.get("username")
    return user


def list_officers() -> list[dict[str, Any]]:
    ensure_govsafe_schema()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, display_name FROM buyers WHERE role='petugas' AND account_status='active' ORDER BY username"
        ).fetchall()
    return [dict(row) for row in rows]


def get_dashboard_stats(user_id: int, role: str) -> dict[str, int]:
    ensure_govsafe_schema()
    with get_connection() as conn:
        assets = int(conn.execute("SELECT COUNT(*) FROM govsafe_assets WHERE asset_status='Aktif'").fetchone()[0])
        if role == "petugas":
            requests = int(conn.execute("SELECT COUNT(*) FROM govsafe_requests WHERE request_status NOT IN ('Ditutup')").fetchone()[0])
            pending = int(conn.execute("SELECT COUNT(*) FROM govsafe_requests WHERE request_status IN ('Menunggu','Diproses')").fetchone()[0])
            messages = int(conn.execute("SELECT COUNT(*) FROM govsafe_messages WHERE recipient_id=?", (user_id,)).fetchone()[0])
        else:
            requests = int(conn.execute("SELECT COUNT(*) FROM govsafe_requests WHERE applicant_id=?", (user_id,)).fetchone()[0])
            pending = int(conn.execute("SELECT COUNT(*) FROM govsafe_requests WHERE applicant_id=? AND request_status IN ('Menunggu','Diproses')", (user_id,)).fetchone()[0])
            messages = int(conn.execute("SELECT COUNT(*) FROM govsafe_messages WHERE recipient_id=?", (user_id,)).fetchone()[0])
        return {"assets": assets, "requests": requests, "pending": pending, "messages": messages}


def create_asset(*, officer_id: int, asset_code: str, name: str, category: str,
                 legal_status: str, condition: str, storage_location: str,
                 access_level: str, description: str, image_bytes: bytes) -> int:
    ensure_govsafe_schema()
    if _user_role(officer_id) != "petugas":
        raise PermissionError("Hanya Petugas yang dapat mendaftarkan aset.")
    code = asset_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{2,39}", code):
        raise ValueError("Kode aset harus 3-40 karakter dan hanya berisi huruf, angka, titik, garis bawah, atau tanda hubung.")
    if not all(x.strip() for x in (name, category, description, condition, storage_location)):
        raise ValueError("Seluruh informasi aset wajib diisi.")
    if legal_status not in LEGAL_STATUSES:
        raise ValueError("Status hukum aset tidak dikenal.")
    if access_level not in ("Publik", "Terbatas"):
        raise ValueError("Tingkat akses tidak valid.")
    if not image_bytes:
        raise ValueError("Foto aset wajib diunggah.")

    # Validasi berdasarkan format konten, bukan hanya ekstensi nama file.
    try:
        with Image.open(BytesIO(image_bytes)) as uploaded_image:
            if uploaded_image.format != "PNG":
                raise ValueError("Foto aset harus berupa file PNG.")
            uploaded_image.verify()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Foto aset bukan PNG yang valid atau berkas rusak.") from exc

    created = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO govsafe_assets(asset_code,category,legal_status,access_level,asset_status,encrypted_name,encrypted_description,encrypted_condition,encrypted_storage_location,encrypted_image_path,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (code, category.strip(), legal_status, access_level, "Aktif", b"pending", b"pending", b"pending", b"pending", b"pending", officer_id, created, created),
        )
        asset_id = int(cursor.lastrowid)
        secret_metadata = {
            "asset_id": asset_id,
            "asset_code": code,
            "name": name.strip(),
            "category": category.strip(),
            "legal_status": legal_status,
            "condition": condition,
            "description": description.strip(),
            "storage_location": storage_location.strip(),
            "access_level": access_level,
        }
        stego_png = encode_message(image_bytes, secret_metadata)
        # File aset baru disimpan sebagai PNG steganografi LSB tanpa enkripsi file.
        ASSET_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        image_path = ASSET_STORAGE_PATH / f"{code}.png"
        image_path.write_bytes(stego_png)
        values = {
            "encrypted_name": name.strip(),
            "encrypted_description": description.strip(),
            "encrypted_condition": condition.strip(),
            "encrypted_storage_location": storage_location.strip(),
            "encrypted_image_path": str(image_path.resolve()),
        }
        for column, value in values.items():
            conn.execute(f"UPDATE govsafe_assets SET {column}=? WHERE id=?", (_enc("govsafe_assets", column, asset_id, value), asset_id))

    add_block("ASSET_CREATED", {"asset_id": asset_id, "asset_code": code, "category": category.strip(), "legal_status": legal_status, "actor_id": officer_id})
    return asset_id


def _asset_from_row(row, *, include_private: bool) -> dict[str, Any]:
    item = dict(row)
    for column in ("encrypted_name", "encrypted_description", "encrypted_condition", "encrypted_storage_location", "encrypted_image_path"):
        item[column.removeprefix("encrypted_")] = _dec("govsafe_assets", column, item["id"], item[column])
        del item[column]
    if not include_private and item["access_level"] == "Terbatas":
        item["storage_location"] = "Informasi lokasi dibatasi"
    if not include_private:
        item.pop("created_by", None)
    return item



def update_asset_catalog(*, officer_id: int, asset_id: int, name: str, category: str,
                         legal_status: str, condition: str, storage_location: str,
                         access_level: str, description: str) -> None:
    """Perbarui metadata katalog di database tanpa mengubah PNG/metadata snapshot LSB."""
    ensure_govsafe_schema()
    if _user_role(officer_id) != "petugas":
        raise PermissionError("Hanya Petugas yang dapat mengubah metadata katalog.")
    values = {
        "name": name.strip() if isinstance(name, str) else "",
        "category": category.strip() if isinstance(category, str) else "",
        "condition": condition.strip() if isinstance(condition, str) else "",
        "description": description.strip() if isinstance(description, str) else "",
        "storage_location": storage_location.strip() if isinstance(storage_location, str) else "",
    }
    if not all(values.values()):
        raise ValueError("Nama, kategori, kondisi, deskripsi, dan lokasi wajib diisi.")
    if values["category"] not in ASSET_CATEGORIES:
        raise ValueError("Kategori aset tidak dikenal.")
    if legal_status not in LEGAL_STATUSES:
        raise ValueError("Status hukum aset tidak dikenal.")
    if access_level not in ("Publik", "Terbatas"):
        raise ValueError("Tingkat akses tidak valid.")

    encrypted_values = {
        "encrypted_name": _enc("govsafe_assets", "encrypted_name", int(asset_id), values["name"]),
        "encrypted_description": _enc("govsafe_assets", "encrypted_description", int(asset_id), values["description"]),
        "encrypted_condition": _enc("govsafe_assets", "encrypted_condition", int(asset_id), values["condition"]),
        "encrypted_storage_location": _enc("govsafe_assets", "encrypted_storage_location", int(asset_id), values["storage_location"]),
    }
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM govsafe_assets WHERE id=?", (int(asset_id),)).fetchone()
        if not row:
            raise LookupError("Aset tidak ditemukan.")
        cursor = conn.execute(
            """UPDATE govsafe_assets
               SET category=?, legal_status=?, access_level=?,
                   encrypted_name=?, encrypted_description=?, encrypted_condition=?,
                   encrypted_storage_location=?, updated_at=?
               WHERE id=?""",
            (
                values["category"], legal_status, access_level,
                encrypted_values["encrypted_name"], encrypted_values["encrypted_description"],
                encrypted_values["encrypted_condition"], encrypted_values["encrypted_storage_location"],
                _now(), int(asset_id),
            ),
        )
        if cursor.rowcount != 1:
            raise LookupError("Metadata aset tidak berhasil diperbarui.")

    # Audit hanya menyimpan daftar nama field; nilai deskripsi/lokasi tidak dimasukkan ke ledger.
    add_block(
        "ASSET_CATALOG_UPDATED",
        {
            "asset_id": int(asset_id),
            "officer_id": int(officer_id),
            "changed_fields": ["name", "category", "legal_status", "condition", "description", "storage_location", "access_level"],
            "image_snapshot_changed": False,
        },
    )

def list_assets(*, role: str, include_inactive: bool = False) -> list[dict[str, Any]]:
    ensure_govsafe_schema()
    if role not in VALID_ROLES:
        raise PermissionError("Peran akun tidak valid.")
    where = "" if include_inactive and role == "petugas" else "WHERE asset_status='Aktif'"
    with get_connection() as conn:
        rows = conn.execute(f"SELECT * FROM govsafe_assets {where} ORDER BY created_at DESC").fetchall()
    return [_asset_from_row(row, include_private=(role == "petugas")) for row in rows]


def get_asset_detail(asset_id: int, *, role: str) -> dict[str, Any] | None:
    ensure_govsafe_schema()
    if role not in VALID_ROLES:
        raise PermissionError("Peran akun tidak valid.")
    with get_connection() as conn:
        if role == "petugas":
            row = conn.execute("SELECT * FROM govsafe_assets WHERE id=?", (int(asset_id),)).fetchone()
        else:
            row = conn.execute("SELECT * FROM govsafe_assets WHERE id=? AND asset_status='Aktif'", (int(asset_id),)).fetchone()
    if not row:
        return None
    item = _asset_from_row(row, include_private=(role == "petugas"))
    try:
        stored_file = Path(item["image_path"]).read_bytes()
    except OSError as exc:
        raise FileNotFoundError("Berkas foto aset tidak ditemukan. Metadata katalog tetap tersimpan di database.") from exc
    # Kompatibilitas baca: file lama ber-header UGFILE tetap didekripsi.
    # File aset baru adalah PNG LSB biasa dan tidak memerlukan kunci file.
    if stored_file.startswith(b"UGFILE"):
        stego_png = decrypt_bytes(stored_file, get_key("UNDERGRID_FILE_KEY"))
    else:
        stego_png = stored_file
    item["image_bytes"] = stego_png
    item.pop("image_path", None)
    return item


def prepare_asset_download_png(image_bytes: bytes, *, access_level: str, role: str) -> bytes:
    """Siapkan PNG untuk Pemohon; samarkan lokasi pada payload LSB jika akses terbatas."""
    if role != "pemohon":
        raise PermissionError("Unduhan PNG katalog ini hanya tersedia untuk Pemohon.")
    if access_level != "Terbatas":
        return image_bytes

    # Steganografi LSB bukan enkripsi. Jangan membocorkan lokasi terbatas melalui
    # payload tersembunyi pada PNG yang diunduh Pemohon.
    snapshot = decode_message(image_bytes)
    if not isinstance(snapshot, dict):
        raise ValueError("Metadata steganografi aset tidak memiliki struktur yang dapat disamarkan.")
    if "storage_location" in snapshot:
        snapshot = dict(snapshot)
        snapshot["storage_location"] = "Informasi lokasi dibatasi"
        return encode_message(image_bytes, snapshot)
    return image_bytes


def create_request(*, applicant_id: int, asset_id: int, request_type: str, subject: str, details: str) -> int:
    ensure_govsafe_schema()
    if _user_role(applicant_id) != "pemohon":
        raise PermissionError("Permohonan informasi hanya dapat diajukan oleh Pemohon.")
    if request_type not in ("Permohonan Informasi", "Permohonan Dokumen"):
        raise ValueError("Jenis permohonan tidak valid.")
    if not subject.strip() or not details.strip():
        raise ValueError("Subjek dan rincian permohonan wajib diisi.")
    with get_connection() as conn:
        asset = conn.execute("SELECT id, asset_code, asset_status FROM govsafe_assets WHERE id=?", (int(asset_id),)).fetchone()
        if not asset or asset["asset_status"] != "Aktif":
            raise LookupError("Aset tidak ditemukan atau tidak tersedia.")
        request_code = "GVS-" + datetime.now(timezone.utc).strftime("%y%m%d%H%M%S") + "-" + secrets.token_hex(2).upper()
        created = _now()
        cur = conn.execute(
            "INSERT INTO govsafe_requests(request_code,asset_id,applicant_id,assigned_officer_id,request_type,request_status,encrypted_subject,encrypted_details,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (request_code, int(asset_id), applicant_id, None, request_type, "Menunggu", b"pending", b"pending", created, created),
        )
        request_id = int(cur.lastrowid)
        conn.execute("UPDATE govsafe_requests SET encrypted_subject=?, encrypted_details=? WHERE id=?", (
            _enc("govsafe_requests", "encrypted_subject", request_id, subject.strip()),
            _enc("govsafe_requests", "encrypted_details", request_id, details.strip()), request_id))
    add_block("INFORMATION_REQUESTED" if request_type == "Permohonan Informasi" else "DOCUMENT_REQUESTED",
              {"request_id": request_id, "request_code": request_code, "asset_id": int(asset_id), "applicant_id": applicant_id})
    return request_id


def list_requests(*, user_id: int, role: str) -> list[dict[str, Any]]:
    ensure_govsafe_schema()
    if role == "pemohon":
        query = "SELECT r.*, a.asset_code, a.category, a.legal_status, u.username AS applicant_username, o.username AS officer_username FROM govsafe_requests r JOIN govsafe_assets a ON a.id=r.asset_id JOIN buyers u ON u.id=r.applicant_id LEFT JOIN buyers o ON o.id=r.assigned_officer_id WHERE r.applicant_id=? ORDER BY r.created_at DESC"
    elif role == "petugas":
        query = "SELECT r.*, a.asset_code, a.category, a.legal_status, u.username AS applicant_username, o.username AS officer_username FROM govsafe_requests r JOIN govsafe_assets a ON a.id=r.asset_id JOIN buyers u ON u.id=r.applicant_id LEFT JOIN buyers o ON o.id=r.assigned_officer_id ORDER BY CASE r.request_status WHEN 'Menunggu' THEN 0 WHEN 'Diproses' THEN 1 ELSE 2 END, r.created_at DESC"
    else:
        raise PermissionError("Peran akun tidak valid.")
    with get_connection() as conn:
        rows = conn.execute(query, (user_id,) if role == "pemohon" else ()).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["subject"] = _dec("govsafe_requests", "encrypted_subject", item["id"], item.pop("encrypted_subject"))
        item["details"] = _dec("govsafe_requests", "encrypted_details", item["id"], item.pop("encrypted_details"))
        result.append(item)
    return result


def claim_request(*, officer_id: int, request_id: int) -> None:
    if _user_role(officer_id) != "petugas":
        raise PermissionError("Hanya Petugas yang dapat mengambil permohonan.")
    with get_connection() as conn:
        row = conn.execute("SELECT assigned_officer_id FROM govsafe_requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise LookupError("Permohonan tidak ditemukan.")
        if row["assigned_officer_id"] not in (None, officer_id):
            raise PermissionError("Permohonan sudah ditangani Petugas lain.")
        conn.execute("UPDATE govsafe_requests SET assigned_officer_id=?, request_status='Diproses', updated_at=? WHERE id=?", (officer_id, _now(), request_id))
    add_block("REQUEST_CLAIMED", {"request_id": request_id, "officer_id": officer_id})


def update_request_status(*, officer_id: int, request_id: int, status: str) -> None:
    if _user_role(officer_id) != "petugas":
        raise PermissionError("Hanya Petugas yang dapat mengubah status permohonan.")
    if status not in REQUEST_STATUSES:
        raise ValueError("Status permohonan tidak dikenal.")
    with get_connection() as conn:
        row = conn.execute("SELECT assigned_officer_id FROM govsafe_requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise LookupError("Permohonan tidak ditemukan.")
        if row["assigned_officer_id"] != officer_id:
            raise PermissionError("Ambil permohonan terlebih dahulu sebelum mengubah status.")
        conn.execute("UPDATE govsafe_requests SET request_status=?, updated_at=? WHERE id=?", (status, _now(), request_id))
    add_block("REQUEST_STATUS_UPDATED", {"request_id": request_id, "status": status, "officer_id": officer_id})


def list_request_messages(*, user_id: int, role: str, request_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        request = conn.execute("SELECT applicant_id, assigned_officer_id FROM govsafe_requests WHERE id=?", (request_id,)).fetchone()
        if not request:
            raise LookupError("Permohonan tidak ditemukan.")
        allowed = user_id == request["applicant_id"] or user_id == request["assigned_officer_id"]
        if not allowed or _user_role(user_id) != role:
            raise PermissionError("Akun tidak memiliki akses ke percakapan ini.")
        rows = conn.execute("SELECT m.*, s.username AS sender_username FROM govsafe_messages m JOIN buyers s ON s.id=m.sender_id WHERE m.request_id=? ORDER BY m.created_at", (request_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["ciphertext"] = item["encrypted_message"]
        item["plaintext"] = decrypt_message(item.pop("encrypted_message"))
        item["is_own"] = item["sender_id"] == user_id
        result.append(item)
    return result


def send_request_message(*, sender_id: int, request_id: int, plaintext: str) -> int:
    if not plaintext.strip():
        raise ValueError("Pesan tidak boleh kosong.")
    role = _user_role(sender_id)
    with get_connection() as conn:
        req = conn.execute("SELECT applicant_id, assigned_officer_id, request_status FROM govsafe_requests WHERE id=?", (request_id,)).fetchone()
        if not req:
            raise LookupError("Permohonan tidak ditemukan.")
        if req["request_status"] == "Ditutup":
            raise ValueError("Percakapan telah ditutup.")
        if role == "pemohon" and sender_id == req["applicant_id"] and req["assigned_officer_id"]:
            recipient_id = req["assigned_officer_id"]
        elif role == "petugas" and sender_id == req["assigned_officer_id"]:
            recipient_id = req["applicant_id"]
        else:
            raise PermissionError("Petugas harus mengambil permohonan sebelum percakapan dapat digunakan.")
        ciphertext = encrypt_message(plaintext.strip())
        cur = conn.execute("INSERT INTO govsafe_messages(request_id,sender_id,recipient_id,encrypted_message,created_at) VALUES(?,?,?,?,?)",
                           (request_id, sender_id, recipient_id, ciphertext, _now()))
        message_id = int(cur.lastrowid)
    add_block("MESSAGE_SENT", {"message_id": message_id, "request_id": request_id, "sender_id": sender_id, "recipient_id": recipient_id, "sender_role": role})
    return message_id


def mark_request_answered(*, officer_id: int, request_id: int) -> None:
    update_request_status(officer_id=officer_id, request_id=request_id, status="Dijawab")


def archive_asset(*, officer_id: int, asset_id: int) -> None:
    if _user_role(officer_id) != "petugas":
        raise PermissionError("Hanya Petugas yang dapat mengubah status aset.")
    with get_connection() as conn:
        cur = conn.execute("UPDATE govsafe_assets SET asset_status='Diarsipkan', updated_at=? WHERE id=?", (_now(), int(asset_id)))
        if cur.rowcount != 1:
            raise LookupError("Aset tidak ditemukan.")
    add_block("ASSET_ARCHIVED", {"asset_id": int(asset_id), "officer_id": officer_id})
