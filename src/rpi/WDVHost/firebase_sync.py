"""
firebase_sync.py — DEPRECATED

This module has been superseded by the full Firebase integration added in
WDVHost.  Firebase is now the single source of truth for all user accounts
and credit balances:

  • firebase_config.py   — Firebase client singletons (pyrebase4 + firebase-admin)
  • storage.py            — RTDB-backed user store (replaces local JSON files)
  • app_state.py          — Async point sync via AppState._sync_points_async()

Do not import this file.  It is kept only for reference.

RTDB Structure (matches local JSON exactly, minus password)
-----------------------------------------------------------
    /users/{username}
        username   : str
        email      : str
        phone      : str
        points     : int
        is_guest   : bool

Security
--------
- Passwords are NEVER written to RTDB.
- RTDB rules should restrict read access to authenticated users
  whose email matches the stored email field.
"""

import pyrebase  # type: ignore

# ── Fill in your Firebase project config ──────────────────────────────────────
FIREBASE_CONFIG = {
    "apiKey":            "",
    "authDomain":        "",
    "databaseURL":       "",
    "projectId":         "",
    "storageBucket":     "",
    "messagingSenderId": "",
    "appId":             "",
}

_firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
_db = _firebase.database()

# ── Fields that must never be pushed to RTDB ──────────────────────────────────
_EXCLUDED_FIELDS = {"password"}


def sync_user(user_dict: dict) -> bool:
    """Push a single user dict to /users/{username} in RTDB.

    Password is stripped automatically for security.
    Returns True on success, False on error.
    """
    username = user_dict.get("username", "")
    if not username or username == "Guest":
        return False

    data = {k: v for k, v in user_dict.items() if k not in _EXCLUDED_FIELDS}

    try:
        _db.child("users").child(username).set(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[firebase_sync] Failed to sync {username}: {exc}")
        return False


def sync_points(username: str, points: int) -> bool:
    """Update only the points field for a user — fastest possible write."""
    if not username or username == "Guest":
        return False
    try:
        _db.child("users").child(username).update({"points": points})
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[firebase_sync] Failed to sync points for {username}: {exc}")
        return False


def sync_all_users() -> int:
    """Bulk-sync every local account file to RTDB.

    Returns the number of users successfully synced.
    """
    import storage  # local import to avoid circular dependency

    count = 0
    for user_dict in storage.list_all_users():
        if sync_user(user_dict):
            count += 1
    return count


def delete_user(username: str) -> bool:
    """Remove a user record from RTDB."""
    if not username:
        return False
    try:
        _db.child("users").child(username).remove()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[firebase_sync] Failed to delete {username}: {exc}")
        return False
