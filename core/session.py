import json
import os
import time
from pathlib import Path

SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 minutes

_DEFAULT_SESSION_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "password_manager"
SESSION_DIR = Path(os.environ.get("PM_SESSION_DIR", _DEFAULT_SESSION_DIR))
SESSION_FILE = SESSION_DIR / "session"


def save_session(key: bytes) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "key": key.decode("ascii"),
        "created_at": time.time(),
    })
    tmp = SESSION_FILE.with_suffix(".tmp")
    tmp.write_text(payload)
    os.replace(tmp, SESSION_FILE)
    try:
        SESSION_FILE.chmod(0o600)
    except OSError:
        pass


def load_session() -> bytes:
    if not SESSION_FILE.exists():
        raise PermissionError("Not logged in. Run: pm usr login")

    data = json.loads(SESSION_FILE.read_text())
    created_at = data.get("created_at", 0)
    if time.time() - created_at > SESSION_TIMEOUT_SECONDS:
        clear_session()
        raise PermissionError("Session expired. Run: pm usr login")

    return data["key"].encode("ascii")


def session_info() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text())
        created_at = data.get("created_at", 0)
        age_seconds = int(time.time() - created_at)
        expired = age_seconds > SESSION_TIMEOUT_SECONDS
        return {
            "created_at": created_at,
            "age_seconds": age_seconds,
            "expired": expired,
            "timeout_seconds": SESSION_TIMEOUT_SECONDS,
        }
    except (json.JSONDecodeError, KeyError):
        return None


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
