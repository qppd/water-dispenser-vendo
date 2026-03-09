"""
config.py - WDVHost hardware configuration.

Edit these values to match your hardware setup.
These are used as fallbacks; environment variables always take priority.

  PRINTER_PORT   – Serial/COM port for the thermal receipt printer.
                   "auto" = auto-detect  (default)
                   "COM10", "COM5", "/dev/usb/lp0", etc. = explicit port
"""

# Set to the COM port (or device path) of your thermal printer.
# "auto" lets the software detect it.
PRINTER_PORT: str = "COM10"
