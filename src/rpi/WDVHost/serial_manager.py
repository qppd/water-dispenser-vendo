import threading
import queue
import re
import time
from typing import Optional


_COIN_RE  = re.compile(r"Coin accepted: P(\d+)")
_BILL_RE  = re.compile(r"Bill accepted: P(\d+)")
_DISP_RE  = re.compile(r"Dispensed water", re.IGNORECASE)
_TEMP_RE  = re.compile(r"^TEMP:(HOT|WARM|COLD):([-\d.]+)$")
_WATER_RE = re.compile(r"^ESP:WATER:([01])$")
_WATER_LEVEL_RE = re.compile(r"^ESP:WATER_LEVEL:([01])$")
_ESP_RE   = re.compile(r"^ESP:(\w+):(.+)$")


class SerialManager:
    """
    Manages the serial connection to the ESP32.

    Parameters
    ----------
    event_queue:
        A threading.Queue that receives dicts:
            {"type": "coin",     "value": int}
            {"type": "bill",     "value": int}
            {"type": "dispense_complete"}
            {"type": "raw",      "line": str}
    port:
        Serial port path.  Pass None to run in simulation/demo mode.
    baud:
        Baud rate (must match ESP32 – currently 9600).
    """

    def __init__(
        self,
        event_queue: queue.Queue,
        port: Optional[str] = None,
        baud: int = 9600,
    ) -> None:
        self._q      = event_queue
        self._port   = port
        self._baud   = baud
        self._ser    = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Open serial port (if available) and start background reader thread."""
        if self._port:
            try:
                import serial  # type: ignore
                self._ser = serial.Serial(self._port, self._baud, timeout=0.5)
                print(f"[SerialManager] Connected: {self._port} @ {self._baud}")
            except Exception as exc:
                print(f"[SerialManager] Cannot open {self._port}: {exc}")
                self._ser = None
        else:
            print("[SerialManager] No port – running in simulation mode.")

        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True, name="serial-reader")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._ser and self._ser.is_open:
            self._ser.close()

    # ── Reader thread ─────────────────────────────────────────────────────────

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
                    print(f"[SerialManager] Read error: {exc}")
                    self._close_port()
                    time.sleep(0.1)
            elif self._port:
                # Port configured but not open — attempt reconnect
                self._try_reconnect()
            else:
                # Simulation mode (port=None) — just idle
                time.sleep(0.1)

    def _close_port(self) -> None:
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass
        self._ser = None

    def _try_reconnect(self) -> None:
        try:
            import serial  # type: ignore
            self._ser = serial.Serial(self._port, self._baud, timeout=0.5)
            print(f"[SerialManager] Reconnected: {self._port} @ {self._baud}")
        except Exception as exc:
            print(f"[SerialManager] Reconnect failed ({self._port}): {exc}")
            self._ser = None
            time.sleep(2.0)

    def _parse(self, line: str) -> None:
        """Classify an ESP32 text line and put a typed event onto the queue."""
        m = _COIN_RE.search(line)
        if m:
            self._q.put({"type": "coin", "value": int(m.group(1))})
            return

        m = _BILL_RE.search(line)
        if m:
            self._q.put({"type": "bill", "value": int(m.group(1))})
            return

        if _DISP_RE.search(line):
            self._q.put({"type": "dispense_complete"})
            return

        m = _TEMP_RE.match(line)
        if m:
            try:
                self._q.put({"type": "temp", "sensor": m.group(1), "value": float(m.group(2))})
            except ValueError:
                pass
            return

        m = _WATER_RE.match(line)
        if m:
            self._q.put({"type": "water_level", "present": m.group(1) == "1"})
            return

        m = _WATER_LEVEL_RE.match(line)
        if m:
            self._q.put({"type": "water_level", "present": m.group(1) == "1"})
            return

        m = _ESP_RE.match(line)
        if m:
            cmd, value = m.group(1), m.group(2)
            if cmd == "DONE":
                self._q.put({"type": "dispense_complete"})
            else:
                self._q.put({"type": "esp_status", "cmd": cmd, "value": value})
            return

        # Pass raw lines through for debugging
        self._q.put({"type": "raw", "line": line})

    # ── Command senders ───────────────────────────────────────────────────────

    def send_command(self, cmd: str) -> None:
        """
        Send a command string to the ESP32 terminated with CRLF.
        Silently ignored in simulation mode.
        """
        if self._ser and self._ser.is_open:
            try:
                self._ser.write((cmd + "\r\n").encode("utf-8"))
            except Exception as exc:
                print(f"[SerialManager] Send error: {exc}")
                self._close_port()
        else:
            print(f"[SerialManager] (sim) Would send: {cmd}")

    def dispense(self, duration_ms: int) -> None:
        """Tell ESP32 to open the dispense relay for `duration_ms` ms."""
        self.send_command(f"CMD:DISPENSE:{duration_ms}")

    def fountain(self, duration_ms: int) -> None:
        """Tell ESP32 to activate the fountain relay for `duration_ms` ms."""
        self.send_command(f"CMD:FOUNTAIN:{duration_ms}")

    def stop_flow(self) -> None:
        """Emergency stop – close all relays."""
        self.send_command("CMD:STOP")

    def relay(self, relay_num: int, duration_ms: int) -> None:
        """Open relay <relay_num> (1–3) on ESPWDV for <duration_ms> milliseconds."""
        self.send_command(f"RPI:RELAY{relay_num}:{duration_ms}")

    def set_inlet_valve(self, close: bool) -> None:
        """Persistently control the water inlet solenoid valve (RELAY2).

        close=True  → energize RELAY2 → close inlet valve (tank 100%, stop filling).
        close=False → de-energize RELAY2 → open inlet valve (tank <100%, allow filling).
        """
        self.send_command(f"RPI:INLET:{'ON' if close else 'OFF'}")

    def set_ssr(self, ssr_num: int, on: bool) -> None:
        """Turn SSR <ssr_num> (1–3) on ESPWDV on or off."""
        self.send_command(f"RPI:SSR{ssr_num}:{'ON' if on else 'OFF'}")

    def stop_all(self) -> None:
        """Emergency stop — close all relays on ESPWDV."""
        self.send_command("RPI:STOP:0")

    def query_water_level(self) -> None:
        """Query the current water level from ESPWDV."""
        self.send_command("RPI:WATER_LEVEL:0")

    # ── Enable / Disable controls ─────────────────────────────────────────────

    def enable_coin(self) -> None:
        """Tell ESP32 to enable coin slot processing."""
        self.send_command("ENABLE COIN")

    def disable_coin(self) -> None:
        """Tell ESP32 to disable coin slot processing."""
        self.send_command("DISABLE COIN")

    def enable_bill(self) -> None:
        """Tell ESP32 to enable bill acceptor processing."""
        self.send_command("ENABLE BILL")

    def disable_bill(self) -> None:
        """Tell ESP32 to disable bill acceptor processing."""
        self.send_command("DISABLE BILL")

    # ── Simulation helpers (for testing without hardware) ─────────────────────

    def simulate_coin(self, value: int) -> None:
        """Inject a fake coin event (for UI testing without ESP32)."""
        self._q.put({"type": "coin", "value": value})

    def simulate_bill(self, value: int) -> None:
        """Inject a fake bill event (for UI testing without ESP32)."""
        self._q.put({"type": "bill", "value": value})

    def simulate_dispense_complete(self) -> None:
        self._q.put({"type": "dispense_complete"})

    # ── Port discovery ────────────────────────────────────────────────────────

    @staticmethod
    def find_port() -> Optional[str]:
        """Return the first likely ESP32 serial port, or None."""
        import glob
        candidates = [
            "/dev/ttyUSB0", "/dev/ttyUSB1",
            "/dev/ttyACM0", "/dev/ttyACM1",
        ]
        for pattern in candidates:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None
