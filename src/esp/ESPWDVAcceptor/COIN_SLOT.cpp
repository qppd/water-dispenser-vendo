#include "COIN_SLOT.h"

volatile bool coinInserted = false;
volatile unsigned long coinLastDebounceTime = 0;
const unsigned long coinDebounceDelay = 50; // debounce delay in ms
volatile unsigned int coinPulseCount = 0;
unsigned int coinCredit = 0;
volatile unsigned long lastCoinPulseTime = 0;
volatile bool coinEnabled = true; // enabled by default

void IRAM_ATTR ITRCOIN() {
  if (!coinEnabled) return; // ignore pulses when disabled
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
  pinMode(coinEnablePin, OUTPUT);
  digitalWrite(coinEnablePin, HIGH); // enabled by default
  attachInterrupt(digitalPinToInterrupt(coinPin), ITRCOIN, FALLING);
  Serial.println("Coin Slot initialized");
  Serial.println("Accepts: P1, P5, P10, P20 coins");
}

// Enable coin slot: raise the enable pin and allow ISR processing
void enableCoin() {
  coinEnabled = true;
  digitalWrite(coinEnablePin, HIGH);
  Serial.println("Coin enabled");
}

// Disable coin slot: pull enable pin low and block ISR processing
void disableCoin() {
  coinEnabled = false;
  digitalWrite(coinEnablePin, LOW);
  Serial.println("Coin disabled");
}

bool isCoinEnabled() {
  return coinEnabled;
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