from unittest.mock import patch

from typer.testing import CliRunner

from cli.commands import app

runner = CliRunner()


def test_init_and_list(isolated_vault):
    with patch("cli.commands.getpass.getpass", side_effect=["secret123", "secret123"]):
        with patch("cli.commands.getpass.getuser", return_value="alice"):
            result = runner.invoke(app, ["usr", "init"])
            assert result.exit_code == 0
            assert "Vault initialized" in result.stdout

    result = runner.invoke(app, ["pss", "ls"])
    assert result.exit_code == 0
    assert "No passwords saved yet" in result.stdout


def test_status_shows_vault_path(isolated_vault):
    result = runner.invoke(app, ["usr", "status"])
    assert result.exit_code == 0
    assert "Vault path:" in result.stdout
