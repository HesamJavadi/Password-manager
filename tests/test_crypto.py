from core.crypto import decrypt_data, derive_key, encrypt_data, generate_salt


def test_derive_key_is_deterministic():
    salt = generate_salt()
    key1 = derive_key("test-password", salt)
    key2 = derive_key("test-password", salt)
    assert key1 == key2


def test_derive_key_differs_with_different_salts():
    key1 = derive_key("test-password", generate_salt())
    key2 = derive_key("test-password", generate_salt())
    assert key1 != key2


def test_encrypt_decrypt_round_trip():
    salt = generate_salt()
    key = derive_key("master", salt)
    plaintext = '{"entries": []}'
    token = encrypt_data(plaintext, key)
    assert decrypt_data(token, key) == plaintext


def test_salt_uniqueness():
    salts = {generate_salt() for _ in range(10)}
    assert len(salts) == 10
