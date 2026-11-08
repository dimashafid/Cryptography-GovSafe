from io import BytesIO

from PIL import Image
import pytest

from crypto.steganography import (
    calculate_capacity,
    decode_message,
    decode_message_trace,
    encode_message,
)


def png_bytes(size=(160, 160)):
    buffer = BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_lsb_round_trip():
    original = png_bytes()
    message = {"sku": "UG-001", "secret": "internal metadata"}
    encoded = encode_message(original, message)
    assert decode_message(encoded) == message
    assert calculate_capacity(original) > 0


def test_trace_contains_all_extraction_stages():
    message = {"asset_code": "GOV-001", "name": "Dokumen"}
    encoded = encode_message(png_bytes(), message)
    trace = decode_message_trace(encoded)

    assert trace["success"] is True
    assert trace["header"]["magic_text"] == "UGLS"
    assert trace["header"]["version"] == 1
    assert trace["payload"]["utf8_valid"] is True
    assert trace["payload"]["json_valid"] is True
    assert trace["payload"]["checksum_valid"] is True
    assert trace["metadata"] == message


def test_rejects_payload_over_capacity():
    with pytest.raises(ValueError):
        encode_message(png_bytes((8, 8)), {"secret": "x" * 100})


def test_rejects_plain_png_without_header():
    with pytest.raises(ValueError):
        decode_message(png_bytes())


def test_trace_reports_missing_header():
    trace = decode_message_trace(png_bytes())
    assert trace["success"] is False
    assert "Magic header" in trace["error"]
    assert trace["stages"][-1]["status"] == "failed"
