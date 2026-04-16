#include "WATER_LEVEL_SENSOR.h"

// ── WaterLevelSensor implementation ──────────────────────────────────────────

WaterLevelSensor::WaterLevelSensor()
    : _pin(0)
{}

void WaterLevelSensor::begin(uint8_t pin) {
    _pin = pin;
    // GPIO 35 on the ESP32 is input-only; no internal pull-up is available.
    // Use an external 10 kΩ pull-down resistor so the pin rests cleanly at LOW.
    pinMode(_pin, INPUT);
}

bool WaterLevelSensor::isWaterPresent() const {
    return digitalRead(_pin) == HIGH;
}

int WaterLevelSensor::rawRead() const {
    return digitalRead(_pin);
}
