#ifndef COIN_SLOT_H
#define COIN_SLOT_H

#include <Arduino.h>
#include "PINS_CONFIG.h"

// Coin values supported by the slot
#define COIN_VALUE_1 1
#define COIN_VALUE_5 5
#define COIN_VALUE_10 10
#define COIN_VALUE_20 20

extern volatile bool coinInserted;
extern volatile unsigned long coinLastDebounceTime;
extern const unsigned long coinDebounceDelay;
extern volatile unsigned int coinPulseCount;
extern unsigned int coinCredit;
extern unsigned long lastCoinPulseTime;

void IRAM_ATTR ITRCOIN();
void initALLANCOIN();
int getCoinValue(); // Get the value of the detected coin
void resetCoinDetection(); // Reset coin detection variables

#endif // COIN_SLOT_H