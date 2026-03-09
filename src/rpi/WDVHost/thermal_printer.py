"""
thermal_printer.py - Thermal receipt printer module for the WDV kiosk.

Wraps ESC/POS command building and transport for the POS-5805DD (58 mm)
USB thermal printer.  Adapted from the tested sample code in
``src/sample/thermal-printer/``.

Connection types
----------------
- **Serial** (COM / /dev/ttyUSB*): uses pyserial.
- **USB device** (/dev/usb/lp*): direct file I/O.

All public ``print_*()`` methods dispatch the actual I/O to a background
daemon thread so the GUI never blocks.

Cross-platform: Windows (COMx) + Raspberry Pi Debian Trixie ARM64
(/dev/usb/lp*, /dev/ttyUSB*).
"""

import glob
import logging
import os
import platform
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# ── ESC/POS byte constants ────────────────────────────────────────────────────
ESC = b"\x1b"
GS  = b"\x1d"
LF  = b"\x0a"


# ── ESCPOSFormatter ───────────────────────────────────────────────────────────

class ESCPOSFormatter:
    """
    Builds ESC/POS raw byte sequences for common printer operations.

    Every method returns ``bytes`` so commands can be concatenated with ``+``
    before being sent in a single write — minimising round-trips.
    """

    def initialize(self) -> bytes:
        return ESC + b"@"

    # -- Alignment ----------------------------------------------------------
    def align_left(self) -> bytes:
        return ESC + b"a\x00"

    def align_center(self) -> bytes:
        return ESC + b"a\x01"

    def align_right(self) -> bytes:
        return ESC + b"a\x02"

    # -- Style --------------------------------------------------------------
    def bold_on(self) -> bytes:
        return ESC + b"E\x01"

    def bold_off(self) -> bytes:
        return ESC + b"E\x00"

    def underline_on(self) -> bytes:
        return ESC + b"-\x01"

    def underline_off(self) -> bytes:
        return ESC + b"-\x00"

    def double_size_on(self) -> bytes:
        return GS + b"!\x11"

    def normal_size(self) -> bytes:
        return GS + b"!\x00"

    # -- Text ---------------------------------------------------------------
    def text(self, content: str, encoding: str = "cp437") -> bytes:
        return content.encode(encoding, errors="replace") + LF

    def raw_text(self, content: str, encoding: str = "cp437") -> bytes:
        return content.encode(encoding, errors="replace")

    # -- Feed / cut ---------------------------------------------------------
    def feed(self, lines: int = 1) -> bytes:
        lines = max(0, min(lines, 255))
        return ESC + b"d" + bytes([lines])

    def cut(self) -> bytes:
        return GS + b"V\x01"

    def full_cut(self) -> bytes:
        return GS + b"V\x00"

    # -- QR code (native GS ( k) -------------------------------------------
    def qr_code(
        self,
        data: str,
        size: int = 6,
        error_correction: str = "M",
        model: int = 2,
    ) -> bytes:
        size = max(1, min(size, 16))
        model_byte = 49 if model == 1 else 50
        ec_map = {"L": 48, "M": 49, "Q": 50, "H": 51}
        ec_byte = ec_map.get(error_correction.upper(), 49)

        data_bytes = data.encode("utf-8")
        store_len = len(data_bytes) + 3
        pL = store_len & 0xFF
        pH = (store_len >> 8) & 0xFF

        return (
            # fn 0x41 (65): select QR model
            GS + b"(k\x04\x00\x31\x41" + bytes([model_byte]) + b"\x00"
            # fn 0x43 (67): set module (dot) size
            + GS + b"(k\x03\x00\x31\x43" + bytes([size])
            # fn 0x45 (69): set error correction level
            + GS + b"(k\x03\x00\x31\x45" + bytes([ec_byte])
            # fn 0x50 (80): store QR data in symbol storage area
            + GS + b"(k" + bytes([pL, pH]) + b"\x31\x50\x30" + data_bytes
            # fn 0x51 (81): print the stored QR symbol
            + GS + b"(k\x03\x00\x31\x51\x30"
        )


# ── ThermalPrinter ────────────────────────────────────────────────────────────

class ThermalPrinter:
    """
    Manages the USB thermal printer connection and print jobs.

    Parameters
    ----------
    port : str | None
        Serial port (e.g. ``"COM10"``, ``"/dev/ttyUSB0"``) or USB device
        path (``"/dev/usb/lp0"``).  ``None`` = printer unavailable.
    baudrate : int
        Baud rate for serial connections (default 9600).
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 9600,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial = None
        self._device_file = None
        self._lock = threading.Lock()
        self._connected = False

        # /dev/usb/lp* are USB printer devices (not serial)
        self._is_usb_device = bool(
            port and port.startswith("/dev/usb/")
        )

    # ── Connection management ──────────────────────────────────────────────

    def connect(self) -> bool:
        """Open the printer port.  Returns True on success."""
        if not self._port:
            logger.warning("No printer port configured.")
            return False

        try:
            if self._is_usb_device:
                self._device_file = open(self._port, "wb")
                self._connected = True
                logger.info("Printer connected (USB device): %s", self._port)
            else:
                import serial
                self._serial = serial.Serial(
                    port=self._port,
                    baudrate=self._baudrate,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                    timeout=5,
                    write_timeout=5,
                )
                self._connected = self._serial.is_open
                if self._connected:
                    logger.info(
                        "Printer connected (serial): %s @ %d",
                        self._port, self._baudrate,
                    )
            return self._connected
        except Exception as exc:
            logger.error("Cannot open printer %s: %s", self._port, exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the printer port."""
        with self._lock:
            if self._device_file:
                try:
                    self._device_file.close()
                except Exception:
                    pass
                self._device_file = None
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
            self._connected = False
            logger.info("Printer disconnected.")

    def is_connected(self) -> bool:
        """Return True if the printer port is open."""
        return self._connected

    # ── Low-level send ─────────────────────────────────────────────────────

    def _send(self, data: bytes) -> bool:
        """Thread-safe write of raw ESC/POS bytes to the printer."""
        with self._lock:
            try:
                if self._device_file:
                    self._device_file.write(data)
                    self._device_file.flush()
                    return True
                if self._serial and self._serial.is_open:
                    self._serial.write(data)
                    self._serial.flush()
                    return True
            except Exception as exc:
                logger.error("Printer write error: %s", exc)
            return False

    # ── Public print API (all run in background threads) ───────────────────

    def print_receipt(self, transaction: dict) -> None:
        """
        Print a dispensing receipt in a background thread.

        Parameters
        ----------
        transaction : dict
            Keys: ``transaction_id``, ``credit`` (points spent),
            ``volume_ml``, ``service``, ``temperature``.
        """
        threading.Thread(
            target=self._job_receipt,
            args=(transaction,),
            daemon=True,
            name="printer-receipt",
        ).start()

    def print_qr(
        self,
        data: str,
        header: str = "AQUA SPLASH",
        subheader: str = "Scan to Login",
    ) -> None:
        """Print a QR code with header/footer text in a background thread."""
        threading.Thread(
            target=self._job_qr,
            args=(data, header, subheader),
            daemon=True,
            name="printer-qr",
        ).start()

    def print_test(self) -> None:
        """Print a test page in a background thread."""
        threading.Thread(
            target=self._job_test,
            daemon=True,
            name="printer-test",
        ).start()

    # ── Background print jobs ──────────────────────────────────────────────

    def _job_receipt(self, txn: dict) -> None:
        if not self._connected:
            logger.warning("Printer not connected – skipping receipt.")
            return

        fmt = ESCPOSFormatter()
        sep = "-" * 32
        txn_id = txn.get("transaction_id", "N/A")
        credit = txn.get("credit", 0)
        volume = txn.get("volume_ml", 0)
        service = txn.get("service", "")
        temp = txn.get("temperature", "")

        try:
            job: bytes = (
                fmt.initialize()
                + fmt.align_center()
                + fmt.double_size_on()
                + fmt.bold_on()
                + fmt.text("WATER DISPENSER")
                + fmt.normal_size()
                + fmt.bold_off()
                + fmt.text(sep)
                + fmt.align_left()
                + fmt.text(f"Transaction ID: {txn_id}")
                + fmt.text(f"Credit: P{credit}")
                + fmt.text(f"Volume: {volume} mL")
                + fmt.text(f"Service: {service}")
                + fmt.text(f"Temp: {temp}" if temp else "")
                + fmt.text("Water Dispensed")
                + fmt.align_center()
                + fmt.text(sep)
                + fmt.bold_on()
                + fmt.text("Thank you!")
                + fmt.bold_off()
                + fmt.text("Come back again!")
                + fmt.feed(3)
                + fmt.cut()
            )
            ok = self._send(job)
            if ok:
                logger.info("Receipt printed (txn=%s).", txn_id)
            else:
                logger.error("Failed to send receipt data.")
        except Exception as exc:
            logger.exception("Receipt print error: %s", exc)

    def _job_qr(self, data: str, header: str, subheader: str) -> None:
        if not self._connected:
            logger.warning("Printer not connected – skipping QR print.")
            return

        fmt = ESCPOSFormatter()
        try:
            job: bytes = (
                fmt.initialize()
                + fmt.align_center()
                + fmt.bold_on()
                + fmt.text(header)
                + fmt.bold_off()
                + fmt.text(subheader)
                + fmt.feed(1)
                + fmt.qr_code(data, size=6, error_correction="M")
                + fmt.feed(1)
                + fmt.text("Thank you!")
                + fmt.feed(3)
                + fmt.cut()
            )
            ok = self._send(job)
            if ok:
                logger.info("QR printed (data=%s).", data[:50])
            else:
                logger.error("Failed to send QR print data.")
        except Exception as exc:
            logger.exception("QR print error: %s", exc)

    def _job_test(self) -> None:
        if not self._connected:
            logger.warning("Printer not connected – skipping test print.")
            return

        fmt = ESCPOSFormatter()
        sep = "-" * 32
        try:
            job: bytes = (
                fmt.initialize()
                + fmt.align_center()
                + fmt.bold_on()
                + fmt.text("WATER DISPENSER")
                + fmt.bold_off()
                + fmt.text(sep)
                + fmt.text("Printer Test Page")
                + fmt.text("Connection OK")
                + fmt.text(sep)
                + fmt.text("Thank you!")
                + fmt.feed(3)
                + fmt.cut()
            )
            ok = self._send(job)
            if ok:
                logger.info("Test page printed.")
            else:
                logger.error("Failed to send test print data.")
        except Exception as exc:
            logger.exception("Test print error: %s", exc)

    # ── Port auto-detection ────────────────────────────────────────────────

    @staticmethod
    def detect_port() -> Optional[str]:
        """
        Heuristically locate the thermal printer port.

        Checks the ``PRINTER_PORT`` environment variable first; if set,
        that value is returned immediately without scanning.

        Windows
            Scans COM ports for known USB-serial chip keywords
            (CH340, CP210x, FTDI, POS, printer, Bluetooth).

        Linux / Raspberry Pi
            Checks ``/dev/usb/lp*`` first, then ``/dev/ttyUSB*``.

        Returns
        -------
        str | None
            Port path, or ``None`` if no printer was found.
        """
        env_port = os.environ.get("PRINTER_PORT", "").strip()
        if env_port:
            logger.info("Using PRINTER_PORT env var: %s", env_port)
            return env_port

        system = platform.system()
        if system == "Windows":
            return ThermalPrinter._detect_windows()
        if system == "Linux":
            return ThermalPrinter._detect_linux()
        return None

    @staticmethod
    def _detect_windows() -> Optional[str]:
        try:
            import serial.tools.list_ports
        except ImportError:
            return None

        keywords = (
            "pos", "printer", "thermal", "receipt",
            "ch340", "cp210", "ftdi", "usb-serial", "usb serial",
            "bluetooth", "rfcomm", "serial over bluetooth",
        )

        candidates = []
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if any(kw in desc for kw in keywords):
                candidates.append(p)

        if not candidates:
            logger.info("No printer auto-detected on Windows COM ports.")
            return None

        # Among Bluetooth SPP ports there are usually two channels:
        #   LOCALMFG&0000 = local/incoming (PC as server)
        #   LOCALMFG&0002 = remote/outgoing (PC connects to printer) ← prefer this
        for p in candidates:
            hwid = (p.hwid or "").upper()
            if "LOCALMFG&0002" in hwid or "LOCALMFG&0004" in hwid:
                logger.info(
                    "Auto-detected Bluetooth printer (outgoing): %s (%s)",
                    p.device, p.description,
                )
                return p.device

        # Fallback: return first matching port
        p = candidates[0]
        logger.info("Auto-detected printer: %s (%s)", p.device, p.description)
        return p.device

    @staticmethod
    def _detect_linux() -> Optional[str]:
        # USB printer class devices (no serial driver)
        for pattern in ("/dev/usb/lp*",):
            matches = sorted(glob.glob(pattern))
            if matches:
                logger.info("Auto-detected USB printer device: %s", matches[0])
                return matches[0]

        # USB-to-serial adapters
        for pattern in ("/dev/ttyUSB*",):
            matches = sorted(glob.glob(pattern))
            if matches:
                logger.info("Auto-detected serial printer: %s", matches[0])
                return matches[0]

        logger.info("No printer device detected on Linux.")
        return None
