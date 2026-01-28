#include "driver/ledc.h" // sudah ada di core ESP32
#include <Arduino.h>

// ====== KONFIG PWM ======
static constexpr uint32_t PWM_FREQ = 20000; // 20 kHz (silent)
static constexpr uint8_t PWM_RES = 8;       // 8-bit (0..255)
#define LED_ON LOW
#define LED_OFF HIGH

// ====== ENCODER / KECEPATAN ======
static constexpr float PULSES_PER_REV = 2.0f;      // encoder 2 PPR
static constexpr uint32_t RPM_TIMEOUT_US = 500000; // 0.5 s tanpa pulsa -> dianggap 0 RPM
static constexpr float RPM_EMA_ALPHA = 0.30f;      // smoothing RPM (0..1)

// ====== LOOP KONTROL ======
static constexpr uint16_t CTRL_PERIOD_MS = 20; // 50 Hz kontrol
static constexpr float DT = CTRL_PERIOD_MS / 1000.0f;

// PI + Feedforward (satuan: pwm / rpm)
static constexpr float KFF = 1.20f; // feedforward: kira2 1.2 PWM per 1 RPM (sesuaikan)
static constexpr float KP = 0.60f;  // proporsional
static constexpr float KI = 0.15f;  // integral (per detik)

// Batas aktuator
static constexpr int16_t PWM_MAX = 255;
static constexpr int16_t PWM_MIN_RUN = 40;  // untuk atasi static friction
static constexpr uint8_t SLEW_PER_TICK = 8; // batas perubahan PWM per 20 ms

// ====== KONFIG CETAK RPM (opsional, untuk monitor saja) ======
static constexpr uint32_t SPEED_REPORT_MS = 1000; // cetak tiap 1 s

// (MX1508 = pin esp32)
// Motor pins (A1/A2, A3/A4, ...)
const uint8_t PIN_M1_A1 = 27;
const uint8_t PIN_M1_A2 = 14;
const uint8_t PIN_M2_A3 = 12;
const uint8_t PIN_M2_A4 = 13;
const uint8_t PIN_M3_A1 = 26;
const uint8_t PIN_M3_A2 = 25;
const uint8_t PIN_M4_A3 = 33;
const uint8_t PIN_M4_A4 = 32;

// Encoder pins (INPUT-ONLY, no internal pullup!)
const uint8_t PIN_ENC1_M1 = 35;
const uint8_t PIN_ENC2_M2 = 34;
const uint8_t PIN_ENC3_M3 = 39;
const uint8_t PIN_ENC4_M4 = 36;

// LEDs (aktif-LOW)
const uint8_t L_MAJU = 19;
const uint8_t L_KANAN = 18;
const uint8_t L_MUNDUR = 5; // bootstrap pin—pastikan stabil saat boot
const uint8_t L_KIRI = 15;  // bootstrap pin—pastikan stabil saat boot

// ====== LEDC CHANNEL ASSIGN ======
// Kita pakai 8 channel: 2 per motor (FWD/REV)
enum
{
    CH_M1_FWD = 0,
    CH_M1_REV,
    CH_M2_FWD,
    CH_M2_REV,
    CH_M3_FWD,
    CH_M3_REV,
    CH_M4_FWD,
    CH_M4_REV
};

struct MotorHW
{
    uint8_t pinFwd; // pin "maju"
    uint8_t pinRev; // pin "mundur"
    uint8_t chFwd;  // LEDC channel forward
    uint8_t chRev;  // LEDC channel reverse
};

// Susun agar "maju" konsisten seperti sketsa awal
MotorHW M[4] = {
    {PIN_M1_A2, PIN_M1_A1, CH_M1_FWD, CH_M1_REV}, // M1: FWD=A2
    {PIN_M2_A3, PIN_M2_A4, CH_M2_FWD, CH_M2_REV}, // M2: FWD=A3
    {PIN_M3_A2, PIN_M3_A1, CH_M3_FWD, CH_M3_REV}, // M3: FWD=A2
    {PIN_M4_A3, PIN_M4_A4, CH_M4_FWD, CH_M4_REV}  // M4: FWD=A3
};

// Kalibrasi polaritas tambahan jika perlu (+1 atau -1 per motor)
int8_t POL[4] = {+1, +1, +1, +1};

// ====== STATE ENCODER (ISR) ======
volatile uint32_t encCount[4] = {0, 0, 0, 0};        // tetap kita jaga utk debug / akumulasi
volatile uint32_t lastEdgeUs[4] = {0, 0, 0, 0};      // timestamp edge terakhir
volatile uint32_t lastPeriodUsRaw[4] = {0, 0, 0, 0}; // periode antar edge terakhir (raw)

// anti-bounce sederhana di ISR (unit: microseconds)
static inline bool edge_ok(uint8_t i, uint32_t now)
{
    uint32_t dt = now - lastEdgeUs[i];
    if (dt < 1000) return false; // 1 ms minimum (filter noise)
    lastEdgeUs[i] = now;
    return true;
}

void IRAM_ATTR isrEnc0()
{
    uint32_t t = micros();
    if (edge_ok(0, t))
    {
        encCount[0]++;
        lastPeriodUsRaw[0] = t - lastPeriodUsRaw[0] ? t - (t - lastPeriodUsRaw[0]) : 0;
    }
}
void IRAM_ATTR isrEnc1()
{
    uint32_t t = micros();
    if (edge_ok(1, t))
    {
        encCount[1]++;
        lastPeriodUsRaw[1] = t - lastPeriodUsRaw[1] ? t - (t - lastPeriodUsRaw[1]) : 0;
    }
}
void IRAM_ATTR isrEnc2()
{
    uint32_t t = micros();
    if (edge_ok(2, t))
    {
        encCount[2]++;
        lastPeriodUsRaw[2] = t - lastPeriodUsRaw[2] ? t - (t - lastPeriodUsRaw[2]) : 0;
    }
}
void IRAM_ATTR isrEnc3()
{
    uint32_t t = micros();
    if (edge_ok(3, t))
    {
        encCount[3]++;
        lastPeriodUsRaw[3] = t - lastPeriodUsRaw[3] ? t - (t - lastPeriodUsRaw[3]) : 0;
    }
}

// Catatan: baris di atas sekadar menyimpan "periode terakhir" via lastPeriodUsRaw[*].
// Kita akan salin & olah aman di task kontrol (bukan di ISR).

// ====== STATE ESTIMASI & KONTROL ======
float rpmEMA[4] = {0, 0, 0, 0};    // RPM tersaring (EMA)
float targetRPM[4] = {0, 0, 0, 0}; // setpoint per roda (bisa negatif)
float integ[4] = {0, 0, 0, 0};     // integral PI
int16_t uPWM[4] = {0, 0, 0, 0};    // output PWM signed (-255..+255)

inline uint8_t clamp255(int v) { return (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v)); }

void motorWrite(uint8_t idx, int speed)
{
    speed *= POL[idx];
    const uint8_t fwdDuty = speed > 0 ? clamp255(speed) : 0;
    const uint8_t revDuty = speed < 0 ? clamp255(-speed) : 0;
    ledcWrite(M[idx].chFwd, fwdDuty);
    ledcWrite(M[idx].chRev, revDuty);
}

void motorCoast(uint8_t idx)
{
    ledcWrite(M[idx].chFwd, 0);
    ledcWrite(M[idx].chRev, 0);
}
void motorBrake(uint8_t idx)
{
    ledcWrite(M[idx].chFwd, 255);
    ledcWrite(M[idx].chRev, 255);
}

void setLED(bool maju, bool kanan, bool kiri, bool mundur)
{
    digitalWrite(L_MAJU, maju ? LED_ON : LED_OFF);
    digitalWrite(L_KANAN, kanan ? LED_ON : LED_OFF);
    digitalWrite(L_KIRI, kiri ? LED_ON : LED_OFF);
    digitalWrite(L_MUNDUR, mundur ? LED_ON : LED_OFF);
}

void STOP_COAST()
{
    for (int i = 0; i < 4; i++)
    {
        motorCoast(i);
        targetRPM[i] = 0;
        integ[i] = 0;
        uPWM[i] = 0;
    }
    setLED(false, false, false, false);
}
void STOP_BRAKE()
{
    for (int i = 0; i < 4; i++)
    {
        motorBrake(i);
        targetRPM[i] = 0;
        integ[i] = 0;
        uPWM[i] = 0;
    }
    setLED(false, false, false, false);
}

// ====== ESTIMASI RPM (pakai periode antar pulsa + EMA) ======
void estimateRPMs()
{
    // salin atomik data ISR
    uint32_t lastEdge[4], periodRaw[4];
    noInterrupts();
    for (int i = 0; i < 4; i++)
    {
        lastEdge[i] = lastEdgeUs[i];
        periodRaw[i] = lastPeriodUsRaw[i];
    }
    interrupts();

    uint32_t now = micros();
    for (int i = 0; i < 4; i++)
    {
        float rpmInst = 0.0f;
        // kalau ada periode valid dan pulsa belum timeout
        if (periodRaw[i] > 0 && (now - lastEdge[i]) < RPM_TIMEOUT_US)
        {
            // RPM = 60e6 / (PPR * period_us)
            rpmInst = 60000000.0f / (PULSES_PER_REV * (float)periodRaw[i]);
        }
        else
        {
            rpmInst = 0.0f;
        }
        // EMA
        rpmEMA[i] = RPM_EMA_ALPHA * rpmInst + (1.0f - RPM_EMA_ALPHA) * rpmEMA[i];
    }
}

// ====== KONTROL KECEPATAN (PI + feedforward + slew limit + deadzone) ======
void speedControllerTick()
{
    static uint32_t lastMs = 0;
    uint32_t now = millis();
    if (now - lastMs < CTRL_PERIOD_MS) return;
    lastMs = now;

    estimateRPMs();

    for (int i = 0; i < 4; i++)
    {
        // definisikan arah: rpm terukur dianggap mengikuti tanda setpoint
        float sp = targetRPM[i];
        float meas = (sp >= 0 ? +rpmEMA[i] : -rpmEMA[i]);
        float err = sp - meas;

        // PI + Feedforward
        float ff = KFF * sp;
        integ[i] += (KI * err) * DT;

        // anti-windup sederhana: clamp integrator agar output tak terus "lari"
        if (integ[i] > 200) integ[i] = 200;
        if (integ[i] < -200) integ[i] = -200;

        float u = ff + KP * err + integ[i];

        // deadzone untuk atasi static friction
        if (sp == 0.0f)
        {
            u = 0.0f;
            integ[i] = 0.0f;
        }
        else
        {
            if (fabsf(u) < PWM_MIN_RUN) u = copysignf(PWM_MIN_RUN, u);
        }

        // clamp & slew limit
        if (u > PWM_MAX) u = PWM_MAX;
        if (u < -PWM_MAX) u = -PWM_MAX;

        int16_t targetPWM = (int16_t)lroundf(u);
        int16_t du = targetPWM - uPWM[i];
        if (du > SLEW_PER_TICK) du = SLEW_PER_TICK;
        if (du < -SLEW_PER_TICK) du = -SLEW_PER_TICK;
        uPWM[i] += du;

        motorWrite(i, uPWM[i]);
    }
}

// ====== GERAK (setpoint RPM, kontrol yang eksekusi PWM) ======
void setTargetsRPM(float m1, float m2, float m3, float m4,
                   bool ledMaju, bool ledKanan, bool ledKiri, bool ledMundur)
{
    targetRPM[0] = m1;
    targetRPM[1] = m2;
    targetRPM[2] = m3;
    targetRPM[3] = m4;
    setLED(ledMaju, ledKanan, ledKiri, ledMundur);
}

// Pilih angka setpoint yang mirip karakter PWM lamamu (silakan ubah sesuai realita)
static constexpr float RPM_SLOW = 110.0f;
static constexpr float RPM_MID = 140.0f;
static constexpr float RPM_FAST = 160.0f;

void MAJU() { setTargetsRPM(+RPM_MID, +RPM_MID + 10, +RPM_MID + 10, +RPM_MID, true, false, false, false); }
void MUNDUR() { setTargetsRPM(-RPM_MID, -RPM_MID, -RPM_MID, -RPM_MID, false, false, false, true); }
void KANAN() { setTargetsRPM(-RPM_FAST, +RPM_FAST, -RPM_FAST, +RPM_FAST, false, true, false, false); }
void KIRI() { setTargetsRPM(+RPM_MID, -RPM_MID, +RPM_MID, -RPM_MID, false, false, true, false); }
void KANAN_ATAS() { setTargetsRPM(0, +RPM_MID, 0, +RPM_MID, true, true, false, false); }
void KANAN_BAWAH() { setTargetsRPM(-RPM_FAST, 0, -RPM_FAST, 0, false, true, false, true); }
void KIRI_ATAS() { setTargetsRPM(+RPM_MID, 0, +RPM_MID, 0, true, false, true, false); }
void KIRI_BAWAH() { setTargetsRPM(0, -RPM_MID, 0, -RPM_MID, false, false, true, true); }

// ====== CETAK RPM ke Serial (tiap 1 s) ======
void updateAndPrintRPM()
{
    static uint32_t lastPrint = 0;
    uint32_t now = millis();
    if (now - lastPrint < SPEED_REPORT_MS) return;
    lastPrint = now;

    // pakai rpmEMA agar enak dibaca
    Serial.print("roda 1 : ");
    Serial.print((int)lroundf(fabsf(rpmEMA[0])));
    Serial.print(" | roda 2 : ");
    Serial.print((int)lroundf(fabsf(rpmEMA[1])));
    Serial.print(" | roda 3 : ");
    Serial.print((int)lroundf(fabsf(rpmEMA[2])));
    Serial.print(" | roda 4 : ");
    Serial.println((int)lroundf(fabsf(rpmEMA[3])));
}

// ====== SETUP ======
void setup()
{
    delay(50);

    // LED
    pinMode(L_MAJU, OUTPUT);
    pinMode(L_KANAN, OUTPUT);
    pinMode(L_MUNDUR, OUTPUT);
    pinMode(L_KIRI, OUTPUT);
    setLED(true, true, true, true);

    // Encoder (ingat: 34..39 tak punya pull-up internal)
    pinMode(PIN_ENC1_M1, INPUT);
    pinMode(PIN_ENC2_M2, INPUT);
    pinMode(PIN_ENC3_M3, INPUT);
    pinMode(PIN_ENC4_M4, INPUT);

    attachInterrupt(digitalPinToInterrupt(PIN_ENC1_M1), isrEnc0, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC2_M2), isrEnc1, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC3_M3), isrEnc2, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC4_M4), isrEnc3, RISING);

    // LEDC setup & attach
    for (int ch = 0; ch < 8; ch++) ledcSetup(ch, PWM_FREQ, PWM_RES);
    ledcAttachPin(M[0].pinFwd, M[0].chFwd);
    ledcAttachPin(M[0].pinRev, M[0].chRev);
    ledcAttachPin(M[1].pinFwd, M[1].chFwd);
    ledcAttachPin(M[1].pinRev, M[1].chRev);
    ledcAttachPin(M[2].pinFwd, M[2].chFwd);
    ledcAttachPin(M[2].pinRev, M[2].chRev);
    ledcAttachPin(M[3].pinFwd, M[3].chFwd);
    ledcAttachPin(M[3].pinRev, M[3].chRev);

    STOP_COAST(); // keadaan aman saat boot
    Serial.begin(115200);
    delay(500);
    setLED(false, false, false, false);
}

// ====== LOOP ======
void loop()
{
    // kontrol gerak via Serial
    if (Serial.available())
    {
        char c = Serial.read();
        switch (c)
        {
        case '1': MAJU(); break;
        case '2': KANAN_ATAS(); break;
        case '3': KANAN(); break;
        case '4': KANAN_BAWAH(); break;
        case '5': MUNDUR(); break;
        case '6': KIRI_BAWAH(); break;
        case '7': KIRI(); break;
        case '8': KIRI_ATAS(); break;
        case '0': STOP_COAST(); break; // ganti ke STOP_BRAKE() jika mau rem cepat
        case 's': STOP_BRAKE(); break; // ganti ke STOP_BRAKE() jika mau rem cepat
        }
    }

    // jalankan kontrol kecepatan
    speedControllerTick();

    // debug RPM (opsional)
    updateAndPrintRPM();
}
