// Pin connected to bill acceptor signal
const byte billPin = 2;  // INT0 on Arduino Uno

// Variables for pulse counting
volatile unsigned int pulseCount = 0;
unsigned int credit = 0;         // In pesos
unsigned long lastPulseTime = 0; // For debounce
const unsigned long pulseDebounce = 50; // ms debounce

// Value of each pulse in pesos
const int billValuePerPulse = 10; // 1 pulse = ₱10

void setup() {
  Serial.begin(9600);
  pinMode(billPin, INPUT_PULLUP); // Use internal pull-up
  attachInterrupt(digitalPinToInterrupt(billPin), billPulseISR, FALLING);
  Serial.println("Bill Acceptor Ready...");
}

void loop() {
  // If there are pulses and 250ms have passed since last pulse, update credit
  if (pulseCount > 0 && (millis() - lastPulseTime > 250)) {
    credit += pulseCount * billValuePerPulse;
    Serial.print("Credit: ₱");
    Serial.println(credit);

    // Reset pulse counter
    pulseCount = 0;
  }
}

// Interrupt Service Routine
void billPulseISR() {
  unsigned long currentTime = millis();

  // Debounce to avoid false counting
  if (currentTime - lastPulseTime > pulseDebounce) {
    pulseCount++;
    lastPulseTime = currentTime;
  }
}
