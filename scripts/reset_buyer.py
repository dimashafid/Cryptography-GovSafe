"""Reset password Buyer secara interaktif tanpa mencatat password ke log."""
import getpass
import sys
from auth.password_auth import hash_password
from database.db_manager import get_buyer_by_username, update_buyer_password

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Penggunaan: python -m scripts.reset_buyer <username>")
    buyer = get_buyer_by_username(sys.argv[1].strip().lower())
    if not buyer:
        raise SystemExit("Buyer tidak ditemukan.")
    password = getpass.getpass("Password baru (minimal 10 karakter): ")
    confirm = getpass.getpass("Ulangi password baru: ")
    if password != confirm:
        raise SystemExit("Password tidak sama.")
    update_buyer_password(buyer["id"], hash_password(password))
    print("Password Buyer berhasil direset.")
