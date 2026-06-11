import getpass
import json
import secrets
import string
from datetime import datetime

import pyperclip
import typer
from cryptography.fernet import InvalidToken

from core.session import clear_session, load_session, save_session, session_info
from core.storage import VAULT_DIR, load_meta
from core.vault import (
    vault_change_password,
    vault_init,
    vault_login,
    vault_read,
    vault_write,
)
from models.PasswordEntry import PasswordEntry

app = typer.Typer(help="CLI password manager")
user_typer = typer.Typer(help="Vault and session commands")
pass_typer = typer.Typer(help="Password entry commands")

app.add_typer(user_typer, name="usr")
app.add_typer(user_typer, name="user")
app.add_typer(pass_typer, name="pss")
app.add_typer(pass_typer, name="pass")


def require_session() -> bytes:
    try:
        return load_session()
    except PermissionError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)


def read_vault(key: bytes) -> list:
    try:
        return vault_read(key)
    except InvalidToken:
        typer.echo("✗ Vault corrupted or session expired. Run: pm usr login", err=True)
        raise typer.Exit(1)
    except json.JSONDecodeError:
        typer.echo("✗ Vault data is corrupted", err=True)
        raise typer.Exit(1)


def find_entry(entries: list, name: str) -> dict | None:
    for entry in entries:
        if entry["title"].lower() == name.lower():
            return entry
    return None


def copy_to_clipboard(text: str) -> bool:
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException:
        return False


# --- user commands ---

@user_typer.command(help="Create a new encrypted vault")
def init():
    if VAULT_DIR.exists():
        typer.echo("✗ Vault already exists! Use: pm usr login", err=True)
        raise typer.Exit(1)

    password = getpass.getpass(prompt="Enter password: ")
    confirm = getpass.getpass(prompt="Confirm password: ")

    if password != confirm:
        typer.echo("✗ Passwords do not match!", err=True)
        raise typer.Exit(1)

    username = getpass.getuser()
    key = vault_init(username, password)
    save_session(key)
    typer.echo(f"✓ Vault initialized for '{username}'")
    typer.echo(f"  Vault location: {VAULT_DIR}")
    typer.echo("✓ Logged in automatically")


@user_typer.command(help="Change the master password")
def stpass():
    if not VAULT_DIR.exists():
        typer.echo("✗ Vault not found! Use: pm usr init", err=True)
        raise typer.Exit(1)

    username = getpass.getuser()
    try:
        old_key = load_session()
    except PermissionError:
        current = getpass.getpass(prompt="Current master password: ")
        old_key = vault_login(username, current)
        if old_key is None:
            typer.echo("✗ Invalid current password!", err=True)
            raise typer.Exit(1)

    new_password = getpass.getpass(prompt="New password: ")
    confirm = getpass.getpass(prompt="Confirm new password: ")
    if new_password != confirm:
        typer.echo("✗ Passwords do not match!", err=True)
        raise typer.Exit(1)

    new_key = vault_change_password(old_key, new_password, username)
    save_session(new_key)
    typer.echo(f"✓ Master password changed for '{username}'")


@user_typer.command(help="Unlock the vault")
def login():
    try:
        load_meta()
    except FileNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)

    password = getpass.getpass("Master password: ")
    username = getpass.getuser()

    key = vault_login(username, password)

    if key is None:
        typer.echo("✗ Invalid password!", err=True)
        raise typer.Exit(1)

    save_session(key)
    typer.echo(f"✓ Logged in as {username}")


@user_typer.command(help="Lock the vault (clear session)")
def logout():
    clear_session()
    typer.echo("✓ Logged out")


@user_typer.command(name="lock", help="Lock the vault (alias for logout)")
def lock():
    logout()


@user_typer.command(help="Show vault path, login state, and entry count")
def status():
    typer.echo(f"Vault path: {VAULT_DIR}")
    typer.echo(f"Vault exists: {'yes' if VAULT_DIR.exists() else 'no'}")

    info = session_info()
    if info is None:
        typer.echo("Session: locked")
        return

    if info["expired"]:
        typer.echo("Session: expired")
        return

    age_min = info["age_seconds"] // 60
    typer.echo(f"Session: unlocked ({age_min} min ago)")

    try:
        key = load_session()
        entries = read_vault(key)
        typer.echo(f"Entries: {len(entries)}")
    except PermissionError:
        typer.echo("Session: locked")


# --- password commands ---

@pass_typer.command(help="Add a password entry with full details")
def add(
    title: str = typer.Option(..., "--title", "-t", prompt=True, help="Entry title"),
    username: str = typer.Option(..., "--username", "-u", prompt=True, help="Account username"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Password"),
    url: str = typer.Option("", "--url", prompt="URL (optional)", help="Website URL"),
    notes: str = typer.Option("", "--notes", prompt="Notes (optional)", help="Notes"),
):
    key = require_session()
    entries = read_vault(key)

    for entry in entries:
        if entry["title"].lower() == title.lower():
            typer.echo(f"✗ Entry '{title}' already exists!", err=True)
            raise typer.Exit(1)

    new_entry = PasswordEntry(
        title=title,
        username=username,
        password=password,
        url=url,
        notes=notes,
    )

    entries.append(new_entry.to_dict())
    vault_write(entries, key)
    typer.echo(f"✓ '{title}' added successfully!")


@pass_typer.command(help="Quick-add an entry (title and password only)")
def use(
    title: str = typer.Option(..., "--title", "-t", prompt=True, help="Entry title"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Password"),
):
    key = require_session()
    entries = read_vault(key)

    for entry in entries:
        if entry["title"].lower() == title.lower():
            typer.echo(f"✗ Entry '{title}' already exists!", err=True)
            raise typer.Exit(1)

    new_entry = PasswordEntry(title=title, password=password)
    entries.append(new_entry.to_dict())
    vault_write(entries, key)
    typer.echo(f"✓ '{title}' added successfully!")


def _list_entries():
    key = require_session()
    entries = read_vault(key)
    if not entries:
        typer.echo("No passwords saved yet.")
        return

    for entry in entries:
        typer.echo(f"[{entry['id'][:8]}] {entry['title']} - {entry['username']}")


@pass_typer.command("ls", help="List all password entries")
def ls():
    _list_entries()


@pass_typer.command("list", help="List all password entries")
def list_cmd():
    _list_entries()


@pass_typer.command(help="Show full entry details")
def show(
    name: str = typer.Argument(..., help="Entry title"),
    reveal_password: bool = typer.Option(False, "--show", "-s", help="Reveal password"),
):
    key = require_session()
    entries = read_vault(key)
    entry = find_entry(entries, name)

    if entry is None:
        typer.echo(f"✗ Entry '{name}' not found!", err=True)
        raise typer.Exit(1)

    typer.echo(f"Title:    {entry['title']}")
    typer.echo(f"Username: {entry['username']}")
    typer.echo(f"URL:      {entry.get('url') or '-'}")
    typer.echo(f"Notes:    {entry.get('notes') or '-'}")
    password_display = entry["password"] if reveal_password else "••••••"
    typer.echo(f"Password: {password_display}")
    typer.echo(f"Updated:  {entry.get('updated_at', '-')}")


@pass_typer.command(help="Remove an entry by title")
def rm(
    name: str = typer.Argument(..., help="Entry title"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    key = require_session()
    entries = read_vault(key)

    if not entries:
        typer.echo("No passwords saved yet.")
        raise typer.Exit(1)

    matching = [e for e in entries if e["title"].lower() == name.lower()]
    if not matching:
        typer.echo(f"✗ Entry '{name}' not found!", err=True)
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Delete '{matching[0]['title']}'?")
        if not confirm:
            typer.echo("Cancelled.")
            raise typer.Exit(0)

    remaining = [e for e in entries if e["title"].lower() != name.lower()]
    vault_write(remaining, key)
    typer.echo(f"✓ '{matching[0]['title']}' removed")


@pass_typer.command(help="Change the password for an entry")
def edit(name: str = typer.Argument(..., help="Entry title")):
    key = require_session()
    entries = read_vault(key)

    if not entries:
        typer.echo("No passwords saved yet.")
        raise typer.Exit(1)

    entry = find_entry(entries, name)
    if entry is None:
        typer.echo(f"✗ Entry '{name}' not found!", err=True)
        raise typer.Exit(1)

    entry["password"] = getpass.getpass(prompt="Enter new password: ")
    entry["updated_at"] = datetime.now().isoformat()
    vault_write(entries, key)
    typer.echo(f"✓ Password updated for '{entry['title']}'")


@pass_typer.command(help="Get an entry's password")
def get(
    name: str = typer.Argument(..., help="Entry title"),
    show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal password"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy password to clipboard"),
):
    key = require_session()
    entries = read_vault(key)
    entry = find_entry(entries, name)

    if entry is None:
        typer.echo(f"✗ Entry '{name}' not found!", err=True)
        raise typer.Exit(1)

    password_display = entry["password"] if show_pass else "••••••"
    typer.echo(f"Password: {password_display}")

    if copy:
        if copy_to_clipboard(entry["password"]):
            typer.echo("✓ Password copied to clipboard!")
        else:
            typer.echo("✗ Clipboard unavailable; use --show to reveal password", err=True)
            raise typer.Exit(1)


def _search(
    query: str,
    show_pass: bool = False,
):
    key = require_session()
    entries = read_vault(key)
    q = query.lower()

    results = [
        entry for entry in entries
        if q in entry["title"].lower()
        or q in entry.get("username", "").lower()
        or q in entry.get("url", "").lower()
        or q in entry.get("notes", "").lower()
    ]

    if not results:
        typer.echo(f"✗ No results for '{query}'", err=True)
        raise typer.Exit(1)

    for entry in results:
        display = entry["password"] if show_pass else entry["username"]
        typer.echo(f"[{entry['id'][:8]}] {entry['title']} - {display}")


@pass_typer.command("sch", help="Search entries by title, username, URL, or notes")
def sch(
    query: str = typer.Argument(..., help="Search query"),
    show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal passwords"),
):
    _search(query, show_pass)


@pass_typer.command("search", help="Search entries by title, username, URL, or notes")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal passwords"),
):
    _search(query, show_pass)


def _generate(
    length: int = 16,
    title: str = "",
    symbols: bool = True,
    digits: bool = True,
    quiet: bool = False,
):
    if length <= 0:
        typer.echo("✗ Length must be greater than 0", err=True)
        raise typer.Exit(1)

    chars = string.ascii_letters
    if digits:
        chars += string.digits
    if symbols:
        chars += string.punctuation

    if not chars:
        typer.echo("✗ No character set available (enable --digits or --symbols)", err=True)
        raise typer.Exit(1)

    password = "".join(secrets.choice(chars) for _ in range(length))

    if copy_to_clipboard(password):
        typer.echo("✓ Password copied to clipboard")
    elif not quiet and not title:
        typer.echo("✗ Clipboard unavailable; password shown below", err=True)

    if not quiet and not title:
        typer.echo(password)

    if title:
        key = require_session()
        entries = read_vault(key)

        for entry in entries:
            if entry["title"].lower() == title.lower():
                typer.echo(f"✗ Entry '{title}' already exists!", err=True)
                raise typer.Exit(1)

        new_entry = PasswordEntry(title=title, password=password)
        entries.append(new_entry.to_dict())
        vault_write(entries, key)
        typer.echo(f"✓ '{title}' added successfully!")


@pass_typer.command("gn", help="Generate a random password")
def gn(
    length: int = typer.Option(16, "--length", "-l", help="Password length"),
    title: str = typer.Option("", "--title", "-t", help="Save with this title"),
    symbols: bool = typer.Option(True, "--symbols", help="Include symbols"),
    digits: bool = typer.Option(True, "--digits", "-d", help="Include digits"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Do not print password to terminal"),
):
    _generate(length, title, symbols, digits, quiet)


@pass_typer.command("generate", help="Generate a random password")
def generate_cmd(
    length: int = typer.Option(16, "--length", "-l", help="Password length"),
    title: str = typer.Option("", "--title", "-t", help="Save with this title"),
    symbols: bool = typer.Option(True, "--symbols", help="Include symbols"),
    digits: bool = typer.Option(True, "--digits", "-d", help="Include digits"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Do not print password to terminal"),
):
    _generate(length, title, symbols, digits, quiet)


def cli():
    app()
