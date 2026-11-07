from auth.password_auth import hash_password, verify_password

def test_argon2id_hash_is_salted():
    a = hash_password("correct-horse-battery")
    b = hash_password("correct-horse-battery")
    assert a != b
    assert "$argon2id$" in a

def test_password_verification():
    hashed = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password", hashed)
