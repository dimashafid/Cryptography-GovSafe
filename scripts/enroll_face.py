"""Daftarkan biometrik Buyer dari satu foto referensi lokal."""
import argparse
from pathlib import Path
from auth.biometric_auth import enroll_face, encrypt_face_template
from database.db_manager import get_buyer_by_username, update_buyer_face, add_log
from database.db_manager import init_db

parser = argparse.ArgumentParser(description="Enroll Buyer face template")
parser.add_argument("username")
parser.add_argument("image_path", type=Path)
args = parser.parse_args()
init_db()
buyer = get_buyer_by_username(args.username.strip().lower())
if not buyer:
    raise SystemExit("Buyer tidak ditemukan.")
encoding = enroll_face(args.image_path.read_bytes())
encrypted = encrypt_face_template(encoding, buyer["id"])
update_buyer_face(buyer["id"], encrypted)
add_log(buyer["id"], "BIOMETRIC_ENROLLED", {"template_encrypted": True})
print("Template biometrik berhasil dienkripsi dan disimpan. Foto sumber tidak disalin.")
