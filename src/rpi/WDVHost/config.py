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
# Permanent udev symlink created by /etc/udev/rules.d/99-wdv-devices.rules
# (VID 0416 / PID 5011 — Winbond Virtual Com Port, mounts as /dev/usb/lp0)
PRINTER_PORT: str = "/dev/thermal_printer"

# Serial port for ESPWDVAcceptor (Silicon Labs CP2102, VID 10c4 / PID ea60).
# Permanent udev symlink: /dev/esp_acceptor → /dev/ttyUSB*
ESP_ACCEPTOR_PORT: str = "/dev/esp_acceptor"
