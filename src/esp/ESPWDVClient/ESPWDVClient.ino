#include "COIN_SLOT.h"
#include "BILL_ACCEPTOR.h"
#include "BUZZER_CONFIG.h"
#include "RELAY_CONFIG.h"

// ── Non-blocking relay state ──────────────────────────────────────────────────
// The RPi owns all dispensing decisions.  The ESP32 only executes the relay
// for the requested duration and reports completion.
static unsigned long relayOpenTime  = 0;  // millis() when relay was opened
static unsigned long relayDurationMs = 0; // requested hold duration
static bool          relayActive    = false;
static uint16_t      activeRelay    = 0;  // which relay is currently open

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup()
{
    Serial.begin(9600);

    initALLANCOIN();    // Attach coin slot ISR, set enable pin HIGH
    initBILLACCEPTOR(); // Attach bill ISR, set enable pin HIGH
    initBuzzer();
    initRELAY();        // Sets RELAY_1 and RELAY_2 to OUTPUT, both HIGH (off)

    playTone(1200, 300); // Startup tone

    Serial.println("WDVClient ready");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
static void startRelay(uint16_t relay, unsigned long durationMs)
{
    stopAllRelays();           // Safety: close any previously open relay first
    operateRELAY(relay, true); // Open (active LOW → write LOW)
    activeRelay    = relay;
    relayDurationMs = durationMs;
    relayOpenTime  = millis();
    relayActive    = true;
}

// ── Main loop ─────────────────────────────────────────────────────────────────
void loop()
{
    // ── 1. Inbound serial commands from RPi ──────────────────────────────────
    // Commands are \n-terminated (SerialManager appends \r\n; trim() handles both).
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd == "ENABLE COIN") {
            enableCoin();
        } else if (cmd == "DISABLE COIN") {
            disableCoin();
        } else if (cmd == "ENABLE BILL") {
            enableBill();
        } else if (cmd == "DISABLE BILL") {
            disableBill();
        } else if (cmd.startsWith("CMD:DISPENSE:")) {
            // RPi requests: open RELAY_1 (bottle) for duration_ms milliseconds
            unsigned long ms = cmd.substring(13).toInt();
            if (ms > 0) startRelay(RELAY_1, ms);
        } else if (cmd.startsWith("CMD:FOUNTAIN:")) {
            // RPi requests: open RELAY_2 (fountain) for duration_ms milliseconds
            unsigned long ms = cmd.substring(13).toInt();
            if (ms > 0) startRelay(RELAY_2, ms);
        } else if (cmd == "CMD:STOP") {
            // Emergency stop: close all relays immediately
            relayActive = false;
            stopAllRelays();
            Serial.println("Dispensed water"); // Notify RPi that flow has stopped
        }
    }

    // ── 2. Non-blocking relay timer ───────────────────────────────────────────
    if (relayActive && (millis() - relayOpenTime >= relayDurationMs)) {
        operateRELAY(activeRelay, false); // Close relay
        relayActive = false;
        Serial.println("Dispensed water"); // RPi expects exactly this string
    }

    // ── 3. Coin pulse aggregation ─────────────────────────────────────────────
    // Collect all pulses for one coin and report once 250ms after the last pulse
    if (coinInserted && (millis() - lastCoinPulseTime > 250)) {
        int coinValue = getCoinValue();
        if (coinValue > 0) {
            coinCredit += coinValue; // Local running total for debug output only
            playTone(1200, 300);
            Serial.print("Coin accepted: P");
            Serial.print(coinValue);
            Serial.print(" | Coin Credit: P");
            Serial.println(coinCredit);
        }
        resetCoinDetection();
    }

    // ── 4. Bill pulse aggregation ─────────────────────────────────────────────
    // TB-74 pulses ~100 ms apart; wait 250 ms after last pulse to collect them all
    if (billInserted && (millis() - lastPulseTime > 250)) {
        int billValue = getBillValue();
        if (billValue > 0) {
            billCredit += billValue; // Local running total for debug output only
            playTone(1200, 300);
            Serial.print("Bill accepted: P");
            Serial.print(billValue);
            Serial.print(" | Bill Credit: P");
            Serial.println(billCredit);
        }
        resetBillDetection();
    }
}