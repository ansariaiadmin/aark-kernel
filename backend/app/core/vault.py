"""Secure API-key vault.

Single source of truth for the Nobitex credential vault.

Previously the vault path and its (un)locking logic were copy-pasted in
``app/main.py`` and ``app/api/v1/trading.py``; the two copies had already
drifted (only ``main.py`` enforced ``0o600``). Everything now goes through
here so there is exactly one definition of "where the key lives" and "how it
is protected".
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

VAULT_DIR_ENV = "AARK_VAULT_DIR"
DEFAULT_VAULT_DIR = os.path.join(os.path.expanduser("~"), ".aark")

VAULT_DIR = os.environ.get(VAULT_DIR_ENV, DEFAULT_VAULT_DIR)
CONFIG_DIR = VAULT_DIR  # backwards-compatible alias used across the codebase
CONFIG_FILE = os.path.join(VAULT_DIR, "nobitex.vault")

DIR_MODE = 0o700
FILE_MODE = 0o600


def ensure_vault_dir() -> str:
    """Create the vault directory with ``0700`` and return its path."""
    os.makedirs(VAULT_DIR, mode=DIR_MODE, exist_ok=True)
    try:
        os.chmod(VAULT_DIR, DIR_MODE)
    except OSError:  # pragma: no cover - best effort on exotic filesystems
        logger.warning("Could not enforce %o on vault dir %s", DIR_MODE, VAULT_DIR)
    return VAULT_DIR


def get_vault_token() -> str:
    """Return the stored API key, or ``""`` when absent/unreadable/corrupt."""
    if not os.path.exists(CONFIG_FILE):
        return ""
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("api_key", "") or "")
    except (OSError, ValueError) as exc:
        logger.warning("Vault unreadable at %s: %s", CONFIG_FILE, exc)
        return ""


def save_vault_token(api_key: str) -> None:
    """Persist the API key atomically with ``0600`` permissions."""
    ensure_vault_dir()
    tmp_path = f"{CONFIG_FILE}.tmp"
    # Create with the right mode *before* writing so the secret is never
    # briefly world-readable.
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"api_key": api_key}, f)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    os.replace(tmp_path, CONFIG_FILE)
    os.chmod(CONFIG_FILE, FILE_MODE)


def clear_vault_token() -> bool:
    """Delete the vault file. Returns ``True`` when something was removed."""
    try:
        os.unlink(CONFIG_FILE)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:  # pragma: no cover
        logger.warning("Could not clear vault: %s", exc)
        return False
