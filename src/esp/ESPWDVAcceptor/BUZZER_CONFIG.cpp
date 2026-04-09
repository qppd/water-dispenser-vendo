#include "BUZZER_CONFIG.h"

// Initialize the buzzer
void initBuzzer() {
    pinMode(BUZZER_PIN, OUTPUT);
    stopTone(); // Ensure the buzzer is off initially
}

// Play a tone at a specific frequency for a given duration
void playTone(int frequency, int duration) {
    tone(BUZZER_PIN, frequency, duration);
}

// Stop any ongoing tone
void stopTone() {
    noTone(BUZZER_PIN);
}