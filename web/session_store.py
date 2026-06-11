import secrets
import time
from dataclasses import dataclass

SESSION_TIMEOUT_SECONDS = 30 * 60
SESSION_COOKIE_NAME = "pm_session"
CSRF_HEADER = "X-CSRF-Token"


@dataclass
class WebSession:
    key: bytes
    created_at: float
    csrf_token: str


_sessions: dict[str, WebSession] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [
        sid for sid, session in _sessions.items()
        if now - session.created_at > SESSION_TIMEOUT_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]


def create_session(key: bytes) -> tuple[str, str]:
    _purge_expired()
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    _sessions[session_id] = WebSession(
        key=key,
        created_at=time.time(),
        csrf_token=csrf_token,
    )
    return session_id, csrf_token


def get_session(session_id: str | None) -> WebSession | None:
    if not session_id:
        return None
    _purge_expired()
    session = _sessions.get(session_id)
    if session is None:
        return None
    if time.time() - session.created_at > SESSION_TIMEOUT_SECONDS:
        del _sessions[session_id]
        return None
    return session


def destroy_session(session_id: str | None) -> None:
    if session_id and session_id in _sessions:
        del _sessions[session_id]


def clear_all_sessions() -> None:
    _sessions.clear()


def session_info(session_id: str | None) -> dict | None:
    session = get_session(session_id)
    if session is None:
        return None
    age_seconds = int(time.time() - session.created_at)
    return {
        "created_at": session.created_at,
        "age_seconds": age_seconds,
        "expired": False,
        "timeout_seconds": SESSION_TIMEOUT_SECONDS,
    }


def verify_csrf(session: WebSession, token: str | None) -> bool:
    if not token:
        return False
    return secrets.compare_digest(session.csrf_token, token)
