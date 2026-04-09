#include "RELAY_CONFIG.h"

void initRELAY() {
    // Regular relays: active-LOW → start closed (HIGH = off)
    pinMode(RELAY1_PIN, OUTPUT); digitalWrite(RELAY1_PIN, HIGH);
    pinMode(RELAY2_PIN, OUTPUT); digitalWrite(RELAY2_PIN, HIGH);
    pinMode(RELAY3_PIN, OUTPUT); digitalWrite(RELAY3_PIN, HIGH);

    // SSRs: active-HIGH → start off (LOW = off)
    pinMode(SSR1_PIN, OUTPUT); digitalWrite(SSR1_PIN, LOW);
    pinMode(SSR2_PIN, OUTPUT); digitalWrite(SSR2_PIN, LOW);
    pinMode(SSR3_PIN, OUTPUT); digitalWrite(SSR3_PIN, LOW);
}

void operateRELAY(uint8_t pin, bool opened) {
    // Active-LOW: opened = LOW, closed = HIGH
    digitalWrite(pin, opened ? LOW : HIGH);
}

void operateSSR(uint8_t pin, bool opened) {
    // Active-HIGH: on = HIGH, off = LOW
    digitalWrite(pin, opened ? HIGH : LOW);
}

void stopAllRelays() {
    operateRELAY(RELAY1_PIN, false);
    operateRELAY(RELAY2_PIN, false);
    operateRELAY(RELAY3_PIN, false);
}

void stopAllSSRs() {
    operateSSR(SSR1_PIN, false);
    operateSSR(SSR2_PIN, false);
    operateSSR(SSR3_PIN, false);
}