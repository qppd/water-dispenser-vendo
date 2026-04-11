/*
 * ESPWDV.ino  —  Water Dispenser Vendo  (Dispenser Node)
 *
 * Hardware:
 *   SSR1 (GPIO32) → HEATER1    SSR2 (GPIO33) → HEATER2    SSR3 (GPIO25) → COOLER1
 *   RELAY1 (GPIO23) → Valve1+Pump1
 *   RELAY2 (GPIO22) → Valve2+Pump2
 *   RELAY3 (GPIO21) → Valve3+Pump3
 *   FLOW_SENSOR1 (GPIO39)   FLOW_SENSOR2 (GPIO34)   FLOW_SENSOR3 (GPIO35)
 *   DS18B20 OneWire bus (GPIO4)
 *
 * Serial (USB):   115200 baud  —  debug / manual test commands
 * Serial2 (UART2): 115200 baud  —  ESP32 ↔ Raspberry Pi 4
 *   TX  GPIO17  →  RPi GPIO15 (Pin 10)
 *   RX  GPIO16  ←  RPi GPIO14 (Pin 8)
 *
 * Protocol  (Serial2):
 *   Inbound  (RPi → ESP):  "RPI:<COMMAND>:<VALUE>\n"
 *   Outbound (ESP → RPi):  "ESP:<COMMAND>:<VALUE>\n"
 */

#include "PINS_CONFIG.h"
#include "RELAY_CONFIG.h"
#include "FLOW_SENSOR.h"
#include "DS18B20_SENSOR.h"

// ── UART2 ─────────────────────────────────────────────────────────────────────
#define SERIAL2_BAUD 115200
HardwareSerial RpiSerial(2);

// ── Sensor instances ──────────────────────────────────────────────────────────
FlowSensor    flow1, flow2, flow3;
DS18B20Sensor temp1, temp2, temp3;

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

// ── Helpers ───────────────────────────────────────────────────────────────────
static void startRelay(uint8_t idx, unsigned long durationMs) {
    if (idx > 2 || durationMs == 0) return;
    stopAllRelays();                              // safety: one relay at a time
    operateRELAY(relayTimers[idx].pin, true);
    relayTimers[idx].active     = true;
    relayTimers[idx].openAtMs   = millis();
    relayTimers[idx].durationMs = durationMs;
}

static FlowSensor& flowByIndex(uint8_t idx) {
    if (idx == 1) return flow2;
    if (idx == 2) return flow3;
    return flow1;
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
    else if (cmd == "FLOW3") {
        Serial.printf("FLOW3: %.3f L/min | Total: %.1f mL\n",
                      flow3.readFlowRate(), flow3.getTotalVolume());
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
        Serial.printf("FLOW3: %.3f L/min | Total: %.1f mL\n",
                      flow3.readFlowRate(), flow3.getTotalVolume());
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
        Serial.println("Commands: SSR1/2/3 ON|OFF | R1/2/3 ON|OFF | FLOW1/2/3 | TEMP | STATUS");
    }
}

// ── UART2 (RPi) command parser ────────────────────────────────────────────────
// Protocol format: "RPI:<COMMAND>:<VALUE>\n"
//
//   RPI:RELAY1:<ms>   open relay 1 for <ms> milliseconds
//   RPI:RELAY2:<ms>   open relay 2 for <ms> milliseconds
//   RPI:RELAY3:<ms>   open relay 3 for <ms> milliseconds
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
    } else if (command == "SSR1") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR1_PIN, on);
        RpiSerial.printf("ESP:SSR1:%s\n", on ? "ON" : "OFF");
    } else if (command == "SSR2") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR2_PIN, on);
        RpiSerial.printf("ESP:SSR2:%s\n", on ? "ON" : "OFF");
    } else if (command == "SSR3") {
        bool on = (value == "1" || value == "ON");
        operateSSR(SSR3_PIN, on);
        RpiSerial.printf("ESP:SSR3:%s\n", on ? "ON" : "OFF");
    } else if (command == "STOP") {
        for (uint8_t i = 0; i < 3; i++) relayTimers[i].active = false;
        stopAllRelays();
        RpiSerial.println("ESP:STOP:OK");
    }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    RpiSerial.begin(SERIAL2_BAUD, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN);

    initRELAY();

    flow1.begin(FLOW_SENSOR1_PIN);
    flow2.begin(FLOW_SENSOR2_PIN);
    flow3.begin(FLOW_SENSOR3_PIN);

    temp1.begin(DS18B20_1_PIN);
    temp2.begin(DS18B20_2_PIN);
    temp3.begin(DS18B20_3_PIN);

    Serial.println("ESPWDV ready");
    RpiSerial.println("ESP:STATUS:READY");
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

    // ── 2. UART2 inbound commands from Raspberry Pi ──────────────────────────
    if (RpiSerial.available()) {
        String msg = RpiSerial.readStringUntil('\n');
        msg.trim();
        if (msg.length() > 0) handleRpiCommand(msg);
    }

    // ── 3. Non-blocking relay timers ─────────────────────────────────────────
    for (uint8_t i = 0; i < 3; i++) {
        RelayTimer& t = relayTimers[i];
        if (t.active && (millis() - t.openAtMs >= t.durationMs)) {
            operateRELAY(t.pin, false);
            t.active = false;

            // Report completion + flow reading to RPi
            FlowSensor& fs = flowByIndex(i);
            RpiSerial.printf("ESP:DONE:%s\n", t.label);
            RpiSerial.printf("ESP:FLOW%u:%.3f\n", i + 1, fs.readFlowRate());
            RpiSerial.printf("ESP:VOL%u:%.1f\n",  i + 1, fs.getTotalVolume());
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
    // Format sent on RpiSerial (UART2):
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
        RpiSerial.printf("TEMP:HOT:%.1f\n",  hot);
        RpiSerial.printf("TEMP:WARM:%.1f\n", warm);
        RpiSerial.printf("TEMP:COLD:%.1f\n", cold);
        _tempLastSendMs= millis();
        _tempConverting= false;
    }
}
