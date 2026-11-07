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


def decode_message_trace(image_bytes: bytes, preview_limit: int = 256) -> dict:
    """Ekstrak LSB sekaligus mengembalikan jejak setiap tahap untuk demonstrasi."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        raise ValueError("File tidak dapat dibaca sebagai gambar.") from exc

    flat = np.asarray(image, dtype=np.uint8).reshape(-1)
    result = {
        "image": {
            "width": image.width,
            "height": image.height,
            "channels": 3,
            "channel_order": "RGB",
            "pixel_channel_count": int(flat.size),
            "maximum_extractable_bytes": int(flat.size // 8),
        },
        "bit_order": "MSB-first per byte; kanal RGB berurutan, baris demi baris",
        "header": {},
        "payload": {},
        "metadata": None,
        "stages": [],
        "success": False,
        "error": None,
    }

    result["stages"].append({
        "name": "Membaca gambar",
        "status": "success",
        "detail": f"PNG dikonversi ke RGB: {image.width} × {image.height} piksel, {flat.size} nilai kanal.",
    })

    header_bit_count = HEADER_SIZE * 8
    if flat.size < header_bit_count:
        result["error"] = "Gambar terlalu kecil untuk memuat header steganografi GOVSAFE."
        result["stages"].append({"name": "Membaca header", "status": "failed", "detail": result["error"]})
        return result

    header_bits_array = flat[:header_bit_count] & 1
    header_bytes = np.packbits(header_bits_array, bitorder="big").tobytes()
    header_bits = "".join(str(int(bit)) for bit in header_bits_array)
    magic = header_bytes[:4]
    version = header_bytes[4]
    payload_length = int.from_bytes(header_bytes[5:9], "big")
    expected_digest = header_bytes[9:41]

    result["header"] = {
        "bit_count": header_bit_count,
        "bits": header_bits,
        "bytes_hex": header_bytes.hex(" "),
        "magic_hex": magic.hex(),
        "magic_text": magic.decode("ascii", errors="replace"),
        "version": version,
        "payload_length": payload_length,
        "sha256_expected": expected_digest.hex(),
    }
    result["stages"].append({
        "name": "Ekstraksi bit LSB",
        "status": "success",
        "detail": f"{header_bit_count} bit pertama dibaca dari kanal RGB. Delapan bit digabungkan menjadi satu byte dengan urutan MSB-first.",
    })

    if magic != MAGIC:
        result["error"] = "Magic header UGLS tidak ditemukan. Gambar bukan format LSB GOVSAFE yang digunakan decoder ini."
        result["stages"].append({"name": "Identifikasi header", "status": "failed", "detail": result["error"]})
        return result
    if version != VERSION:
        result["error"] = f"Versi format tidak didukung: {version}. Versi yang didukung: {VERSION}."
        result["stages"].append({"name": "Validasi versi", "status": "failed", "detail": result["error"]})
        return result
    if payload_length <= 0 or HEADER_SIZE + payload_length > flat.size // 8:
        result["error"] = "Panjang payload tidak valid atau melebihi kapasitas gambar."
        result["stages"].append({"name": "Validasi panjang payload", "status": "failed", "detail": result["error"]})
        return result

    result["stages"].append({
        "name": "Validasi header",
        "status": "success",
        "detail": f"Magic {magic.decode('ascii')}, versi {version}, panjang payload {payload_length} byte.",
    })

    packet_bit_count = (HEADER_SIZE + payload_length) * 8
    packet_bits = flat[:packet_bit_count] & 1
    packet = np.packbits(packet_bits, bitorder="big").tobytes()
    payload = packet[HEADER_SIZE:HEADER_SIZE + payload_length]
    payload_text = None
    utf8_valid = True
    try:
        payload_text = payload.decode("utf-8")
        utf8_status = "success"
        utf8_detail = f"Payload berhasil dikonversi menjadi teks UTF-8 ({len(payload_text)} karakter)."
    except UnicodeDecodeError as exc:
        utf8_valid = False
        utf8_status = "failed"
        utf8_detail = f"Payload bukan UTF-8 yang valid: {exc}."

    digest_actual = hashlib.sha256(payload).digest()
    checksum_valid = digest_actual == expected_digest
    result["payload"] = {
        "byte_count": len(payload),
        "bytes_hex": payload[:preview_limit].hex(" "),
        "bytes_preview_truncated": len(payload) > preview_limit,
        "bytes_preview_limit": preview_limit,
        "utf8_text": payload_text,
        "utf8_valid": utf8_valid,
        "sha256_actual": digest_actual.hex(),
        "checksum_valid": checksum_valid,
    }
    result["stages"].append({
        "name": "Rekonstruksi byte",
        "status": "success",
        "detail": f"{payload_length} byte payload dipisahkan dari header. Pratinjau heksadesimal menampilkan maksimal {preview_limit} byte.",
    })
    result["stages"].append({
        "name": "Dekode UTF-8",
        "status": utf8_status,
        "detail": utf8_detail,
    })
    result["stages"].append({
        "name": "Verifikasi SHA-256",
        "status": "success" if checksum_valid else "failed",
        "detail": "Hash payload cocok dengan hash pada header." if checksum_valid else "Hash payload berbeda dari hash pada header; data mungkin berubah atau rusak.",
    })

    if not utf8_valid:
        result["error"] = "Payload tidak dapat dibaca sebagai UTF-8."
        return result

    try:
        metadata = json.loads(payload_text)
        json_valid = True
        json_detail = "Struktur JSON valid dan berhasil diparsing."
    except json.JSONDecodeError as exc:
        metadata = None
        json_valid = False
        json_detail = f"JSON tidak valid pada baris {exc.lineno}, kolom {exc.colno}: {exc.msg}."

    result["payload"]["json_valid"] = json_valid
    result["metadata"] = metadata
    result["stages"].append({
        "name": "Validasi dan parsing JSON",
        "status": "success" if json_valid else "failed",
        "detail": json_detail,
    })

    result["success"] = bool(checksum_valid and json_valid)
    if not checksum_valid:
        result["error"] = "JSON dapat dibaca, tetapi checksum SHA-256 tidak cocok. Metadata tidak dinyatakan valid."
    elif not json_valid:
        result["error"] = "Payload UTF-8 berhasil dibaca, tetapi isinya bukan JSON yang valid."
    return result


def decode_message(image_bytes: bytes) -> object:
    """Ekstrak dan validasi header, panjang, checksum, serta JSON payload."""
    trace = decode_message_trace(image_bytes)
    if not trace["success"]:
        raise ValueError(trace["error"] or "Gambar steganografi tidak valid atau rusak.")
    return trace["metadata"]


def embed_secret_data(image_path: str | Path, message: object) -> bytes:
    """Helper path untuk proses import katalog; hasil PNG dikembalikan di RAM."""
    return encode_message(Path(image_path).read_bytes(), message)


def extract_secret_data(image_bytes: bytes) -> object:
    """Alias eksplisit untuk ekstraksi metadata tersembunyi."""
    return decode_message(image_bytes)
