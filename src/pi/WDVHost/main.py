"""
Minimal WDVHost - Water Dispenser Vending Host
Reads serial data from ESP32 and prints to console
"""

import serial
import time


def find_serial_port():
    """Try common serial ports for ESP32 on Raspberry Pi."""
    import glob
    candidates = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1', '/dev/serial0']
    for port in candidates:
        if glob.glob(port):
            return port
    print("No known ESP32 serial port found. Please specify manually.")
    return None

def main():
    port = find_serial_port()
    if not port:
        return
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"Connected to ESP32 serial port: {port}")
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='replace').strip()
                except Exception as e:
                    print(f"Decode error: {e}")
                    continue
                if line:
                    print(f"ESP32: {line}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
