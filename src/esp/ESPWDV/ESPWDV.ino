/*
 * ESPWDV.ino  —  Water Dispenser Vendo  (Dispenser Node)
 *
 * Hardware:
 *   SSR1 (GPIO32) → HEATER1    SSR2 (GPIO33) → HEATER2    SSR3 (GPIO25) → COOLER1
 *   RELAY1 (GPIO19) → Valve19603
 *   5390
 *   8844
 *   +Pump1
 *   RELAY2 (GPIO18) → Valve2+Pump2
 *   R5096
 *   ELAY3 (GPIO5)  → Valve3+Pump3
 *   FLOW_SENSOR1 (GPIO39)   FLOW_SENSOR2 (GPIO34)
 *   WATER_LEVEL_SENSOR (GPIO35) — S8050 NPN digital output, HIGH = water present
 *   DS18B20 OneWire bus (GPIO4)
 *
 * Serial (USB):  115200 baud  —  debug / manual test commands only
 *
 * Communication: ESP-Now  —  ESPWDV ↔ ESPWDVAcceptor
 *   All RPI: commands are received from ESPWDVAcceptor via ESP-Now.
 *   All ESP: / TEMP: responses are sent to ESPWDVAcceptor via ESP-Now.
 *
 * Protocol  (ESP-Now):
 *   Inbound  (Acceptor → Dispenser):  "RPI:<COMMAND>:<VALUE>"
 *   Outbound (Dispenser → Acceptor):  "ESP:<COMMAND>:<VALUE>"
 *                                     "TEMP:<SENSOR>:<VALUE>"
 *
 * To find the MAC address of ESPWDVAcceptor, flash it and run:
 *   Serial.println(WiFi.macAddress());
 * Then update ACCEPTOR_MAC below.
 */

#include <WiFi.h>
#include <esp_now.h>
#include "PINS_CONFIG.h"
#include "RELAY_CONFIG.h"
#include "FLOW_SENSOR.h"
#include "WATER_LEVEL_SENSOR.h"
#include "DS18B20_SENSOR.h"

// ── ESP-Now peer: ESPWDVAcceptor MAC address ──────────────────────────────────
// *** REQUIRED: Replace with the actual MAC address of your ESPWDVAcceptor. ***
// Flash ESPWDVAcceptor, open Serial Monitor (9600 baud), type MAC and press Enter.
// Copy the printed MAC here.  ESP-Now will NOT work with placeholder values.
static uint8_t acceptorMAC[] = {0x7C, 0x9E, 0xBD, 0x91, 0x8F, 0x1C};  // ESPWDVAcceptor MAC: 7C:9E:BD:91:8F:1C

// ── ESP-Now helpers ───────────────────────────────────────────────────────────
static void sendToAcceptor(const char* msg) {
    size_t len = strlen(msg);
    if (len > 250) len = 250;
    esp_now_send(acceptorMAC, (const uint8_t*)msg, len);
}

// Forward-declare the RPI command handler so the recv callback can call it.
static void handleRpiCommand(const String& msg);

// ── Sensor instances ──────────────────────────────────────────────────────────
FlowSensor       flow1, flow2;
WaterLevelSensor waterLevel;
DS18B20Sensor    temp1, temp2, temp3;

// ── Water-level broadcast state ──────────────────────────────────────────────
static bool          _lastWaterLevel   = false;
static unsigned long _waterLevelSendMs = 0;
#define WATER_LEVEL_BROADCAST_INTERVAL_MS 2000UL

// ── ESP-Now receive callback ─────────────────────────────────────────────────
// Called when ESPWDVAcceptor forwards an RPI: command to this node.
// Signature matches ESP32 Arduino core 3.x (IDF v5): first arg is recv_info.
static void onDataRecv(const esp_now_recv_info_t* recv_info, const uint8_t* data, int len) {
    if (len <= 0 || len > 250) return;
    char buf[251];
    memcpy(buf, data, len);
    buf[len] = '\0';
    String msg(buf);
    msg.trim();
    if (msg.length() > 0) {
        handleRpiCommand(msg);
    }
}

// ── Non-blocking relay timer state ───────────────────────────────────────────
struct RelayTimer {
    bool          active;
    uint8_t       pin;
    unsigned long openAtMs;
    unsigned long durationMs;
    char          label[8];  // e.g. "RELAY1"
};

static RelayTimer relayTimers[3] = {
    { false, RELAY1_PIN, 0, 0, "RELAY1" },
    { false, RELAY2_PIN, 0, 0, "RELAY2" },
    { false, RELAY3_PIN, 0, 0, "RELAY3" },
};

// ── Warm-water sequential mixer state ────────────────────────────────────────
// RPI:WARM:<total_ms>  causes the ESP32 to run two phases:
//   Phase 1: R3 (HOT pump/valve)  for hot_ms  = round(total_ms * 0.4375)
//   Phase 2: R1 (COLD pump/valve) for cold_ms = total_ms - hot_ms
// After Phase 2 completes, ESP:DONE:WARM is sent to the RPi.
//
// Target warm temperature: 40 °C
//   hot_frac = (40 - 5) / (85 - 5) = 35/80 = 0.4375  (44 %)
//   cold_frac = 45/80 = 0.5625                          (56 %)
struct WarmMixer {
    bool          active;
    uint8_t       phase;     // 1 = hot running, 2 = cold running
    unsigned long cold_ms;   // duration saved for the cold phase
};

static WarmMixer warmMixer = { false, 0, 0UL };

// ── Thermostat state ─────────────────────────────────────────────────────────
// SSR2 (HEATER) maintains HOT water at 85°C; SSR3 (COOLER) maintains 5°C.
// Both start true so heating/cooling begins immediately on boot.
static bool _ssr2Active = true;   // SSR2 (GPIO33, HEATER2) — HOT water, target 85°C
static bool _ssr3Active = true;   // SSR3 (GPIO25, COOLER1) — COLD water, target 5°C

// ── Helpers ───────────────────────────────────────────────────────────────────
static void startRelay(uint8_t idx, unsigned long durationMs) {
    if (idx > 2 || durationMs == 0) return;
    stopAllRelays();                              // safety: one relay at a time
    operateRELAY(relayTimers[idx].pin, true);
    relayTimers[idx].active     = true;
    relayTimers[idx].openAtMs   = millis();
    relayTimers[idx].durationMs = durationMs;
}

// Relay 3 (idx 2) used to share GPIO35 with flow3; GPIO35 is now the water-level
// sensor, so relay 3 no longer has a dedicated flow sensor.
static FlowSensor& flowByIndex(uint8_t idx) {
    if (idx == 1) return flow2;
    return flow1;   // idx 0, or idx 2 fallback (relay3 has no dedicated flow sensor)
}

// ── Serial monitor (USB) command parser ──────────────────────────────────────
static void handleSerialCommand(const String& cmd) {
    // SSR commands
    if      (cmd == "SSR1 ON")  { operateSSR(SSR1_PIN, true);   Serial.println("SSR1 ON");      }
    else if (cmd == "SSR1 OFF") { operateSSR(SSR1_PIN, false);  Serial.println("SSR1 OFF");     }
    else if (cmd == "SSR2 ON")  { operateSSR(SSR2_PIN, true);   Serial.println("SSR2 ON");      }
    else if (cmd == "SSR2 OFF") { operateSSR(SSR2_PIN, false);  Serial.println("SSR2 OFF");     }
    else if (cmd == "SSR3 ON")  { operateSSR(SSR3_PIN, true);   Serial.println("SSR3 ON");      }
    else if (cmd == "SSR3 OFF") { operateSSR(SSR3_PIN, false);  Serial.println("SSR3 OFF");     }
    // Relay commands
    else if (cmd == "R1 ON")    { operateRELAY(RELAY1_PIN, true);  Serial.println("RELAY1 OPEN");   }
    else if (cmd == "R1 OFF")   { operateRELAY(RELAY1_PIN, false); Serial.println("RELAY1 CLOSED"); }
    else if (cmd == "R2 ON")    { operateRELAY(RELAY2_PIN, true);  Serial.println("RELAY2 OPEN");   }
    else if (cmd == "R2 OFF")   { operateRELAY(RELAY2_PIN, false); Serial.println("RELAY2 CLOSED"); }
    else if (cmd == "R3 ON")    { operateRELAY(RELAY3_PIN, true);  Serial.println("RELAY3 OPEN");   }
    else if (cmd == "R3 OFF")   { operateRELAY(RELAY3_PIN, false); Serial.println("RELAY3 CLOSED"); }
    // Flow sensor readings
    else if (cmd == "FLOW1") {
        Serial.printf("FLOW1: %.3f L/min | Total: %.1f mL\n",
                      flow1.readFlowRate(), flow1.getTotalVolume());
    }
    else if (cmd == "FLOW2") {
        Serial.printf("FLOW2: %.3f L/min | Total: %.1f mL\n",
                      flow2.readFlowRate(), flow2.getTotalVolume());
    }
    else if (cmd == "WATER_LEVEL") {
        Serial.printf("WATER_LEVEL: %s (raw: %d)\n",
                      waterLevel.isWaterPresent() ? "PRESENT" : "LOW",
                      waterLevel.rawRead());
    }
    // Flow accumulator reset
    else if (cmd == "FLOW1 RESET") { flow1.reset(); Serial.println("FLOW1 reset"); }
    else if (cmd == "FLOW2 RESET") { flow2.reset(); Serial.println("FLOW2 reset"); }
    // Print WiFi MAC address (needed to configure ESP-Now peer on ESPWDVAcceptor)
    else if (cmd == "MAC") {
        Serial.print("ESPWDV MAC: ");
        Serial.println(WiFi.macAddress());
    }
    // Forward any RPI: protocol command from the serial monitor directly to the
    // RPI command handler — useful for testing dispensing without the RPi.
    // Examples:  RPI:RELAY1:5000   RPI:WARM:17143   RPI:STOP:0
    else if (cmd.startsWith("RPI:")) {
        handleRpiCommand(cmd);
        Serial.print("[SER→RPI] ");
        Serial.println(cmd);
    }
    // Temperature reading (debug: blocking wait acceptable on USB monitor)
    else if (cmd == "TEMP") {
        temp1.requestTemperature();
        temp2.requestTemperature();
        temp3.requestTemperature();
        delay(1000);  // wait for conversion (non-blocking mode is off; needed here)
        Serial.printf("TEMP HOT  (GPIO%d): %.2f C\n", DS18B20_1_PIN, temp1.getTemperatureC());
        Serial.printf("TEMP WARM (GPIO%d): %.2f C\n", DS18B20_2_PIN, temp2.getTemperatureC());
        Serial.printf("TEMP COLD (GPIO%d): %.2f C\n", DS18B20_3_PIN, temp3.getTemperatureC());
    }
    // Full status dump
    else if (cmd == "STATUS") {
        Serial.println("=== STATUS ===");
        Serial.printf("SSR1 (HEATER1  GPIO%d): %s\n", SSR1_PIN, digitalRead(SSR1_PIN) ? "ON"     : "OFF");
        Serial.printf("SSR2 (HEATER2  GPIO%d): %s\n", SSR2_PIN, digitalRead(SSR2_PIN) ? "ON"     : "OFF");
        Serial.printf("SSR3 (COOLER1  GPIO%d): %s\n", SSR3_PIN, digitalRead(SSR3_PIN) ? "ON"     : "OFF");
        Serial.printf("RELAY1         GPIO%d : %s\n", RELAY1_PIN, !digitalRead(RELAY1_PIN) ? "OPEN" : "CLOSED");
        Serial.printf("RELAY2         GPIO%d : %s\n", RELAY2_PIN, !digitalRead(RELAY2_PIN) ? "OPEN" : "CLOSED");
        Serial.printf("RELAY3         GPIO%d : %s\n", RELAY3_PIN, !digitalRead(RELAY3_PIN) ? "OPEN" : "CLOSED");
        Serial.printf("FLOW1: %.3f L/min | Total: %.1f mL\n",
                      flow1.readFlowRate(), flow1.getTotalVolume());
        Serial.printf("FLOW2: %.3f L/min | Total: %.1f mL\n",
                      flow2.readFlowRate(), flow2.getTotalVolume());
        Serial.printf("WATER_LEVEL: %s (raw: %d)\n",
                      waterLevel.isWaterPresent() ? "PRESENT" : "LOW",
                      waterLevel.rawRead());
        temp1.requestTemperature();
        temp2.requestTemperature();
        temp3.requestTemperature();
        delay(1000);  // wait for conversion
        Serial.printf("TEMP HOT  (GPIO%d): %.2f C\n", DS18B20_1_PIN, temp1.getTemperatureC());
        Serial.printf("TEMP WARM (GPIO%d): %.2f C\n", DS18B20_2_PIN, temp2.getTemperatureC());
        Serial.printf("TEMP COLD (GPIO%d): %.2f C\n", DS18B20_3_PIN, temp3.getTemperatureC());
        Serial.println("==============");
    }
    else {
        Serial.print("Unknown command: ");
        Serial.println(cmd);
        Serial.println("Commands:");
        Serial.println("  SSR1/2/3 ON|OFF          — heater / cooler SSR control");
        Serial.println("  R1/2/3 ON|OFF            — relay open / close (no timer)");
        Serial.println("  FLOW1|FLOW2              — read flow rate and volume");
        Serial.println("  FLOW1 RESET|FLOW2 RESET  — zero flow accumulator");
        Serial.println("  WATER_LEVEL              — read water-level sensor");
        Serial.println("  TEMP                     — read all DS18B20 temperatures");
        Serial.println("  STATUS                   — full status dump");
        Serial.println("  MAC                      — print WiFi MAC address");
        Serial.println("  RPI:<CMD>:<VAL>          — run any RPI: protocol command");
        Serial.println("  Examples: RPI:RELAY1:5000  RPI:WARM:17143  RPI:STOP:0");
    }
}

// ── ESP-Now (RPi) command parser ─────────────────────────────────────────────
// Protocol format: "RPI:<COMMAND>:<VALUE>\n"
//
//   RPI:RELAY1:<ms>   open relay 1 for <ms> milliseconds
//   RPI:RELAY2:<ms>   open relay 2 for <ms> milliseconds
//   RPI:RELAY3:<ms>   open relay 3 for <ms> milliseconds
//   RPI:WARM:<ms>     warm dispense — R3(HOT 44%) then R1(COLD 56%) sequentially
//   RPI:SSR1:1|ON     turn SSR1 on
//   RPI:SSR1:0|OFF    turn SSR1 off
//   RPI:SSR2:1|ON     turn SSR2 on / off
//   RPI:SSR3:1|ON     turn SSR3 on / off
//   RPI:STOP:0        emergency stop — close all relays
static void handleRpiCommand(const String& msg) {
    if (!msg.startsWith("RPI:")) return;

    int firstColon  = msg.indexOf(':');
    int secondColon = msg.indexOf(':', firstColon + 1);
    if (firstColon < 0 || secondColon < 0) return;

    String command = msg.substring(firstColon + 1, secondColon);
    String value   = msg.substring(secondColon + 1);
    command.toUpperCase();
    value.trim();

    if (command == "RELAY1") {
        startRelay(0, (unsigned long)value.toInt());
    } else if (command == "RELAY2") {
        startRelay(1, (unsigned long)value.toInt());
    } else if (command == "RELAY3") {
        startRelay(2, (unsigned long)value.toInt());
    } else if (command == "WARM") {
        // Sequential hot+cold mixing for warm water (~40 °C).
        // Phase 1: R3 (HOT)  for 43.75 % of total duration.
        // Phase 2: R1 (COLD) for the remaining 56.25 %.
        unsigned long total_ms = (unsigned long)value.toInt();
        unsigned long hot_ms   = (unsigned long)round(total_ms * 0.4375f);
        unsigned long cold_ms  = total_ms - hot_ms;
        warmMixer.active  = true;
        warmMixer.phase   = 1;
        warmMixer.cold_ms = cold_ms;
        startRelay(2, hot_ms);  // index 2 = RELAY3 (R3, HOT pump/valve)
    } else if (command == "SSR1") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR1_PIN, on);
        char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR1:%s", on ? "ON" : "OFF");
        sendToAcceptor(buf);
    } else if (command == "SSR2") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR2_PIN, on);
        _ssr2Active = on;   // keep thermostat state in sync
        char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR2:%s", on ? "ON" : "OFF");
        sendToAcceptor(buf);
    } else if (command == "SSR3") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR3_PIN, on);
        _ssr3Active = on;   // keep thermostat state in sync
        char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR3:%s", on ? "ON" : "OFF");
        sendToAcceptor(buf);
    } else if (command == "STOP") {
        for (uint8_t i = 0; i < 3; i++) relayTimers[i].active = false;
        warmMixer.active = false;   // cancel any in-progress warm mixing
        stopAllRelays();
        sendToAcceptor("ESP:STOP:OK");
    } else if (command == "PING") {
        // Respond to a connectivity ping from the acceptor or serial monitor.
        sendToAcceptor("ESP:PONG:1");
    } else if (command == "WATER_LEVEL") {
        // Query water level sensor and respond immediately.
        bool present = waterLevel.isWaterPresent();
        char buf[32]; snprintf(buf, sizeof(buf), "ESP:WATER_LEVEL:%d", present ? 1 : 0);
        sendToAcceptor(buf);
    }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    // ── ESP-Now init ──────────────────────────────────────────────────────────
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    if (esp_now_init() != ESP_OK) {
        Serial.println("ESP-Now init failed");
    } else {
        esp_now_register_recv_cb(onDataRecv);
        esp_now_peer_info_t peerInfo{};
        memcpy(peerInfo.peer_addr, acceptorMAC, 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        if (esp_now_add_peer(&peerInfo) != ESP_OK) {
            Serial.println("ESP-Now: failed to add Acceptor peer");
        } else {
            Serial.println("ESP-Now: Acceptor peer registered");
        }
    }

    initRELAY();

    // Start heater (SSR2) and cooler (SSR3) immediately — thermostat manages them.
    operateSSR(SSR2_PIN, true);   // HEATER ON  (_ssr2Active = true at init)
    operateSSR(SSR3_PIN, true);   // COOLER ON  (_ssr3Active = true at init)

    flow1.begin(FLOW_SENSOR1_PIN);
    flow2.begin(FLOW_SENSOR2_PIN);
    waterLevel.begin(WATER_LEVEL_SENSOR_PIN);

    temp1.begin(DS18B20_1_PIN);
    temp2.begin(DS18B20_2_PIN);
    temp3.begin(DS18B20_3_PIN);

    Serial.println("ESPWDV ready");
    Serial.print("ESPWDV MAC: ");
    Serial.println(WiFi.macAddress());
    Serial.println(">>> IMPORTANT: Copy this MAC into ESPWDVAcceptor dispenserMAC[] <<<");
    sendToAcceptor("ESP:STATUS:READY");
}

// ── Temperature broadcast state (module-level, used in loop) ─────────────────
static unsigned long _tempReqMs     = 0;   // millis() when last conversion was requested
static unsigned long _tempLastSendMs= 0;   // millis() of last completed broadcast
static bool          _tempConverting= false; // true while waiting for conversion

// Interval between temperature broadcasts (5 seconds)
#define TEMP_BROADCAST_INTERVAL_MS 5000UL
// DS18B20 12-bit conversion time: 750 ms; use 800 ms for safety margin
#define TEMP_CONVERSION_WAIT_MS    800UL

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    // ── 1. USB Serial monitor commands (for debugging / testing) ─────────────
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd.length() > 0) handleSerialCommand(cmd);
    }

    // ── 2. Inbound commands from ESPWDVAcceptor arrive via ESP-Now (onDataRecv)
    //    No polling needed here — handled by the registered callback above.

    // ── 3. Non-blocking relay timers ─────────────────────────────────────────
    for (uint8_t i = 0; i < 3; i++) {
        RelayTimer& t = relayTimers[i];
        if (t.active && (millis() - t.openAtMs >= t.durationMs)) {
            operateRELAY(t.pin, false);
            t.active = false;

            if (warmMixer.active) {
                // ── Warm-water mixing: intercept relay expiry ─────────────────
                if (warmMixer.phase == 1) {
                    // Hot phase done → start cold phase (R1)
                    warmMixer.phase = 2;
                    startRelay(0, warmMixer.cold_ms);   // index 0 = RELAY1 (COLD)
                } else if (warmMixer.phase == 2) {
                    // Cold phase done → warm dispense complete
                    warmMixer.active = false;
                    sendToAcceptor("ESP:DONE:WARM");
                }
            } else {
                // Normal single-relay completion
                FlowSensor& fs = flowByIndex(i);
                char buf[64];
                snprintf(buf, sizeof(buf), "ESP:DONE:%s", t.label);
                sendToAcceptor(buf);
                snprintf(buf, sizeof(buf), "ESP:FLOW%u:%.3f", i + 1, fs.readFlowRate());
                sendToAcceptor(buf);
                snprintf(buf, sizeof(buf), "ESP:VOL%u:%.1f", i + 1, fs.getTotalVolume());
                sendToAcceptor(buf);
            }
        }
    }

    // ── 4. Non-blocking periodic temperature broadcast (every 5 s) ───────────
    //
    // Phase A: Every 5 seconds, start a conversion on all 3 sensors.
    //          setWaitForConversion(false) was set in DS18B20Sensor::begin(),
    //          so requestTemperature() returns immediately (no blocking delay).
    //
    // Phase B: After 800 ms (conversion complete), read values and send to RPi.
    //
    // Format sent via ESP-Now to ESPWDVAcceptor:
    //   TEMP:HOT:<celsius>    e.g.  TEMP:HOT:45.2
    //   TEMP:WARM:<celsius>          TEMP:WARM:32.8
    //   TEMP:COLD:<celsius>          TEMP:COLD:12.4
    // ─────────────────────────────────────────────────────────────────────────
    unsigned long nowMs = millis();

    // Phase A — trigger conversion
    if (!_tempConverting && (nowMs - _tempLastSendMs >= TEMP_BROADCAST_INTERVAL_MS)) {
        temp1.requestTemperature();   // HOT  tank
        temp2.requestTemperature();   // WARM tank
        temp3.requestTemperature();   // COLD tank
        _tempReqMs     = nowMs;
        _tempConverting= true;
    }

    // Phase B — read and transmit (runs once, 800 ms after Phase A)
    if (_tempConverting && (millis() - _tempReqMs >= TEMP_CONVERSION_WAIT_MS)) {
        float hot  = temp1.getTemperatureC();
        float warm = temp2.getTemperatureC();
        float cold = temp3.getTemperatureC();
        char buf[40];
        snprintf(buf, sizeof(buf), "TEMP:HOT:%.1f",  hot);  sendToAcceptor(buf); Serial.println(buf);
        snprintf(buf, sizeof(buf), "TEMP:WARM:%.1f", warm); sendToAcceptor(buf); Serial.println(buf);
        snprintf(buf, sizeof(buf), "TEMP:COLD:%.1f", cold); sendToAcceptor(buf); Serial.println(buf);
        _tempLastSendMs= millis();
        _tempConverting= false;

        // ── 5. Thermostat control (runs once per temperature cycle) ──────────
        //
        // SSR2 (HEATER) — HOT water, target 85°C, 2°C hysteresis.
        if (!_ssr2Active && hot < 83.0f) {
            operateSSR(SSR2_PIN, true);
            _ssr2Active = true;
            sendToAcceptor("ESP:SSR2:ON");
        } else if (_ssr2Active && hot >= 85.0f) {
            operateSSR(SSR2_PIN, false);
            _ssr2Active = false;
            sendToAcceptor("ESP:SSR2:OFF");
        }

        // SSR3 (COOLER) — COLD water, target 5°C, 2°C hysteresis.
        if (!_ssr3Active && cold > 7.0f) {
            operateSSR(SSR3_PIN, true);
            _ssr3Active = true;
            sendToAcceptor("ESP:SSR3:ON");
        } else if (_ssr3Active && cold <= 5.0f) {
            operateSSR(SSR3_PIN, false);
            _ssr3Active = false;
            sendToAcceptor("ESP:SSR3:OFF");
        }
    }

    // ── 6. Non-blocking periodic water-level broadcast (every 2 s) ───────────
    // Sends "ESP:WATER:1" when water is present, "ESP:WATER:0" when tank is low.
    // Also broadcasts immediately on state change (present ↔ low).
    {
        bool nowPresent = waterLevel.isWaterPresent();
        bool stateChanged = (nowPresent != _lastWaterLevel);
        bool intervalElapsed = (nowMs - _waterLevelSendMs >= WATER_LEVEL_BROADCAST_INTERVAL_MS);

        if (stateChanged || intervalElapsed) {
            char wbuf[24];
            snprintf(wbuf, sizeof(wbuf), "ESP:WATER:%d", nowPresent ? 1 : 0);
            sendToAcceptor(wbuf);
            Serial.println(wbuf);
            _lastWaterLevel   = nowPresent;
            _waterLevelSendMs = nowMs;
        }
    }
}
