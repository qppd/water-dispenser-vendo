#ifndef WATER_LEVEL_SENSOR_H
#define WATER_LEVEL_SENSOR_H

#include <Arduino.h>

/*
 * WATER_LEVEL_SENSOR  —  Digital water-level detection module
 *
 * Hardware:
 *   The sensor uses an S8050 NPN transistor as a switch.
 *   Ten interleaved copper traces are split into two sets:
 *     • Five traces connected to +5V through a 100-ohm resistor (power set).
 *     • Five traces connected to the transistor base (sense set).
 *   When water bridges the two sets, a small base current turns the
 *   transistor ON, pulling the output pin HIGH.
 *   When no water is present, the transistor is OFF and the output is LOW.
 *
 *   GPIO 35 on the ESP32 is input-only (no internal pull-up).
 *   An external 10 kΩ pull-down resistor is recommended on the signal line
 *   so the pin reads LOW cleanly when the sensor is dry.
 *
 * Logic:
 *   isWaterPresent() → true  when pin reads HIGH (water detected)
 *   isWaterPresent() → false when pin reads LOW  (no water / dry)
 */

class WaterLevelSensor {
public:
    WaterLevelSensor();

    // Configure the GPIO pin. Call once in setup().
    void begin(uint8_t pin);

    // Return true if water is currently detected on the sensor.
    bool isWaterPresent() const;

    // Return raw digitalRead value (HIGH = 1, LOW = 0).
    int  rawRead() const;

private:
    uint8_t _pin;
};

#endif // WATER_LEVEL_SENSOR_H
