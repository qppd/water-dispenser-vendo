#ifndef WATER_LEVEL_SENSOR_H
#define WATER_LEVEL_SENSOR_H

#include <Arduino.h>

/*
 * WATER_LEVEL_SENSOR — Analog water-level detection module
 *
 * Hardware:
 * MakerLab Rain/Water Level Sensor (analog output)
 * Operating voltage: DC 3-5V
 * Operating current: <20mA
 * Sensor type: Analog (outputs 0-4095 on ESP32 ADC)
 * Detection area: 40mm x 16mm
 * GPIO 34 on the ESP32 is ADC-capable (12-bit, 0-4095).
 *
 * Logic:
 * - raw = 0 → EMPTY (no water)
 * - raw >= 1 → FULL (water detected)
 * Simple: sends raw value to WDVHost for display
 */

class WaterLevelSensor {
public:
  WaterLevelSensor();

  // Configure the GPIO pin. Call once in setup().
  void begin(uint8_t pin);

  // Return raw analog value (0-4095) directly from ADC.
  int rawRead() const;

  // Return true if water detected (raw >= 1).
  bool isWaterPresent() const;

private:
  uint8_t _pin;
};

#endif // WATER_LEVEL_SENSOR_H
