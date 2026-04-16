"""
config.py – Project-wide configuration for the Bluetooth thermal printer demo.

Edit the values in this file to match your hardware setup before running
test_print.py.
"""

import platform

# ---------------------------------------------------------------------------
# Runtime OS detection (do not edit)
# ---------------------------------------------------------------------------
_SYSTEM = platform.system()   # "Windows" | "Linux" | "Darwin"

# ---------------------------------------------------------------------------
# Printer connection
# ---------------------------------------------------------------------------
# Serial port for the thermal printer.
#
#   USB printer class (usblp) — Winbond 0416:5011 Virtual Com Port.
#   A permanent udev symlink is created by /etc/udev/rules.d/99-thermal-printer.rules.
#   Windows: check Device Manager ▶ Ports. Typical values: "COM5", "COM6"
#
# Set to "auto" to let the program scan and pick the first available port.
PRINTER_PORT: str = "COM5" if _SYSTEM == "Windows" else "/dev/thermal_printer"

# Baud rate – POS-5805DD default is 9600.
BAUDRATE: int = 9600

# Serial read/write timeout in seconds.
TIMEOUT: int = 5

# ---------------------------------------------------------------------------
# QR code content
# ---------------------------------------------------------------------------
# The string that will be encoded inside the QR code.
# Can be a URL, plain text, numeric ID, etc.
QR_DATA: str = "https://smart-vendo.local/pay?id=12345"

# ---------------------------------------------------------------------------
# Print layout text
# ---------------------------------------------------------------------------
HEADER_TEXT: str    = "SMART WATER DISPENSER"
SUBHEADER_TEXT: str = "Scan QR Code"
FOOTER_TEXT: str    = "Thank you!"

# ---------------------------------------------------------------------------
# QR code appearance
# ---------------------------------------------------------------------------
# Module (dot) size: 1 (tiny) – 16 (large).
# Recommended range for 58 mm paper: 5–8.
QR_BOX_SIZE: int = 6

# Error correction level.
#   "L" =  7% data recovery
#   "M" = 15% data recovery  ← good default
#   "Q" = 25% data recovery
#   "H" = 30% data recovery
QR_ERROR_CORRECTION: str = "M"
