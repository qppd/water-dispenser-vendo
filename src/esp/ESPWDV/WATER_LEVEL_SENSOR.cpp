#include "WATER_LEVEL_SENSOR.h"

// ── WaterLevelSensor implementation ──────────────────────────────────────────

WaterLevelSensor::WaterLevelSensor()
    : _pin(0), _threshold(WATER_LEVEL_THRESHOLD),
      _filterIndex(0), _lastState(false), _pendingState(false),
      _stateChangeTimeMs(0)
{
    // Initialize filter buffer with zeros
    for (uint8_t i = 0; i < WATER_LEVEL_FILTER_SIZE; i++) {
        _filterBuffer[i] = 0;
    }
}

void WaterLevelSensor::begin(uint8_t pin) {
    _pin = pin;

    // GPIO 34 on the ESP32 is ADC1_CH6 (safe with WiFi/ESP-NOW).
    // Configure for proper analog reading with 5V sensor input:
    // - analogSetAttenuation(ADC_11db): 0-3.9V range
    // - analogSetWidth(12): 12-bit resolution (0-4095)
    pinMode(_pin, INPUT);
    
    // Set ADC1 parameters BEFORE calling analogRead()
    // 11dB attenuation: ~0-3.9V input range (safe for 3.3V sensors)
    // Use 6dB for 5V sensors if available: analogSetAttenuation(ADC_6db)
    analogSetAttenuation(ADC_11db);
    analogSetWidth(12);
    
    // Prime the filter with a few initial readings
    for (uint8_t i = 0; i < WATER_LEVEL_FILTER_SIZE; i++) {
        _filterBuffer[i] = analogRead(_pin);
        delay(2);  // Small delay between reads to avoid ADC contention
    }
    
    // Initialize state from first filtered reading
    _lastState = (rawReadFiltered() > _threshold);
    _pendingState = _lastState;
    _stateChangeTimeMs = millis();
    
    Serial.printf("[WATER_LEVEL] Initialized on GPIO%d, threshold=%d, initial_state=%s\n",
                  _pin, _threshold, _lastState ? "FULL(1)" : "EMPTY(0)");
}

bool WaterLevelSensor::isWaterPresent() const {
    // Return the debounced state (only changes after debounce timer expires)
    return _lastState;
}

int WaterLevelSensor::rawRead() const {
    // Return raw 12-bit analog value (0-4095) without filtering
    // WARNING: Can be noisy; use rawReadFiltered() for stable readings.
    return analogRead(_pin);
}

int WaterLevelSensor::rawReadFiltered() const {
    // Compute moving average of filter buffer
    int sum = 0;
    for (uint8_t i = 0; i < WATER_LEVEL_FILTER_SIZE; i++) {
        sum += _filterBuffer[i];
    }
    return sum / WATER_LEVEL_FILTER_SIZE;
}

void WaterLevelSensor::setThreshold(int threshold) {
    // Clamp threshold to valid ADC range
    _threshold = constrain(threshold, 0, 4095);
    Serial.printf("[WATER_LEVEL] Threshold updated to %d\n", _threshold);
}

int WaterLevelSensor::getThreshold() const {
    return _threshold;
}

bool WaterLevelSensor::getLastState() const {
    return _lastState;
}

bool WaterLevelSensor::update() {
    // This should be called periodically from loop() to update the filter
    // and debounce the water level state.
    // Returns true if state changed (useful for logging state transitions).

    // Shift filter buffer and add new reading
    for (uint8_t i = 0; i < (WATER_LEVEL_FILTER_SIZE - 1); i++) {
        _filterBuffer[i] = _filterBuffer[i + 1];
    }
    _filterBuffer[WATER_LEVEL_FILTER_SIZE - 1] = analogRead(_pin);
    
    // Compute filtered value and compare against threshold
    int filteredVal = rawReadFiltered();
    bool currentState = (filteredVal > _threshold);
    
    // If no pending state change or state matches pending, just continue
    if (currentState == _pendingState) {
        // Still in expected state; check if debounce time has elapsed
        if (currentState != _lastState && 
            (millis() - _stateChangeTimeMs >= WATER_LEVEL_DEBOUNCE_MS)) {
            // Debounce timer expired; accept the state change
            bool stateChanged = (currentState != _lastState);
            _lastState = currentState;
            
            if (stateChanged) {
                Serial.printf("[WATER_LEVEL] State changed to %s (raw=%d, filtered=%d, threshold=%d)\n",
                              _lastState ? "FULL(1)" : "EMPTY(0)", 
                              _filterBuffer[WATER_LEVEL_FILTER_SIZE - 1], filteredVal, _threshold);
            }
            return stateChanged;
        }
    } else {
        // State changed (filtered value crossed threshold)
        _pendingState = currentState;
        _stateChangeTimeMs = millis();
        
        Serial.printf("[WATER_LEVEL] State transition initiated: %s→%s (raw=%d, filtered=%d, threshold=%d)\n",
                      _lastState ? "FULL" : "EMPTY",
                      currentState ? "FULL" : "EMPTY",
                      _filterBuffer[WATER_LEVEL_FILTER_SIZE - 1], filteredVal, _threshold);
    }
    
    return false;
}
