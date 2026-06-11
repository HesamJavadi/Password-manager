import core.storage as storage


def test_atomic_write_meta(isolated_vault):
    storage.save_meta({"username": "alice", "salt": "abc", "vault_hash": "def"})
    data = storage.load_meta()
    assert data["username"] == "alice"
    assert storage.META_FILE.exists()


def test_atomic_write_vault(isolated_vault):
    storage.save_vault(b"encrypted-bytes")
    assert storage.load_vault() == b"encrypted-bytes"


def test_load_meta_missing_raises(isolated_vault):
    import pytest

    with pytest.raises(FileNotFoundError):
        storage.load_meta()
