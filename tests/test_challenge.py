from auth.cryptographic_challenge import generate_challenge, verify_challenge, vigenere_decrypt_challenge

def test_random_challenges_and_single_use():
    first = generate_challenge()
    second = generate_challenge()
    assert first["id"] != second["id"]
    assert first["ciphertext"] != second["ciphertext"] or first["key"] != second["key"]
    assert vigenere_decrypt_challenge(first["ciphertext"], first["key"]) == first["answer"]
    assert verify_challenge(first, first["answer"])
    assert not verify_challenge(first, first["answer"])

def test_wrong_answer_consumes_challenge():
    challenge = generate_challenge()
    assert not verify_challenge(challenge, "WRONGANSWER")
    assert challenge["used"] is True
