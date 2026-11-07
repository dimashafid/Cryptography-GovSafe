"""LSB steganography untuk PNG; menyembunyikan JSON, bukan mengenkripsinya."""
from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from PIL import Image
import numpy as np

MAGIC = b"UGLS"
VERSION = 1
HEADER_SIZE = 4 + 1 + 4 + 32


def _payload(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def calculate_capacity(image: Image.Image | bytes | str | Path) -> int:
    """Kapasitas maksimum payload JSON dalam byte setelah overhead header."""
    if isinstance(image, Image.Image):
        img = image
    elif isinstance(image, bytes):
        img = Image.open(BytesIO(image))
    else:
        img = Image.open(image)
    width, height = img.size
    return max(0, (width * height * 3) // 8 - HEADER_SIZE)


def encode_message(image_bytes: bytes, message: object) -> bytes:
    """Sisipkan pesan JSON pada bit paling rendah kanal RGB gambar PNG."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("Gambar sumber tidak dapat dibaca.") from exc
    data = _payload(message)
    header = MAGIC + bytes([VERSION]) + len(data).to_bytes(4, "big") + hashlib.sha256(data).digest()
    packet = header + data
    capacity = (image.width * image.height * 3) // 8
    if len(packet) > capacity:
        raise ValueError(f"Pesan melebihi kapasitas gambar ({len(data)} byte; kapasitas {max(0, capacity-HEADER_SIZE)} byte).")
    bits = np.unpackbits(np.frombuffer(packet, dtype=np.uint8), bitorder="big")
    pixels = np.asarray(image, dtype=np.uint8).copy().reshape(-1)
    pixels[:len(bits)] = (pixels[:len(bits)] & 0xFE) | bits
    output = Image.fromarray(pixels.reshape(image.height, image.width, 3), mode="RGB")
    buffer = BytesIO()
    output.save(buffer, format="PNG")
    return buffer.getvalue()


def decode_message(image_bytes: bytes) -> object:
    """Ekstrak dan validasi header, panjang, checksum, serta JSON payload."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        flat = np.asarray(image, dtype=np.uint8).reshape(-1)
        header_bits = flat[:HEADER_SIZE * 8] & 1
        header = np.packbits(header_bits, bitorder="big").tobytes()
        if header[:4] != MAGIC or header[4] != VERSION:
            raise ValueError("Magic header steganografi tidak ditemukan.")
        length = int.from_bytes(header[5:9], "big")
        if length <= 0 or HEADER_SIZE + length > flat.size // 8:
            raise ValueError("Panjang payload steganografi tidak valid.")
        payload_bits = flat[:(HEADER_SIZE + length) * 8] & 1
        packet = np.packbits(payload_bits, bitorder="big").tobytes()
        payload = packet[HEADER_SIZE:HEADER_SIZE + length]
        if not hashlib.sha256(payload).digest() == header[9:41]:
            raise ValueError("Checksum payload steganografi tidak cocok.")
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise
    except Exception as exc:
        raise ValueError("Gambar steganografi tidak valid atau rusak.") from exc


def embed_secret_data(image_path: str | Path, message: object) -> bytes:
    """Helper path untuk proses import katalog; hasil PNG dikembalikan di RAM."""
    return encode_message(Path(image_path).read_bytes(), message)


def extract_secret_data(image_bytes: bytes) -> object:
    """Alias eksplisit untuk ekstraksi metadata tersembunyi."""
    return decode_message(image_bytes)
