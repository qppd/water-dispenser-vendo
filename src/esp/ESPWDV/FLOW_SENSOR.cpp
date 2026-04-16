#include "FLOW_SENSOR.h"

// ── ISR trampolines  (supports up to 3 sensor instances) ─────────────────────
static FlowSensor* _sensorInstances[3] = { nullptr, nullptr, nullptr };
static uint8_t     _sensorCount = 0;

// C++17 deprecates ++ and += on volatile types; use explicit read-then-write.
static void IRAM_ATTR _isr0() { if (_sensorInstances[0]) _sensorInstances[0]->_pulseCount = _sensorInstances[0]->_pulseCount + 1; }
static void IRAM_ATTR _isr1() { if (_sensorInstances[1]) _sensorInstances[1]->_pulseCount = _sensorInstances[1]->_pulseCount + 1; }
static void IRAM_ATTR _isr2() { if (_sensorInstances[2]) _sensorInstances[2]->_pulseCount = _sensorInstances[2]->_pulseCount + 1; }

typedef void (*IsrFn)();
static const IsrFn ISR_TABLE[3] = { _isr0, _isr1, _isr2 };

// ── FlowSensor implementation ─────────────────────────────────────────────────
FlowSensor::FlowSensor()
    : _pulseCount(0),
      _pin(0),
      _totalVolumeMl(0.0f),
      _lastPulseCount(0),
      _lastCalcTimeMs(0)
{}

void FlowSensor::begin(uint8_t pin) {
    _pin           = pin;
    _pulseCount    = 0;
    _totalVolumeMl = 0.0f;
    _lastPulseCount = 0;
    _lastCalcTimeMs = millis();

    // GPIO 34/35/39 on ESP32 are INPUT-ONLY; no internal pull-up available.
    // Use an external 10 kΩ pull-up on the signal line.
    pinMode(_pin, INPUT);

    if (_sensorCount < 3) {
        uint8_t idx = _sensorCount++;
        _sensorInstances[idx] = this;
        attachInterrupt(digitalPinToInterrupt(_pin), ISR_TABLE[idx], RISING);
    }
}

float FlowSensor::readFlowRate() {
    unsigned long now     = millis();
    unsigned long elapsed = now - _lastCalcTimeMs;

    if (elapsed == 0) return 0.0f;

    // Snapshot pulse count atomically
    noInterrupts();
    uint32_t currentPulse = _pulseCount;
    interrupts();

    uint32_t pulses = currentPulse - _lastPulseCount;
    _lastPulseCount = currentPulse;
    _lastCalcTimeMs = now;

    float litres   = pulses / FLOW_PULSES_PER_LITRE;
    float minutes  = elapsed / 60000.0f;
    float flowRate = (minutes > 0.0f) ? (litres / minutes) : 0.0f;

    _totalVolumeMl += litres * 1000.0f;

    return flowRate;
}

float FlowSensor::getTotalVolume() {
    return _totalVolumeMl;
}

void FlowSensor::reset() {
    noInterrupts();
    _pulseCount = 0;
    interrupts();

    _totalVolumeMl  = 0.0f;
    _lastPulseCount = 0;
    _lastCalcTimeMs = millis();
}
