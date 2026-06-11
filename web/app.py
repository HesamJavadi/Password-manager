import getpass
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core import service
from core.storage import VAULT_DIR, load_meta
from models.PasswordEntry import PasswordEntry
from web.deps import require_csrf, require_web_session
from web.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    EntryCreate,
    EntryDetail,
    EntrySummary,
    EntryUpdate,
    GenerateRequest,
    GenerateResponse,
    PasswordRequest,
    StatusResponse,
)
from web.session_store import (
    SESSION_COOKIE_NAME,
    SESSION_TIMEOUT_SECONDS,
    WebSession,
    create_session,
    destroy_session,
    get_session,
    session_info,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Password Manager", docs_url=None, redoc_url=None)


def _mask_entry(entry: dict) -> EntrySummary:
    return EntrySummary(
        id=entry["id"],
        title=entry["title"],
        username=entry.get("username", ""),
        url=entry.get("url", ""),
        updated_at=entry.get("updated_at", ""),
    )


def _full_entry(entry: dict) -> EntryDetail:
    return EntryDetail(
        id=entry["id"],
        title=entry["title"],
        username=entry.get("username", ""),
        url=entry.get("url", ""),
        notes=entry.get("notes", ""),
        password=entry["password"],
        created_at=entry.get("created_at", ""),
        updated_at=entry.get("updated_at", ""),
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="strict",
        max_age=SESSION_TIMEOUT_SECONDS,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True, samesite="strict")


@app.get("/api/status", response_model=StatusResponse)
def api_status(pm_session: str | None = Cookie(default=None)):
    info = session_info(pm_session)
    logged_in = info is not None
    entry_count = None
    csrf_token = None
    username = None
    if logged_in:
        session = get_session(pm_session)
        if session:
            csrf_token = session.csrf_token
            try:
                meta = load_meta()
                username = meta.get("username")
                entry_count = len(service.list_entries(session.key))
            except (service.VaultCorruptedError, FileNotFoundError):
                logged_in = False
                csrf_token = None
    return StatusResponse(
        vault_exists=VAULT_DIR.exists(),
        logged_in=logged_in,
        entry_count=entry_count,
        session_age_seconds=info["age_seconds"] if info else None,
        session_timeout_seconds=info["timeout_seconds"] if info else None,
        csrf_token=csrf_token,
        username=username,
    )


@app.post("/api/init", response_model=AuthResponse)
def api_init(body: PasswordRequest, response: Response):
    if VAULT_DIR.exists():
        raise HTTPException(status_code=409, detail="Vault already exists")
    username = getpass.getuser()
    try:
        key = service.init_vault(username, body.password)
    except service.VaultExistsError:
        raise HTTPException(status_code=409, detail="Vault already exists")
    session_id, csrf_token = create_session(key)
    _set_session_cookie(response, session_id)
    return AuthResponse(csrf_token=csrf_token, username=username)


@app.post("/api/login", response_model=AuthResponse)
def api_login(body: PasswordRequest, response: Response):
    if not VAULT_DIR.exists():
        raise HTTPException(status_code=404, detail="Vault not found")
    username = getpass.getuser()
    try:
        key = service.login(username, body.password)
    except service.InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id, csrf_token = create_session(key)
    _set_session_cookie(response, session_id)
    return AuthResponse(csrf_token=csrf_token, username=username)


@app.post("/api/logout")
def api_logout(
    response: Response,
    pm_session: str | None = Cookie(default=None),
):
    destroy_session(pm_session)
    _clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/entries", response_model=list[EntrySummary])
def api_list_entries(session: WebSession = Depends(require_web_session)):
    try:
        entries = service.list_entries(session.key)
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return [_mask_entry(e) for e in entries]


@app.get("/api/entries/{title}", response_model=EntryDetail)
def api_get_entry(title: str, session: WebSession = Depends(require_web_session)):
    try:
        entry = service.get_entry(session.key, title)
    except service.EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Entry not found")
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return _full_entry(entry)


@app.post("/api/entries", response_model=EntryDetail)
def api_add_entry(
    body: EntryCreate,
    session: WebSession = Depends(require_csrf),
):
    entry = PasswordEntry(
        title=body.title,
        username=body.username,
        password=body.password,
        url=body.url,
        notes=body.notes,
    )
    try:
        created = service.add_entry(session.key, entry)
    except service.EntryExistsError:
        raise HTTPException(status_code=409, detail="Entry already exists")
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return _full_entry(created)


@app.patch("/api/entries/{title}", response_model=EntryDetail)
def api_update_entry(
    title: str,
    body: EntryUpdate,
    session: WebSession = Depends(require_csrf),
):
    try:
        updated = service.update_entry(
            session.key,
            title,
            username=body.username,
            password=body.password,
            url=body.url,
            notes=body.notes,
        )
    except service.EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Entry not found")
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return _full_entry(updated)


@app.delete("/api/entries/{title}")
def api_delete_entry(
    title: str,
    session: WebSession = Depends(require_csrf),
):
    try:
        deleted = service.delete_entry(session.key, title)
    except service.EntryNotFoundError:
        raise HTTPException(status_code=404, detail="Entry not found")
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return {"ok": True, "title": deleted["title"]}


@app.get("/api/search", response_model=list[EntrySummary])
def api_search(q: str, session: WebSession = Depends(require_web_session)):
    if not q.strip():
        return []
    try:
        results = service.search_entries(session.key, q)
    except service.VaultCorruptedError:
        raise HTTPException(status_code=401, detail="Session invalid")
    return [_mask_entry(e) for e in results]


@app.post("/api/generate", response_model=GenerateResponse)
def api_generate(
    body: GenerateRequest,
    session: WebSession = Depends(require_csrf),
):
    try:
        password = service.generate_password(
            body.length, symbols=body.symbols, digits=body.digits
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    saved = False
    if body.title:
        entry = PasswordEntry(title=body.title, password=password)
        try:
            service.add_entry(session.key, entry)
            saved = True
        except service.EntryExistsError:
            raise HTTPException(status_code=409, detail="Entry already exists")

    return GenerateResponse(
        password=password,
        saved=saved,
        title=body.title or None,
    )


@app.post("/api/change-password")
def api_change_password(
    body: ChangePasswordRequest,
    response: Response,
    pm_session: str | None = Cookie(default=None),
    session: WebSession = Depends(require_csrf),
):
    username = getpass.getuser()
    try:
        service.login(username, body.current_password)
    except service.InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    new_key = service.change_master_password(
        session.key, body.new_password, username
    )
    destroy_session(pm_session)
    session_id, csrf_token = create_session(new_key)
    _set_session_cookie(response, session_id)
    return {"ok": True, "csrf_token": csrf_token}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
