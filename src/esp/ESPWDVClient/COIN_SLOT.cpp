#include "COIN_SLOT.h"

volatile bool coinInserted = false;
volatile unsigned long coinLastDebounceTime = 0;
const unsigned long coinDebounceDelay = 50; // debounce delay in ms
volatile unsigned int coinPulseCount = 0;
unsigned int coinCredit = 0;
unsigned long lastCoinPulseTime = 0;

void IRAM_ATTR ITRCOIN() {
  unsigned long coinCurrentTime = millis();
  if ((coinCurrentTime - coinLastDebounceTime) > coinDebounceDelay) {
    coinPulseCount++;
    coinInserted = true;
    coinLastDebounceTime = coinCurrentTime;
    lastCoinPulseTime = coinCurrentTime;
  }
}

void initALLANCOIN() {
  pinMode(coinPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(coinPin), ITRCOIN, FALLING);
  Serial.println("Coin Slot initialized");
  Serial.println("Accepts: P1, P5, P10, P20 coins");
}


// Reset coin detection variables
void resetCoinDetection() {
  coinPulseCount = 0;
  coinInserted = false;
}

// Determine coin value based on pulse count
int getCoinValue() {
  int coinValue = 0;
  if (coinPulseCount > 0) {
    coinValue = coinPulseCount; // Assuming 1 pulse = 1 peso
  }
  return coinValue;
}