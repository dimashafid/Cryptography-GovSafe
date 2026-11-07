"""Provision akun GOVSAFE melalui CLI; registrasi publik tidak tersedia."""
import getpass
from auth.password_auth import create_buyer_account
from database.db_manager import init_db
from database.govsafe_schema import ensure_govsafe_schema
from services.govsafe_service import set_user_role

if __name__ == "__main__":
    init_db()
    ensure_govsafe_schema()
    username = input("Username akun GOVSAFE: ").strip().lower()
    display_name = input("Nama tampilan: ").strip() or username
    role = input("Peran [pemohon/petugas] (default pemohon): ").strip().lower() or "pemohon"
    if role not in ("pemohon", "petugas"):
        raise SystemExit("Peran tidak valid. Pilih pemohon atau petugas.")
    password = getpass.getpass("Password (minimal 10 karakter): ")
    confirm = getpass.getpass("Ulangi password: ")
    if password != confirm:
        raise SystemExit("Password tidak sama.")
    user_id = create_buyer_account(username, password)
    set_user_role(user_id, role, display_name)
    print(f"Akun GOVSAFE berhasil dibuat. ID: {user_id}; Peran: {role}.")
    print("Lanjutkan provisioning USB dongle dan template biometrik menggunakan username akun.")
