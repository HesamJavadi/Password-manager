from fastapi import Cookie, Depends, Header, HTTPException

from web.session_store import CSRF_HEADER, WebSession, get_session, verify_csrf


def require_web_session(
    pm_session: str | None = Cookie(default=None),
) -> WebSession:
    session = get_session(pm_session)
    if session is None:
        raise HTTPException(status_code=401, detail="Not logged in or session expired")
    return session


def require_csrf(
    x_csrf_token: str | None = Header(default=None, alias=CSRF_HEADER),
    session: WebSession = Depends(require_web_session),
) -> WebSession:
    if not verify_csrf(session, x_csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return session
