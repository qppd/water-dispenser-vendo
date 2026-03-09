#include "RELAY_CONFIG.h"

//-----------------------------------------------------------------
//FUNCTION FOR SETTING RELAY PIN MODE------------------------------
//-----------------------------------------------------------------
void initRELAY(){
  pinMode(RELAY_1, OUTPUT);
  pinMode(RELAY_2, OUTPUT);
  // Relays are active-LOW: start with both closed (HIGH = off)
  digitalWrite(RELAY_1, HIGH);
  digitalWrite(RELAY_2, HIGH);
}


void operateRELAY(uint16_t RELAY, boolean OPENED) {
  if (OPENED)
    digitalWrite(RELAY, LOW);
  else
    digitalWrite(RELAY, HIGH);
}


void operateSSR(uint16_t RELAY, boolean OPENED) {
  if (OPENED)
    digitalWrite(RELAY, HIGH);
  else
    digitalWrite(RELAY, LOW);
}

void stopAllRelays() {
  operateRELAY(RELAY_1, false);
  operateRELAY(RELAY_2, false);
}