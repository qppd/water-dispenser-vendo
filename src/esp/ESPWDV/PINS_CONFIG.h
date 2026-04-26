#ifndef PINS_CONFIG_H
#define PINS_CONFIG_H

// ── SSR (Solid State Relays, active HIGH) ─────────────────────────────────────
#define SSR1_PIN   32   // HEATER1
#define SSR2_PIN   33   // HEATER2
#define SSR3_PIN   25   // COOLER1

// ── Regular Relays (active LOW) ───────────────────────────────────────────────
#define RELAY1_PIN 19   // Solenoid Valve1 + Pump1
#define RELAY2_PIN 18   // INLET SOLENOID VALVE (RPI:INLET command)
#define RELAY3_PIN  5   // Solenoid Valve3 + Pump3

// ── Flow Sensors (input-only GPIOs, external pull-up required) ────────────────
#define FLOW_SENSOR1_PIN 39
#define FLOW_SENSOR2_PIN 35

// ── Water Level Sensor (analog input, GPIO 34 — 12-bit ADC, 0-4095) ─────────
// MakerLab Rain/Water Level Sensor (analog output)
// Threshold comparison: analogRead > 1500 → water present
// Calibrate by reading raw values: setThreshold(new_value) or modify WATER_LEVEL_THRESHOLD
#define WATER_LEVEL_SENSOR_PIN 34

// ── DS18B20 OneWire Temperature Sensors (one pin each) ───────────────────────
#define DS18B20_1_PIN 23
#define DS18B20_2_PIN 22
#define DS18B20_3_PIN 21

#endif // PINS_CONFIG_H