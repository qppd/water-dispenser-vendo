"""
logger_config.py — Centralized file-based logging for WDV Kiosk.

All modules should call get_logger(__name__) to get a named logger that
writes to both the rotating log file and the console (stdout).

Usage
-----
    from logger_config import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
    logger.error("Something went wrong: %s", exc)

Log file
--------
Stored at  <WDVHost>/logs/wdv_kiosk.log
Rotated at 5 MB, 3 backup files kept (≈ 15 MB total).
"""

import logging
import os
from logging.handlers import RotatingFileHandler


# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
_LOG_DIR  = os.path.join(_HERE, "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "wdv_kiosk.log")

# ── Rotation settings ─────────────────────────────────────────────────────────
_MAX_BYTES    = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3                  # keep 3 old files → max 20 MB on disk

# ── Sentinel to prevent double-init ──────────────────────────────────────────
_initialized = False


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger with a rotating file handler and a console handler.

    Call this ONCE at application startup (main.py).
    Subsequent calls are no-ops.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    os.makedirs(_LOG_DIR, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # ── Rotating file handler ─────────────────────────────────────────────────
    try:
        fh = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as exc:
        # Non-fatal: log files may be unavailable on some setups
        print(f"[logger_config] Cannot open log file {_LOG_FILE}: {exc}")

    # ── Console (stdout) handler ──────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    root.info("[logger_config] Logging initialized — file: %s", _LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger ready for use (call setup_logging first)."""
    return logging.getLogger(name)
