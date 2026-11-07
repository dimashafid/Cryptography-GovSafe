"""Import katalog legal/fiktif dari CSV, dengan LSB dan enkripsi file."""
import argparse
from services.catalog_service import import_catalog_csv
from database.db_manager import init_db
from blockchain.blockchain import create_genesis_block

parser = argparse.ArgumentParser(description="Import Undergrid catalog CSV")
parser.add_argument("csv_path")
args = parser.parse_args()
init_db()
create_genesis_block()
count = import_catalog_csv(args.csv_path)
print(f"Import selesai: {count} produk.")
