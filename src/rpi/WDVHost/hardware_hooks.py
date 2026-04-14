from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serial_manager import SerialManager
    from serial_second_esp import SecondESPSerial
    from thermal_printer import ThermalPrinter

from app_state import ML_TO_MS

# Relay mapping: temperature → relay number on ESPWDV
# Warm is handled separately via RPI:WARM:<ms> (sequential hot+cold mixing).
_TEMP_TO_RELAY = {
    "Cold": 1,   # R1 → Valve1+Pump1 (COLD water)
    "Hot":  3,   # R3 → Valve3+Pump3 (HOT  water)
}

# Warm water mixing target: 40 °C from 85 °C hot and 5 °C cold.
# Formula: hot_frac = (T_target - T_cold) / (T_hot - T_cold)
#          = (40 - 5) / (85 - 5) = 35/80 = 0.4375
# The ESP32 receives RPI:WARM:<total_ms> and runs R3 (hot) then R1 (cold)
# sequentially using this ratio, then sends ESP:DONE:WARM when complete.
_WARM_HOT_FRAC = 0.4375


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
    second_esp: "SecondESPSerial",
) -> int:
    """
    Trigger water dispensing via the ESPWDV (second ESP32).

    Parameters
    ----------
    service     : "Dispense" (bottle) | "Fountain"
    temperature : "Cold" | "Warm" | "Hot"  — selects the relay
    volume_ml   : target volume in mL
    serial_mgr  : first ESP32 serial manager (bill/coin acceptor)
    second_esp  : second ESP32 serial manager (ESPWDV dispenser)

    Returns
    -------
    Expected dispense duration in milliseconds.
    """
    # Look up the exact relay duration for this volume (100/250/500/1000 ml).
    # Falls back to a dynamic calculation for any unlisted volume.
    duration_ms = ML_TO_MS.get(
        volume_ml,
        max(1, round(volume_ml * 60_000 / 1_750)),
    )

    if temperature == "Warm":
        # Sequential mixing: ESP32 opens R3 (hot) then R1 (cold) in ratio 44/56.
        # Send a single RPI:WARM:<total_ms> command; ESP32 handles the phasing.
        second_esp.send_command(f"RPI:WARM:{duration_ms}")
    else:
        # Route to the correct relay: Cold→R1, Hot→R3
        relay_num = _TEMP_TO_RELAY.get(temperature, 1)
        second_esp.relay(relay_num, duration_ms)

    return duration_ms


def stop_dispense(serial_mgr: "SerialManager", second_esp: "SecondESPSerial") -> None:
    """Emergency stop for all relays on the ESPWDV."""
    second_esp.stop_all()


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
