from auth.biometric_auth import encrypt_face_template, load_encrypted_face_template

def test_face_template_is_encrypted_and_round_trips():
    encoding = [0.123, -0.456, 0.789]
    encrypted = encrypt_face_template(encoding, 42)
    assert b"0.123" not in encrypted
    assert load_encrypted_face_template(encrypted, 42) == encoding
