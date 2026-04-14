#include "COIN_SLOT.h"
#include "BILL_ACCEPTOR.h"
#include "BUZZER_CONFIG.h"

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup()
{
    Serial.begin(9600);

    initALLANCOIN();    // Attach coin slot ISR, set enable pin HIGH
    initBILLACCEPTOR(); // Attach bill ISR, set enable pin HIGH
    initBuzzer();

    playTone(1200, 300); // Startup tone

    Serial.println("WDVClient ready");
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
    // TB-74 pulses ~100 ms apart; wait 250 ms after last pulse to collect them all
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