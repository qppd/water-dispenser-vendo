#ifndef RELAY_CONFIG_H
#define RELAY_CONFIG_H

#include <Arduino.h>
#include "PINS_CONFIG.h"

void initRELAY();
void operateRELAY(uint16_t RELAY, boolean OPENED);
void operateSSR(uint16_t RELAY, boolean OPENED);

#endif // RELAY_CONFIG_H