from io import BytesIO
from PIL import Image
import pytest
from crypto.steganography import encode_message, decode_message, calculate_capacity

def png_bytes(size=(160,160)):
    buffer = BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()

def test_lsb_round_trip():
    original = png_bytes()
    message = {"sku":"UG-001", "secret":"internal metadata"}
    encoded = encode_message(original, message)
    assert decode_message(encoded) == message
    assert calculate_capacity(original) > 0

def test_rejects_payload_over_capacity():
    with pytest.raises(ValueError):
        encode_message(png_bytes((8,8)), {"secret":"x" * 100})

def test_rejects_plain_png_without_header():
    with pytest.raises(ValueError):
        decode_message(png_bytes())
