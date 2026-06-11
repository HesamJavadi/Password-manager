import hashlib
import json
import secrets

from core.crypto import decrypt_data, derive_key, encrypt_data, generate_salt
from core.storage import load_meta, load_vault, save_meta, save_vault
from models.user import User


def vault_init(username: str, password: str) -> bytes:
    salt = generate_salt()
    key = derive_key(password, salt)

    save_meta({
        "username": username,
        "salt": salt.hex(),
        "vault_hash": hashlib.sha256(key).hexdigest(),
    })

    empty_vault = json.dumps([])
    save_vault(encrypt_data(empty_vault, key))
    return key


def vault_change_password(old_key: bytes, new_password: str, username: str) -> bytes:
    entries = vault_read(old_key)
    salt = generate_salt()
    new_key = derive_key(new_password, salt)

    save_meta({
        "username": username,
        "salt": salt.hex(),
        "vault_hash": hashlib.sha256(new_key).hexdigest(),
    })
    vault_write(entries, new_key)
    return new_key


def vault_login(username: str, password: str) -> bytes | None:
    data = load_meta()
    user = User(**data)

    if user.username != username:
        return None

    salt_bytes = bytes.fromhex(user.salt)
    key = derive_key(password, salt_bytes)
    entered_hash = hashlib.sha256(key).hexdigest()

    if not secrets.compare_digest(entered_hash, user.vault_hash):
        return None

    return key


def vault_read(key: bytes) -> list:
    raw = load_vault()
    if not raw:
        return []
    decrypted = decrypt_data(raw, key)
    return json.loads(decrypted)


def vault_write(entries: list, key: bytes) -> None:
    data = json.dumps(entries)
    save_vault(encrypt_data(data, key))
