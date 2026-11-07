"""Aksi simulasi Buyer yang dicatat ke blockchain lokal; tanpa transaksi dana."""
from __future__ import annotations
from blockchain.blockchain import add_block
from database import db_manager


def create_purchase_intent(buyer_id: int, product_id: int, db_path=None) -> dict:
    product = db_manager.get_product(product_id, db_path)
    if not product:
        raise LookupError("Produk tidak ditemukan.")
    payload = {"buyer_id": int(buyer_id), "product_id": int(product_id), "sku": product["sku"], "simulation": True}
    block = add_block("PURCHASE_INTENT", payload, db_path)
    db_manager.add_log(buyer_id, "PURCHASE_INTENT", payload, str(product_id), db_path)
    return block


def request_information(buyer_id: int, product_id: int, db_path=None) -> dict:
    product = db_manager.get_product(product_id, db_path)
    if not product:
        raise LookupError("Produk tidak ditemukan.")
    payload = {"buyer_id": int(buyer_id), "product_id": int(product_id), "sku": product["sku"]}
    block = add_block("REQUEST_INFORMATION", payload, db_path)
    db_manager.add_log(buyer_id, "CONTACT_REQUESTED", payload, str(product_id), db_path)
    return block
