import threading
import queue
import re
import time
from typing import Optional


_COIN_RE  = re.compile(r"Coin accepted: P(\d+)")
_BILL_RE  = re.compile(r"Bill accepted: P(\d+)")
_DISP_RE  = re.compile(r"Dispensed water", re.IGNORECASE)


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
            else:
                # No serial connection – just idle
                time.sleep(0.1)

    def _parse(self, line: str) -> None:
        """Classify an ESP32 text line and put a typed event onto the queue."""
        print(f"[ESP32] {line}")

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
                print(f"[SerialManager] Sent: {cmd}")
            except Exception as exc:
                print(f"[SerialManager] Send error: {exc}")
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
            "/dev/serial0",
        ]
        for pattern in candidates:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None
