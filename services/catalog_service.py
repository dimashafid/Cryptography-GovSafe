"""Layanan katalog dan dekripsi gambar produk secara in-memory."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from crypto.file_cipher import encrypt_bytes, decrypt_bytes
from crypto.key_manager import get_key
from crypto.steganography import embed_secret_data, extract_secret_data
from config import STORAGE_PATH
from database import db_manager


def import_catalog_csv(csv_path: str | Path, db_path=None) -> int:
    """Import data CSV; embed secret JSON ke PNG lalu enkripsi PNG menjadi .enc."""
    source = Path(csv_path)
    if not source.is_file():
        raise FileNotFoundError(f"CSV tidak ditemukan: {source}")
    file_key = get_key("UNDERGRID_FILE_KEY")
    STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    imported = 0
    with source.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {"sku", "name", "category", "description", "price", "seller_contact", "image_path"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"CSV wajib memiliki kolom: {', '.join(sorted(required))}")
        for row in reader:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", row["sku"]):
                raise ValueError("SKU hanya boleh berisi huruf, angka, titik, garis bawah, atau tanda hubung.")
            image_path = Path(row["image_path"])
            if not image_path.is_absolute():
                image_path = source.parent / image_path
            original_image = image_path.read_bytes()
            secret_metadata = {
                "sku": row["sku"],
                "internal_specifications": row.get("specifications", ""),
                "secret_note": row.get("secret_note", ""),
            }
            stego_png = embed_secret_data(image_path, secret_metadata)
            encrypted_file = encrypt_bytes(stego_png, file_key)
            encrypted_path = STORAGE_PATH / f"{row['sku']}.png.enc"
            encrypted_path.write_bytes(encrypted_file)
            db_manager.add_product({
                "sku": row["sku"],
                "category": row["category"],
                "title": row["name"],
                "description": row["description"],
                "specifications": row.get("specifications", ""),
                "seller_contact": row["seller_contact"],
                "secret_metadata": secret_metadata,
                "price_display": row["price"],
                "image_path": str(encrypted_path.resolve()),
                "status": row.get("status", "available") or "available",
            }, db_path=db_path)
            imported += 1
    return imported


def get_catalog(db_path=None) -> list[dict]:
    """Ambil daftar produk yang sudah didekripsi untuk Buyer terautentikasi."""
    return db_manager.list_products(db_path)


def get_product_detail(product_id: int, db_path=None) -> dict | None:
    """Dekripsi file produk di RAM, verifikasi tag, lalu ekstrak pesan LSB."""
    product = db_manager.get_product(product_id, db_path)
    if not product:
        return None
    encrypted_path = Path(product["image_path"])
    stego_png = decrypt_bytes(encrypted_path.read_bytes(), get_key("UNDERGRID_FILE_KEY"))
    secret = extract_secret_data(stego_png)
    product["image_bytes"] = stego_png
    product["secret_metadata"] = secret
    return product
