/*
 * ESPWDV.ino — Water Dispenser Vendo (Dispenser Node)
 *
 * Hardware:
 *   SSR1 (GPIO32) → HEATER1     SSR2 (GPIO33) → HEATER2     SSR3 (GPIO25) → COOLER1
 *   RELAY1 (GPIO19) → Valve1+Pump1
 *   RELAY2 (GPIO18) → Inlet solenoid valve (tank fill)
 *   RELAY3 (GPIO5)  → Valve3+Pump3
 *   FLOW_SENSOR1 (GPIO39)     FLOW_SENSOR2 (GPIO34)
 *   WATER_LEVEL_SENSOR (GPIO35) — Analog, raw=0 empty, raw>=1 full
 *   DS18B20 OneWire bus (GPIO4)
 *
 * Serial (USB): 115200 baud — debug / manual test commands only
 *
 * Communication: ESP-Now — ESPWDV ↔ ESPWDVAcceptor
 * All RPI: commands are received from ESPWDVAcceptor via ESP-Now.
 * All ESP: / TEMP: responses are sent to ESPWDVAcceptor via ESP-Now.
 *
 * Protocol (ESP-Now):
 *   Inbound (Acceptor → Dispenser): "RPI:<COMMAND>:<VALUE>"
 *   Outbound (Dispenser → Acceptor): "ESP:<COMMAND>:<VALUE>"
 *                                    "TEMP:<SENSOR>:<VALUE>"
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
static uint8_t acceptorMAC[] = {0x7C, 0x9E, 0xBD, 0x91, 0x8F, 0x1C};

// ── ESP-Now helpers ───────────────────────────────────────────────────────────
static void sendToAcceptor(const char* msg) {
  size_t len = strlen(msg);
  if (len > 250) len = 250;
  esp_now_send(acceptorMAC, (const uint8_t*)msg, len);
}

static void handleRpiCommand(const String& msg);

// ── Sensor instances ──────────────────────────────────────────────────────────
FlowSensor flow1, flow2;
WaterLevelSensor waterLevel;
DS18B20Sensor temp1, temp2, temp3;

// ── Water-level broadcast state ──────────────────────────────────────────────
static bool _lastWaterLevel = false;
static bool _inletAutoMode = true;
static unsigned long _waterLevelSendMs = 0;
#define WATER_LEVEL_BROADCAST_INTERVAL_MS 2000UL

// ── ESP-Now receive callback ─────────────────────────────────────────────────
static void onDataRecv(const esp_now_recv_info_t* recv_info, const uint8_t* data, int len) {
  if (len <= 0 || len > 250) return;
  char buf[251];
  memcpy(buf, data, len);
  buf[len] = '\0';
  String msg(buf);
  msg.trim();
  if (msg.length() > 0) handleRpiCommand(msg);
}

// ── Non-blocking relay timer state ───────────────────────────────────────────
struct RelayTimer {
  bool active;
  uint8_t pin;
  unsigned long openAtMs;
  unsigned long durationMs;
  char label[8];
};

static RelayTimer relayTimers[3] = {
  { false, RELAY1_PIN, 0, 0, "RELAY1" },
  { false, RELAY2_PIN, 0, 0, "RELAY2" },
  { false, RELAY3_PIN, 0, 0, "RELAY3" },
};

// ── Warm-water sequential mixer state ────────────────────────────────────────
struct WarmMixer {
  bool active;
  uint8_t phase;
  unsigned long cold_ms;
};

static WarmMixer warmMixer = { false, 0, 0UL };

// ── Thermostat state ─────────────────────────────────────────────────────────
static bool _ssr2Active = true;
static bool _ssr3Active = true;

// ── Helpers ───────────────────────────────────────────────────────────────────
static void startRelay(uint8_t idx, unsigned long durationMs) {
  if (idx > 2 || durationMs == 0) return;
  stopAllRelays();
  operateRELAY(relayTimers[idx].pin, true);
  relayTimers[idx].active = true;
  relayTimers[idx].openAtMs = millis();
  relayTimers[idx].durationMs = durationMs;
}

static FlowSensor& flowByIndex(uint8_t idx) {
  if (idx == 1) return flow2;
  return flow1;
}

// ── Serial monitor (USB) command parser ──────────────────────────────────────
static void handleSerialCommand(const String& cmd) {
  if (cmd == "SSR1 ON") { operateSSR(SSR1_PIN, true); Serial.println("SSR1 ON"); }
  else if (cmd == "SSR1 OFF") { operateSSR(SSR1_PIN, false); Serial.println("SSR1 OFF"); }
  else if (cmd == "SSR2 ON") { operateSSR(SSR2_PIN, true); Serial.println("SSR2 ON"); }
  else if (cmd == "SSR2 OFF") { operateSSR(SSR2_PIN, false); Serial.println("SSR2 OFF"); }
  else if (cmd == "SSR3 ON") { operateSSR(SSR3_PIN, true); Serial.println("SSR3 ON"); }
  else if (cmd == "SSR3 OFF") { operateSSR(SSR3_PIN, false); Serial.println("SSR3 OFF"); }
  else if (cmd == "R1 ON") { operateRELAY(RELAY1_PIN, true); Serial.println("RELAY1 OPEN"); }
  else if (cmd == "R1 OFF") { operateRELAY(RELAY1_PIN, false); Serial.println("RELAY1 CLOSED"); }
  else if (cmd == "R2 ON") { operateRELAY(RELAY2_PIN, true); Serial.println("RELAY2 OPEN"); }
  else if (cmd == "R2 OFF") { operateRELAY(RELAY2_PIN, false); Serial.println("RELAY2 CLOSED"); }
  else if (cmd == "R3 ON") { operateRELAY(RELAY3_PIN, true); Serial.println("RELAY3 OPEN"); }
  else if (cmd == "R3 OFF") { operateRELAY(RELAY3_PIN, false); Serial.println("RELAY3 CLOSED"); }
  else if (cmd == "FLOW1") {
    Serial.printf("FLOW1: %.3f L/min | Total: %.1f mL\n",
      flow1.readFlowRate(), flow1.getTotalVolume());
  }
  else if (cmd == "FLOW2") {
    Serial.printf("FLOW2: %.3f L/min | Total: %.1f mL\n",
      flow2.readFlowRate(), flow2.getTotalVolume());
  }
  else if (cmd == "WATER_LEVEL") {
    int raw = waterLevel.rawRead();
    bool present = waterLevel.isWaterPresent();
    Serial.printf("WATER_LEVEL: raw=%d present=%s\n",
      raw, present ? "YES(1)" : "NO(0)");
  }
  else if (cmd == "FLOW1 RESET") { flow1.reset(); Serial.println("FLOW1 reset"); }
  else if (cmd == "FLOW2 RESET") { flow2.reset(); Serial.println("FLOW2 reset"); }
  else if (cmd == "MAC") {
    Serial.print("ESPWDV MAC: ");
    Serial.println(WiFi.macAddress());
  }
  else if (cmd.startsWith("RPI:")) {
    handleRpiCommand(cmd);
    Serial.print("[SER→RPI] ");
    Serial.println(cmd);
  }
  else if (cmd == "TEMP") {
    temp1.requestTemperature();
    temp2.requestTemperature();
    temp3.requestTemperature();
    delay(1000);
    Serial.printf("TEMP HOT (GPIO%d): %.2f C\n", DS18B20_1_PIN, temp1.getTemperatureC());
    Serial.printf("TEMP WARM (GPIO%d): %.2f C\n", DS18B20_2_PIN, temp2.getTemperatureC());
    Serial.printf("TEMP COLD (GPIO%d): %.2f C\n", DS18B20_3_PIN, temp3.getTemperatureC());
  }
  else if (cmd == "STATUS") {
    Serial.println("=== STATUS ===");
    Serial.printf("SSR1 (HEATER1 GPIO%d): %s\n", SSR1_PIN, digitalRead(SSR1_PIN) ? "ON" : "OFF");
    Serial.printf("SSR2 (HEATER2 GPIO%d): %s\n", SSR2_PIN, digitalRead(SSR2_PIN) ? "ON" : "OFF");
    Serial.printf("SSR3 (COOLER1 GPIO%d): %s\n", SSR3_PIN, digitalRead(SSR3_PIN) ? "ON" : "OFF");
    Serial.printf("RELAY1 GPIO%d : %s\n", RELAY1_PIN, !digitalRead(RELAY1_PIN) ? "OPEN" : "CLOSED");
    Serial.printf("RELAY2 GPIO%d : %s\n", RELAY2_PIN, !digitalRead(RELAY2_PIN) ? "OPEN" : "CLOSED");
    Serial.printf("RELAY3 GPIO%d : %s\n", RELAY3_PIN, !digitalRead(RELAY3_PIN) ? "OPEN" : "CLOSED");
    Serial.printf("FLOW1: %.3f L/min | Total: %.1f mL\n",
      flow1.readFlowRate(), flow1.getTotalVolume());
    Serial.printf("FLOW2: %.3f L/min | Total: %.1f mL\n",
      flow2.readFlowRate(), flow2.getTotalVolume());
    {
      int raw = waterLevel.rawRead();
      bool present = waterLevel.isWaterPresent();
      Serial.printf("WATER_LEVEL: raw=%d present=%s\n",
        raw, present ? "YES(1)" : "NO(0)");
    }
    temp1.requestTemperature();
    temp2.requestTemperature();
    temp3.requestTemperature();
    delay(1000);
    Serial.printf("TEMP HOT (GPIO%d): %.2f C\n", DS18B20_1_PIN, temp1.getTemperatureC());
    Serial.printf("TEMP WARM (GPIO%d): %.2f C\n", DS18B20_2_PIN, temp2.getTemperatureC());
    Serial.printf("TEMP COLD (GPIO%d): %.2f C\n", DS18B20_3_PIN, temp3.getTemperatureC());
    Serial.println("==============");
  }
  else {
    Serial.print("Unknown command: ");
    Serial.println(cmd);
    Serial.println("Commands:");
    Serial.println(" SSR1/2/3 ON|OFF — heater / cooler SSR control");
    Serial.println(" R1/2/3 ON|OFF — relay open / close (no timer)");
    Serial.println(" FLOW1|FLOW2 — read flow rate and volume");
    Serial.println(" FLOW1 RESET|FLOW2 RESET — zero flow accumulator");
    Serial.println(" WATER_LEVEL — read water-level sensor");
    Serial.println(" TEMP — read all DS18B20 temperatures");
    Serial.println(" STATUS — full status dump");
    Serial.println(" MAC — print WiFi MAC address");
    Serial.println(" RPI:<CMD>:<VAL> — run any RPI: protocol command");
    Serial.println(" Examples: RPI:RELAY1:5000 RPI:WARM:17143 RPI:STOP:0");
  }
}

// ── ESP-Now (RPi) command parser ─────────────────────────────────────────────
static void handleRpiCommand(const String& msg) {
  if (!msg.startsWith("RPI:")) return;

  int firstColon = msg.indexOf(':');
  int secondColon = msg.indexOf(':', firstColon + 1);
  if (firstColon < 0 || secondColon < 0) return;

  String command = msg.substring(firstColon + 1, secondColon);
  String value = msg.substring(secondColon + 1);
  command.toUpperCase();
  value.trim();

  if (command == "RELAY1") {
    startRelay(0, (unsigned long)value.toInt());
  } else if (command == "RELAY2") {
    startRelay(1, (unsigned long)value.toInt());
  } else if (command == "RELAY3") {
    startRelay(2, (unsigned long)value.toInt());
  } else if (command == "WARM") {
    unsigned long total_ms = (unsigned long)value.toInt();
    unsigned long hot_ms = (unsigned long)round(total_ms * 0.4375f);
    unsigned long cold_ms = total_ms - hot_ms;
    warmMixer.active = true;
    warmMixer.phase = 1;
    warmMixer.cold_ms = cold_ms;
    startRelay(2, hot_ms);
  } else if (command == "SSR1") {
    bool on = (value == "1" || value == "ON");
    operateSSR(SSR1_PIN, on);
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR1:%s", on ? "ON" : "OFF");
    sendToAcceptor(buf);
  } else if (command == "SSR2") {
    bool on = (value == "1" || value == "ON");
    operateSSR(SSR2_PIN, on);
    _ssr2Active = on;
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR2:%s", on ? "ON" : "OFF");
    sendToAcceptor(buf);
  } else if (command == "SSR3") {
    bool on = (value == "1" || value == "ON");
    operateSSR(SSR3_PIN, on);
    _ssr3Active = on;
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:SSR3:%s", on ? "ON" : "OFF");
    sendToAcceptor(buf);
  } else if (command == "INLET") {
    bool closeValve = (value == "1" || value == "ON");
    operateRELAY(RELAY2_PIN, !closeValve);
    _inletAutoMode = false;
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:INLET:%s", closeValve ? "CLOSED" : "OPEN");
    sendToAcceptor(buf);
  } else if (command == "INLET_AUTO") {
    _inletAutoMode = (value == "1" || value == "ON");
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:INLET_AUTO:%d", _inletAutoMode ? 1 : 0);
    sendToAcceptor(buf);
  } else if (command == "STOP") {
    for (uint8_t i = 0; i < 3; i++) relayTimers[i].active = false;
    warmMixer.active = false;
    stopAllRelays();
    sendToAcceptor("ESP:STOP:OK");
  } else if (command == "PING") {
    sendToAcceptor("ESP:PONG:1");
  } else if (command == "WATER_LEVEL") {
    bool present = waterLevel.isWaterPresent();
    char buf[32]; snprintf(buf, sizeof(buf), "ESP:WATER_LEVEL:%d", present ? 1 : 0);
    sendToAcceptor(buf);
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

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

  operateSSR(SSR2_PIN, true);
  operateSSR(SSR3_PIN, true);

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

// ── Temperature broadcast state ──────────────────────────────────────────────
static unsigned long _tempReqMs = 0;
static unsigned long _tempLastSendMs = 0;
static bool _tempConverting = false;

#define TEMP_BROADCAST_INTERVAL_MS 5000UL
#define TEMP_CONVERSION_WAIT_MS 800UL

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  // ── 1. USB Serial monitor commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) handleSerialCommand(cmd);
  }

  // ── 2. Non-blocking relay timers
  for (uint8_t i = 0; i < 3; i++) {
    RelayTimer& t = relayTimers[i];
    if (t.active && (millis() - t.openAtMs >= t.durationMs)) {
      operateRELAY(t.pin, false);
      t.active = false;

      if (warmMixer.active) {
        if (warmMixer.phase == 1) {
          warmMixer.phase = 2;
          startRelay(0, warmMixer.cold_ms);
        } else if (warmMixer.phase == 2) {
          warmMixer.active = false;
          sendToAcceptor("ESP:DONE:WARM");
        }
      } else {
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

  unsigned long nowMs = millis();

  // ── 3. Temperature broadcast & thermostat control
  if (!_tempConverting && (nowMs - _tempLastSendMs >= TEMP_BROADCAST_INTERVAL_MS)) {
    temp1.requestTemperature();
    temp2.requestTemperature();
    temp3.requestTemperature();
    _tempReqMs = nowMs;
    _tempConverting = true;
  }

  if (_tempConverting && (millis() - _tempReqMs >= TEMP_CONVERSION_WAIT_MS)) {
    float hot = temp1.getTemperatureC();
    float warm = temp2.getTemperatureC();
    float cold = temp3.getTemperatureC();
    char buf[40];
    snprintf(buf, sizeof(buf), "TEMP:HOT:%.1f", hot); sendToAcceptor(buf); Serial.println(buf);
    snprintf(buf, sizeof(buf), "TEMP:WARM:%.1f", warm); sendToAcceptor(buf); Serial.println(buf);
    snprintf(buf, sizeof(buf), "TEMP:COLD:%.1f", cold); sendToAcceptor(buf); Serial.println(buf);
    _tempLastSendMs = millis();
    _tempConverting = false;

    // Thermostat control
    if (!_ssr2Active && hot < 83.0f) {
      operateSSR(SSR2_PIN, true);
      _ssr2Active = true;
      sendToAcceptor("ESP:SSR2:ON");
    } else if (_ssr2Active && hot >= 85.0f) {
      operateSSR(SSR2_PIN, false);
      _ssr2Active = false;
      sendToAcceptor("ESP:SSR2:OFF");
    }

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

  // ── 4. Water-level broadcast & automatic inlet valve control ────────────────
  {
    int raw = waterLevel.rawRead();
    bool nowPresent = waterLevel.isWaterPresent();
    bool stateChanged = (nowPresent != _lastWaterLevel);
    bool intervalElapsed = (nowMs - _waterLevelSendMs >= WATER_LEVEL_BROADCAST_INTERVAL_MS);

    // Automatic inlet valve control (when auto mode enabled)
    static bool _lastPresent = false;
    if (_inletAutoMode && nowPresent != _lastPresent) {
      if (nowPresent) {
        operateRELAY(RELAY2_PIN, false);
        sendToAcceptor("ESP:INLET:CLOSED_AUTO");
        Serial.println("[INLET] Tank FULL → valve CLOSED (auto)");
      } else {
        operateRELAY(RELAY2_PIN, true);
        sendToAcceptor("ESP:INLET:OPEN_AUTO");
        Serial.println("[INLET] Tank EMPTY → valve OPEN (auto)");
      }
      _lastPresent = nowPresent;
    }

    if (stateChanged || intervalElapsed) {
      char wbuf[24];
      snprintf(wbuf, sizeof(wbuf), "ESP:WATER:%d", nowPresent ? 1 : 0);
      sendToAcceptor(wbuf);
      Serial.printf("[WATER_LEVEL_TX] Sent: %s (state=%s, changed=%d, interval=%d)\n",
        wbuf, nowPresent ? "FULL" : "EMPTY", stateChanged, intervalElapsed);
      _lastWaterLevel = nowPresent;
      _waterLevelSendMs = nowMs;
    }
  }
}
