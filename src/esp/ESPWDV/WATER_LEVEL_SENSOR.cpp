#include "WATER_LEVEL_SENSOR.h"

WaterLevelSensor::WaterLevelSensor() : _pin(0) {}

void WaterLevelSensor::begin(uint8_t pin) {
  _pin = pin;
  pinMode(_pin, INPUT);
  //analogSetAttenuation(ADC_11db);
  //analogSetWidth(12);
}

int WaterLevelSensor::rawRead() const {
  return analogRead(_pin);
}

bool WaterLevelSensor::isWaterPresent() const {
  return rawRead() >= 1;
}
