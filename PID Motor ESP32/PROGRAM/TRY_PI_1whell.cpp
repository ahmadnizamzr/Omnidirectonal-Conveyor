// === 1 Motor Speed Control (Stabilized) ===
// ESP32 + MX1508 + Encoder 2 PPR (single channel)
// Perbaikan: soft-debounce di ISR, timeout diperpanjang, clamp RPM,
// Kp dinaikkan, Ki=0 untuk uji awal.

#include "driver/pcnt.h"
#include <Arduino.h>

// ------- Pin -------
constexpr int PIN_M1_A1 = 27;
constexpr int PIN_M1_A2 = 14;
constexpr int PIN_ENC1 = 35; // input-only ok

// ------- PWM (LEDC) -------
constexpr int PWM_FREQ = 20000; // 20 kHz
constexpr int PWM_RES = 10;     // 10-bit
constexpr int PWM_MAX = (1 << PWM_RES) - 1;
constexpr int LEDC_CH_M1_A1 = 0;
constexpr int LEDC_CH_M1_A2 = 1;

// ------- PCNT -------
constexpr pcnt_unit_t PCNT_UNIT = PCNT_UNIT_0;
constexpr int16_t PCNT_LIMIT = 10000;
constexpr uint16_t PCNT_GLITCH_NS = 12500; // ~12.5 us (maks filter HW)

// ------- Encoder / Estimator -------
constexpr int PPR = 2;       // pulses per rotation (rising)
constexpr float Ts = 0.010f; // 10 ms
constexpr uint32_t Ts_us = uint32_t(Ts * 1e6);

constexpr uint32_t MIN_PERIOD_US = 5000;          // <5 ms dianggap bounce → abaikan
constexpr uint32_t NO_PULSE_TIMEOUT_US = 3000000; // 3 s (biar low RPM tetap kebaca)
constexpr float ALPHA = 0.2f;                     // smoothing EMA
constexpr float MAX_RPM_PLAUS = 500.0f;           // clamp agar spike tak gila2an

// ------- PI Control (awal: P-only) -------
float Kp = 0.010f; // naikan/ turunkan saat uji
float Ki = 0.0f;   // 0 dulu supaya tak wind-up; nanti diaktifkan
float Kaw = 0.0f;  // tak terpakai kalau Ki=0

constexpr float DEAD_MIN = 0.15f;    // duty min utk lewati zona mati
constexpr float SLEW_PER_SEC = 3.0f; // batasi perubahan duty per detik

// ------- Vars -------
volatile uint32_t lastRise_us = 0;
volatile uint32_t period_us = 0;
volatile uint32_t lastPulseSeen_us = 0;

float rpm_meas = 0.0f, rpm_ref = 0.0f;
float integ = 0.0f, u_prev = 0.0f;

// ------- ISR: debounce lunak -------
void IRAM_ATTR enc_isr()
{
    uint32_t now = micros();
    uint32_t dt = now - lastRise_us;
    if (dt < MIN_PERIOD_US) return; // bounce, abaikan
    period_us = dt;
    lastRise_us = now;
    lastPulseSeen_us = now;
}

// ------- PCNT init -------
void pcnt_init_single(uint8_t pin)
{
    pcnt_config_t cfg = {};
    cfg.pulse_gpio_num = pin;
    cfg.ctrl_gpio_num = PCNT_PIN_NOT_USED;
    cfg.unit = PCNT_UNIT;
    cfg.channel = PCNT_CHANNEL_0;
    cfg.pos_mode = PCNT_COUNT_INC; // rising saja
    cfg.neg_mode = PCNT_COUNT_DIS;
    cfg.lctrl_mode = PCNT_MODE_KEEP;
    cfg.hctrl_mode = PCNT_MODE_KEEP;
    cfg.counter_h_lim = PCNT_LIMIT;
    cfg.counter_l_lim = -PCNT_LIMIT;
    pcnt_unit_config(&cfg);

    // HW glitch filter (maks ~12.7us @80MHz). Tetap aktif, walau kecil.
    uint16_t filter = (uint16_t)(PCNT_GLITCH_NS / 12.5);
    if (filter < 1) filter = 1;
    pcnt_set_filter_value(PCNT_UNIT, filter);
    pcnt_filter_enable(PCNT_UNIT);

    pcnt_counter_pause(PCNT_UNIT);
    pcnt_counter_clear(PCNT_UNIT);
    pcnt_counter_resume(PCNT_UNIT);

    pinMode(pin, INPUT);
    attachInterrupt(digitalPinToInterrupt(pin), enc_isr, RISING);
}

// ------- PWM init -------
void pwm_init()
{
    ledcSetup(LEDC_CH_M1_A1, PWM_FREQ, PWM_RES);
    ledcSetup(LEDC_CH_M1_A2, PWM_FREQ, PWM_RES);
    ledcAttachPin(PIN_M1_A1, LEDC_CH_M1_A1);
    ledcAttachPin(PIN_M1_A2, LEDC_CH_M1_A2);
    ledcWrite(LEDC_CH_M1_A1, 0);
    ledcWrite(LEDC_CH_M1_A2, 0);
}

// ------- Apply motor command u ∈ [-1..1] -------
void motorWrite(float u)
{
    u = constrain(u, -1.0f, 1.0f);

    // Slew-rate
    float maxStep = SLEW_PER_SEC * Ts;
    float du = u - u_prev;
    if (du > maxStep) u = u_prev + maxStep;
    if (du < -maxStep) u = u_prev - maxStep;
    u_prev = u;

    if (fabs(u) < 1e-3)
    {
        ledcWrite(LEDC_CH_M1_A1, 0);
        ledcWrite(LEDC_CH_M1_A2, 0);
        return;
    }

    float sgn = (u >= 0.0f) ? 1.0f : -1.0f;
    float duty = DEAD_MIN + (1.0f - DEAD_MIN) * fabs(u);
    uint32_t pwm = (uint32_t)(duty * PWM_MAX);

    if (sgn > 0)
    { // maju
        ledcWrite(LEDC_CH_M1_A1, pwm);
        ledcWrite(LEDC_CH_M1_A2, 0);
    }
    else
    { // mundur
        ledcWrite(LEDC_CH_M1_A1, 0);
        ledcWrite(LEDC_CH_M1_A2, pwm);
    }
}

// ------- Estimator RPM (hybrid) -------
float estimateRPM(uint32_t dt_us)
{
    int16_t cnt = 0;
    pcnt_get_counter_value(PCNT_UNIT, &cnt);
    pcnt_counter_clear(PCNT_UNIT);

    float rpm_from_count = 0.0f;
    if (cnt != 0)
    {
        float rev = float(cnt) / float(PPR);
        float dt_s = dt_us * 1e-6f;
        rpm_from_count = (rev / dt_s) * 60.0f;
    }

    float rpm_from_period = 0.0f;
    uint32_t age = micros() - lastPulseSeen_us;
    if (age < NO_PULSE_TIMEOUT_US && period_us >= MIN_PERIOD_US)
    {
        rpm_from_period = 60.0e6f / (float(period_us) * float(PPR));
    }

    float rpm_raw = 0.0f;
    if (cnt != 0)
        rpm_raw = rpm_from_count;
    else if (age < NO_PULSE_TIMEOUT_US)
        rpm_raw = rpm_from_period;
    else
        rpm_raw = 0.0f;

    // clamp & smoothing
    if (rpm_raw > MAX_RPM_PLAUS) rpm_raw = MAX_RPM_PLAUS;
    if (rpm_raw < -MAX_RPM_PLAUS) rpm_raw = -MAX_RPM_PLAUS;

    rpm_meas = (1.0f - ALPHA) * rpm_meas + ALPHA * rpm_raw;
    return rpm_meas;
}

// ------- P-only (Ki=0 untuk uji awal) -------
float speedPI(float rpm_ref, float rpm_meas)
{
    float e = rpm_ref - rpm_meas;
    float u_unsat = Kp * e + integ; // integ=0 saat Ki=0
    float u_sat = constrain(u_unsat, -1.0f, 1.0f);
    return u_sat;
}

// Tambahkan util brake & coast (MX1508: kedua input HIGH = brake, LOW = coast)
void motorCoast()
{
    ledcWrite(LEDC_CH_M1_A1, 0);
    ledcWrite(LEDC_CH_M1_A2, 0);
}
void motorBrake(float duty = 0.4f)
{ // duty 0..1, jangan terlalu besar
    uint32_t pwm = (uint32_t)(constrain(duty, 0.0f, 1.0f) * PWM_MAX);
    ledcWrite(LEDC_CH_M1_A1, pwm);
    ledcWrite(LEDC_CH_M1_A2, pwm);
}

// Deadband untuk “anggap berhenti”
constexpr float RPM_EPS = 8.0f;

// Ganti fungsi kontrol agar tak pernah memberi torsi berlawanan saat ref ≈ 0
float speedPI_signed(float ref_rpm, float meas_abs_rpm)
{
    if (fabs(ref_rpm) < RPM_EPS) return 0.0f;     // no torque; stop handled di loop
    float sgn = (ref_rpm >= 0.0f) ? 1.0f : -1.0f; // arah dari perintah
    float meas_signed = meas_abs_rpm * sgn;       // asumsikan arah sama dg ref
    float e = fabs(ref_rpm) - meas_signed;        // error pada magnitudo
    float u_mag = Kp * e + integ * (Ki > 0 ? 1.0f : 0.0f);
    u_mag = constrain(u_mag, 0.0f, 1.0f); // JANGAN beri torsi berlawanan
    return sgn * u_mag;
}

// GANTI fungsi kontrol jadi ini
float speedPI_mag(float ref_rpm, float meas_abs_rpm)
{
    float sgn = (ref_rpm >= 0.0f) ? 1.0f : -1.0f; // arah ikut ref
    float ref_mag = fabs(ref_rpm);
    float e_mag = ref_mag - meas_abs_rpm; // <-- perbaikan inti

    // (opsional) integral pada magnitudo
    if (Ki > 0.0f)
    {
        float Ki_d = Ki * Ts;
        integ += Ki_d * e_mag;
        integ = constrain(integ, -0.5f, 0.5f); // clamp biar ga liar
    }

    float u_mag = Kp * e_mag + integ;
    u_mag = constrain(u_mag, 0.0f, 1.0f); // jangan beri torsi berlawanan
    return sgn * u_mag;
}

void setup()
{
    Serial.begin(115200);
    delay(50);
    Serial.println("\n=== 1 Motor Control (debounced) ===");
    Serial.println("Keys: w=+20RPM, s=-20RPM, 0=stop");
    pwm_init();
    pcnt_init_single(PIN_ENC1);
}

void loop()
{
    static uint32_t t0 = micros();
    static uint32_t tPrint = millis();

    uint32_t now = micros();
    if ((now - t0) >= Ts_us)
    {
        uint32_t dt = now - t0;
        t0 = now;

        float rpm = estimateRPM(dt);

        if (fabs(rpm_ref) < RPM_EPS)
        {                 // MODE BERHENTI
            integ = 0.0f; // matikan I saat stop
            if (rpm > 12.0f)
                motorBrake(0.4f); // short-brake sebentar
            else
                motorCoast(); // lalu lepas
            u_prev = 0.0f;    // reset slew
        }
        else
        { // MODE KECEPATAN
            float u = speedPI_mag(rpm_ref, rpm_meas);
            motorWrite(u);
        }
    }

    if (Serial.available())
    {
        char c = Serial.read();
        if (c == 'w') rpm_ref += 20.0f;
        if (c == 's') rpm_ref -= 20.0f;
        if (c == '0') rpm_ref = 0.0f;
        rpm_ref = constrain(rpm_ref, 400.0f, 400.0f);
    }

    if (millis() - tPrint >= 100)
    {
        tPrint += 100;
        Serial.printf("ref=%6.1f rpm | meas=%6.1f rpm | u=%5.2f\n",
                      rpm_ref, rpm_meas, u_prev);
    }
}