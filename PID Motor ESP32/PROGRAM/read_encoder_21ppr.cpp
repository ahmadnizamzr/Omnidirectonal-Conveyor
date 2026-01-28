#include <Arduino.h>

const uint8_t PIN_PWM = 27; // IN1 MX1508
const uint8_t PIN_DIR = 14; // IN2 MX1508

#define ENCODER_PIN 35
#define SLOTS_PER_REV 21

#define PWM_CH 0
#define PWM_FREQ 1000 // MX1508 AMAN
#define PWM_RES 8
#define SAMPLE_TIME_MS 1000

volatile uint32_t pulseCount = 0;
volatile uint32_t lastPulseMicros = 0;
unsigned long lastSample = 0;

void IRAM_ATTR encoderISR()
{
    uint32_t now = micros();
    if (now - lastPulseMicros > 300)
    {
        pulseCount++;
        lastPulseMicros = now;
    }
}

void motorForward(uint8_t speed)
{
    digitalWrite(PIN_DIR, LOW); // arah
    ledcWrite(PWM_CH, speed);   // PWM
}

void setup()
{
    Serial.begin(115200);

    pinMode(PIN_PWM, OUTPUT);
    pinMode(PIN_DIR, OUTPUT);

    ledcSetup(PWM_CH, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_PWM, PWM_CH);

    pinMode(ENCODER_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(ENCODER_PIN), encoderISR, RISING);

    Serial.println("ESP32 + MX1508 STABLE");
}

void loop()
{
    motorForward(250);

    if (millis() - lastSample >= SAMPLE_TIME_MS)
    {
        noInterrupts();
        uint32_t pulses = pulseCount;
        pulseCount = 0;
        interrupts();

        float rpm = (pulses / 21.0) * 60.0;

        Serial.print("RPM: ");
        Serial.println(rpm);

        lastSample = millis();
    }
}
