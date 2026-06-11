import getpass

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.session_store import SESSION_COOKIE_NAME, clear_all_sessions


@pytest.fixture
def client(isolated_vault, monkeypatch):
    clear_all_sessions()
    monkeypatch.setattr(getpass, "getuser", lambda: "testuser")
    with TestClient(app) as c:
        yield c
    clear_all_sessions()


def _init_and_login(client):
    res = client.post("/api/init", json={"password": "secret123"})
    assert res.status_code == 200
    data = res.json()
    csrf = data["csrf_token"]
    return csrf


def _headers(csrf):
    return {"X-CSRF-Token": csrf}


def test_status_no_vault(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["vault_exists"] is False
    assert data["logged_in"] is False


def test_init_login_flow(client):
    csrf = _init_and_login(client)

    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.json()["logged_in"] is True
    assert res.json()["entry_count"] == 0
    assert res.json()["csrf_token"] == csrf


def test_add_list_get_delete_entry(client):
    csrf = _init_and_login(client)
    headers = _headers(csrf)

    res = client.post(
        "/api/entries",
        json={
            "title": "GitHub",
            "username": "dev",
            "password": "p@ssw0rd",
            "url": "https://github.com",
            "notes": "work account",
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "GitHub"

    res = client.get("/api/entries")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "GitHub"
    assert "password" not in res.json()[0]

    res = client.get("/api/entries/GitHub")
    assert res.status_code == 200
    assert res.json()["password"] == "p@ssw0rd"

    res = client.delete("/api/entries/GitHub", headers=headers)
    assert res.status_code == 200

    res = client.get("/api/entries")
    assert res.json() == []


def test_unauthorized_without_session(client):
    res = client.get("/api/entries")
    assert res.status_code == 401


def test_csrf_required(client):
    _init_and_login(client)
    res = client.post(
        "/api/entries",
        json={"title": "Test", "password": "x"},
    )
    assert res.status_code == 403


def test_search_and_generate(client):
    csrf = _init_and_login(client)
    headers = _headers(csrf)

    client.post(
        "/api/entries",
        json={"title": "Email", "username": "me@example.com", "password": "abc"},
        headers=headers,
    )

    res = client.get("/api/search?q=email")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = client.post(
        "/api/generate",
        json={"length": 20, "title": "NewSite"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["saved"] is True
    assert len(data["password"]) == 20


def test_login_invalid_credentials(client):
    _init_and_login(client)
    client.post("/api/logout")

    res = client.post("/api/login", json={"password": "wrong"})
    assert res.status_code == 401


def test_init_when_vault_exists(client):
    _init_and_login(client)
    res = client.post("/api/init", json={"password": "other"})
    assert res.status_code == 409


def test_logout_clears_session(client):
    _init_and_login(client)
    res = client.post("/api/logout")
    assert res.status_code == 200

    res = client.get("/api/status")
    assert res.json()["logged_in"] is False
