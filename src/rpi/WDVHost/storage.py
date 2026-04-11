"""
storage.py — Firebase Realtime Database-backed user store.

Replaces the old local JSON-file implementation.
The public API is identical so all existing callers work without change.

RTDB layout
-----------
/users/{uid}
    username  : str
    email     : str   (user's real contact email; may be "---")
    phone     : str
    points    : int
    is_guest  : bool

/usernames/{sanitised_username} : uid
    Fast reverse-index for username → uid lookups (used by login + QR scan).

NOTE: Passwords are NEVER written to RTDB.
      Firebase Authentication owns all credentials.
"""

from typing import Optional, List
from firebase_config import admin_db, admin_auth

_USERS     = "users"
_USERNAMES = "usernames"

# Fields that must never be persisted to RTDB
_STRIP = {"password", "uid"}


def _safe(username: str) -> str:
    """Sanitise a username so it can be used as an RTDB key."""
    return "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in username.lower()
    )


def _uid_for_username(username: str) -> Optional[str]:
    """Return the Firebase UID for *username* via the /usernames index."""
    try:
        return admin_db.reference(f"{_USERNAMES}/{_safe(username)}").get()
    except Exception:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def save_user(user_dict: dict) -> None:
    """Persist a user dict to RTDB (creates or merges existing record).

    The 'uid' key must be present in *user_dict*.
    'password' and 'uid' are stripped before writing.
    """
    uid      = user_dict.get("uid", "")
    username = user_dict.get("username", "")
    if not uid:
        print("[storage] save_user: missing uid — skipping")
        return

    data = {k: v for k, v in user_dict.items() if k not in _STRIP}
    admin_db.reference(f"{_USERS}/{uid}").update(data)

    # Keep the username → uid reverse index current
    if username and username not in ("Guest", "Guest User"):
        admin_db.reference(f"{_USERNAMES}/{_safe(username)}").set(uid)


def load_user(username: str) -> Optional[dict]:
    """Return the stored dict for *username*, or None if not found.

    The returned dict contains a 'uid' key for use in subsequent calls.
    """
    uid = _uid_for_username(username)
    if not uid:
        return None
    try:
        data = admin_db.reference(f"{_USERS}/{uid}").get()
    except Exception:
        return None
    if data is None:
        return None
    data["uid"] = uid
    return data


def delete_user(username: str) -> None:
    """Remove a user from RTDB and Firebase Auth."""
    uid = _uid_for_username(username)
    if not uid:
        return
    try:
        admin_db.reference(f"{_USERS}/{uid}").delete()
        admin_db.reference(f"{_USERNAMES}/{_safe(username)}").delete()
        admin_auth.delete_user(uid)
    except Exception as exc:
        print(f"[storage] delete_user error: {exc}")


def find_user_by_phone(phone: str) -> Optional[dict]:
    """Return the first user dict whose phone matches, or None.

    Requires the Firebase RTDB index:  "users": { ".indexOn": ["phone"] }
    """
    try:
        result = (
            admin_db.reference(_USERS)
            .order_by_child("phone")
            .equal_to(phone)
            .get()
        )
    except Exception:
        return None
    if not result:
        return None
    uid  = next(iter(result))
    data = result[uid]
    data["uid"] = uid
    return data


def list_all_users() -> List[dict]:
    """Return all stored user dicts."""
    try:
        result = admin_db.reference(_USERS).get()
    except Exception:
        return []
    if not result:
        return []
    users: List[dict] = []
    for uid, data in result.items():
        data["uid"] = uid
        users.append(data)
    return users


def update_password(uid: str, new_password: str) -> None:
    """Update a user's Firebase Auth password via the admin SDK."""
    admin_auth.update_user(uid, password=new_password)
