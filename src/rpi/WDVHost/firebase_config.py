"""
firebase_config.py — Firebase client singletons for AquaSmart Kiosk.

Two clients are initialised here:

  fb_auth    — pyrebase4 auth client (user-facing sign-in / sign-up)
  admin_db   — firebase-admin RTDB client (admin-level reads + writes)
  admin_auth — firebase-admin Auth client (password resets, custom tokens)

Setup
-----
1.  Fill in FIREBASE_CONFIG below OR set environment variables.
2.  Place your service-account JSON at the path in SERVICE_ACCOUNT_PATH
    (download from Firebase Console → Project Settings → Service Accounts).
3.  pip install pyrebase4 firebase-admin

RTDB Layout
-----------
/users/{uid}
    username  : str
    email     : str   (user's real Gmail / contact email — used for Firebase Auth)
    phone     : str
    points    : int
    is_guest  : bool

/usernames/{sanitised_username} : uid   ← fast username → uid reverse index

Firebase Auth Email
-------------------
The user's REAL email (e.g. gmail) is used directly as the Firebase Auth email.
This is the same credential used on the web dashboard — no conversion needed.
"""

import os
import json
import requests          # type: ignore
import pyrebase          # type: ignore
import firebase_admin
from firebase_admin import credentials, auth as _fb_admin_auth, db as _fb_admin_db

# ── Config ────────────────────────────────────────────────────────────────────
# Fill values directly OR export them as environment variables before starting.

FIREBASE_CONFIG: dict = {

    "apiKey":            os.environ.get("FIREBASE_API_KEY",             "AIzaSyC2toXhT_-NKleEB0lUkTCdGXmbp_WKa0c"),
    "authDomain":        os.environ.get("FIREBASE_AUTH_DOMAIN",         "wdvm-18790.firebaseapp.com"),
    "databaseURL":       os.environ.get("FIREBASE_DATABASE_URL",        "https://wdvm-18790-default-rtdb.firebaseio.com"),
    "projectId":         os.environ.get("FIREBASE_PROJECT_ID",          "wdvm-18790"),
    "storageBucket":     os.environ.get("FIREBASE_STORAGE_BUCKET",      "wdvm-18790.firebasestorage.app"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "500117983419"),
    "appId":             os.environ.get("FIREBASE_APP_ID",              "1:500117983419:web:c977291102537fcf95599e"),
}

# Path to the Firebase service-account JSON file (for admin SDK).
SERVICE_ACCOUNT_PATH: str = os.environ.get(
    "FIREBASE_SERVICE_ACCOUNT", "service_account.json"
)

# ── pyrebase4 — user-facing Auth only ─────────────────────────────────────────
_pyrebase_app = pyrebase.initialize_app(FIREBASE_CONFIG)

#: Use this to call sign_in_with_email_and_password / create_user_with_email_and_password
fb_auth = _pyrebase_app.auth()

# ── REST-based fallbacks (used when service_account.json is absent) ───────────

class _RestQuery:
    """Minimal RTDB query object for order_by_child(...).equal_to(...).get()."""
    def __init__(self, url: str, field: str):
        self._url   = url
        self._field = field
        self._value = None

    def equal_to(self, value):
        self._value = value
        return self

    def get(self):
        params = {"orderBy": f'"{self._field}"', "equalTo": json.dumps(self._value)}
        r = requests.get(self._url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()


class _RestReference:
    """Mimics firebase_admin.db.Reference using the RTDB REST API."""
    def __init__(self, base_url: str, path: str):
        path = path.strip("/")
        self._url = f"{base_url}/{path}.json"

    def get(self):
        r = requests.get(self._url, timeout=10)
        r.raise_for_status()
        return r.json()

    def set(self, data):
        r = requests.put(self._url, json=data, timeout=10)
        r.raise_for_status()

    def update(self, data):
        r = requests.patch(self._url, json=data, timeout=10)
        r.raise_for_status()

    def delete(self):
        r = requests.delete(self._url, timeout=10)
        r.raise_for_status()

    def order_by_child(self, field: str) -> _RestQuery:
        return _RestQuery(self._url.replace(".json", ""), field)


class _RestAdminDB:
    """Mimics the firebase_admin.db module's reference() entry-point."""
    def __init__(self, database_url: str):
        self._base = database_url.rstrip("/")

    def reference(self, path: str = "/") -> _RestReference:
        return _RestReference(self._base, path)


class _StubAdminAuth:
    """No-op admin auth — warns when service account is missing."""
    def delete_user(self, uid: str):
        print(f"[firebase_config] WARNING: delete_user({uid}) skipped — no service account")

    def update_user(self, uid: str, **kwargs):
        print(f"[firebase_config] WARNING: update_user({uid}) skipped — no service account")


# ── firebase-admin — RTDB + Auth admin ────────────────────────────────────────
_use_admin_sdk = os.path.isfile(SERVICE_ACCOUNT_PATH)

if _use_admin_sdk:
    if not firebase_admin._apps:
        _cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(
            _cred,
            {"databaseURL": FIREBASE_CONFIG["databaseURL"]},
        )
    admin_db   = _fb_admin_db    # type: ignore[assignment]
    admin_auth = _fb_admin_auth  # type: ignore[assignment]
else:
    print(
        "[firebase_config] service_account.json not found — "
        "using REST-based RTDB fallback (admin Auth ops will be skipped).\n"
        "  → Download a service account key from Firebase Console → "
        "Project Settings → Service Accounts and save it as service_account.json"
    )
    admin_db   = _RestAdminDB(FIREBASE_CONFIG["databaseURL"])  # type: ignore[assignment]
    admin_auth = _StubAdminAuth()                              # type: ignore[assignment]
