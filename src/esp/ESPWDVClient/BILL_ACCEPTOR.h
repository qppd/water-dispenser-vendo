#ifndef BILL_ACCEPTOR_H
#define BILL_ACCEPTOR_H

#include <Arduino.h>
#include "PINS_CONFIG.h"

// Bill values supported by TB-74 acceptor
#define BILL_VALUE_20 20
#define BILL_VALUE_50 50
#define BILL_VALUE_100 100

extern volatile unsigned int pulseCount;
extern unsigned int billCredit;
extern unsigned long lastPulseTime;
extern const unsigned long pulseDebounce;
extern volatile int detectedBillValue; // Value of the detected bill

void IRAM_ATTR billPulseISR();
void initBILLACCEPTOR();
int getBillValue(); // Get the value of the detected bill

#endif // BILL_ACCEPTOR_H