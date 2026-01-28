#include "driver/mcpwm.h"
#include <Arduino.h>

// =====================
// Konfigurasi PWM
// =====================
static const uint32_t PWM_FREQ_HZ = 20000; // 20 kHz (umumnya lebih senyap)
static const float DEADZONE = 0.0f;        // set mis. 5.0f kalau motor susah mulai

// =====================
// Mapping motor -> MCPWM channel + GPIO
// Tiap motor pakai 1 timer, output A/B jadi IN1/IN2
// =====================
typedef struct
{
    mcpwm_unit_t unit;
    mcpwm_timer_t timer;
    int gpio_in1; // ke INx1
    int gpio_in2; // ke INx2
} MotorHw;

MotorHw motors[4] = {
    // Motor 1: Unit0 Timer0 => PWM0A/PWM0B
    {MCPWM_UNIT_0, MCPWM_TIMER_0, 25, 26},

    // Motor 2: Unit0 Timer1 => PWM1A/PWM1B
    {MCPWM_UNIT_0, MCPWM_TIMER_1, 27, 14},

    // Motor 3: Unit1 Timer0 => PWM0A/PWM0B (tapi unit berbeda)
    {MCPWM_UNIT_1, MCPWM_TIMER_0, 32, 33},

    // Motor 4: Unit1 Timer1 => PWM1A/PWM1B
    {MCPWM_UNIT_1, MCPWM_TIMER_1, 18, 19},
};

// Helper: set duty untuk A/B pada (unit,timer) dalam persen 0..100
static inline void setDutyAB(mcpwm_unit_t unit, mcpwm_timer_t timer, float dutyA, float dutyB)
{
    dutyA = constrain(dutyA, 0.0f, 100.0f);
    dutyB = constrain(dutyB, 0.0f, 100.0f);

    mcpwm_set_duty(unit, timer, MCPWM_GEN_A, dutyA);
    mcpwm_set_duty_type(unit, timer, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);

    mcpwm_set_duty(unit, timer, MCPWM_GEN_B, dutyB);
    mcpwm_set_duty_type(unit, timer, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
}

// speed: -100..100
// + = maju (IN1 PWM, IN2 LOW)
// - = mundur (IN1 LOW, IN2 PWM)
// 0 = coast/standby (IN1 LOW, IN2 LOW)
// brake: IN1 HIGH, IN2 HIGH (duty 100/100)
void motorSetSpeed(uint8_t idx, float speedPercent)
{
    if (idx >= 4) return;

    speedPercent = constrain(speedPercent, -100.0f, 100.0f);

    float absSpd = fabs(speedPercent);
    if (absSpd < DEADZONE) absSpd = 0.0f;

    auto &m = motors[idx];

    if (speedPercent > 0.0f)
    {
        // Forward: IN1=PWM, IN2=0
        setDutyAB(m.unit, m.timer, absSpd, 0.0f);
    }
    else if (speedPercent < 0.0f)
    {
        // Reverse: IN1=0, IN2=PWM
        setDutyAB(m.unit, m.timer, 0.0f, absSpd);
    }
    else
    {
        // Standby/Coast: IN1=0, IN2=0
        setDutyAB(m.unit, m.timer, 0.0f, 0.0f);
    }
}

void motorBrake(uint8_t idx)
{
    if (idx >= 4) return;
    auto &m = motors[idx];
    // Brake: IN1=1, IN2=1  -> duty 100% pada kedua input
    setDutyAB(m.unit, m.timer, 100.0f, 100.0f);
}

void motorCoastAll()
{
    for (int i = 0; i < 4; i++) motorSetSpeed(i, 0);
}

void initMotor(const MotorHw &m)
{
    // Tentukan pasangan output A/B untuk timer yang dipakai:
    // Timer0 => MCPWM0A/MCPWM0B
    // Timer1 => MCPWM1A/MCPWM1B
    // Timer2 => MCPWM2A/MCPWM2B
    mcpwm_io_signals_t sigA, sigB;
    switch (m.timer)
    {
    case MCPWM_TIMER_0:
        sigA = MCPWM0A;
        sigB = MCPWM0B;
        break;
    case MCPWM_TIMER_1:
        sigA = MCPWM1A;
        sigB = MCPWM1B;
        break;
    default:
        sigA = MCPWM2A;
        sigB = MCPWM2B;
        break;
    }

    // Route MCPWM ke GPIO
    mcpwm_gpio_init(m.unit, sigA, m.gpio_in1);
    mcpwm_gpio_init(m.unit, sigB, m.gpio_in2);

    // Init timer config
    mcpwm_config_t cfg = {};
    cfg.frequency = PWM_FREQ_HZ;
    cfg.cmpr_a = 0.0;                    // duty A awal
    cfg.cmpr_b = 0.0;                    // duty B awal
    cfg.counter_mode = MCPWM_UP_COUNTER; // sederhana & stabil
    cfg.duty_mode = MCPWM_DUTY_MODE_0;

    mcpwm_init(m.unit, m.timer, &cfg);

    // Pastikan berhenti (standby) saat start
    setDutyAB(m.unit, m.timer, 0.0f, 0.0f);
}

void setup()
{
    Serial.begin(115200);
    delay(200);

    // Inisialisasi semua motor
    for (int i = 0; i < 4; i++) initMotor(motors[i]);

    Serial.println("MCPWM 4-motor MX1508 ready.");
}

void loop()
{
    // Demo: semua maju pelan->cepat->stop->brake->mundur
    for (float s = 20; s <= 80; s += 10)
    {
        for (int i = 0; i < 4; i++) motorSetSpeed(i, s);
        delay(600);
    }

    motorCoastAll();
    delay(500);

    for (int i = 0; i < 4; i++) motorBrake(i);
    delay(400);

    motorCoastAll();
    delay(400);

    for (float s = 30; s <= 70; s += 10)
    {
        for (int i = 0; i < 4; i++) motorSetSpeed(i, -s);
        delay(600);
    }

    motorCoastAll();
    delay(1000);
}
