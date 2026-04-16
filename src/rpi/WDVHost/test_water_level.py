#!/usr/bin/env python3
"""
test_water_level.py – Test script for water level sensor.

Usage:
    python test_water_level.py                  # uses default serial port
    python test_water_level.py /dev/ttyUSB0     # specify serial port

This script connects to the ESPWDV via serial and queries the water level sensor.
It will print the current water level status.
"""

import sys
import time
import queue
import threading
from typing import Optional

# Import from the local package
from serial_manager import SerialManager


def main() -> None:
    # Determine serial port
    port = sys.argv[1] if len(sys.argv) > 1 else None
    if not port:
        print("No port specified. Usage: python test_water_level.py [PORT]")
        print("Example: python test_water_level.py /dev/ttyUSB0")
        return

    # Create event queue
    event_queue = queue.Queue()

    # Create serial manager
    serial_mgr = SerialManager(event_queue, port=port, baud=9600)
    serial_mgr.start()

    try:
        print(f"Testing water level sensor on {port}...")
        print("Sending water level query...")

        # Send query
        serial_mgr.query_water_level()

        # Wait for response
        timeout = 5.0
        start_time = time.time()
        response_received = False

        while time.time() - start_time < timeout:
            try:
                event = event_queue.get(timeout=0.1)
                if event["type"] == "esp_status" and event["cmd"] == "WATER_LEVEL":
                    present = event["value"] == "1"
                    print(f"Water level: {'PRESENT' if present else 'LOW'}")
                    response_received = True
                    break
                elif event["type"] == "raw":
                    print(f"Raw: {event['line']}")
            except queue.Empty:
                continue

        if not response_received:
            print("Timeout: No response received from ESPWDV")

    finally:
        serial_mgr.stop()


if __name__ == "__main__":
    main()