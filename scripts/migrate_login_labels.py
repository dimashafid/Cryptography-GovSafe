"""Pembaruan istilah tampilan login lama tanpa mengubah modul autentikasi."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "ui" / "login_page.py"
text = path.read_text(encoding="utf-8")
replacements = {
    "Buyer terdeteksi": "Pengguna terdeteksi",
    "Buyer tidak aktif": "Akun tidak aktif",
    "Buyer belum": "Pengguna belum",
    "Buyer dari USB": "Akun dari USB",
    "USB dongle Buyer": "USB dongle akun",
    "Buyer Login": "Login GOVSAFE",
    "Password Buyer": "Password akun GOVSAFE",
    "Token USB tidak valid atau tidak cocok dengan database Buyer": "Token USB tidak valid atau tidak cocok dengan akun GOVSAFE",
    "UNDERGRID": "GOVSAFE",
}
for old, new in replacements.items():
    text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Label login telah disesuaikan ke GOVSAFE. Logika autentikasi tidak diubah.")
