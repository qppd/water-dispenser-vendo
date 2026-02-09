#ifndef BUZZER_CONFIG_H
#define BUZZER_CONFIG_H

#include <Arduino.h>
#include "PINS_CONFIG.h"

// Function declarations
void initBuzzer();
void playTone(int frequency, int duration);
void stopTone();

#endif // BUZZER_CONFIG_H