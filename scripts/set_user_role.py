"""Ubah peran akun lama menjadi Pemohon atau Petugas."""
import argparse
from database.db_manager import init_db, get_buyer_by_username
from database.govsafe_schema import ensure_govsafe_schema
from services.govsafe_service import set_user_role

parser = argparse.ArgumentParser(description="Atur peran akun GOVSAFE")
parser.add_argument("username")
parser.add_argument("role", choices=["pemohon", "petugas"])
parser.add_argument("--nama", default=None, help="Nama tampilan opsional")
args = parser.parse_args()
init_db()
ensure_govsafe_schema()
user = get_buyer_by_username(args.username.strip().lower())
if not user:
    raise SystemExit("Akun tidak ditemukan.")
set_user_role(user["id"], args.role, args.nama)
print(f"Peran akun {user['username']} berhasil diubah menjadi {args.role}.")
