/*
 * ESPWDVAcceptor.ino  —  Water Dispenser Vendo  (Acceptor / Gateway Node)
 *
 * Hardware:
 *   Coin Slot     (GPIO33, enable GPIO12) — Allantek, 1 pulse = P1
 *   Bill Acceptor (GPIO26, enable GPIO27) — TB-74,    1 pulse = P10
 *   Buzzer        (GPIO23)
 *
 * Serial (USB): 9600 baud — connected to Raspberry Pi (UART bridge)
 *   Inbound  (RPi → Acceptor):  plain-text control commands
 *   Outbound (Acceptor → RPi):  "Coin accepted: P<n>"
 *                               "Bill accepted: P<n>"
 *                               All ESP-Now messages forwarded verbatim from ESPWDV
 *
 * Communication: ESP-Now — ESPWDVAcceptor ↔ ESPWDV
 *   Inbound  (ESPWDV → Acceptor):  forwarded verbatim to Serial → RPi
 *   Outbound (Acceptor → ESPWDV):  RPI: commands forwarded from Serial
 *
 * Serial Monitor test commands (9600 baud):
 *   STATUS           — coin/bill credits, enable states, MAC address
 *   ENABLE COIN      — enable coin slot processing
 *   DISABLE COIN     — disable coin slot processing
 *   ENABLE BILL      — enable bill acceptor processing
 *   DISABLE BILL     — disable bill acceptor processing
 *   RESET COIN       — zero coin credit total and counters
 *   RESET BILL       — zero bill credit total and counters
 *   BUZZ <f> <ms>    — play tone at <f> Hz for <ms> ms  (e.g. BUZZ 1200 500)
 *   BUZZ OFF         — stop buzzer immediately
 *   MAC              — print this node's WiFi MAC address (for ESP-Now config)
 *   PING             — forward RPI:PING:1 to ESPWDV; expect ESP:PONG:1 in response
 *   RPI:<CMD>:<VAL>  — forward any RPI: command directly to ESPWDV via ESP-Now
 *   HELP             — print this command list
 */

#include <WiFi.h>
#include <esp_now.h>
#include "COIN_SLOT.h"
#include "BILL_ACCEPTOR.h"
#include "BUZZER_CONFIG.h"

// ── ESP-Now peer: ESPWDV (dispenser) MAC address ─────────────────────────────
// *** REQUIRED: Replace with the actual MAC address of your ESPWDV. ***
// Flash ESPWDV, open Serial Monitor (115200 baud), type MAC and press Enter.
// Copy the printed MAC here.  ESP-Now will NOT work with placeholder values.
static uint8_t dispenserMAC[] = {0x80, 0xF3, 0xDA, 0x55, 0x10, 0x64};  // ESPWDV MAC: 80:F3:DA:55:10:64

// ── ESP-Now ready flag ────────────────────────────────────────────────────────
// Guards all esp_now_send() calls; set true only after successful init + peer add.
static bool _espNowReady = false;

// ── Thread-safe ESP-Now receive ring buffer ───────────────────────────────────
// onDataRecv() runs in the WiFi task. Calling Serial.println() there directly
// races with Serial I/O in the loop task and produces a LoadProhibited crash
// inside the UART driver (EXCVADDR 0x4C — an internal queue-handle offset).
// Messages are queued here; loop() flushes them to Serial safely.
//
// Ring buffer with 8 slots so that rapid bursts (e.g. TEMP:HOT + TEMP:WARM +
// TEMP:COLD sent back-to-back from ESPWDV) are not silently dropped.
#define RECV_BUF_LEN   251
#define RECV_RING_SIZE   8

static char          _recvRing[RECV_RING_SIZE][RECV_BUF_LEN];
static volatile int  _recvHead = 0;  // next slot to write (WiFi task)
static volatile int  _recvTail = 0;  // next slot to read  (loop task)

static inline bool _ringFull()  { return (((_recvHead + 1) % RECV_RING_SIZE) == _recvTail); }
static inline bool _ringEmpty() { return (_recvHead == _recvTail); }

// ── ESP-Now receive callback ─────────────────────────────────────────────────
void onDataRecv(const esp_now_recv_info_t* recv_info, const uint8_t* data, int len) {
    if (len <= 0 || len > 250 || _ringFull()) return;
    memcpy(_recvRing[_recvHead], data, len);
    _recvRing[_recvHead][len] = '\0';
    _recvHead = (_recvHead + 1) % RECV_RING_SIZE;
}

// ── Serial monitor command handler ───────────────────────────────────────────
// Handles both RPi-originated (forwarded through) commands and direct hardware
// test commands typed into the Arduino Serial Monitor.
static void handleSerialCommand(const String& cmd) {

    // ── Coin slot control ────────────────────────────────────────────────────
    if (cmd == "ENABLE COIN") {
        enableCoin();

    } else if (cmd == "DISABLE COIN") {
        disableCoin();

    } else if (cmd == "RESET COIN") {
        coinCredit = 0;
        resetCoinDetection();
        Serial.println("Coin credit reset to 0");

    // ── Bill acceptor control ────────────────────────────────────────────────
    } else if (cmd == "ENABLE BILL") {
        enableBill();

    } else if (cmd == "DISABLE BILL") {
        disableBill();

    } else if (cmd == "RESET BILL") {
        billCredit = 0;
        resetBillDetection();
        Serial.println("Bill credit reset to 0");

    // ── Buzzer test ──────────────────────────────────────────────────────────
    // Usage: BUZZ <frequency_Hz> <duration_ms>   e.g.  BUZZ 1200 500
    } else if (cmd == "BUZZ OFF") {
        stopTone();
        Serial.println("Buzzer off");

    } else if (cmd.startsWith("BUZZ ")) {
        String args  = cmd.substring(5);
        args.trim();
        int spaceIdx = args.indexOf(' ');
        if (spaceIdx > 0) {
            int freq = args.substring(0, spaceIdx).toInt();
            int dur  = args.substring(spaceIdx + 1).toInt();
            if (freq > 0 && dur > 0) {
                playTone(freq, dur);
                Serial.printf("Buzzer: %d Hz for %d ms\n", freq, dur);
            } else {
                Serial.println("Usage: BUZZ <freq_Hz> <duration_ms>  e.g. BUZZ 1200 500");
            }
        } else {
            Serial.println("Usage: BUZZ <freq_Hz> <duration_ms>  e.g. BUZZ 1200 500");
        }

    // ── Status dump ──────────────────────────────────────────────────────────
    } else if (cmd == "STATUS") {
        Serial.println("=== ESPWDVAcceptor STATUS ===");
        Serial.printf("Coin slot : %s | Credit: P%u\n",
                      isCoinEnabled() ? "ENABLED" : "DISABLED", coinCredit);
        Serial.printf("Bill acpt : %s | Credit: P%u\n",
                      isBillEnabled() ? "ENABLED" : "DISABLED", billCredit);
        Serial.print ("MAC       : ");
        Serial.println(WiFi.macAddress());
        Serial.println("=============================");

    // ── MAC address ──────────────────────────────────────────────────────────
    } else if (cmd == "MAC") {
        Serial.print("ESPWDVAcceptor MAC: ");
        Serial.println(WiFi.macAddress());

    // ── ESP-Now ping to ESPWDV ───────────────────────────────────────────────
    } else if (cmd == "PING") {
        if (_espNowReady) {
            const char* ping = "RPI:PING:1";
            esp_now_send(dispenserMAC, (const uint8_t*)ping, strlen(ping));
            Serial.println("PING sent to ESPWDV — watch for ESP:PONG:1");
        } else {
            Serial.println("[ESP-Now] Not ready");
        }

    // ── Forward RPI: protocol commands to ESPWDV via ESP-Now ─────────────────
    // Also used by the RPi serial manager for all dispenser control.
    } else if (cmd.startsWith("RPI:")) {
        if (_espNowReady) {
            esp_now_send(dispenserMAC, (const uint8_t*)cmd.c_str(), cmd.length());
            Serial.print("[SER→ESP-Now] ");
            Serial.println(cmd);
        } else {
            Serial.println("[ESP-Now] Not ready");
        }

    // ── Help ─────────────────────────────────────────────────────────────────
    } else if (cmd == "HELP") {
        Serial.println("Commands:");
        Serial.println("  STATUS              — coin/bill credits, enable states, MAC");
        Serial.println("  ENABLE COIN         — enable coin slot");
        Serial.println("  DISABLE COIN        — disable coin slot");
        Serial.println("  RESET COIN          — zero coin credit total");
        Serial.println("  ENABLE BILL         — enable bill acceptor");
        Serial.println("  DISABLE BILL        — disable bill acceptor");
        Serial.println("  RESET BILL          — zero bill credit total");
        Serial.println("  BUZZ <f> <ms>       — play tone (e.g. BUZZ 1200 500)");
        Serial.println("  BUZZ OFF            — stop buzzer");
        Serial.println("  MAC                 — print WiFi MAC address");
        Serial.println("  PING                — send RPI:PING:1 to ESPWDV");
        Serial.println("  RPI:<CMD>:<VAL>     — forward command to ESPWDV");
        Serial.println("  Examples:");
        Serial.println("    RPI:RELAY1:5000   open cold relay for 5 s");
        Serial.println("    RPI:WARM:17143    warm dispense 500 ml");
        Serial.println("    RPI:STOP:0        emergency stop all relays");
        Serial.println("    RPI:SSR2:ON       turn heater on");

    } else {
        Serial.print("Unknown command: ");
        Serial.println(cmd);
        Serial.println("Type HELP for a list of commands.");
    }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup()
{
    Serial.begin(115200);
    Serial.setTimeout(10);   // prevent readStringUntil() blocking loop for 1 s

    // ── ESP-Now init ──────────────────────────────────────────────────────────
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    if (esp_now_init() == ESP_OK) {
        esp_now_register_recv_cb(onDataRecv);
        esp_now_peer_info_t peerInfo{};
        memcpy(peerInfo.peer_addr, dispenserMAC, 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        if (!esp_now_is_peer_exist(dispenserMAC)) {
            if (esp_now_add_peer(&peerInfo) == ESP_OK) {
                _espNowReady = true;
            } else {
                Serial.println("[ESP-Now] Failed to add Dispenser peer");
            }
        } else {
            _espNowReady = true;
        }
        if (_espNowReady) Serial.println("[ESP-Now] Initialized OK");
    } else {
        Serial.println("[ESP-Now] Init failed");
    }

    initALLANCOIN();    // Attach coin slot ISR, set enable pin HIGH
    initBILLACCEPTOR(); // Attach bill ISR, set enable pin HIGH
    initBuzzer();

    playTone(1200, 300); // Startup tone

    Serial.println("ESPWDVAcceptor ready");
    Serial.print("ESPWDVAcceptor MAC: ");
    Serial.println(WiFi.macAddress());
    Serial.println(">>> IMPORTANT: Copy this MAC into ESPWDV acceptorMAC[] <<<");
    Serial.println("Type HELP for serial monitor commands.");
}

// ── Main loop ─────────────────────────────────────────────────────────────────
void loop()
{
    // ── 0. Flush deferred ESP-Now messages to Serial (safe: loop-task context) ─
    while (!_ringEmpty()) {
        Serial.println(_recvRing[_recvTail]);
        _recvTail = (_recvTail + 1) % RECV_RING_SIZE;
    }

    // ── 1. Inbound serial commands from RPi (or Serial Monitor) ──────────────
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd.length() > 0) {
            handleSerialCommand(cmd);
        }
    }

    // ── 2. Coin pulse aggregation ─────────────────────────────────────────────
    // Allantek coin slot pulses ~50 ms apart; wait 250 ms idle to collect all pulses.
    if (coinInserted && (millis() - lastCoinPulseTime > 250)) {
        int coinValue = getCoinValue();
        if (coinValue > 0) {
            coinCredit += coinValue;
            playTone(1200, 300);
            Serial.print("Coin accepted: P");
            Serial.print(coinValue);
            Serial.print(" | Coin Credit: P");
            Serial.println(coinCredit);
        }
        resetCoinDetection();
    }

    // ── 3. Bill pulse aggregation ─────────────────────────────────────────────
    // TB-74 pulses ~100 ms apart; wait 250 ms after last pulse to collect them all.
    if (billInserted && (millis() - lastPulseTime > 250)) {
        int billValue = getBillValue();
        if (billValue > 0) {
            billCredit += billValue;
            playTone(1200, 300);
            Serial.print("Bill accepted: P");
            Serial.print(billValue);
            Serial.print(" | Bill Credit: P");
            Serial.println(billCredit);
        }
        resetBillDetection();
    }

}
