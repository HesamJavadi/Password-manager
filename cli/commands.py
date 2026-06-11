import getpass

import pyperclip
import typer

from core import service
from core.session import clear_session, load_session, save_session, session_info
from core.storage import VAULT_DIR, load_meta
from models.PasswordEntry import PasswordEntry

app = typer.Typer(help="CLI password manager")
user_typer = typer.Typer(help="Vault and session commands")
pass_typer = typer.Typer(help="Password entry commands")
web_typer = typer.Typer(help="Web UI commands")

app.add_typer(user_typer, name="usr")
app.add_typer(user_typer, name="user")
app.add_typer(pass_typer, name="pss")
app.add_typer(pass_typer, name="pass")
app.add_typer(web_typer, name="web")


def require_session() -> bytes:
    try:
        return load_session()
    except PermissionError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)


def read_vault(key: bytes) -> list:
    try:
        return service.read_vault(key)
    except service.VaultCorruptedError as e:
        typer.echo(f"✗ {e}. Run: pm usr login", err=True)
        raise typer.Exit(1)


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
    try:
        key = service.init_vault(username, password)
    except service.VaultExistsError:
        typer.echo("✗ Vault already exists! Use: pm usr login", err=True)
        raise typer.Exit(1)
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
        try:
            old_key = service.login(username, current)
        except service.InvalidCredentialsError:
            typer.echo("✗ Invalid current password!", err=True)
            raise typer.Exit(1)

    new_password = getpass.getpass(prompt="New password: ")
    confirm = getpass.getpass(prompt="Confirm new password: ")
    if new_password != confirm:
        typer.echo("✗ Passwords do not match!", err=True)
        raise typer.Exit(1)

    new_key = service.change_master_password(old_key, new_password, username)
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

    try:
        key = service.login(username, password)
    except service.InvalidCredentialsError:
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
    new_entry = PasswordEntry(
        title=title,
        username=username,
        password=password,
        url=url,
        notes=notes,
    )
    try:
        service.add_entry(key, new_entry)
    except service.EntryExistsError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✓ '{title}' added successfully!")


@pass_typer.command(help="Quick-add an entry (title and password only)")
def use(
    title: str = typer.Option(..., "--title", "-t", prompt=True, help="Entry title"),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True, help="Password"),
):
    key = require_session()
    new_entry = PasswordEntry(title=title, password=password)
    try:
        service.add_entry(key, new_entry)
    except service.EntryExistsError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✓ '{title}' added successfully!")


def _list_entries():
    key = require_session()
    entries = service.list_entries(key)
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
    try:
        entry = service.get_entry(key, name)
    except service.EntryNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
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
    entries = service.list_entries(key)

    if not entries:
        typer.echo("No passwords saved yet.")
        raise typer.Exit(1)

    try:
        matching = service.get_entry(key, name)
    except service.EntryNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Delete '{matching['title']}'?")
        if not confirm:
            typer.echo("Cancelled.")
            raise typer.Exit(0)

    service.delete_entry(key, name)
    typer.echo(f"✓ '{matching['title']}' removed")


@pass_typer.command(help="Change the password for an entry")
def edit(name: str = typer.Argument(..., help="Entry title")):
    key = require_session()
    entries = service.list_entries(key)

    if not entries:
        typer.echo("No passwords saved yet.")
        raise typer.Exit(1)

    try:
        entry = service.update_entry_password(
            key, name, getpass.getpass(prompt="Enter new password: ")
        )
    except service.EntryNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"✓ Password updated for '{entry['title']}'")


@pass_typer.command(help="Get an entry's password")
def get(
    name: str = typer.Argument(..., help="Entry title"),
    show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal password"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy password to clipboard"),
):
    key = require_session()
    try:
        entry = service.get_entry(key, name)
    except service.EntryNotFoundError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)

    password_display = entry["password"] if show_pass else "••••••"
    typer.echo(f"Password: {password_display}")

    if copy:
        if copy_to_clipboard(entry["password"]):
            typer.echo("✓ Password copied to clipboard!")
        else:
            typer.echo("✗ Clipboard unavailable; use --show to reveal password", err=True)
            raise typer.Exit(1)


def _search(query: str, show_pass: bool = False):
    key = require_session()
    results = service.search_entries(key, query)

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
    try:
        password = service.generate_password(length, symbols=symbols, digits=digits)
    except ValueError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)

    if copy_to_clipboard(password):
        typer.echo("✓ Password copied to clipboard")
    elif not quiet and not title:
        typer.echo("✗ Clipboard unavailable; password shown below", err=True)

    if not quiet and not title:
        typer.echo(password)

    if title:
        key = require_session()
        new_entry = PasswordEntry(title=title, password=password)
        try:
            service.add_entry(key, new_entry)
        except service.EntryExistsError as e:
            typer.echo(f"✗ {e}", err=True)
            raise typer.Exit(1)
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


# --- web commands ---

@web_typer.command(help="Start the localhost web UI")
def start(
    port: int = typer.Option(8765, "--port", "-p", help="Port to listen on"),
):
    from web.main import run_server
    run_server(port=port)


def cli():
    app()
