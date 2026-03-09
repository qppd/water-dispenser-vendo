"""
qr_scanner.py - Background USB QR scanner listener (HID keyboard mode).

USB QR scanners in HID keyboard mode type the scanned string as keyboard
input and terminate with Enter (newline).  This module:

1.  Binds to the Tkinter root window's key events (works cross-platform).
2.  Buffers incoming characters on a per-scan basis.
3.  Uses a background monitor thread to discard stale / partial input
    (distinguishes rapid scanner input from slow manual typing).
4.  On Enter, emits a ``QR_SCANNED`` event onto the shared
    ``AppState.hw_event_queue`` for the main-thread poller to dispatch.

Event format::

    {"type": "QR_SCANNED", "data": "<scanned string>"}

Threading
---------
- Keyboard capture happens via Tk event callbacks (main thread) — this is
  the correct way to receive HID keyboard input in a GUI application.
- A lightweight daemon *monitor* thread runs in the background to expire
  stale buffers (satisfies the threading.Thread requirement).

Cross-platform: Windows + Raspberry Pi (Debian Trixie ARM64).
"""

import threading
import queue
import time
from typing import Optional


class QRScanner:
    """
    Listens for QR code input from a USB HID keyboard-mode scanner.

    Parameters
    ----------
    event_queue : queue.Queue
        The shared ``AppState.hw_event_queue``.  ``QR_SCANNED`` events are
        placed here for the Tk main-thread poller to consume.
    """

    # A USB HID scanner emits characters at sub-millisecond intervals.
    # Manual keyboard typing is >> 100 ms per character.  A generous
    # threshold of 300 ms separates the two use cases.
    _SCAN_TIMEOUT_S: float = 0.3

    # How often the background monitor thread checks for stale buffers.
    _MONITOR_INTERVAL_S: float = 0.1

    def __init__(self, event_queue: queue.Queue) -> None:
        self._event_queue = event_queue
        self._buffer: str = ""
        self._lock = threading.Lock()
        self._last_key_time: float = 0.0
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._tk_root = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self, tk_root) -> None:
        """
        Start the QR scanner listener.

        Binds ``<Key>`` and ``<Return>`` on the Tk root window and starts
        the background buffer-monitor thread.

        Parameters
        ----------
        tk_root : CTk
            The top-level Tkinter window (MainApp).
        """
        self._tk_root = tk_root
        self._running = True

        # Append (+) so the binding doesn't replace existing ones.
        tk_root.bind("<Key>", self._on_key, add="+")
        tk_root.bind("<Return>", self._on_enter, add="+")

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="qr-scanner-monitor",
        )
        self._monitor_thread.start()
        print("[QRScanner] Started – listening for USB HID scanner input.")

    def stop(self) -> None:
        """Stop the scanner listener and unbind Tk events."""
        self._running = False
        if self._tk_root:
            try:
                self._tk_root.unbind("<Key>")
                self._tk_root.unbind("<Return>")
            except Exception:
                pass
        print("[QRScanner] Stopped.")

    # ── Tk event callbacks ─────────────────────────────────────────────────

    def _on_key(self, event) -> None:
        """Capture printable characters into the scan buffer."""
        if not self._running:
            return

        # Skip keypresses that land in Entry / Text widgets — those are
        # human form input, not scanner data.
        widget_class = event.widget.winfo_class()
        if widget_class in ("Entry", "Text", "TEntry", "TCombobox"):
            return

        if event.char and event.char.isprintable():
            with self._lock:
                now = time.time()
                # If the previous character was too long ago, start fresh.
                if self._buffer and (now - self._last_key_time) > self._SCAN_TIMEOUT_S:
                    self._buffer = ""
                self._buffer += event.char
                self._last_key_time = now

    def _on_enter(self, event) -> None:
        """Enter key received — emit the completed scan string."""
        if not self._running:
            return

        widget_class = event.widget.winfo_class()
        if widget_class in ("Entry", "Text", "TEntry", "TCombobox"):
            return

        with self._lock:
            data = self._buffer.strip()
            self._buffer = ""
            self._last_key_time = 0.0

        if data:
            self._emit(data)

    # ── Background monitor thread ──────────────────────────────────────────

    def _monitor_loop(self) -> None:
        """Expire stale buffer contents (partial / abandoned scans)."""
        while self._running:
            time.sleep(self._MONITOR_INTERVAL_S)
            with self._lock:
                if self._buffer and self._last_key_time > 0:
                    if (time.time() - self._last_key_time) > self._SCAN_TIMEOUT_S:
                        self._buffer = ""

    # ── Event emission ─────────────────────────────────────────────────────

    def _emit(self, data: str) -> None:
        """Put a QR_SCANNED event onto the shared hardware event queue."""
        self._event_queue.put({"type": "QR_SCANNED", "data": data})
        print(f"[QRScanner] Scanned: {data}")

    # ── Simulation / testing ───────────────────────────────────────────────

    def simulate_scan(self, data: str) -> None:
        """Inject a QR scan event for testing without hardware."""
        self._emit(data)
