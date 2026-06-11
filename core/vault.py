import json

from core.crypto import encrypt_data, decrypt_data
from core.storage import save_vault, load_vault

def vault_init(username: str, password: str):
    from core.crypto import generate_salt, derive_key
    from core.storage import save_meta
    import hashlib

    salt = generate_salt()
    key = derive_key(password, salt)

    save_meta({
        "username": username,
        "salt": salt.hex(),
        "vault_hash": hashlib.sha256(key).hexdigest()
    })

    empty_vault = json.dumps([])
    save_vault(encrypt_data(empty_vault, key))

def vault_change_password(username: str, password: str):
    from core.crypto import generate_salt, derive_key
    from core.storage import save_meta
    import hashlib

    salt = generate_salt()
    key = derive_key(password, salt)

    save_meta({
        "username": username,
        "salt": salt.hex(),
        "vault_hash": hashlib.sha256(key).hexdigest()
    })

    empty_vault = json.dumps([])
    save_vault(encrypt_data(empty_vault, key))

def vault_login(username: str, password: str) -> bytes | None:
    from core.crypto import derive_key
    from core.storage import load_meta
    from models.user import User
    import hashlib

    data = load_meta()
    user = User(**data)
    salt_bytes = bytes.fromhex(user.salt)

    key = derive_key(password, salt_bytes)
    entered_hash = hashlib.sha256(key).hexdigest()

    if entered_hash != user.vault_hash:
        return None

    print(f"✓ Logged in as {username}")
    return key

def vault_read(key: bytes) -> list:
    raw = load_vault()
    if not raw:
        return []
    decrypted = decrypt_data(raw, key)
    return json.loads(decrypted)

def vault_write(entries: list, key: bytes):
    data = json.dumps(entries)
    save_vault(encrypt_data(data, key))
