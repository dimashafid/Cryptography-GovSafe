"""Face recognition untuk verifikasi Buyer; tidak memiliki liveness detection."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Sequence
from crypto.db_crypto import encrypt_column, decrypt_column
from crypto.key_manager import get_key
from config import FACE_THRESHOLD


def extract_face_encoding(image_bytes: bytes) -> list[float]:
    """Ekstrak satu face encoding; menolak nol atau lebih dari satu wajah."""
    try:
        import face_recognition
        image = face_recognition.load_image_file(BytesIO(image_bytes))
        # Batasi sisi terpanjang menjadi 640 px agar ekstraksi HOG lebih ringan.
        # Gambar tidak diperbesar; threshold pencocokan tetap menggunakan konfigurasi.
        if max(image.shape[:2]) > 640:
            import numpy as np
            from PIL import Image

            resized = Image.fromarray(image)
            resized.thumbnail((640, 640), Image.Resampling.LANCZOS)
            image = np.asarray(resized)

        locations = face_recognition.face_locations(image, model="hog")
        if len(locations) != 1:
            raise ValueError("Gambar harus memuat tepat satu wajah.")
        encodings = face_recognition.face_encodings(image, known_face_locations=locations)
        if len(encodings) != 1:
            raise ValueError("Encoding wajah gagal dibuat.")
        return [float(value) for value in encodings[0]]
    except ImportError as exc:
        raise RuntimeError("face_recognition/dlib belum terpasang pada environment.") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Gambar wajah gagal diproses.") from exc


def enroll_face(image_bytes: bytes) -> list[float]:
    """API pendaftaran wajah; hasilnya harus dienkripsi sebelum disimpan."""
    return extract_face_encoding(image_bytes)


def encrypt_face_template(encoding: Sequence[float], buyer_id: int) -> bytes:
    """Serialisasi lalu enkripsi template wajah dengan AAD per Buyer."""
    payload = json.dumps(list(encoding), separators=(",", ":")).encode("utf-8")
    return encrypt_column(payload, get_key("UNDERGRID_DB_KEY"), f"buyers:face_encoding_enc:{buyer_id}")


def load_encrypted_face_template(encrypted: bytes, buyer_id: int) -> list[float]:
    """Muat template dari ciphertext database."""
    raw = decrypt_column(encrypted, get_key("UNDERGRID_DB_KEY"), f"buyers:face_encoding_enc:{buyer_id}")
    return [float(value) for value in json.loads(raw.decode("utf-8"))]


def verify_face(image_bytes: bytes, known_encoding: Sequence[float], threshold: float | None = None) -> bool:
    """Bandingkan encoding langsung dari webcam dengan template referensi."""
    import numpy as np
    try:
        import face_recognition
    except ImportError as exc:
        raise RuntimeError("face_recognition/dlib belum terpasang.") from exc
    candidate = np.asarray(extract_face_encoding(image_bytes), dtype=float)
    known = np.asarray(known_encoding, dtype=float)
    if candidate.shape != known.shape:
        return False
    distance = float(face_recognition.face_distance([known], candidate)[0])
    return distance <= (FACE_THRESHOLD if threshold is None else threshold)
