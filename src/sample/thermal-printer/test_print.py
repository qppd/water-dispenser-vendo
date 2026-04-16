"""
test_print.py – Demo script: connect to a Bluetooth printer and print a QR code.

Usage:
    python test_print.py                  # uses settings from config.py
    python test_print.py COM6             # override port (Windows)
    python test_print.py /dev/rfcomm1     # override port (Raspberry Pi)

Expected printer output:
    ┌──────────────────────────────┐
    │   SMART WATER DISPENSER      │
    │   Scan QR Code               │
    │                              │
    │        [QR CODE]             │
    │                              │
    │   Thank you!                 │
    └──────────────────────────────┘
"""

import logging
import sys

from config import (
    BAUDRATE,
    FOOTER_TEXT,
    HEADER_TEXT,
    PRINTER_PORT,
    QR_BOX_SIZE,
    QR_DATA,
    QR_ERROR_CORRECTION,
    SUBHEADER_TEXT,
)
from bluetooth_printer import BluetoothPrinter, detect_printer_port
from printer_qr import print_qr

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  [%(levelname)-8s]  %(name)s  %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_raw_device(port: str) -> bool:
    """Return True if port should be written as a raw file (hidraw / USB lp)."""
    _RAW_PREFIXES = ("/dev/usb/", "/dev/hidraw")
    if any(port.startswith(p) for p in _RAW_PREFIXES):
        return True
    try:
        import os
        resolved = os.path.realpath(port)
        return any(resolved.startswith(p) for p in _RAW_PREFIXES)
    except OSError:
        return False


def _resolve_port() -> str:
    """
    Determine which serial port to use, in priority order:

    1. Command-line argument  (``python test_print.py COM6``)
    2. Auto-detection         (when ``PRINTER_PORT = "auto"`` in config.py)
    3. Value from config.py
    """
    if len(sys.argv) > 1:
        port = sys.argv[1]
        logger.info("Using port supplied on command line: %s", port)
        return port

    if PRINTER_PORT.strip().lower() == "auto":
        logger.info("Auto-detecting Bluetooth printer port …")
        port = detect_printer_port()
        if not port:
            logger.error(
                "Auto-detection failed.  "
                "Set PRINTER_PORT in config.py or pass the port as an argument."
            )
            sys.exit(1)
        logger.info("Auto-detected port: %s", port)
        return port

    return PRINTER_PORT


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("="*52)
    logger.info("  Smart Water Dispenser – Thermal Printer Demo")
    logger.info("="*52)

    port = _resolve_port()
    logger.info("Connecting to printer on %s …", port)

    # ── Raw USB HID / lp device (no serial driver) ────────────────────────────
    if _is_raw_device(port):
        logger.info("Detected raw USB device – using direct file write.")
        from printer_qr import ESCPOSFormatter
        fmt = ESCPOSFormatter()
        sep = "-" * 32
        job: bytes = (
            fmt.initialize()
            + fmt.align_center()
            + fmt.bold_on()
            + fmt.text(HEADER_TEXT)
            + fmt.bold_off()
            + fmt.text(sep)
            + fmt.text(SUBHEADER_TEXT)
            + fmt.qr_code(QR_DATA, size=QR_BOX_SIZE, error_correction=QR_ERROR_CORRECTION)
            + fmt.text(sep)
            + fmt.text(FOOTER_TEXT)
            + fmt.feed(3)
            + fmt.cut()
        )
        try:
            with open(port, "wb") as f:
                f.write(job)
                f.flush()
            logger.info("Done!  Check your printer output.")
        except Exception as exc:
            logger.error("Print failed: %s", exc)
            sys.exit(1)
        return

    # ── Bluetooth / RFCOMM / serial path ─────────────────────────────────────
    logger.info("Using Bluetooth/serial transport.")
    with BluetoothPrinter(port, BAUDRATE) as printer:

        if not printer.is_connected():
            logger.error(
                "Could not open %s.  "
                "Make sure the printer is powered on, paired, and "
                "the port name is correct.",
                port,
            )
            sys.exit(1)

        logger.info("Printer connected.  Sending QR print job …")
        success = print_qr(
            data             = QR_DATA,
            printer          = printer,
            header           = HEADER_TEXT,
            subheader        = SUBHEADER_TEXT,
            footer           = FOOTER_TEXT,
            qr_size          = QR_BOX_SIZE,
            error_correction = QR_ERROR_CORRECTION,
        )

    if success:
        logger.info("Done!  Check your printer output.")
    else:
        logger.error("Print job failed.  See log messages above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
