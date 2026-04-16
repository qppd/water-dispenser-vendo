#ifndef DS18B20_SENSOR_H
#define DS18B20_SENSOR_H

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>

class DS18B20Sensor {
public:
    DS18B20Sensor();

    // Initialise the OneWire bus on the given pin and discover devices.
    void begin(uint8_t pin);

    // Send a temperature conversion request to all devices on the bus.
    void requestTemperature();

    // Return temperature in °C for the sensor at the given bus index.
    // Returns DEVICE_DISCONNECTED_C (-127) if index is out of range.
    float getTemperatureC(uint8_t index = 0);

    // Number of DS18B20 sensors found on the bus.
    uint8_t getDeviceCount();

private:
    uint8_t  _pin;
    uint8_t  _deviceCount;
    bool     _ready;   // true once begin() has constructed the objects

    // Pre-allocated storage — avoids heap allocation and any malloc failure.
    alignas(OneWire)           uint8_t _oneWireBuf[sizeof(OneWire)];
    alignas(DallasTemperature) uint8_t _sensorsBuf[sizeof(DallasTemperature)];

    OneWire*           _oneWire;
    DallasTemperature* _sensors;
};

#endif // DS18B20_SENSOR_H
