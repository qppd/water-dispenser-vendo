#include "DS18B20_SENSOR.h"
#include <new>   // placement new

DS18B20Sensor::DS18B20Sensor()
    : _pin(0), _deviceCount(0), _ready(false), _oneWire(nullptr), _sensors(nullptr)
{}

void DS18B20Sensor::begin(uint8_t pin) {
    _pin = pin;
    // Construct directly into pre-allocated member buffers — no heap involved.
    _oneWire = new (_oneWireBuf) OneWire(_pin);
    _sensors = new (_sensorsBuf) DallasTemperature(_oneWire);
    _sensors->begin();
    // Non-blocking: requestTemperatures() returns immediately;
    // caller must wait ~800 ms before reading (see ESPWDV loop).
    _sensors->setWaitForConversion(false);
    _deviceCount = _sensors->getDeviceCount();
    _ready = true;
}

void DS18B20Sensor::requestTemperature() {
    if (!_ready) return;
    _sensors->requestTemperatures();
}

float DS18B20Sensor::getTemperatureC(uint8_t index) {
    if (!_ready || index >= _deviceCount) {
        return DEVICE_DISCONNECTED_C;
    }
    return _sensors->getTempCByIndex(index);
}

uint8_t DS18B20Sensor::getDeviceCount() {
    return _deviceCount;
}
