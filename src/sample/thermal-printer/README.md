# Bluetooth Thermal Printer – QR Code Printer
> Print QR codes on a **POS-5805DD** Bluetooth thermal printer from
> **Windows 10/11** or a **Raspberry Pi** (Debian Trixie ARM64).

---

## Table of Contents
1. [Project Structure](#project-structure)
2. [Requirements](#requirements)
3. [Installation – Windows](#installation--windows)
4. [Installation – Raspberry Pi](#installation--raspberry-pi)
5. [Bluetooth Pairing Guide](#bluetooth-pairing-guide)
   - [Windows](#pairing-on-windows)
   - [Raspberry Pi](#pairing-on-raspberry-pi)
6. [Configuration](#configuration)
7. [Running the Demo](#running-the-demo)
8. [Module Overview](#module-overview)
9. [Troubleshooting](#troubleshooting)

---

## Project Structure

```
thermal-printer/
├── printer_qr.py        # ESC/POS command builder + high-level print functions
├── bluetooth_printer.py # Serial transport layer (pyserial wrapper)
├── config.py            # All user-editable settings in one place
├── test_print.py        # Demo entry point
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## Requirements

| Requirement        | Detail                                    |
|--------------------|-------------------------------------------|
| Python             | 3.9 or newer                              |
| Printer            | POS-5805DD (ESC/POS, Bluetooth)           |
| OS (host)          | Windows 10/11  **or**  Debian Trixie ARM64 |
| Python libraries   | `pyserial`, `python-escpos`, `qrcode[pil]` |

---

## Installation – Windows

### 1. Install Python
Download Python 3.9+ from <https://www.python.org/downloads/> and ensure
**"Add Python to PATH"** is checked during installation.

### 2. Clone / copy the project
```powershell
cd C:\Users\QPPD\Desktop\Projects\water-dispenser-vendo\src\sample\thermal-printer
```

### 3. (Recommended) Create a virtual environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 4. Install dependencies
```powershell
pip install -r requirements.txt
```

---

## Installation – Raspberry Pi

### 1. Update the system
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install system packages
```bash
sudo apt install -y bluetooth bluez bluez-tools rfcomm python3-pip python3-venv
```

### 3. Start and enable the Bluetooth service
```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### 4. Navigate to the project folder
```bash
cd ~/water-dispenser-vendo/src/sample/thermal-printer
```

### 5. Create a virtual environment and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Bluetooth Pairing Guide

### Pairing on Windows

1. Turn on the POS-5805DD printer.
2. Open **Settings → Bluetooth & devices → Add device**.
3. Select the printer (often listed as **"POS-5805DD"** or **"BT Printer"**).
4. After pairing, open **Device Manager → Ports (COM & LPT)** to find
   the COM port number assigned to the printer (e.g. **COM5**).
5. Update `PRINTER_PORT` in `config.py`:
   ```python
   PRINTER_PORT = "COM5"
   ```

### Pairing on Raspberry Pi

#### Step 1 – Find the printer MAC address
```bash
sudo bluetoothctl
```
Inside `bluetoothctl`:
```
power on
agent on
scan on
```
Wait until you see the printer in the list, e.g.:
```
[NEW] Device XX:XX:XX:XX:XX:XX POS-5805DD
```
Note the MAC address, then stop scanning:
```
scan off
```

#### Step 2 – Pair, trust, and connect
```
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX
quit
```

#### Step 3 – Bind the RFCOMM device
```bash
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
```
The printer will now be available as `/dev/rfcomm0`.

#### Step 4 – (Optional) Auto-bind on boot
Add the following line to `/etc/rc.local` before `exit 0`:
```bash
rfcomm bind 0 XX:XX:XX:XX:XX:XX
```

#### Step 5 – Update `config.py`
```python
PRINTER_PORT = "/dev/rfcomm0"
```

---

## Configuration

All settings live in **`config.py`**.  Edit this file before running the demo.

| Setting               | Default                                   | Description                        |
|-----------------------|-------------------------------------------|------------------------------------|
| `PRINTER_PORT`        | `"COM5"` / `"/dev/rfcomm0"`               | Serial port for the printer        |
| `BAUDRATE`            | `9600`                                    | Serial baud rate                   |
| `TIMEOUT`             | `5`                                       | Read/write timeout (seconds)       |
| `QR_DATA`             | `"https://smart-vendo.local/pay?id=12345"`| Content encoded in the QR code     |
| `HEADER_TEXT`         | `"SMART WATER DISPENSER"`                 | Bold title above the QR            |
| `SUBHEADER_TEXT`      | `"Scan QR Code"`                          | Subtitle above the QR              |
| `FOOTER_TEXT`         | `"Thank you!"`                            | Text below the QR                  |
| `QR_BOX_SIZE`         | `6`                                       | QR module size in dots (1–16)      |
| `QR_ERROR_CORRECTION` | `"M"`                                     | Error correction (`L/M/Q/H`)       |

Set `PRINTER_PORT = "auto"` to enable automatic port detection.

---

## Running the Demo

```bash
# Use the port configured in config.py
python test_print.py

# Override the port on the command line
python test_print.py COM6                 # Windows
python test_print.py /dev/rfcomm1         # Raspberry Pi
```

### Expected printer output

```
┌──────────────────────────────┐
│   SMART WATER DISPENSER      │
│   Scan QR Code               │
│                              │
│        ██ ██  ██ ██          │
│        ██   ████  ██         │
│        ████████████          │
│                              │
│   Thank you!                 │
└──────────────────────────────┘
```

---

## Module Overview

### `config.py`
Single source of truth for all user-editable settings.  Change the port,
QR data, and text here.

### `bluetooth_printer.py`
Low-level serial transport.  Key API:

```python
from bluetooth_printer import BluetoothPrinter, detect_printer_port

# Context manager (recommended – auto-closes the port)
with BluetoothPrinter("COM5") as p:
    p.send(raw_bytes)

# Auto-detect the port
port = detect_printer_port()   # None if not found
```

### `printer_qr.py`
ESC/POS command builder and high-level print helpers.  Key API:

```python
from printer_qr import print_qr, print_receipt

# Print a QR code with text
print_qr(
    data     = "https://example.com",
    printer  = printer,
    header   = "MY SHOP",
    subheader= "Scan to pay",
    footer   = "Thank you!",
    qr_size  = 6,
)

# Print a full vending receipt
print_receipt(
    printer        = printer,
    transaction_id = "TXN-001",
    amount         = 5.00,
    volume_ml      = 500,
)
```

### `test_print.py`
Runnable entry point.  Reads settings from `config.py`, connects to the
printer, and sends a QR print job.

---

## Troubleshooting

### `SerialException: could not open port COM5`
- The printer may be off or out of Bluetooth range.
- On Windows: check Device Manager → Ports for the correct COM number.
- The port may already be in use by another application.

### `No /dev/rfcommN device found` (Raspberry Pi)
Run the bind command:
```bash
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX
```
Replace `XX:XX:XX:XX:XX:XX` with the printer's Bluetooth MAC address.

### Printer does not respond / garbled output
- Verify the baud rate matches the printer setting (default **9600**).
- Try a full power-cycle of the printer and re-pair it.

### QR code prints but cannot be scanned
- Increase `QR_BOX_SIZE` in `config.py` (try `7` or `8`).
- Shorten the `QR_DATA` string.
- Switch to a higher error correction level (`QR_ERROR_CORRECTION = "H"`).

### `ModuleNotFoundError: No module named 'serial'`
```bash
pip install pyserial
```

### Raspberry Pi: permission denied on `/dev/rfcomm0`
```bash
sudo usermod -aG dialout $USER
# Log out and back in, then retry.
```

### Windows: printer appears twice in Device Manager
Windows sometimes creates two COM ports (standard and outgoing) for a
Bluetooth device.  Try each port in `config.py` until one works.
