"""
Per-browser ownership.

CodeAtlas has no user accounts. Instead, each browser generates a random
secret token (kept in localStorage) and sends it on every request in the
X-Owner-Token header. The server never stores the token itself, only its
SHA-256 hash, and stamps that hash on every upload, clone, analysis and
report. Every endpoint that reads or changes one of those checks that the
caller's hash matches.

Result: people can only see, download and delete their own work, and a
leaked report file or server log never contains a usable token.

Note this is ownership, not identity: clearing site data (or switching
browser) means starting fresh, the same as an anonymous session.
"""
import hashlib
import hmac
import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

OWNER_HEADER = "X-Owner-Token"
OWNER_KEY = "_owner"  # field name stored inside report / result dicts
SIDECAR_SUFFIX = ".owner"

# 32-128 URL-safe chars. crypto.randomUUID() (36 chars) and 64-char hex both fit.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_owner(
    x_owner_token: Optional[str] = Header(default=None, alias=OWNER_HEADER),
) -> str:
    """FastAPI dependency: validate the header and return the owner hash."""
    if not x_owner_token or not _TOKEN_RE.match(x_owner_token):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid owner token. Reload the page and try again.",
        )
    return hash_token(x_owner_token)


def same_owner(stored: Optional[str], owner: str) -> bool:
    """Constant-time comparison. Data with no owner belongs to nobody."""
    if not stored or not owner:
        return False
    return hmac.compare_digest(stored, owner)


# ── Ownership of folders on disk (uploads / clones) ──────────────────
# Stored in a sidecar file NEXT TO the folder (not inside it), so the
# analyzer never scans it and a ZIP can't ship its own forged owner file.
def _sidecar(folder: Path) -> Path:
    folder = Path(folder)
    return folder.parent / (folder.name + SIDECAR_SUFFIX)


def write_folder_owner(folder: str, owner: str) -> None:
    _sidecar(Path(folder)).write_text(owner, encoding="utf-8")


def read_folder_owner(folder: str) -> Optional[str]:
    try:
        return _sidecar(Path(folder)).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def delete_folder_owner(folder: str) -> None:
    try:
        _sidecar(Path(folder)).unlink()
    except OSError:
        pass


def owns_folder(folder: str, owner: str) -> bool:
    return same_owner(read_folder_owner(folder), owner)


# ── Ownership stamped inside result / report dicts ───────────────────
def owns_record(record: Optional[Dict[str, Any]], owner: str) -> bool:
    return isinstance(record, dict) and same_owner(record.get(OWNER_KEY), owner)


def strip_owner(record: Dict[str, Any]) -> Dict[str, Any]:
    """Copy of a record without the owner hash, for API responses."""
    if not isinstance(record, dict):
        return record
    clean = dict(record)
    clean.pop(OWNER_KEY, None)
    return clean