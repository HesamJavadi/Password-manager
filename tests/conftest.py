import pytest


@pytest.fixture
def isolated_vault(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    session_dir = tmp_path / "session"
    monkeypatch.setenv("PM_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("PM_SESSION_DIR", str(session_dir))

    import cli.commands as commands
    import core.service as service_module
    import core.storage as storage
    import core.session as session
    import web.app as web_app

    monkeypatch.setattr(storage, "VAULT_DIR", vault_dir)
    monkeypatch.setattr(service_module, "VAULT_DIR", vault_dir)
    monkeypatch.setattr(web_app, "VAULT_DIR", vault_dir)
    monkeypatch.setattr(storage, "VAULT_FILE", vault_dir / "vault.enc")
    monkeypatch.setattr(storage, "META_FILE", vault_dir / "meta.json")
    monkeypatch.setattr(session, "SESSION_DIR", session_dir)
    monkeypatch.setattr(session, "SESSION_FILE", session_dir / "session")
    monkeypatch.setattr(commands, "VAULT_DIR", vault_dir)

    return vault_dir
