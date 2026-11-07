"""Layanan pesan Buyer; isi database selalu ciphertext super encryption."""
from __future__ import annotations
from crypto.vigenere_aes import encrypt_message, decrypt_message
from database import db_manager


def send_message(buyer_id: int, message: str, recipient: str = "Admin/Pengelola", db_path=None) -> int:
    if not message or not message.strip():
        raise ValueError("Pesan tidak boleh kosong.")
    ciphertext = encrypt_message(message)
    message_id = db_manager.add_message(buyer_id, recipient, ciphertext, db_path)
    db_manager.add_log(buyer_id, "MESSAGE_SENT", {"message_id": message_id}, str(message_id), db_path)
    return message_id


def get_buyer_messages(buyer_id: int, db_path=None) -> list[dict]:
    return db_manager.list_messages(buyer_id, db_path)


def decrypt_for_admin(ciphertext: str) -> str:
    """Dekripsi dilakukan hanya oleh skrip eksternal dengan akses kunci."""
    return decrypt_message(ciphertext)


def export_all_messages(db_path=None) -> list[dict]:
    """Ambil dan dekripsi seluruh pesan untuk penggunaan CLI admin."""
    messages = db_manager.list_messages(None, db_path)
    for item in messages:
        item["plaintext"] = decrypt_for_admin(item["encrypted_message"])
    return messages
