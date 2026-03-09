"""
bluetooth_printer.py – Serial transport layer for ESC/POS Bluetooth printers.

Provides:
    BluetoothPrinter     – context-manager class that wraps a pyserial port.
    detect_printer_port  – heuristic auto-detection for Windows COM ports and
                           Linux RFCOMM devices.
    connect_printer      – convenience factory; raises ConnectionError on failure.

Platform support:
    Windows  : COM ports  (e.g. "COM5")
    Linux/RPi: RFCOMM devices  (e.g. "/dev/rfcomm0")
"""

import os
import platform
import logging
from typing import Optional

import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BluetoothPrinter
# ---------------------------------------------------------------------------

class BluetoothPrinter:
    """
    Manages a serial (Bluetooth RFCOMM / COM port) connection to an ESC/POS
    thermal printer.

    This class is a *transport only* – it sends raw bytes.  All ESC/POS
    command formatting is the responsibility of ``printer_qr.py``.

    Recommended usage – context manager:

        with BluetoothPrinter("COM5") as p:
            p.send(b"\\x1b@Hello\\n")

    Manual usage:

        p = BluetoothPrinter("/dev/rfcomm0")
        p.connect()
        p.send(data)
        p.disconnect()
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: int  = 5,
    ) -> None:
        """
        Args:
            port     : Serial port (e.g. "COM5" or "/dev/rfcomm0").
            baudrate : Baud rate – POS-5805DD default is 9600.
            timeout  : Read/write timeout in seconds.
        """
        self.port     = port
        self.baudrate = baudrate
        self.timeout  = timeout
        self._serial: Optional[serial.Serial] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Open the serial port.

        Returns:
            True if the port was opened successfully, False otherwise.
        """
        try:
            self._serial = serial.Serial(
                port          = self.port,
                baudrate      = self.baudrate,
                bytesize      = serial.EIGHTBITS,
                parity        = serial.PARITY_NONE,
                stopbits      = serial.STOPBITS_ONE,
                timeout       = self.timeout,
                write_timeout = self.timeout,
            )
            if self._serial.is_open:
                logger.info(
                    "Connected to printer on %s @ %d baud.",
                    self.port, self.baudrate,
                )
                return True
            return False  # pragma: no cover

        except serial.SerialException as exc:
            logger.error("Cannot open %s: %s", self.port, exc)
            return False

    def disconnect(self) -> None:
        """Close the serial port if it is open."""
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Disconnected from %s.", self.port)

    # ------------------------------------------------------------------
    # Data transfer
    # ------------------------------------------------------------------

    def send(self, data: bytes) -> bool:
        """
        Write raw bytes to the printer.

        Args:
            data: Byte string to transmit (ESC/POS commands + text).

        Returns:
            True if all bytes were written successfully.
        """
        if not self.is_connected():
            logger.error("Printer is not connected – call connect() first.")
            return False

        try:
            written = self._serial.write(data)   # type: ignore[union-attr]
            self._serial.flush()                 # type: ignore[union-attr]
            logger.debug("Sent %d bytes to printer.", written)
            return True

        except serial.SerialTimeoutException:
            logger.error("Write timeout on %s.", self.port)
            return False

        except serial.SerialException as exc:
            logger.error("Serial write error on %s: %s", self.port, exc)
            return False

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        """Return True if the underlying serial port is open."""
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "BluetoothPrinter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected() else "disconnected"
        return f"BluetoothPrinter(port={self.port!r}, status={status})"


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------

def detect_printer_port() -> Optional[str]:
    """
    Heuristically locate the Bluetooth printer's serial port.

    - **Windows**: Searches the pyserial COM-port list for descriptions that
      contain "bluetooth", "pos", or "printer".  Falls back to probing
      COM1–COM20 for the first port that can be opened.
    - **Linux / Raspberry Pi**: Returns the first existing ``/dev/rfcommN``
      (N = 0–9).

    Returns:
        Port string (e.g. ``"COM5"`` or ``"/dev/rfcomm0"``), or ``None``
        if no port was found.
    """
    system = platform.system()
    if system == "Windows":
        return _detect_windows()
    if system in ("Linux", "Darwin"):
        return _detect_linux()
    logger.warning("Port auto-detection is not supported on %s.", system)
    return None


def _detect_windows() -> Optional[str]:
    """Scan Windows COM ports for a Bluetooth printer."""
    keywords = ("bluetooth", "pos", "printer", "rfcomm", "serial")
    ports    = serial.tools.list_ports.comports()

    # Prefer ports whose description matches a known keyword.
    for p in ports:
        if any(kw in p.description.lower() for kw in keywords):
            logger.info(
                "Auto-detected printer port: %s (%s).", p.device, p.description
            )
            return p.device

    # Fall back: probe COM1–COM20 for the first port that opens cleanly.
    for n in range(1, 21):
        port = f"COM{n}"
        try:
            with serial.Serial(port, 9600, timeout=1):
                logger.info("Auto-detected open COM port: %s.", port)
                return port
        except serial.SerialException:
            pass

    logger.warning("No Bluetooth printer COM port was found automatically.")
    return None


def _detect_linux() -> Optional[str]:
    """Return the first existing /dev/rfcommN device."""
    for n in range(10):
        port = f"/dev/rfcomm{n}"
        if os.path.exists(port):
            logger.info("Auto-detected RFCOMM port: %s.", port)
            return port

    logger.warning(
        "No /dev/rfcommN device found.  "
        "Run: sudo rfcomm bind 0 <PRINTER_MAC_ADDRESS>"
    )
    return None


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def connect_printer(port: str, baudrate: int = 9600) -> BluetoothPrinter:
    """
    Create a :class:`BluetoothPrinter`, connect it, and return it.

    Args:
        port    : Serial port string.
        baudrate: Baud rate (default 9600).

    Returns:
        A connected :class:`BluetoothPrinter` instance.

    Raises:
        ConnectionError: If the port cannot be opened.
    """
    printer = BluetoothPrinter(port, baudrate)
    if not printer.connect():
        raise ConnectionError(f"Failed to connect to printer on {port!r}.")
    return printer
