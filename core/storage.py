# storage/db.py
import json
from pathlib import Path

# VAULT_DIR = Path.home() / ".password_manager"
VAULT_DIR = Path.cwd() / ".password_manager"
VAULT_FILE = VAULT_DIR / "vault.enc"
META_FILE = VAULT_DIR / "meta.json"

def save_meta(data: dict):
    VAULT_DIR.mkdir(exist_ok=True)
    META_FILE.write_text(json.dumps(data))

def load_meta() -> dict:
    if not META_FILE.exists():
        raise FileNotFoundError("Vault not initialized. Run: pm usr init")
    return json.loads(META_FILE.read_text())

def save_vault(encrypted_data: bytes):
    VAULT_FILE.write_bytes(encrypted_data)

def load_vault() -> bytes:
    if not VAULT_FILE.exists():
        return b""
    return VAULT_FILE.read_bytes()
