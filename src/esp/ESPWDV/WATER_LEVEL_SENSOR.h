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

// Moving average filter: number of samples (1=no filter, higher=more stable)
#define WATER_LEVEL_FILTER_SIZE 5

// Debounce time: must stay in new state for this many ms before accepting change
#define WATER_LEVEL_DEBOUNCE_MS 500UL

class WaterLevelSensor {
public:
    WaterLevelSensor();

    // Configure the GPIO pin & ADC settings. Call once in setup().
    // Sets ADC1 attenuation for proper 0-3.9V range and enables 12-bit resolution.
    void begin(uint8_t pin);

    // Return true if water is currently detected (debounced & filtered).
    bool isWaterPresent() const;

    // Return raw analog value (0-4095) without filtering.
    int  rawRead() const;

    // Return filtered (moving average) analog value.
    int  rawReadFiltered() const;

    // Set custom threshold for water detection.
    void setThreshold(int threshold);

    // Get current threshold.
    int  getThreshold() const;

    // Get last computed state (for debug logging).
    bool getLastState() const;

    // Update filter; call periodically from loop. Returns true if state changed.
    bool update();

private:
    uint8_t      _pin;
    int          _threshold;
    int          _filterBuffer[WATER_LEVEL_FILTER_SIZE];
    uint8_t      _filterIndex;
    bool         _lastState;            // Last debounced state
    bool         _pendingState;         // Candidate state waiting for debounce
    unsigned long _stateChangeTimeMs;   // When pendingState started
};

#endif // WATER_LEVEL_SENSOR_H

