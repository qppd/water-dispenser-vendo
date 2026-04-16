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

    # -- QR code: raster bitmap (GS v 0) -----------------------------------
    # Renders QR code via qrcode+Pillow then sends as ESC/POS raster image.
    # Works on all thermal printers; no native GS(k support required.
    def qr_code(
        self,
        data: str,
        box_size: int = 16,
        border: int = 2,
        max_width: int = 384,
        max_height: int = 200,
    ) -> bytes:
        import qrcode  # type: ignore
        from PIL import Image as PILImage  # type: ignore

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("1")

        w, h = img.size
        if w > max_width:
            scale = max_width / w
            w, h = int(w * scale), int(h * scale)
            img = img.resize((w, h), PILImage.LANCZOS)
        if h > max_height:
            scale = max_height / h
            w, h = int(w * scale), int(h * scale)
            img = img.resize((w, h), PILImage.LANCZOS)

        # Pad width to a multiple of 8 for byte packing
        row_bytes = (w + 7) // 8
        padded_w = row_bytes * 8
        if padded_w != w:
            canvas = PILImage.new("1", (padded_w, h), 1)  # white=1 in mode "1"
            canvas.paste(img, (0, 0))
            img = canvas

        pixels = img.load()
        raster = bytearray()
        for y in range(h):
            for bx in range(row_bytes):
                byte_val = 0
                for bit in range(8):
                    x = bx * 8 + bit
                    # PIL mode "1": 0=black, 1(or 255)=white
                    # ESC/POS GS v 0: bit 1=dot(black), 0=white
                    if pixels[x, y] == 0:
                        byte_val |= 0x80 >> bit
                raster.append(byte_val)

        xL = row_bytes & 0xFF
        xH = (row_bytes >> 8) & 0xFF
        yL = h & 0xFF
        yH = (h >> 8) & 0xFF
        # GS v 0: 0x1D 0x76 0x30  m  xL xH yL yH  <data>
        return GS + b"\x76\x30\x00" + bytes([xL, xH, yL, yH]) + bytes(raster)


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

        # Raw-file devices (not serial): /dev/usb/lp*, /dev/hidraw*, and
        # symlinks that resolve to either of those paths.
        self._is_usb_device = self._detect_raw_device(port)

    @staticmethod
    def _detect_raw_device(port: Optional[str]) -> bool:
        """Return True if the port should be opened as a raw file, not serial."""
        if not port:
            return False
        _RAW_PREFIXES = ("/dev/usb/", "/dev/hidraw")
        if any(port.startswith(p) for p in _RAW_PREFIXES):
            return True
        # Resolve symlinks (e.g. /dev/thermal_printer → hidraw1)
        try:
            resolved = os.path.realpath(port)
            return any(resolved.startswith(p) for p in _RAW_PREFIXES)
        except OSError:
            return False

    # ── Connection management ──────────────────────────────────────────────

    def connect(self) -> bool:
        """Open the printer port.  Returns True on success."""
        if not self._port:
            logger.warning("No printer port configured.")
            return False

        try:
            if self._is_usb_device:
                # Verify device is accessible. Don't hold the descriptor open
                # between jobs — LP drivers treat open()/close() as job boundaries.
                open(self._port, "wb").close()
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
                if self._is_usb_device and self._port:
                    with open(self._port, "wb") as f:
                        f.write(data)
                        f.flush()
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
        sep = "-" * 32
        try:
            job: bytes = (
                fmt.initialize()
                + fmt.align_center()
                + fmt.bold_on()
                + fmt.text(header)
                + fmt.bold_off()
                + fmt.text(sep)
                + fmt.text(subheader)
                + fmt.qr_code(data)
                + fmt.text(sep)
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
        import subprocess

        # 0. Permanent udev symlink (created by 99-thermal-printer.rules) — highest priority
        if os.path.exists("/dev/thermal_printer"):
            logger.info("Auto-detected printer via udev symlink: /dev/thermal_printer")
            return "/dev/thermal_printer"

        # 1a. hidraw devices (USB HID printers — raw byte writes)
        hidraw_matches = sorted(glob.glob("/dev/hidraw*"))
        if hidraw_matches:
            logger.info("Auto-detected hidraw printer device: %s", hidraw_matches[0])
            return hidraw_matches[0]

        # 1b. USB printer class devices (no serial driver)
        lp_matches = sorted(glob.glob("/dev/usb/lp*"))
        if lp_matches:
            logger.info("Auto-detected USB printer device: %s", lp_matches[0])
            return lp_matches[0]

        # 2. USB-to-serial: identify printer by sysfs VID, skip ESP32 adapters
        #    CH340/CH341 = 0x1a86, CP210x = 0x10c4, FT232 = 0x0403
        ESP_VIDS = {"1a86", "10c4", "0403"}
        for dev in sorted(glob.glob("/dev/ttyUSB*")):
            idx = dev.replace("/dev/ttyUSB", "")
            vid_path = f"/sys/bus/usb-serial/devices/ttyUSB{idx}/../../../idVendor"
            try:
                with open(vid_path) as fh:
                    vid = fh.read().strip().lower()
                if vid not in ESP_VIDS:
                    logger.info(
                        "Auto-detected printer via sysfs VID %s: %s", vid, dev
                    )
                    return dev
            except OSError:
                pass

        # 3. Fallback: use lsusb to confirm USB devices are present, then return
        #    the first ttyUSB* that is not ttyUSB0 (reserved for ESPWDVAcceptor)
        ttyusb_all = sorted(glob.glob("/dev/ttyUSB*"))
        if ttyusb_all:
            try:
                subprocess.check_call(
                    ["lsusb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except Exception:
                pass
            for dev in ttyusb_all:
                if dev != "/dev/ttyUSB0":
                    logger.info("Auto-detected printer (lsusb fallback): %s", dev)
                    return dev

        logger.info("No printer device detected on Linux.")
        return None
