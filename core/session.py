import tempfile
import os
from pathlib import Path

SESSION_FILE = Path(tempfile.gettempdir()) / ".pm_session"


def save_session(key: bytes):
    SESSION_FILE.write_bytes(key)
    SESSION_FILE.chmod(0o600)  # فقط owner بخونه

def load_session() -> bytes:
    if not SESSION_FILE.exists():
        raise PermissionError("Not logged in. Run: pm usr login")
    return SESSION_FILE.read_bytes()

def clear_session():
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
