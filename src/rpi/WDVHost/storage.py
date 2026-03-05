"""
storage.py - JSON-file persistence layer (replaces HTML localStorage).

Accounts are stored as individual JSON files under a local 'accounts/'
folder relative to this module.  The format mirrors the User dataclass
so serialisation/deserialisation is trivial.
"""

import json
import os
from typing import Optional, List

_BASE_DIR = os.path.join(os.path.dirname(__file__), "accounts")


def _ensure_dir() -> None:
    os.makedirs(_BASE_DIR, exist_ok=True)


def _path(username: str) -> str:
    # Sanitise username so it is a safe filename
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in username)
    return os.path.join(_BASE_DIR, f"{safe}.json")


# ── Public API ────────────────────────────────────────────────────────────────

def save_user(user_dict: dict) -> None:
    """Persist a user dict to disk."""
    _ensure_dir()
    path = _path(user_dict["username"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(user_dict, fh, indent=2)


def load_user(username: str) -> Optional[dict]:
    """Return the stored dict for *username*, or None if not found."""
    path = _path(username)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def delete_user(username: str) -> None:
    path = _path(username)
    if os.path.exists(path):
        os.remove(path)


def find_user_by_phone(phone: str) -> Optional[dict]:
    """Scan all stored accounts and return the first one matching *phone*."""
    _ensure_dir()
    for fname in os.listdir(_BASE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(_BASE_DIR, fname), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("phone") == phone:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def list_all_users() -> List[dict]:
    """Return all stored user dicts – used for QR-login (find first account)."""
    _ensure_dir()
    users: List[dict] = []
    for fname in os.listdir(_BASE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(_BASE_DIR, fname), "r", encoding="utf-8") as fh:
                users.append(json.load(fh))
        except (json.JSONDecodeError, OSError):
            continue
    return users
