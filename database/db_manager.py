"""Operasi SQLite terparameterisasi dan helper repository."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
from config import DB_PATH
from crypto.db_crypto import encrypt_column, decrypt_column
from crypto.key_manager import get_key

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS buyers (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 face_encoding_enc BLOB,
 dongle_token_hash TEXT,
 dongle_volume_serial_hash TEXT,
 account_status TEXT NOT NULL DEFAULT 'active',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 sku TEXT NOT NULL UNIQUE,
 category TEXT NOT NULL,
 encrypted_title BLOB NOT NULL,
 encrypted_description BLOB NOT NULL,
 encrypted_specifications BLOB NOT NULL,
 encrypted_seller_contact BLOB NOT NULL,
 encrypted_secret_metadata BLOB NOT NULL,
 price_display TEXT NOT NULL,
 encrypted_image_path BLOB NOT NULL,
 status TEXT NOT NULL DEFAULT 'available',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 buyer_id INTEGER NOT NULL,
 recipient TEXT NOT NULL,
 encrypted_message TEXT NOT NULL,
 created_at TEXT NOT NULL,
 message_status TEXT NOT NULL DEFAULT 'sent',
 FOREIGN KEY (buyer_id) REFERENCES buyers(id)
);
CREATE TABLE IF NOT EXISTS buyer_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 buyer_id INTEGER NOT NULL,
 event_type TEXT NOT NULL,
 resource_id TEXT,
 encrypted_details BLOB NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY (buyer_id) REFERENCES buyers(id)
);
CREATE TABLE IF NOT EXISTS blockchain_blocks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 block_index INTEGER NOT NULL UNIQUE,
 timestamp TEXT NOT NULL,
 event_type TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 previous_hash TEXT NOT NULL,
 current_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_buyer ON messages(buyer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_logs_buyer ON buyer_logs(buyer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
"""


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row factory dan foreign key aktif."""
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    """Buat seluruh tabel yang diperlukan secara idempotent."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_buyer(username: str, password_hash: str, db_path=None) -> int:
    """Tambahkan Buyer; password hash Argon2id disediakan caller."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO buyers(username,password_hash,created_at) VALUES(?,?,?)",
            (username, password_hash, _now()),
        )
        return int(cur.lastrowid)


def update_buyer_password(buyer_id: int, password_hash: str, db_path=None) -> None:
    """Ganti hash password Buyer melalui script provisioning tepercaya."""
    with get_connection(db_path) as conn:
        cur = conn.execute("UPDATE buyers SET password_hash = ? WHERE id = ?", (password_hash, buyer_id))
        if cur.rowcount != 1:
            raise LookupError("Buyer tidak ditemukan.")


def get_buyer_by_username(username: str, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM buyers WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_buyer_by_id(buyer_id: int, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM buyers WHERE id = ?", (buyer_id,)).fetchone()
        return dict(row) if row else None


def update_buyer_face(buyer_id: int, encrypted_encoding: bytes, db_path=None) -> None:
    with get_connection(db_path) as conn:
        cur = conn.execute("UPDATE buyers SET face_encoding_enc = ? WHERE id = ?", (encrypted_encoding, buyer_id))
        if cur.rowcount != 1:
            raise LookupError("Buyer tidak ditemukan.")


def update_buyer_dongle(buyer_id: int, token_hash: str, serial_hash: str | None, db_path=None) -> None:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE buyers SET dongle_token_hash = ?, dongle_volume_serial_hash = ? WHERE id = ?",
            (token_hash, serial_hash, buyer_id),
        )
        if cur.rowcount != 1:
            raise LookupError("Buyer tidak ditemukan.")


def add_product(product: dict[str, Any], db_path=None) -> int:
    """Tambahkan produk; semua field sensitif dienkripsi setelah ID didapat."""
    key = get_key("UNDERGRID_DB_KEY")
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO products(sku,category,encrypted_title,encrypted_description,encrypted_specifications,encrypted_seller_contact,encrypted_secret_metadata,price_display,encrypted_image_path,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (product["sku"], product["category"], b"pending", b"pending", b"pending", b"pending", b"pending", product["price_display"], b"pending", product.get("status", "available"), _now()),
        )
        product_id = int(cur.lastrowid)
        values = {
            "encrypted_title": product["title"],
            "encrypted_description": product["description"],
            "encrypted_specifications": product.get("specifications", ""),
            "encrypted_seller_contact": product.get("seller_contact", ""),
            "encrypted_secret_metadata": product.get("secret_metadata", {}),
            "encrypted_image_path": product["image_path"],
        }
        encrypted = {}
        for column, value in values.items():
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            encrypted[column] = encrypt_column(str(value), key, f"products:{column}:{product_id}")
        conn.execute(
            "UPDATE products SET encrypted_title=?,encrypted_description=?,encrypted_specifications=?,encrypted_seller_contact=?,encrypted_secret_metadata=?,encrypted_image_path=? WHERE id=?",
            (encrypted["encrypted_title"], encrypted["encrypted_description"], encrypted["encrypted_specifications"], encrypted["encrypted_seller_contact"], encrypted["encrypted_secret_metadata"], encrypted["encrypted_image_path"], product_id),
        )
        return product_id


def _decrypt_product(row: sqlite3.Row) -> dict[str, Any]:
    key = get_key("UNDERGRID_DB_KEY")
    result = dict(row)
    for column in ("encrypted_title", "encrypted_description", "encrypted_specifications", "encrypted_seller_contact", "encrypted_secret_metadata", "encrypted_image_path"):
        raw = decrypt_column(result[column], key, f"products:{column}:{result['id']}").decode("utf-8")
        plain_name = column.removeprefix("encrypted_")
        result[plain_name] = raw
    import json
    try:
        result["secret_metadata"] = json.loads(result["secret_metadata"])
    except json.JSONDecodeError:
        result["secret_metadata"] = {}
    return result


def list_products(db_path=None, *, available_only: bool = True) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        query = "SELECT * FROM products WHERE status = 'available' ORDER BY created_at DESC" if available_only else "SELECT * FROM products ORDER BY created_at DESC"
        rows = conn.execute(query).fetchall()
    return [_decrypt_product(row) for row in rows]


def get_product(product_id: int, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return _decrypt_product(row) if row else None


def add_message(buyer_id: int, recipient: str, ciphertext: str, db_path=None) -> int:
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO messages(buyer_id,recipient,encrypted_message,created_at) VALUES(?,?,?,?)",
            (buyer_id, recipient, ciphertext, _now()),
        )
        return int(cur.lastrowid)


def list_messages(buyer_id: int | None = None, db_path=None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        if buyer_id is None:
            rows = conn.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM messages WHERE buyer_id = ? ORDER BY created_at DESC", (buyer_id,)).fetchall()
        return [dict(row) for row in rows]


def add_log(buyer_id: int, event_type: str, details: dict[str, Any], resource_id: str | None = None, db_path=None) -> int:
    import json
    key = get_key("UNDERGRID_DB_KEY")
    created = _now()
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO buyer_logs(buyer_id,event_type,resource_id,encrypted_details,created_at) VALUES(?,?,?,?,?)",
            (buyer_id, event_type, resource_id, b"pending", created),
        )
        log_id = int(cur.lastrowid)
        aad = f"buyer_logs:encrypted_details:{log_id}"
        encrypted = encrypt_column(json.dumps(details, ensure_ascii=False, sort_keys=True).encode("utf-8"), key, aad)
        conn.execute("UPDATE buyer_logs SET encrypted_details=? WHERE id=?", (encrypted, log_id))
        return log_id


def list_buyer_logs(buyer_id: int, db_path=None) -> list[dict[str, Any]]:
    import json
    key = get_key("UNDERGRID_DB_KEY")
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM buyer_logs WHERE buyer_id=? ORDER BY created_at DESC LIMIT 50", (buyer_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        plain = decrypt_column(item["encrypted_details"], key, f"buyer_logs:encrypted_details:{item['id']}")
        item["details"] = json.loads(plain.decode("utf-8"))
        del item["encrypted_details"]
        result.append(item)
    return result


def insert_block(block: dict[str, Any], db_path=None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO blockchain_blocks(block_index,timestamp,event_type,payload_json,previous_hash,current_hash) VALUES(?,?,?,?,?,?)",
            (block["index"], block["timestamp"], block["event_type"], block["payload_json"], block["previous_hash"], block["current_hash"]),
        )


def get_blocks(db_path=None) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT block_index AS 'index',timestamp,event_type,payload_json,previous_hash,current_hash FROM blockchain_blocks ORDER BY block_index ASC").fetchall()
        return [dict(row) for row in rows]


def product_count(db_path=None) -> int:
    with get_connection(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM products WHERE status='available'").fetchone()[0])
