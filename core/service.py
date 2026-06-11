import json
import secrets
import string
import threading
from datetime import datetime

from cryptography.fernet import InvalidToken

from core.storage import VAULT_DIR
from core.vault import (
    vault_change_password,
    vault_init,
    vault_login,
    vault_read,
    vault_write,
)
from models.PasswordEntry import PasswordEntry

_vault_lock = threading.Lock()


class VaultError(Exception):
    pass


class VaultNotFoundError(VaultError):
    pass


class VaultExistsError(VaultError):
    pass


class EntryNotFoundError(VaultError):
    pass


class EntryExistsError(VaultError):
    pass


class InvalidCredentialsError(VaultError):
    pass


class VaultCorruptedError(VaultError):
    pass


def find_entry(entries: list, name: str) -> dict | None:
    for entry in entries:
        if entry["title"].lower() == name.lower():
            return entry
    return None


def read_vault(key: bytes) -> list:
    try:
        return vault_read(key)
    except InvalidToken:
        raise VaultCorruptedError("Vault corrupted or invalid key")
    except json.JSONDecodeError:
        raise VaultCorruptedError("Vault data is corrupted")


def init_vault(username: str, password: str) -> bytes:
    if VAULT_DIR.exists():
        raise VaultExistsError("Vault already exists")
    return vault_init(username, password)


def login(username: str, password: str) -> bytes:
    if not VAULT_DIR.exists():
        raise VaultNotFoundError("Vault not found")
    key = vault_login(username, password)
    if key is None:
        raise InvalidCredentialsError("Invalid credentials")
    return key


def change_master_password(old_key: bytes, new_password: str, username: str) -> bytes:
    with _vault_lock:
        return vault_change_password(old_key, new_password, username)


def list_entries(key: bytes) -> list[dict]:
    with _vault_lock:
        return read_vault(key)


def get_entry(key: bytes, title: str) -> dict:
    with _vault_lock:
        entries = read_vault(key)
    entry = find_entry(entries, title)
    if entry is None:
        raise EntryNotFoundError(f"Entry '{title}' not found")
    return entry


def add_entry(key: bytes, entry: PasswordEntry) -> dict:
    with _vault_lock:
        entries = read_vault(key)
        if find_entry(entries, entry.title):
            raise EntryExistsError(f"Entry '{entry.title}' already exists")
        entry_dict = entry.to_dict()
        entries.append(entry_dict)
        vault_write(entries, key)
        return entry_dict


def update_entry(key: bytes, title: str, **fields) -> dict:
    with _vault_lock:
        entries = read_vault(key)
        entry = find_entry(entries, title)
        if entry is None:
            raise EntryNotFoundError(f"Entry '{title}' not found")
        for field_name, value in fields.items():
            if value is not None and field_name in entry:
                entry[field_name] = value
        entry["updated_at"] = datetime.now().isoformat()
        vault_write(entries, key)
        return entry


def update_entry_password(key: bytes, title: str, new_password: str) -> dict:
    return update_entry(key, title, password=new_password)


def delete_entry(key: bytes, title: str) -> dict:
    with _vault_lock:
        entries = read_vault(key)
        matching = [e for e in entries if e["title"].lower() == title.lower()]
        if not matching:
            raise EntryNotFoundError(f"Entry '{title}' not found")
        remaining = [e for e in entries if e["title"].lower() != title.lower()]
        vault_write(remaining, key)
        return matching[0]


def search_entries(key: bytes, query: str) -> list[dict]:
    with _vault_lock:
        entries = read_vault(key)
    q = query.lower()
    return [
        entry for entry in entries
        if q in entry["title"].lower()
        or q in entry.get("username", "").lower()
        or q in entry.get("url", "").lower()
        or q in entry.get("notes", "").lower()
    ]


def generate_password(
    length: int = 16,
    symbols: bool = True,
    digits: bool = True,
) -> str:
    if length <= 0:
        raise ValueError("Length must be greater than 0")
    chars = string.ascii_letters
    if digits:
        chars += string.digits
    if symbols:
        chars += string.punctuation
    if not chars:
        raise ValueError("No character set available")
    return "".join(secrets.choice(chars) for _ in range(length))
