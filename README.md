# Password Manager

A CLI password manager with encrypted local storage.

## Install

```bash
pip install -e .
# or with dev dependencies for tests:
pip install -e ".[dev]"
```

## Vault location

By default the vault is stored at:

- **Windows:** `%USERPROFILE%\.password_manager\`
- **Linux/macOS:** `~/.password_manager/`

Override with the `PM_VAULT_DIR` environment variable.

Session files are stored in `%LOCALAPPDATA%\password_manager\` on Windows (or `PM_SESSION_DIR` override). Sessions expire after 30 minutes.

## Quick start

```bash
pm usr init          # Create vault and log in
pm pss add           # Add a password entry
pm pss ls            # List entries
pm pss get <title>   # Get password (--copy to clipboard)
pm usr logout        # Lock vault
```

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `pm usr init` | | Create a new vault |
| `pm usr login` | | Unlock vault |
| `pm usr logout` | `lock` | Lock vault |
| `pm usr stpass` | | Change master password |
| `pm usr status` | | Show vault path and session state |
| `pm pss add` | | Add entry (full details) |
| `pm pss use` | | Quick-add (title + password) |
| `pm pss ls` | `list` | List entries |
| `pm pss show` | | Show full entry details |
| `pm pss get` | | Get password |
| `pm pss edit` | | Change entry password |
| `pm pss rm` | | Remove entry (prompts for confirmation) |
| `pm pss sch` | `search` | Search entries |
| `pm pss gn` | `generate` | Generate random password |

Group aliases: `user` for `usr`, `pass` for `pss`.

## Web UI

Start the localhost web interface:

```bash
pm-web
# or
pm web start
```

Open **http://127.0.0.1:8765** in your browser.

The web UI uses the same encrypted vault as the CLI. You can list, search, copy, add, edit, and delete entries from the browser. Sessions auto-lock after 30 minutes.

**Security notes for web use:**

- The server binds to `127.0.0.1` only (not accessible from other machines).
- Web sessions are stored in memory (not written to disk like the CLI session file).
- CLI and web have separate login sessions; avoid writing to the vault from both at the same time.
- Use the **Lock** button when finished.

## Security notes

- Master password is never stored; only a derived key verifier (SHA-256 of Fernet key) is kept in `meta.json`.
- Vault contents are encrypted with Fernet (AES-128-CBC + HMAC).
- Key derivation uses PBKDF2-HMAC-SHA256 with 2,480,000 iterations.
- Session key is stored locally and expires after 30 minutes.

## Build executable

```bash
pyinstaller pm.spec
```

Output: `dist/pm.exe`

## Tests

```bash
pytest
```
