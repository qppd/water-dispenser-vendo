#include "WATER_LEVEL_SENSOR.h"

// ── WaterLevelSensor implementation ──────────────────────────────────────────

WaterLevelSensor::WaterLevelSensor()
    : _pin(0), _threshold(WATER_LEVEL_THRESHOLD)
{}

void WaterLevelSensor::begin(uint8_t pin) {
    _pin = pin;
    // GPIO 34 on the ESP32 is ADC-capable (analog input).
    // analogRead() returns 0-4095 (12-bit resolution).
    pinMode(_pin, INPUT);
}

bool WaterLevelSensor::isWaterPresent() const {
    // Analog comparison: water is present if reading exceeds threshold
    return analogRead(_pin) > _threshold;
}

int WaterLevelSensor::rawRead() const {
    // Return raw 12-bit analog value (0-4095)
    return analogRead(_pin);
}

void WaterLevelSensor::setThreshold(int threshold) {
    // Clamp threshold to valid ADC range
    _threshold = constrain(threshold, 0, 4095);
}

int WaterLevelSensor::getThreshold() const {
    return _threshold;
}
