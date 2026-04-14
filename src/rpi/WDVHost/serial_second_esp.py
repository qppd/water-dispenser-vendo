"""
serial_second_esp.py — SecondESPSerial

Manages the hardware UART connection to ESPWDV (water dispenser ESP32).

Hardware wiring:
    RPi GPIO14 (TXD, Pin 8)  → ESP32 GPIO16 (RX, UART2)
    RPi GPIO15 (RXD, Pin 10) ← ESP32 GPIO17 (TX, UART2)
    Port:  /dev/serial0
    Baud:  115200

Protocol (ESP32 → RPi):
    TEMP:HOT:<value>      periodic temperature reading (°C)
    TEMP:WARM:<value>     periodic temperature reading (°C)
    TEMP:COLD:<value>     periodic temperature reading (°C)
    ESP:<CMD>:<VALUE>     status / completion messages
        ESP:STATUS:READY  — sent on ESP32 boot
        ESP:DONE:RELAY1   — relay closed after dispense
        ESP:FLOW1:<rate>  — flow rate in L/min
        ESP:VOL1:<vol>    — total volume in mL
        ESP:SSR1:ON|OFF   — SSR state acknowledgment
        ESP:STOP:OK       — emergency stop confirmed

Protocol (RPi → ESP32):
    RPI:<CMD>:<VALUE>
        RPI:RELAY1:<ms>   open relay 1 for <ms> milliseconds
        RPI:RELAY2:<ms>   open relay 2 for <ms> milliseconds
        RPI:RELAY3:<ms>   open relay 3 for <ms> milliseconds
        RPI:SSR1:ON|OFF   control heater SSR1
        RPI:SSR2:ON|OFF   control heater SSR2
        RPI:SSR3:ON|OFF   control cooler SSR3
        RPI:STOP:0        emergency stop — close all relays

Events put onto event_queue (same hw_event_queue shared with SerialManager):
    {"type": "temp",       "sensor": "HOT"|"WARM"|"COLD", "value": float}
    {"type": "esp_status", "cmd": str, "value": str}
    {"type": "raw",        "line": str}
"""

import threading
import queue
import re
import time
from typing import Optional


# ── Message parsers ────────────────────────────────────────────────────────────

# TEMP:HOT:45.2   TEMP:WARM:32.8   TEMP:COLD:12.4
_TEMP_RE = re.compile(r"^TEMP:(HOT|WARM|COLD):([-\d.]+)$")

# ESP:STATUS:READY   ESP:DONE:RELAY1   etc.
_ESP_RE = re.compile(r"^ESP:(\w+):(.+)$")


class SecondESPSerial:
    """
    Manages the serial connection to the ESPWDV (dispenser) ESP32
    via hardware UART (/dev/serial0 on Raspberry Pi Zero W).

    Runs a background daemon thread for non-blocking serial reads.
    Events are placed onto the shared ``event_queue`` (same queue used
    by SerialManager so main.py has a single polling point).

    Pass ``port=None`` to run in simulation / demo mode (no hardware required).
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        port: Optional[str] = "/dev/serial0",
        baud: int = 115200,
    ) -> None:
        self._q       = event_queue
        self._port    = port
        self._baud    = baud
        self._ser     = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open /dev/serial0 (if available) and start background reader thread."""
        if self._port:
            try:
                import serial  # type: ignore
                self._ser = serial.Serial(
                    self._port,
                    self._baud,
                    timeout=0.5,
                )
                print(f"[SecondESPSerial] Connected: {self._port} @ {self._baud} baud")
            except Exception as exc:
                print(f"[SecondESPSerial] Cannot open {self._port}: {exc}")
                self._ser = None
        else:
            print("[SecondESPSerial] No port – running in simulation mode.")

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
            self._ser.close()

    # ── Reader thread (daemon) ─────────────────────────────────────────────────

    def _reader(self) -> None:
        while self._running:
            if self._ser and self._ser.is_open:
                try:
                    raw = self._ser.readline()
                    if raw:
                        line = raw.decode("utf-8", errors="replace").strip()
                        if line:
                            self._parse(line)
                except Exception as exc:
                    print(f"[SecondESPSerial] Read error: {exc}")
                    time.sleep(0.1)
            else:
                # No serial connection – idle
                time.sleep(0.1)

    def _parse(self, line: str) -> None:
        """Classify an ESPWDV text line and push a typed event onto the queue."""
        print(f"[ESPWDV] {line}")

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
