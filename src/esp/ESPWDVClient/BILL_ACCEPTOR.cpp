#include "BILL_ACCEPTOR.h"

volatile unsigned int pulseCount = 0;
unsigned int billCredit = 0;
unsigned long lastPulseTime = 0;
const unsigned long pulseDebounce = 70; // ms debounce (TB-74 pulses are 100ms apart)
volatile int detectedBillValue = 0; // Current detected bill value

void IRAM_ATTR billPulseISR() {
  unsigned long currentTime = millis();
  if (currentTime - lastPulseTime > pulseDebounce) {
    pulseCount++;
    lastPulseTime = currentTime;
  }
}

void initBILLACCEPTOR() {
  pinMode(billPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(billPin), billPulseISR, FALLING);
  Serial.println("TB-74 Bill Acceptor initialized");
  Serial.println("Accepts: P20, P50, and P100 bills");
  Serial.println("Pulse protocol: 1 pulse = P10 value");
}

// Determine bill value based on pulse count
// TB-74 Bill Acceptor: 1 pulse = P10 value
// P20 = 2 pulses, P50 = 5 pulses, P100 = 10 pulses
int getBillValue() {
  int billValue = 0;
  
  // TB-74 uses simple formula: pulse count × 10
  if (pulseCount > 0) {
    billValue = pulseCount * 10;
    
    // Validate pulse count matches TB-74 expected values
    // Valid counts: 2 (P20), 5 (P50), 10 (P100)
    // Also accept 20 (P200), 50 (P500), 100 (P1000) if enabled on TB-74
    if (pulseCount == 2 || pulseCount == 5 || pulseCount == 10 || 
        pulseCount == 20 || pulseCount == 50 || pulseCount == 100) {
      // Valid pulse count
      Serial.print("Valid TB-74 pulse count: ");
      Serial.print(pulseCount);
      Serial.print(" pulses = P");
      Serial.println(billValue);
    } else {
      // Invalid pulse count - likely noise or error
      Serial.print("WARNING: Invalid pulse count detected: ");
      Serial.print(pulseCount);
      Serial.print(" pulses (calculated P");
      Serial.print(billValue);
      Serial.println(")");
      
      // Round to nearest valid denomination to handle ±1-2 pulse errors
      if (pulseCount >= 1 && pulseCount <= 3) {
        billValue = 20;  // 1-3 pulses → P20
        Serial.println("Corrected to P20 (2 pulses expected)");
      } else if (pulseCount >= 4 && pulseCount <= 7) {
        billValue = 50;  // 4-7 pulses → P50
        Serial.println("Corrected to P50 (5 pulses expected)");
      } else if (pulseCount >= 8 && pulseCount <= 12) {
        billValue = 100; // 8-12 pulses → P100
        Serial.println("Corrected to P100 (10 pulses expected)");
      } else {
        Serial.println("ERROR: Pulse count too far from expected values - rejecting");
        billValue = 0; // Reject invalid bills
      }
    }
  }
  
  return billValue;
}