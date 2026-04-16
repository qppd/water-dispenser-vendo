#ifndef PINS_CONFIG_H
#define PINS_CONFIG_H

// ── SSR (Solid State Relays, active HIGH) ─────────────────────────────────────
#define SSR1_PIN   32   // HEATER1
#define SSR2_PIN   33   // HEATER2
#define SSR3_PIN   25   // COOLER1

// ── Regular Relays (active LOW) ───────────────────────────────────────────────
#define RELAY1_PIN 19   // Solenoid Valve1 + Pump1
#define RELAY2_PIN 18   // Solenoid Valve2 + Pump2
#define RELAY3_PIN  5   // Solenoid Valve3 + Pump3

// ── Flow Sensors (input-only GPIOs, external pull-up required) ────────────────
#define FLOW_SENSOR1_PIN 39
#define FLOW_SENSOR2_PIN 34

// ── Water Level Sensor (input-only GPIO 35, external pull-down required) ──────
// S8050 NPN transistor output: HIGH = water present, LOW = no water.
#define WATER_LEVEL_SENSOR_PIN 35

// ── DS18B20 OneWire Temperature Sensors (one pin each) ───────────────────────
#define DS18B20_1_PIN 23
#define DS18B20_2_PIN 22
#define DS18B20_3_PIN 21

#endif // PINS_CONFIG_H