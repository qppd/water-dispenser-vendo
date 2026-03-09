"""
printer_qr.py – ESC/POS print-job builder for Bluetooth thermal printers.

Provides:
    ESCPOSFormatter  – low-level byte builder for ESC/POS commands.
    print_qr()       – print a QR code with header / footer text.
    print_receipt()  – print a full water-vendo receipt with QR code.

QR codes are rendered natively on the printer using  GS ( k  commands.
Hardware rendering produces sharper output than bitmap approaches and
requires no Pillow / image-processing work on the host.

ESC/POS GS ( k reference (QR Code symbol):
    Function 0xA5 – Select model
    Function 0xA7 – Set module (dot) size
    Function 0xA9 – Set error correction level
    Function 0xB0 – Store data in symbol storage area
    Function 0xB1 – Print stored symbol
"""

import logging
from typing import Optional

from bluetooth_printer import BluetoothPrinter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ESC/POS byte constants
# ---------------------------------------------------------------------------
ESC = b"\x1b"   # Escape
GS  = b"\x1d"   # Group Separator
LF  = b"\x0a"   # Line Feed


# ---------------------------------------------------------------------------
# ESCPOSFormatter
# ---------------------------------------------------------------------------

class ESCPOSFormatter:
    """
    Builds ESC/POS raw byte sequences for common printer operations.

    Every method returns a ``bytes`` object so commands can be concatenated
    cleanly with ``+`` before being sent in a single :meth:`BluetoothPrinter.send`
    call – minimising Bluetooth round-trips.

    Example::

        fmt = ESCPOSFormatter()
        job = (
            fmt.initialize()
            + fmt.align_center()
            + fmt.bold_on()
            + fmt.text("Hello, printer!")
            + fmt.bold_off()
            + fmt.qr_code("https://example.com")
            + fmt.feed(3)
            + fmt.cut()
        )
    """

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> bytes:
        """Reset printer to factory defaults (ESC @)."""
        return ESC + b"@"

    # ------------------------------------------------------------------
    # Text alignment
    # ------------------------------------------------------------------

    def align_left(self) -> bytes:
        """Left-align text (ESC a 0)."""
        return ESC + b"a\x00"

    def align_center(self) -> bytes:
        """Centre-align text (ESC a 1)."""
        return ESC + b"a\x01"

    def align_right(self) -> bytes:
        """Right-align text (ESC a 2)."""
        return ESC + b"a\x02"

    # ------------------------------------------------------------------
    # Text style
    # ------------------------------------------------------------------

    def bold_on(self) -> bytes:
        """Enable bold printing (ESC E 1)."""
        return ESC + b"E\x01"

    def bold_off(self) -> bytes:
        """Disable bold printing (ESC E 0)."""
        return ESC + b"E\x00"

    def underline_on(self) -> bytes:
        """Enable single underline (ESC - 1)."""
        return ESC + b"-\x01"

    def underline_off(self) -> bytes:
        """Disable underline (ESC - 0)."""
        return ESC + b"-\x00"

    def double_size_on(self) -> bytes:
        """Enable double width + double height (GS ! 0x11)."""
        return GS + b"!\x11"

    def normal_size(self) -> bytes:
        """Reset to normal character size (GS ! 0x00)."""
        return GS + b"!\x00"

    # ------------------------------------------------------------------
    # Text output
    # ------------------------------------------------------------------

    def text(self, content: str, encoding: str = "cp437") -> bytes:
        """
        Encode *content* as printer-compatible bytes and append a line-feed.

        Args:
            content : String to print.  Keep within the printable width
                      (~32 chars for 58 mm paper).
            encoding: CP437 is the ESC/POS standard.  Some printers also
                      accept "latin-1" or "utf-8" – check your model's manual.
        """
        return content.encode(encoding, errors="replace") + LF

    def raw_text(self, content: str, encoding: str = "cp437") -> bytes:
        """Encode *content* without appending a line-feed."""
        return content.encode(encoding, errors="replace")

    # ------------------------------------------------------------------
    # Paper feed and cut
    # ------------------------------------------------------------------

    def feed(self, lines: int = 1) -> bytes:
        """
        Feed *lines* blank lines (ESC d n).

        Args:
            lines: Number of lines to advance (0–255).
        """
        lines = max(0, min(lines, 255))
        return ESC + b"d" + bytes([lines])

    def cut(self) -> bytes:
        """Partial paper cut (GS V 1) – tears cleanly on most 58 mm printers."""
        return GS + b"V\x01"

    def full_cut(self) -> bytes:
        """Full paper cut (GS V 0)."""
        return GS + b"V\x00"

    # ------------------------------------------------------------------
    # Native ESC/POS QR Code  (GS ( k)
    # ------------------------------------------------------------------

    def qr_code(
        self,
        data: str,
        size: int            = 6,
        error_correction: str = "M",
        model: int           = 2,
    ) -> bytes:
        """
        Build the ``GS ( k`` byte sequence to render a QR code natively.

        The printer's own dot-matrix engine renders the QR symbol; no image
        conversion is required on the host.

        Args:
            data             : Content to encode (URL, text, numeric ID …).
            size             : Module size in printer dots.  Range 1–16.
                               6 is a good default for 58 mm paper; use
                               4–5 when encoding long strings.
            error_correction : Error correction level:

                               * ``"L"`` – 7 % recovery
                               * ``"M"`` – 15 % recovery (default)
                               * ``"Q"`` – 25 % recovery
                               * ``"H"`` – 30 % recovery

            model            : QR model number (1 or 2). Model 2 is the
                               standard and supports the largest capacity.

        Returns:
            Raw ESC/POS bytes.  Append to a print job byte string and send
            via :meth:`BluetoothPrinter.send`.

        ESC/POS function mapping:
            * ``0xA5`` – Select QR model
            * ``0xA7`` – Set module (dot) size
            * ``0xA9`` – Set error correction level
            * ``0xB0`` – Store QR data in symbol storage area
            * ``0xB1`` – Print the stored symbol
        """
        # Clamp and map parameters to ESC/POS byte values.
        size       = max(1, min(size, 16))
        model_byte = 49 if model == 1 else 50           # '1' or '2'
        ec_map     = {"L": 48, "M": 49, "Q": 50, "H": 51}
        ec_byte    = ec_map.get(error_correction.upper(), 49)

        data_bytes = data.encode("utf-8")

        # pL / pH encode (len(data) + 3) as a little-endian 16-bit word.
        # The +3 accounts for the three header bytes (cn fn m) in Function B0.
        store_len = len(data_bytes) + 3
        pL = store_len & 0xFF
        pH = (store_len >> 8) & 0xFF

        return (
            # Function 0xA5: select QR model
            GS + b"(k\x04\x00\x31\xa5" + bytes([model_byte]) + b"\x00"
            # Function 0xA7: set module size
            + GS + b"(k\x03\x00\x31\xa7" + bytes([size])
            # Function 0xA9: set error correction level
            + GS + b"(k\x03\x00\x31\xa9" + bytes([ec_byte])
            # Function 0xB0: store QR data
            + GS + b"(k" + bytes([pL, pH]) + b"\x31\xb0\x30" + data_bytes
            # Function 0xB1: print the stored QR symbol
            + GS + b"(k\x03\x00\x31\xb1\x30"
        )


# ---------------------------------------------------------------------------
# High-level print functions
# ---------------------------------------------------------------------------

def print_qr(
    data: str,
    printer: BluetoothPrinter,
    header: str            = "SMART WATER DISPENSER",
    subheader: str         = "Scan QR Code",
    footer: str            = "Thank you!",
    qr_size: int           = 6,
    error_correction: str  = "M",
    encoding: str          = "cp437",
) -> bool:
    """
    Print a QR code with surrounding text on a thermal printer.

    Print layout::

        ┌──────────────────────────────┐
        │   SMART WATER DISPENSER      │  ← header   (bold, centred)
        │   Scan QR Code               │  ← subheader (centred)
        │                              │
        │        ██ ██  ██ ██          │
        │        ██   ████  ██         │  ← QR code  (centred)
        │        ████████████          │
        │                              │
        │   Thank you!                 │  ← footer   (centred)
        └──────────────────────────────┘

    Args:
        data             : Content to encode in the QR code.
        printer          : Connected :class:`BluetoothPrinter` instance.
        header           : Bold title printed above the QR code.
        subheader        : Secondary title printed above the QR code.
        footer           : Text printed below the QR code.
        qr_size          : QR module size in printer dots (1–16).
        error_correction : QR error correction level ("L" / "M" / "Q" / "H").
        encoding         : ESC/POS text encoding (default ``"cp437"``).

    Returns:
        ``True`` if the print job was transmitted without errors.
    """
    fmt = ESCPOSFormatter()
    try:
        job: bytes = (
            fmt.initialize()
            + fmt.align_center()
            + fmt.bold_on()
            + fmt.text(header, encoding)
            + fmt.bold_off()
            + fmt.text(subheader, encoding)
            + fmt.feed(1)
            + fmt.qr_code(data, size=qr_size, error_correction=error_correction)
            + fmt.feed(1)
            + fmt.text(footer, encoding)
            + fmt.feed(3)
            + fmt.cut()
        )
        success = printer.send(job)
        if success:
            logger.info(
                "QR print job sent successfully  (data=%r, size=%d).",
                data[:50], qr_size,
            )
        return success

    except Exception as exc:
        logger.exception("Failed to build QR print job: %s", exc)
        return False


def print_receipt(
    printer: BluetoothPrinter,
    transaction_id: str,
    amount: float,
    volume_ml: int,
    qr_data: Optional[str] = None,
    encoding: str = "cp437",
) -> bool:
    """
    Print a formatted water-vending receipt with an embedded QR code.

    Print layout::

        ┌──────────────────────────────┐
        │   SMART WATER DISPENSER      │  (bold)
        │   Water Vendo System         │
        │ ──────────────────────────── │
        │ Txn ID  : TXN-20260309-001   │
        │ Volume  : 500 mL             │
        │ Amount  : PHP 5.00           │
        │ ──────────────────────────── │
        │        Scan QR Code          │
        │        [QR CODE]             │
        │                              │
        │        Thank you!            │
        │        Come back again!      │
        └──────────────────────────────┘

    Args:
        printer        : Connected :class:`BluetoothPrinter` instance.
        transaction_id : Unique identifier for this transaction.
        amount         : Amount paid in Philippine Peso.
        volume_ml      : Volume of water dispensed in millilitres.
        qr_data        : Data to encode in the QR code.  If ``None``, a URL
                         containing *transaction_id* is generated automatically.
        encoding       : ESC/POS text encoding (default ``"cp437"``).

    Returns:
        ``True`` if the print job was transmitted without errors.
    """
    if qr_data is None:
        qr_data = f"https://smart-vendo.local/tx?id={transaction_id}"

    fmt       = ESCPOSFormatter()
    separator = "-" * 32

    try:
        job: bytes = (
            fmt.initialize()
            # ── Header ──────────────────────────────────────────────────
            + fmt.align_center()
            + fmt.bold_on()
            + fmt.text("SMART WATER DISPENSER", encoding)
            + fmt.bold_off()
            + fmt.text("Water Vendo System", encoding)
            + fmt.text(separator, encoding)
            # ── Transaction details ──────────────────────────────────────
            + fmt.align_left()
            + fmt.text(f"Txn ID  : {transaction_id}", encoding)
            + fmt.text(f"Volume  : {volume_ml} mL", encoding)
            + fmt.text(f"Amount  : PHP {amount:.2f}", encoding)
            # ── QR code ──────────────────────────────────────────────────
            + fmt.align_center()
            + fmt.text(separator, encoding)
            + fmt.text("Scan QR Code", encoding)
            + fmt.feed(1)
            + fmt.qr_code(qr_data, size=5, error_correction="M")
            + fmt.feed(1)
            # ── Footer ───────────────────────────────────────────────────
            + fmt.text("Thank you!", encoding)
            + fmt.text("Come back again!", encoding)
            + fmt.feed(3)
            + fmt.cut()
        )
        success = printer.send(job)
        if success:
            logger.info(
                "Receipt sent  (txn=%s, amount=PHP %.2f, vol=%d mL).",
                transaction_id, amount, volume_ml,
            )
        return success

    except Exception as exc:
        logger.exception("Failed to build receipt: %s", exc)
        return False
