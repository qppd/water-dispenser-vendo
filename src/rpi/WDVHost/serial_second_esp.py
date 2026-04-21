"""
serial_second_esp.py — SecondESPSerial

NOTE: ESPWDV now communicates via ESP-Now with ESPWDVAcceptor.
All dispenser commands are sent through SerialManager (/dev/ttyUSB0 →
ESPWDVAcceptor → ESP-Now → ESPWDV).  This class is kept for compatibility
but runs in simulation mode (port=None) by default.

Protocol (RPi → ESPWDVAcceptor → ESP-Now → ESPWDV):
    RPI:<CMD>:<VALUE>
        RPI:RELAY1:<ms>   open relay 1 for <ms> milliseconds
        RPI:RELAY2:<ms>   open relay 2 for <ms> milliseconds
        RPI:RELAY3:<ms>   open relay 3 for <ms> milliseconds
        RPI:SSR1:ON|OFF   control heater SSR1
        RPI:SSR2:ON|OFF   control heater SSR2
        RPI:SSR3:ON|OFF   control cooler SSR3
        RPI:STOP:0        emergency stop — close all relays

Events on event_queue (forwarded by ESPWDVAcceptor via Serial):
    {"type": "temp",       "sensor": "HOT"|"WARM"|"COLD", "value": float}
    {"type": "esp_status", "cmd": str, "value": str}
    {"type": "raw",        "line": str}
"""

import threading
import queue
import re
import time
from typing import Optional

from logger_config import get_logger

logger = get_logger(__name__)

# Reconnect backoff bounds (seconds)
_RECONNECT_MIN = 2.0
_RECONNECT_MAX = 60.0


# ── Message parsers ────────────────────────────────────────────────────────────

# TEMP:HOT:45.2   TEMP:WARM:32.8   TEMP:COLD:12.4
_TEMP_RE = re.compile(r"^TEMP:(HOT|WARM|COLD):([-\d.]+)$")

# ESP:WATER:0 or ESP:WATER:1  — periodic water-level broadcast
_WATER_RE = re.compile(r"^ESP:WATER:([01])$")

# ESP:WATER_LEVEL:0 or ESP:WATER_LEVEL:1  — response to RPI:WATER_LEVEL query
_WATER_LEVEL_RE = re.compile(r"^ESP:WATER_LEVEL:([01])$")

# ESP:STATUS:READY   ESP:DONE:RELAY1   etc.
_ESP_RE = re.compile(r"^ESP:(\w+):(.+)$")


class SecondESPSerial:
    """
    Manages the serial connection to the ESPWDV (dispenser) ESP32
    Runs a background daemon thread for non-blocking serial reads.
    Events are placed onto the shared ``event_queue`` (same queue used
    by SerialManager so main.py has a single polling point).

    Pass ``port=None`` to run in simulation / demo mode (no hardware required).
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        port: Optional[str] = None,
        baud: int = 115200,
    ) -> None:
        self._q       = event_queue
        self._port    = port
        self._baud    = baud
        self._ser     = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._reconnect_delay: float = _RECONNECT_MIN

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open the serial port (if set) and start background reader thread."""
        if self._port:
            try:
                import serial  # type: ignore
                self._ser = serial.Serial(
                    self._port,
                    self._baud,
                    timeout=0.5,
                )
                self._reconnect_delay = _RECONNECT_MIN
                logger.info("[SecondESPSerial] Connected: %s @ %d baud", self._port, self._baud)
            except Exception as exc:
                logger.error("[SecondESPSerial] Cannot open %s: %s", self._port, exc)
                self._ser = None
        else:
            logger.info("[SecondESPSerial] No port – running in simulation mode.")

        self._running = True
        self._thread = threading.Thread(
            target=self._reader,
            daemon=True,
            name="second-esp-reader",
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the reader thread to exit and close the port."""
        self._running = False
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass

    # ── Reader thread (daemon) ─────────────────────────────────────────────────

    def _close_port(self) -> None:
        """Safely close the serial port and set ``_ser`` to None."""
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
        self._ser = None

    def _try_reconnect(self) -> None:
        """Attempt to re-open the serial port with exponential backoff."""
        try:
            import serial  # type: ignore
            self._ser = serial.Serial(self._port, self._baud, timeout=0.5)
            self._reconnect_delay = _RECONNECT_MIN   # reset on success
            logger.info("[SecondESPSerial] Reconnected: %s @ %d", self._port, self._baud)
        except Exception as exc:
            logger.warning(
                "[SecondESPSerial] Reconnect failed (%s) — retry in %.0fs: %s",
                self._port, self._reconnect_delay, exc,
            )
            self._ser = None
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, _RECONNECT_MAX)

    def _reader(self) -> None:
        import serial  # type: ignore
        while self._running:
            if self._ser and self._ser.is_open:
                try:
                    raw = self._ser.readline()
                    if raw:
                        line = raw.decode("utf-8", errors="replace").strip()
                        if line:
                            self._parse(line)
                except serial.SerialException:
                    logger.warning("[SecondESPSerial] Device disconnected: %s", self._port)
                    self._close_port()
                    time.sleep(0.5)
                except Exception as exc:
                    logger.error("[SecondESPSerial] Read error: %s", exc)
                    self._close_port()
                    time.sleep(0.5)
            elif self._port:
                # Port configured but not open — attempt reconnect with backoff
                self._try_reconnect()
            else:
                # No serial connection (simulation mode) – idle
                time.sleep(0.1)

    def is_connected(self) -> bool:
        """Return True if the serial port to ESPWDV is currently open."""
        return bool(self._ser and self._ser.is_open)

    def _parse(self, line: str) -> None:
        """Classify an ESPWDV text line and push a typed event onto the queue."""
        logger.debug("[SecondESPSerial] RX: %s", line)

        # ── Temperature reading ────────────────────────────────────────────────
        m = _TEMP_RE.match(line)
        if m:
            try:
                sensor = m.group(1)          # "HOT", "WARM", or "COLD"
                value  = float(m.group(2))
                self._q.put({"type": "temp", "sensor": sensor, "value": value})
            except ValueError:
                pass
            return

        # ── Water-level broadcast (ESP:WATER:0 / ESP:WATER:1) ────────────────
        m = _WATER_RE.match(line)
        if m:
            self._q.put({"type": "water_level", "present": m.group(1) == "1"})
            return

        # ── Water-level query response (ESP:WATER_LEVEL:0 / 1) ───────────────
        m = _WATER_LEVEL_RE.match(line)
        if m:
            self._q.put({"type": "water_level", "present": m.group(1) == "1"})
            return

        # ── ESP status / completion messages ──────────────────────────────────
        m = _ESP_RE.match(line)
        if m:
            cmd   = m.group(1)
            value = m.group(2)
            if cmd == "DONE":
                # ESP:DONE:RELAY1 / RELAY2 / RELAY3 — relay timer expired,
                # dispense is complete.  Translate to a dispense_complete event
                # so DispensingPage._on_hw_complete() fires correctly.
                self._q.put({"type": "dispense_complete"})
            else:
                self._q.put({"type": "esp_status", "cmd": cmd, "value": value})
            return

        # ── Unrecognised line ──────────────────────────────────────────────────
        self._q.put({"type": "raw", "line": line})

    # ── Command senders ────────────────────────────────────────────────────────

    def send_command(self, cmd: str) -> None:
        """Send an RPI:<CMD>:<VALUE> command, terminated with CRLF."""
        if self._ser and self._ser.is_open:
            try:
                self._ser.write((cmd + "\r\n").encode("utf-8"))
                print(f"[SecondESPSerial] Sent: {cmd}")
            except Exception as exc:
                print(f"[SecondESPSerial] Send error: {exc}")
        else:
            print(f"[SecondESPSerial] (sim) Would send: {cmd}")

    def relay(self, relay_num: int, duration_ms: int) -> None:
        """Open relay <relay_num> (1–3) for <duration_ms> milliseconds."""
        self.send_command(f"RPI:RELAY{relay_num}:{duration_ms}")

    def set_ssr(self, ssr_num: int, on: bool) -> None:
        """Turn SSR <ssr_num> (1–3) on or off."""
        state = "ON" if on else "OFF"
        self.send_command(f"RPI:SSR{ssr_num}:{state}")

    def stop_all(self) -> None:
        """Emergency stop — close all relays immediately."""
        self.send_command("RPI:STOP:0")
