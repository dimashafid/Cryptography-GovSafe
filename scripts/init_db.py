"""Inisialisasi database UnderGrid lama dan skema tambahan GOVSAFE."""
from database.db_manager import init_db
from database.govsafe_schema import ensure_govsafe_schema
from blockchain.blockchain import create_genesis_block

if __name__ == "__main__":
    init_db()
    ensure_govsafe_schema()
    create_genesis_block()
    print("Database GOVSAFE berhasil diinisialisasi.")
