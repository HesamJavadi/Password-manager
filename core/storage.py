import json
import os
from pathlib import Path

_DEFAULT_VAULT_DIR = Path.home() / ".password_manager"
VAULT_DIR = Path(os.environ.get("PM_VAULT_DIR", _DEFAULT_VAULT_DIR))
VAULT_FILE = VAULT_DIR / "vault.enc"
META_FILE = VAULT_DIR / "meta.json"


def _restrict_permissions(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _atomic_write(path: Path, data: bytes | str, mode: str = "bytes") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if mode == "bytes":
        tmp.write_bytes(data)  # type: ignore[arg-type]
    else:
        tmp.write_text(data)  # type: ignore[arg-type]
    os.replace(tmp, path)
    _restrict_permissions(path)


def save_meta(data: dict) -> None:
    _atomic_write(META_FILE, json.dumps(data), mode="text")


def load_meta() -> dict:
    if not META_FILE.exists():
        raise FileNotFoundError("Vault not initialized. Run: pm usr init")
    return json.loads(META_FILE.read_text())


def save_vault(encrypted_data: bytes) -> None:
    _atomic_write(VAULT_FILE, encrypted_data, mode="bytes")


def load_vault() -> bytes:
    if not VAULT_FILE.exists():
        return b""
    return VAULT_FILE.read_bytes()
