"""
hardware_hooks.py - Clean API for all hardware actions.

Every UI page calls these functions instead of directly touching
SerialManager.  This makes swapping the transport layer easy and keeps
pages testable without real hardware.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from app_state import ML_TO_MS

if TYPE_CHECKING:
    from serial_manager import SerialManager
    from thermal_printer import ThermalPrinter


def insert_coin(value: int, serial_mgr: "SerialManager") -> None:
    """
    Called when a coin is physically inserted (event from ESP32) OR
    simulated from the UI test buttons.
    """
    serial_mgr.simulate_coin(value)


def insert_bill(value: int, serial_mgr: "SerialManager") -> None:
    """Called when a bill is physically inserted or simulated."""
    serial_mgr.simulate_bill(value)


def start_dispense(
    service: str,
    temperature: str,
    volume_ml: int,
    serial_mgr: "SerialManager",
) -> int:
    """
    Trigger water dispensing.

    Parameters
    ----------
    service     : "Dispense" (bottle) | "Fountain"
    temperature : "Cold" | "Warm" | "Hot"  (informational for future relay mapping)
    volume_ml   : target volume
    serial_mgr  : active SerialManager instance

    Returns
    -------
    Expected dispense duration in milliseconds.
    """
    duration_ms = ML_TO_MS.get(volume_ml, 2000)

    if service == "Fountain":
        serial_mgr.fountain(duration_ms)
    else:
        serial_mgr.dispense(duration_ms)

    return duration_ms


def stop_dispense(serial_mgr: "SerialManager") -> None:
    """Emergency stop for all relays."""
    serial_mgr.stop_flow()


def scan_qr(serial_mgr: "SerialManager") -> None:
    """
    Request a QR scan from the ESP32-attached reader.
    The result will arrive as a serial event handled by the active page.
    Current implementation treats any saved account as the scanned account
    (simulates a successful QR match).
    """
    # In real hardware: send a trigger command to a QR reader module.
    # The decoded QR payload would come back as a serial event.
    serial_mgr.send_command("CMD:QR_SCAN")


def print_qr(username: str, serial_mgr: "SerialManager", printer: "ThermalPrinter | None" = None) -> None:
    """
    Print a QR code containing the username to the thermal receipt printer.
    Falls back to sending a serial command to the ESP32 if no local printer
    is available.
    """
    if printer and printer.is_connected():
        qr_data = f"USER:{username}"
        printer.print_qr(
            data=qr_data,
            header="AQUA SPLASH",
            subheader=f"User: {username}",
        )
    else:
        serial_mgr.send_command(f"CMD:PRINT_QR:{username}")


def print_receipt(
    transaction: dict,
    printer: "ThermalPrinter | None" = None,
) -> None:
    """
    Print a dispensing receipt on the thermal printer.

    Parameters
    ----------
    transaction : dict
        Keys: transaction_id, credit, volume_ml, service, temperature.
    printer : ThermalPrinter | None
        The connected ThermalPrinter instance.
    """
    if printer and printer.is_connected():
        printer.print_receipt(transaction)
    else:
        print("[hardware_hooks] Printer unavailable \u2013 skipping receipt.")


def request_temperature(temp: str, serial_mgr: "SerialManager") -> None:
    """
    Pre-condition the heating/cooling relay before dispensing.
    Sent ahead of the dispense command so the water reaches the right temperature.
    """
    serial_mgr.send_command(f"CMD:TEMP:{temp.upper()}")
