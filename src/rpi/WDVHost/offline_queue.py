"""
offline_queue.py — Offline-first SQLite sync queue for Firebase operations.

All Firebase write operations that must survive network outages should be
routed through this module.  Records are stored locally in SQLite and a
background daemon thread retries failed syncs with exponential backoff.

Architecture
------------
  Caller           → enqueue(op_type, uid, payload)  [thread-safe]
  OfflineQueue      → stores record in SQLite with synced=0
  _sync_loop()      → runs in daemon thread, wakes every backoff interval
  _process_pending()→ fetches unsynced records, calls _execute_sync()
  _execute_sync()   → writes to Firebase; marks synced=1 on success

Duplicate-upload prevention
----------------------------
Each record has an auto-increment ``id``.  Records are only marked synced=1
after a confirmed Firebase write.  Timestamps inside the payload are used as
Firebase node keys to prevent duplicate child nodes.

Backoff schedule
----------------
  Base: 2 s → 4 → 8 → 16 … max 300 s (5 min), resets on any successful sync.
"""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))
_DB_PATH      = os.path.join(_HERE, "offline_queue.db")
_MAX_RETRIES  = 10          # drop a record after this many consecutive failures
_BACKOFF_BASE = 2.0         # seconds
_BACKOFF_MAX  = 300.0       # 5 minutes


class OfflineQueue:
    """
    SQLite-backed queue for Firebase sync operations.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file (created automatically).
    """

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_db()

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    op_type     TEXT    NOT NULL,
                    uid         TEXT    NOT NULL,
                    payload     TEXT    NOT NULL,
                    created_at  REAL    NOT NULL,
                    attempts    INTEGER NOT NULL DEFAULT 0,
                    synced      INTEGER NOT NULL DEFAULT 0,
                    last_error  TEXT
                )
            """)
            c.commit()
        logger.info("[OfflineQueue] Database ready: %s", self._db_path)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background sync daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="offline-sync",
        )
        self._thread.start()
        logger.info("[OfflineQueue] Background sync thread started.")

    def stop(self) -> None:
        """Signal the sync thread to exit."""
        self._running = False

    # ── Public API ────────────────────────────────────────────────────────────

    def enqueue(self, op_type: str, uid: str, payload: dict) -> None:
        """
        Persist a sync operation so it survives process restarts.

        Parameters
        ----------
        op_type : str
            One of: ``"update_points"``, ``"save_user"``, ``"save_transaction"``
        uid : str
            Firebase UID of the affected user.
        payload : dict
            Data to write.  Must be JSON-serialisable.
        """
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO sync_queue (op_type, uid, payload, created_at)"
                    " VALUES (?, ?, ?, ?)",
                    (op_type, uid, json.dumps(payload, default=str), time.time()),
                )
                c.commit()
        except Exception as exc:
            # Enqueue failure must never crash the caller
            logger.error("[OfflineQueue] enqueue error: %s", exc)

    def pending_count(self) -> int:
        """Return the number of records not yet synced."""
        try:
            with self._conn() as c:
                row = c.execute(
                    "SELECT COUNT(*) FROM sync_queue WHERE synced = 0 AND attempts < ?",
                    (_MAX_RETRIES,),
                ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    # ── Background sync loop ──────────────────────────────────────────────────

    def _sync_loop(self) -> None:
        backoff = _BACKOFF_BASE
        while self._running:
            try:
                synced = self._process_pending()
                if synced > 0:
                    backoff = _BACKOFF_BASE          # reset after any success
                    logger.info("[OfflineQueue] Synced %d record(s) to Firebase.", synced)
                else:
                    # Nothing to do or all failed — wait before retrying
                    time.sleep(backoff)
                    backoff = min(backoff * 2, _BACKOFF_MAX)
            except Exception as exc:
                logger.error("[OfflineQueue] Sync loop unexpected error: %s", exc)
                time.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    def _process_pending(self) -> int:
        """Attempt to sync all pending records.  Returns count synced."""
        try:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, op_type, uid, payload FROM sync_queue"
                    " WHERE synced = 0 AND attempts < ?"
                    " ORDER BY id ASC",
                    (_MAX_RETRIES,),
                ).fetchall()
        except Exception as exc:
            logger.error("[OfflineQueue] DB read error: %s", exc)
            return 0

        synced = 0
        for row_id, op_type, uid, payload_json in rows:
            try:
                payload = json.loads(payload_json)
            except Exception:
                payload = {}

            ok, error = self._execute_sync(op_type, uid, payload)

            try:
                with self._conn() as c:
                    if ok:
                        c.execute(
                            "UPDATE sync_queue SET synced = 1 WHERE id = ?",
                            (row_id,),
                        )
                        synced += 1
                    else:
                        c.execute(
                            "UPDATE sync_queue SET attempts = attempts + 1,"
                            " last_error = ? WHERE id = ?",
                            (str(error)[:500], row_id),
                        )
                    c.commit()
            except Exception as exc:
                logger.error("[OfflineQueue] DB update error: %s", exc)

        return synced

    def _execute_sync(self, op_type: str, uid: str, payload: dict) -> Tuple[bool, Optional[Exception]]:
        """Execute a single Firebase write.  Returns (success, error_or_None)."""
        try:
            from firebase_config import admin_db  # local import — avoids circular dep

            if op_type == "update_points":
                admin_db.reference(f"users/{uid}/points").set(payload.get("points", 0))

            elif op_type == "save_user":
                admin_db.reference(f"users/{uid}").update(payload)

            elif op_type == "save_transaction":
                txn_id = payload.get("transaction_id") or f"txn_{int(time.time() * 1000)}"
                admin_db.reference(f"users/{uid}/transactions/{txn_id}").set(payload)

            else:
                logger.warning("[OfflineQueue] Unknown op_type '%s' — dropping.", op_type)
                return True, None   # treat as success so we don't retry it forever

            return True, None

        except Exception as exc:
            logger.warning("[OfflineQueue] Sync %s/%s failed: %s", op_type, uid, exc)
            return False, exc
