from pathlib import Path
import secrets
import  typer
from core.vault import vault_init, vault_login, vault_read, vault_write, vault_change_password
from core.session import save_session, load_session, clear_session
from core.storage import VAULT_DIR, load_meta
import getpass
import pyperclip
import string

from models.PasswordEntry import PasswordEntry

app = typer.Typer()

user_typer = typer.Typer()
pass_typer = typer.Typer()

app.add_typer(user_typer ,name= "usr")
app.add_typer(pass_typer,name= "pss")


def require_session() -> bytes:
    try:
        return load_session()
    except PermissionError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1)

# start user command
@user_typer.command()
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
    vault_init(username, password)
    typer.echo(f"✓ Vault initialized for '{username}'")

@user_typer.command()
def stpass():
    username = getpass.getuser()
    if not VAULT_DIR.exists():
        typer.echo("✗ Vault not exists! Use: pm usr init", err=True)
        raise typer.Exit(1)
    password = getpass.getpass(prompt="Enter password: ")
    confirm = getpass.getpass(prompt="Confirm password: ")
    if password != confirm:
        typer.echo("✗ Passwords do not match!", err=True)
        raise typer.Exit(1)
    vault_change_password(username, password)
    typer.echo(f"✓ password changed '{username}'")


@user_typer.command()
def login():
    password = getpass.getpass("Master password: ")
    username = getpass.getuser()

    key = vault_login(username, password)

    if key is None:
        typer.echo("✗ Invalid password!", err=True)
        raise typer.Exit(1)

    save_session(key)
    typer.echo("✓ Login successful!")
@user_typer.command()
def logout():
    clear_session()

#end user command

#start password
@pass_typer.command()
def add(
        title: str = typer.Option(..., "--title", "-t", prompt=True),
        username: str = typer.Option(..., "--username", "-u", prompt=True),
        password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True),
        url: str = typer.Option("", "--url", prompt="URL (optional)"),
        notes: str = typer.Option("", "--notes", prompt="Notes (optional)"),
):

    key = require_session()

    entries = vault_read(key)

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

@pass_typer.command()
def use(
        title: str = typer.Option(..., "--title", "-t", prompt=True),
        password: str = typer.Option(..., "--password", "-p", prompt=True)
):

    key = require_session()
    entries = vault_read(key)

    for entry in entries:
        if entry["title"].lower() == title.lower():
            typer.echo(f"✗ Entry '{title}' already exists!", err=True)
            raise typer.Exit(1)

    new_entry = PasswordEntry(
        title=title,
        password=password
    )

    entries.append(new_entry.to_dict())
    vault_write(entries, key)

    typer.echo(f"✓ '{title}' added successfully!")

@pass_typer.command()
def ls():

    key = require_session()
    entries = vault_read(key)
    if not entries:
        typer.echo("No passwords saved yet.")
        return

    for entry in entries:
        typer.echo(f"[{entry['id'][:8]}] {entry['title']} - {entry['username']}")

@pass_typer.command()
def rm(name):
    key = require_session()
    entries = vault_read(key)
    if not entries:
        typer.echo("No passwords saved yet.")
    for entry in entries:
        if entry["title"].lower() == name.lower():
            entries.remove(entry)
            vault_write(entries, key)


@pass_typer.command()
def edit(name):
    key = require_session()
    entries = vault_read(key)
    if not entries:
        typer.echo("No passwords saved yet.")
    for entry in entries:
        if entry["title"].lower() == name.lower():
            entry["password"] = getpass.getpass(prompt="Enter new password: ")
            vault_write(entries, key)

@pass_typer.command()
def get(name,
    show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal password"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy password to clipboard"),
):
    key = require_session()
    entries = vault_read(key)
    for entry in entries:
        if entry["title"].lower() == name.lower():
            password_display = entry['password'] if show_pass else "••••••"
            typer.echo(f"Password: {password_display}")
            if copy:
                pyperclip.copy(entry['password'])
                typer.echo("✓ Password copied to clipboard!")
            return
    typer.echo("not found!")

@pass_typer.command()
def sch(
        query: str = typer.Argument(..., help="Search in titles"),
        show_pass: bool = typer.Option(False, "--show", "-s", help="Reveal password")
        ):
    key = require_session()
    entries = vault_read(key)

    results = [
        entry for entry in entries
        if query.lower() in entry["title"].lower()
    ]

    if not results:
        typer.echo(f"✗ No results for '{query}'", err=True)
        raise typer.Exit(1)

    for entry in results:
        typer.echo(f"[{entry['id'][:8]}] {entry['title']} - {entry['password'] if show_pass else entry['username']}")


@pass_typer.command()
def gn(
        length: int = typer.Option(16, "--length", "-l", help="Password length"),
        title: str = typer.Option("", "--title", "-t", help="Save with this title"),
        symbols: bool = typer.Option(True, "--symbols", "-s", help="Include symbols"),
        digits: bool = typer.Option(True, "--digits", "-d", help="Include digits"),
):
    chars = string.ascii_letters
    if digits:
        chars += string.digits
    if symbols:
        chars += string.punctuation

    password = "".join(secrets.choice(chars) for _ in range(length))
    pyperclip.copy(password)
    typer.echo(password)

    if title != "":
        key = require_session()
        entries = vault_read(key)
        new_entry = PasswordEntry(
            title=title,
            password=password
        )
        entries.append(new_entry.to_dict())
        vault_write(entries, key)
        typer.echo(f"✓ '{title}' added successfully!")


# end password command


def cli():
    app()

