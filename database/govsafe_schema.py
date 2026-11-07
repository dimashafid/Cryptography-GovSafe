"""Skema tambahan GOVSAFE dan migrasi aman dari tabel Buyer UnderGrid."""
from database.db_manager import get_connection


def ensure_govsafe_schema(db_path=None) -> None:
    """Tambahkan role serta tabel aset, permohonan, dan pesan tanpa menghapus data lama."""
    with get_connection(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(buyers)").fetchall()}
        if "role" not in columns:
            conn.execute("ALTER TABLE buyers ADD COLUMN role TEXT NOT NULL DEFAULT 'pemohon'")
        if "display_name" not in columns:
            conn.execute("ALTER TABLE buyers ADD COLUMN display_name TEXT")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS govsafe_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_code TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            legal_status TEXT NOT NULL,
            access_level TEXT NOT NULL DEFAULT 'Terbatas',
            asset_status TEXT NOT NULL DEFAULT 'Aktif',
            encrypted_name BLOB NOT NULL,
            encrypted_description BLOB NOT NULL,
            encrypted_condition BLOB NOT NULL,
            encrypted_storage_location BLOB NOT NULL,
            encrypted_image_path BLOB NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (created_by) REFERENCES buyers(id)
        );
        CREATE TABLE IF NOT EXISTS govsafe_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_code TEXT NOT NULL UNIQUE,
            asset_id INTEGER NOT NULL,
            applicant_id INTEGER NOT NULL,
            assigned_officer_id INTEGER,
            request_type TEXT NOT NULL,
            request_status TEXT NOT NULL DEFAULT 'Menunggu',
            encrypted_subject BLOB NOT NULL,
            encrypted_details BLOB NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (asset_id) REFERENCES govsafe_assets(id),
            FOREIGN KEY (applicant_id) REFERENCES buyers(id),
            FOREIGN KEY (assigned_officer_id) REFERENCES buyers(id)
        );
        CREATE TABLE IF NOT EXISTS govsafe_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            encrypted_message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (request_id) REFERENCES govsafe_requests(id),
            FOREIGN KEY (sender_id) REFERENCES buyers(id),
            FOREIGN KEY (recipient_id) REFERENCES buyers(id)
        );
        CREATE INDEX IF NOT EXISTS idx_govsafe_assets_status ON govsafe_assets(asset_status, created_at);
        CREATE INDEX IF NOT EXISTS idx_govsafe_requests_applicant ON govsafe_requests(applicant_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_govsafe_requests_officer ON govsafe_requests(assigned_officer_id, request_status);
        CREATE INDEX IF NOT EXISTS idx_govsafe_messages_request ON govsafe_messages(request_id, created_at);
        """)

        # Akun lama tetap dapat login dan dimigrasikan menjadi Pemohon.
        conn.execute("UPDATE buyers SET role='pemohon' WHERE role IS NULL OR role NOT IN ('pemohon','petugas')")
