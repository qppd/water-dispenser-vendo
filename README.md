## Author / Credits

Developed and maintained by [qppd](https://github.com/qppd)
# Water Dispenser Vending Machine

[![Arduino](https://img.shields.io/badge/Arduino-00979D?style=for-the-badge&logo=Arduino&logoColor=white)](https://www.arduino.cc/)
[![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-latest-orange.svg?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4-red.svg?style=for-the-badge&logo=raspberry-pi&logoColor=white)](https://www.raspberrypi.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/Build-Development-yellow.svg?style=for-the-badge)](https://github.com/qppd/water-dispenser-vendo)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg?style=for-the-badge)](https://github.com/qppd/water-dispenser-vendo/releases)

A smart water dispenser vending machine project built on ESP32 microcontroller, featuring coin and bill acceptance, audio feedback, and automated dispensing.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [System Diagrams](#system-diagrams)
- [Serial Communication Protocol](#serial-communication-protocol)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Software Components](#software-components)
- [Installation](#installation)
- [Usage](#usage)
- [Wiring Diagram](#wiring-diagram)
- [Hardware Models](#hardware-models)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [System Integration](#system-integration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview

The Water Dispenser Vending Machine is an automated system designed to dispense water in exchange for coin and bill payments. Built using an ESP32 microcontroller for the core vending logic and a Raspberry Pi for host monitoring, this project demonstrates the integration of embedded systems, payment processing, and user interface design.

The system accepts Philippine currency (coins: P1, P5, P10, P20; bills: P20, P50, P100) through dedicated hardware interfaces, accumulates credits, and dispenses water automatically when the required amount is reached. Audio feedback and serial communication provide real-time status updates.

This project serves as a comprehensive example of IoT device development, combining hardware interfacing, firmware programming, and software integration for a practical vending application.

## Architecture

The system follows a distributed architecture with two main components:

### ESP32 Client (Vending Machine Core)
- **Role**: Handles payment processing, credit management, and dispensing control
- **Responsibilities**: 
  - Interrupt-driven coin and bill detection
  - Credit accumulation and validation
  - Relay control for water dispensing
  - Audio feedback generation
  - Serial communication for status reporting

### Raspberry Pi Host (Monitoring and Control)
- **Role**: Provides higher-level monitoring and potential future extensions
- **Responsibilities**:
  - Serial data reception from ESP32
  - Data logging and processing
  - User interface (GUI via CustomTkinter)
  - Network connectivity for remote monitoring

### Communication Layer
- Serial communication (UART) between ESP32 and Raspberry Pi
- Standardized message format for status updates and commands

## System Diagrams

### High-Level System Architecture
```
[User] --> [Coin/Bill Input] --> [ESP32] <--Serial--> [Raspberry Pi] --> [Display/Monitoring]
                    |                           |
                    v                           v
              [Credit Logic]              [Data Processing]
                    |                           |
                    v                           v
              [Dispensing Relay]          [Storage/Logging]
```

### Hardware Block Diagram
```
ESP32 DevKitC
├── GPIO 4: Coin Slot Interrupt
├── GPIO 26: Bill Acceptor Interrupt  
├── GPIO 27: Buzzer PWM Output
├── GPIO 23: Relay Control Output
└── UART: Serial Communication

Raspberry Pi 4
└── USB/Serial: ESP32 Connection
```

## Serial Communication Protocol

The system uses a simple text-based serial protocol at 9600 baud for communication between ESP32 and Raspberry Pi.

### Message Format
```
<TYPE>: <DETAILS> | <ADDITIONAL_INFO>
```

### Message Types
- **Coin Acceptance**: `Coin accepted: P<VALUE> | Coin Credit: P<TOTAL>`
- **Bill Acceptance**: `Bill accepted: P<VALUE> | Bill Credit: P<TOTAL>`
- **Dispensing**: `Dispensed water`
- **System Status**: Various debug and status messages

### Example Communication Sequence
```
ESP32: Coin accepted: P5 | Coin Credit: P5
ESP32: Bill accepted: P20 | Bill Credit: P20
ESP32: Dispensed water
```

## Features

- **Coin Acceptance**: Supports multiple coin denominations (P1, P5, P10, P20) via ALLAN coin slot
- **Bill Acceptance**: Accepts Philippine bills (P20, P50, P100) using TB-74 bill acceptor
- **Credit Management**: Accumulates credits from coins and bills
- **Audio Feedback**: Piezo buzzer provides tones for user interactions
- **Automated Dispensing**: Relay-controlled water dispensing when sufficient credit is reached
- **Serial Monitoring**: Real-time feedback via serial console
- **Interrupt-Driven**: Efficient pulse counting for accurate denomination detection

## Hardware Requirements

- ESP32 Development Board
- ALLAN Coin Slot (pulse-based)
- TB-74 Bill Acceptor (pulse-based)
- Piezo Buzzer
- Relay Module (for water pump/valve control)
- Power Supply (appropriate for ESP32 and peripherals)
- Connecting Wires and Breadboard (for prototyping)

### Pin Configuration

| Component | ESP32 Pin | Description |
|-----------|-----------|-------------|
| Coin Slot | GPIO 4 | Interrupt pin for coin pulses |
| Bill Acceptor | GPIO 26 | Interrupt pin for bill pulses |
| Buzzer | GPIO 27 | PWM output for audio feedback |
| Relay | GPIO 23 | Digital output for dispensing control |

## Software Components

### ESP32 Firmware Requirements
- Arduino IDE 1.8.x or later
- ESP32 Board Support Package
- Arduino ESP32 Core (version 2.0.0 or higher)

### ESP32 Dependencies
- Arduino.h (included with ESP32 core)
- Standard C++ libraries
- ESP32-specific libraries for GPIO and serial communication

### Raspberry Pi Host Requirements
- Python 3.7 or higher
- pip package manager
- Linux operating system (Raspberry Pi OS recommended)

### Raspberry Pi Dependencies
- pyserial (for serial communication)
- customtkinter (for modern GUI interface)
- Standard Python libraries (os, time, glob)

### Development Tools
- Git (for version control)
- Fritzing (for circuit design, optional)
- Text editor or IDE (VS Code, Arduino IDE)

## Project Structure

```
water-dispenser-vendo/
├── LICENSE
├── README.md
├── diagrams/          # Circuit diagrams and schematics
├── models/           # 3D models or CAD files
├── src/
│   └── esp/
│       └── ESPWDVClient/
│           ├── ESPWDVClient.ino    # Main Arduino sketch
│           ├── PINS_CONFIG.h       # Pin definitions
│           ├── COIN_SLOT.h         # Coin slot interface
│           ├── COIN_SLOT.cpp       # Coin slot implementation
│           ├── BILL_ACCEPTOR.h     # Bill acceptor interface
│           ├── BILL_ACCEPTOR.cpp   # Bill acceptor implementation
│           ├── BUZZER_CONFIG.h     # Buzzer interface
│           ├── BUZZER_CONFIG.cpp   # Buzzer implementation
│           └── RELAY_CONFIG.h      # Relay interface
│           └── RELAY_CONFIG.cpp    # Relay implementation
└── wiring/            # Wiring instructions and guides
```

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/qppd/water-dispenser-vendo.git
   cd water-dispenser-vendo
   ```

2. **Install Arduino IDE**
   - Download and install Arduino IDE from [arduino.cc](https://www.arduino.cc/en/software)

3. **Install ESP32 Board Support**
   - Open Arduino IDE
   - Go to File > Preferences
   - Add `https://dl.espressif.com/dl/package_esp32_index.json` to Additional Board Manager URLs
   - Go to Tools > Board > Boards Manager
   - Search for "ESP32" and install the package

4. **Open the Project**
   - Open `src/esp/ESPWDVClient/ESPWDVClient.ino` in Arduino IDE
   - Select your ESP32 board from Tools > Board
   - Select the correct COM port

5. **Upload the Code**
   - Click the Upload button in Arduino IDE

## Configuration

### Pin Configuration

Modify `PINS_CONFIG.h` to change pin assignments:

```cpp
// Coin Slot
#define coinPin 4

// Bill Acceptor
#define billPin 26

// Piezo Buzzer
#define BUZZER_PIN 27

#define RELAY_1 23
```

### Dispensing Threshold

In `ESPWDVClient.ino`, modify the credit threshold:

```cpp
if ((coinCredit + billCredit) >= 20)  // Change 20 to desired amount
```

### Timing Parameters

Adjust timing constants in the respective modules:

- Coin debounce: `coinDebounceDelay` in `COIN_SLOT.cpp`
- Bill pulse timeout: `pulseDebounce` in `BILL_ACCEPTOR.cpp`
- Dispensing duration: `delay(2000)` in main loop

## Usage

1. **Power On**: The system initializes and plays a startup tone
2. **Insert Coins/Bills**: Insert Philippine coins or bills
3. **Credit Accumulation**: System tracks credits via serial output
4. **Automatic Dispensing**: When credit reaches threshold, water dispenses automatically
5. **Credit Reset**: Credits reset after successful dispensing

### Serial Output Example

```
Coin accepted: P5 | Coin Credit: P5
Bill accepted: P20 | Bill Credit: P20
Dispensed water
```

## Wiring Diagram

Refer to the `wiring/` directory for detailed wiring diagrams.

![Water Dispenser Wiring Diagram](wiring/Water_Dispenser_Vendo.png)

### Basic Connections

- **Coin Slot**: Connect signal pin to GPIO 4, power, and ground
- **Bill Acceptor**: Connect signal pin to GPIO 26, power, and ground
- **Buzzer**: Connect positive to GPIO 27, negative to ground
- **Relay**: Connect control pin to GPIO 23, power relay coil appropriately

⚠️ **Safety Note**: Ensure proper power isolation between control circuits and high-power dispensing components.

## Hardware Models

The project includes 3D models and CAD files for custom hardware components. These can be found in the `models/` directory.

### Available Models
- **Enclosure Design**: 3D printable case for the vending machine
- **Mounting Brackets**: Custom brackets for hardware components
- **Adapter Plates**: Interface plates for different hardware configurations

### File Formats
- STL files for 3D printing
- STEP files for CAD software
- Fritzing files for circuit prototyping

### Usage
1. Download the appropriate model files from the `models/` directory
2. Open in your preferred CAD software or 3D printing application
3. Modify as needed for your specific requirements
4. Print or manufacture the components

## API Reference

### Coin Slot Functions

- `void initALLANCOIN()`: Initialize coin slot interrupt
- `int getCoinValue()`: Get value of inserted coin
- `void resetCoinDetection()`: Reset coin detection state

### Bill Acceptor Functions

- `void initBILLACCEPTOR()`: Initialize bill acceptor interrupt
- `int getBillValue()`: Get value of accepted bill

### Buzzer Functions

- `void initBuzzer()`: Initialize buzzer pin
- `void playTone(int frequency, int duration)`: Play tone at frequency for duration
- `void stopTone()`: Stop current tone

### Relay Functions

- `void initRELAY()`: Initialize relay pin
- `void operateRELAY(uint16_t RELAY, boolean OPENED)`: Control relay state
- `void operateSSR(uint16_t RELAY, boolean OPENED)`: Control solid-state relay

## Troubleshooting

### Common Issues

1. **No Coin/Bill Detection**
   - Check wiring connections
   - Verify interrupt pins are correct
   - Test with multimeter for signal pulses

2. **Incorrect Denomination**
   - Adjust pulse counting logic
   - Check acceptor calibration
   - Verify timing parameters

3. **Buzzer Not Working**
   - Check GPIO 27 connection
   - Verify buzzer specifications
   - Test with simple tone sketch

4. **Relay Not Activating**
   - Check GPIO 23 connection
   - Verify relay power supply
   - Test relay module independently

### Debug Mode

Enable serial debugging by connecting to the ESP32's serial port at 9600 baud.

## System Integration

### ESP32 and Raspberry Pi Integration
The system integrates ESP32 firmware with Raspberry Pi host software through serial communication. The ESP32 handles real-time hardware interactions while the Raspberry Pi provides monitoring and potential future expansions.

### Hardware Integration
- **Power Management**: Separate power supplies for control circuits and high-power components
- **Signal Isolation**: Optocouplers or isolation modules for safe interfacing
- **Grounding**: Proper grounding to prevent noise and ensure reliable operation

### Software Integration
- **Serial Protocol**: Standardized message format for reliable data exchange
- **Error Handling**: Robust error detection and recovery mechanisms
- **Synchronization**: Time synchronization between devices if needed

## Development

### Development Environment Setup
1. **ESP32 Development**:
   - Install Arduino IDE
   - Add ESP32 board support
   - Configure board settings

2. **Raspberry Pi Development**:
   - Install Python and required packages
   - Set up serial communication
   - Configure GPIO if needed

### Testing Procedures
- **Unit Testing**: Test individual hardware components
- **Integration Testing**: Verify ESP32-Raspberry Pi communication
- **System Testing**: End-to-end testing with actual currency

### Code Quality
- Follow Arduino coding standards for ESP32 code
- Use PEP 8 for Python code
- Add comprehensive comments and documentation
- Implement proper error handling

### Version Control
- Use Git for source code management
- Follow semantic versioning
- Maintain clear commit messages
- Use branches for feature development

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow Arduino coding standards
- Add comments for complex logic
- Test hardware changes thoroughly
- Update documentation for new features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

**Project Author**: [qppd](https://github.com/qppd)

For questions, issues, or contributions, please:
- Open an issue on [GitHub](https://github.com/qppd/water-dispenser-vendo/issues)
- Contact via GitHub profile

---