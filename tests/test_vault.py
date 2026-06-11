from core.vault import (
    vault_change_password,
    vault_init,
    vault_login,
    vault_read,
    vault_write,
)
from models.PasswordEntry import PasswordEntry


def test_vault_init_and_login(isolated_vault):
    vault_init("alice", "secret123")
    key = vault_login("alice", "secret123")
    assert key is not None
    assert vault_read(key) == []


def test_vault_login_invalid_password(isolated_vault):
    vault_init("alice", "secret123")
    assert vault_login("alice", "wrong") is None


def test_vault_login_wrong_username(isolated_vault):
    vault_init("alice", "secret123")
    assert vault_login("bob", "secret123") is None


def test_vault_change_password_preserves_entries(isolated_vault):
    key = vault_init("alice", "old-pass")
    entry = PasswordEntry(title="gmail", username="alice", password="pw1")
    vault_write([entry.to_dict()], key)

    new_key = vault_change_password(key, "new-pass", "alice")
    entries = vault_read(new_key)

    assert len(entries) == 1
    assert entries[0]["title"] == "gmail"
    assert entries[0]["password"] == "pw1"
    assert vault_login("alice", "new-pass") is not None
    assert vault_login("alice", "old-pass") is None
