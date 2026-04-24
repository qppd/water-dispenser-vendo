#ifndef WATER_LEVEL_SENSOR_H
#define WATER_LEVEL_SENSOR_H

#include <Arduino.h>

/*
 * WATER_LEVEL_SENSOR  —  Analog water-level detection module
 *
 * Hardware:
 *   MakerLab Rain/Water Level Sensor (analog output)
 *   Operating voltage: DC 3-5V
 *   Operating current: <20mA
 *   Sensor type: Analog (outputs 0-4095 on ESP32 ADC)
 *   Detection area: 40mm x 16mm
 *   GPIO 34 on the ESP32 is ADC-capable (12-bit, 0-4095).
 *
 * Logic:
 *   - Reads analog value from sensor
 *   - Compares against WATER_LEVEL_THRESHOLD (configurable, default: 1500)
 *   - isWaterPresent() -> true if analogRead > threshold (water detected)
 *   - isWaterPresent() -> false if analogRead <= threshold (dry)
 *
 * Calibration:
 *   Call setThreshold(value) to adjust sensitivity.
 *   Typical range: 1000-2000 depending on sensor condition.
 *   Higher values = requires more water to trigger.
 */

// Default threshold — water detected when analogRead() > this value
// Adjust based on calibration: dry sensor ≈ 0-500, wet sensor ≈ 2500-4095
#define WATER_LEVEL_THRESHOLD 1500

class WaterLevelSensor {
public:
    WaterLevelSensor();

    // Configure the GPIO pin. Call once in setup().
    void begin(uint8_t pin);

    // Return true if water is currently detected on the sensor.
    bool isWaterPresent() const;

    // Return raw analog value (0-4095).
    int  rawRead() const;

    // Set custom threshold for water detection.
    void setThreshold(int threshold);

    // Get current threshold.
    int  getThreshold() const;

private:
    uint8_t _pin;
    int     _threshold;
};

#endif // WATER_LEVEL_SENSOR_H

