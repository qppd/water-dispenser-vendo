#ifndef FLOW_SENSOR_H
#define FLOW_SENSOR_H

#include <Arduino.h>

// Calibration: YF-S201 produces ~450 pulses per litre (7.5 pulses/sec = 1 L/min).
// Override before calling begin() if your sensor differs.
#define FLOW_PULSES_PER_LITRE 450.0f

class FlowSensor {
public:
    FlowSensor();

    // Attach interrupt and start tracking. Call once per sensor in setup().
    void begin(uint8_t pin);

    // Return instantaneous flow rate in L/min since the last call.
    float readFlowRate();

    // Return accumulated volume in mL since last reset().
    float getTotalVolume();

    // Reset pulse counter and accumulated volume.
    void reset();

    // Public to allow direct increment from the ISR trampoline.
    volatile uint32_t _pulseCount;

private:
    uint8_t       _pin;
    float         _totalVolumeMl;
    uint32_t      _lastPulseCount;
    unsigned long _lastCalcTimeMs;
};

#endif // FLOW_SENSOR_H
