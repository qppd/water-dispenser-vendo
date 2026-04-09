#ifndef RELAY_CONFIG_H
#define RELAY_CONFIG_H

#include <Arduino.h>
#include "PINS_CONFIG.h"

// Convenience aliases so call sites can use symbolic names
#define RELAY_1  RELAY1_PIN
#define RELAY_2  RELAY2_PIN
#define RELAY_3  RELAY3_PIN
#define SSR_1    SSR1_PIN
#define SSR_2    SSR2_PIN
#define SSR_3    SSR3_PIN

void initRELAY();
void operateRELAY(uint8_t pin, bool opened);  // active-LOW relay
void operateSSR(uint8_t pin, bool opened);    // active-HIGH SSR
void stopAllRelays();                         // close all 3 relays
void stopAllSSRs();                           // turn off all 3 SSRs

#endif // RELAY_CONFIG_H