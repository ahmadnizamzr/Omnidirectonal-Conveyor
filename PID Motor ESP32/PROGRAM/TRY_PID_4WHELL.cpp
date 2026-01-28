
#include <Arduino.h>

// Pin motor driver MX1508
// Motor1
#define M1_A 27
#define M1_B 14
// Motor2
#define M2_A 12
#define M2_B 13
// Motor3
#define M3_A 26
#define M3_B 25
// Motor4
#define M4_A 33
#define M4_B 32

// Pin encoder
#define ENC1 35
#define ENC2 34
#define ENC3 39
#define ENC4 36

// LED indikator
#define LED1 19
#define LED2 18
#define LED3 5
#define LED4 15

// Konstanta
const int PULSES_PER_REV = 96; // 2 * 48
const float CONTROL_DT = 0.02; // 20 ms loop kontrol

// Variabel encoder
volatile unsigned long lastTime[4] = {0};
volatile unsigned long period[4] = {0};

// PID parameter
struct PID
{
    float Kp, Ki, Kd;
    float integral, lastErr;
};
PID pid[4] = {
    {0.5, 0.2, 0.01, 0, 0},
    {0.5, 0.2, 0.01, 0, 0},
    {0.5, 0.2, 0.01, 0, 0},
    {0.5, 0.2, 0.01, 0, 0}};

// Target RPM tiap motor
float targetRPM[4] = {0, 0, 0, 0};

// --- ISR untuk encoder ---
void IRAM_ATTR encoderISR1()
{
    unsigned long t = micros();
    period[0] = t - lastTime[0];
    lastTime[0] = t;
}
void IRAM_ATTR encoderISR2()
{
    unsigned long t = micros();
    period[1] = t - lastTime[1];
    lastTime[1] = t;
}
void IRAM_ATTR encoderISR3()
{
    unsigned long t = micros();
    period[2] = t - lastTime[2];
    lastTime[2] = t;
}
void IRAM_ATTR encoderISR4()
{
    unsigned long t = micros();
    period[3] = t - lastTime[3];
    lastTime[3] = t;
}

// Hitung RPM
float getRPM(int i)
{
    noInterrupts();
    unsigned long p = period[i];
    interrupts();
    if (p == 0) return 0;
    float freq = 1e6 / (float)p; // pulse/s
    float rpm = (freq * 60.0) / PULSES_PER_REV;
    return rpm;
}

// PID update
float updatePID(PID &pid, float setpoint, float meas)
{
    float err = setpoint - meas;
    pid.integral += err * CONTROL_DT;
    float deriv = (err - pid.lastErr) / CONTROL_DT;
    pid.lastErr = err;
    float u = pid.Kp * err + pid.Ki * pid.integral + pid.Kd * deriv;
    return u;
}

// Set motor speed (PWM)
void setMotor(int id, float pwmVal)
{
    int pinA, pinB, ledPin;
    switch (id)
    {
    case 0:
        pinA = M1_A;
        pinB = M1_B;
        ledPin = LED1;
        break;
    case 1:
        pinA = M2_A;
        pinB = M2_B;
        ledPin = LED2;
        break;
    case 2:
        pinA = M3_A;
        pinB = M3_B;
        ledPin = LED3;
        break;
    case 3:
        pinA = M4_A;
        pinB = M4_B;
        ledPin = LED4;
        break;
    }
    int pwm = constrain(abs(pwmVal), 0, 255);
    if (pwmVal > 0)
    {
        ledcWrite(pinA, pwm);
        ledcWrite(pinB, 0);
    }
    else if (pwmVal < 0)
    {
        ledcWrite(pinA, 0);
        ledcWrite(pinB, pwm);
    }
    else
    {
        ledcWrite(pinA, 0);
        ledcWrite(pinB, 0);
    }
    digitalWrite(ledPin, pwmVal != 0); // LED ON if active
}

// Setup
void setup()
{
    Serial.begin(115200);

    pinMode(M1_A, OUTPUT);
    pinMode(M1_B, OUTPUT);
    pinMode(M2_A, OUTPUT);
    pinMode(M2_B, OUTPUT);
    pinMode(M3_A, OUTPUT);
    pinMode(M3_B, OUTPUT);
    pinMode(M4_A, OUTPUT);
    pinMode(M4_B, OUTPUT);

    pinMode(LED1, OUTPUT);
    pinMode(LED2, OUTPUT);
    pinMode(LED3, OUTPUT);
    pinMode(LED4, OUTPUT);

    attachInterrupt(digitalPinToInterrupt(ENC1), encoderISR1, RISING);
    attachInterrupt(digitalPinToInterrupt(ENC2), encoderISR2, RISING);
    attachInterrupt(digitalPinToInterrupt(ENC3), encoderISR3, RISING);
    attachInterrupt(digitalPinToInterrupt(ENC4), encoderISR4, RISING);

    // Setup PWM channel ESP32 (0-15)
    ledcSetup(0, 1000, 8);
    ledcAttachPin(M1_A, 0);
    ledcSetup(1, 1000, 8);
    ledcAttachPin(M1_B, 1);
    ledcSetup(2, 1000, 8);
    ledcAttachPin(M2_A, 2);
    ledcSetup(3, 1000, 8);
    ledcAttachPin(M2_B, 3);
    ledcSetup(4, 1000, 8);
    ledcAttachPin(M3_A, 4);
    ledcSetup(5, 1000, 8);
    ledcAttachPin(M3_B, 5);
    ledcSetup(6, 1000, 8);
    ledcAttachPin(M4_A, 6);
    ledcSetup(7, 1000, 8);
    ledcAttachPin(M4_B, 7);
}

// Loop kontrol
void loop()
{
    static unsigned long last = 0;
    if (millis() - last >= CONTROL_DT * 1000)
    {
        last = millis();
        for (int i = 0; i < 4; i++)
        {
            float rpm = getRPM(i);
            float u = updatePID(pid[i], targetRPM[i], rpm);
            setMotor(i, u);
        }
        // debug
        Serial.printf("M1 %.1f | M2 %.1f | M3 %.1f | M4 %.1f\n", getRPM(0), getRPM(1), getRPM(2), getRPM(3));
    }
}
