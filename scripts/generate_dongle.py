"""Provision USB dongle dan simpan hanya digest token pada SQLite."""
import argparse
from auth.auth_dongle import generate_dongle_key
from database.db_manager import get_buyer_by_username, update_buyer_dongle
from config import DONGLE_REQUIRE_SERIAL

parser = argparse.ArgumentParser(description="Provision Undergrid USB dongle")
parser.add_argument("username")
parser.add_argument("mount_path", help="Mount point USB, misalnya E:\\ atau /media/user/USB")
args = parser.parse_args()
record = get_buyer_by_username(args.username.strip().lower())
if not record:
    raise SystemExit("Buyer tidak ditemukan. Buat akun terlebih dahulu.")
result = generate_dongle_key(args.mount_path, username=record["username"])
if DONGLE_REQUIRE_SERIAL and not result["serial"]:
    raise SystemExit("Konfigurasi mewajibkan serial volume, tetapi serial tidak tersedia pada OS/perangkat ini.")
update_buyer_dongle(record["id"], result["token_hash"], result["serial_hash"])
print("Dongle berhasil diprovisikan. Token mentah tidak ditampilkan.")
if result["serial"] is None:
    print("Catatan: serial volume tidak tersedia pada OS ini; gunakan mode token saja.")
