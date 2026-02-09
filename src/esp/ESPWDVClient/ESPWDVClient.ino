#include "COIN_SLOT.h"
#include "BILL_ACCEPTOR.h"
#include "BUZZER_CONFIG.h"
#include "RELAY_CONFIG.h"

void setup()
{
    Serial.begin(9600); // Start serial communication

    initALLANCOIN();    // Initialize coin slot interrupt
    initBILLACCEPTOR(); // Initialize bill acceptor interrupt
    initBuzzer();       // Initialize the buzzer
    initRELAY();        // Initialize the relay

    // Play a tone to indicate setup is finished
    playTone(1200, 300); // 1.2kHz tone for 300ms
}

void loop()
{
    // Handle coin insertion
    if (coinInserted && (millis() - lastCoinPulseTime > 250))
    {
        int coinValue = getCoinValue();
        if (coinValue > 0)
        {
            coinCredit += coinValue;
            playTone(1200, 300); // Tone for coin acceptance
            Serial.print("Coin accepted: P");
            Serial.print(coinValue);
            Serial.print(" | Coin Credit: P");
            Serial.println(coinCredit);
        }
        resetCoinDetection();
    }

    // Handle bill insertion
    if (pulseCount > 0 && (millis() - lastPulseTime > 150))
    {
        int billValue = getBillValue();
        if (billValue > 0)
        {
            billCredit += billValue;
            playTone(1200, 300); // Tone for bill acceptance
            Serial.print("Bill accepted: P");
            Serial.print(billValue);
            Serial.print(" | Bill Credit: P");
            Serial.println(billCredit);
        }
        pulseCount = 0;
    }

    // Example: If total credit >= 20, dispense (operate relay)
    if ((coinCredit + billCredit) >= 20)
    {
        operateRELAY(RELAY_1, true);  // Open relay for dispensing
        delay(2000);                  // Dispense time
        operateRELAY(RELAY_1, false); // Close relay
        coinCredit = 0;               // Reset credits after dispensing
        billCredit = 0;
        Serial.println("Dispensed water");
    }
}