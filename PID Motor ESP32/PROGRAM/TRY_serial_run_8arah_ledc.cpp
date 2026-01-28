
#include <Arduino.h>

// ====== KONFIG ======
static constexpr uint32_t PWM_FREQ = 20000; // 20 kHz (silent)
static constexpr uint8_t PWM_RES = 8;       // 8-bit (0..255)
#define LED_ON LOW
#define LED_OFF HIGH

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
    uint8_t pinFwd; // pin yang dianggap "maju" untuk motor tsb
    uint8_t pinRev; // pin "mundur"
    uint8_t chFwd;  // LEDC channel forward
    uint8_t chRev;  // LEDC channel reverse
};

// Susun agar "maju" sesuai kebiasaan kodenya:
// MAJU (versi lama): M1 pakai A2, M2 pakai A3, M3 pakai A2, M4 pakai A3
MotorHW M[4] = {
    {PIN_M1_A2, PIN_M1_A1, CH_M1_FWD, CH_M1_REV}, // M1: FWD=A2
    {PIN_M2_A3, PIN_M2_A4, CH_M2_FWD, CH_M2_REV}, // M2: FWD=A3
    {PIN_M3_A2, PIN_M3_A1, CH_M3_FWD, CH_M3_REV}, // M3: FWD=A2
    {PIN_M4_A3, PIN_M4_A4, CH_M4_FWD, CH_M4_REV}  // M4: FWD=A3
};

// Kalibrasi polaritas tambahan jika perlu (+1 atau -1 per motor)
int8_t POL[4] = {+1, +1, +1, +1};

// ====== HELPER ======
inline uint8_t clamp255(int v) { return (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v)); }

// speed: -255..+255
void motorWrite(uint8_t idx, int speed)
{
    speed *= POL[idx];
    const uint8_t fwdDuty = speed > 0 ? clamp255(speed) : 0;
    const uint8_t revDuty = speed < 0 ? clamp255(-speed) : 0;
    ledcWrite(M[idx].chFwd, fwdDuty);
    ledcWrite(M[idx].chRev, revDuty);
}

// Berhenti “coast” (free run)
void motorCoast(uint8_t idx)
{
    ledcWrite(M[idx].chFwd, 0);
    ledcWrite(M[idx].chRev, 0);
}

// Berhenti “brake” (cepat)
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

// Terapkan ke-4 motor sekaligus
void apply(int m1, int m2, int m3, int m4, bool ledMaju, bool ledKanan, bool ledKiri, bool ledMundur)
{
    motorWrite(0, m1);
    motorWrite(1, m2);
    motorWrite(2, m3);
    motorWrite(3, m4);
    setLED(ledMaju, ledKanan, ledKiri, ledMundur);
}

// ====== MOVES (sesuai gaya kodenya) ======
void MAJU()
{
    uint8_t p = 200;
    apply(+p, +p, +p, +p, true, false, false, false);
}
void MUNDUR()
{
    uint8_t p = 200;
    apply(-p, -p, -p, -p, false, false, false, true);
}
void KANAN()
{
    int p1 = 200, p2 = 200, p3 = 230, p4 = 150;
    apply(-p1, +p2, -p3, +p4, false, true, false, false);
}
void KIRI()
{
    uint8_t p = 200;
    apply(+p, -p, +p, -p, false, false, true, false);
}
void KANAN_ATAS()
{
    int p2 = 200, p4 = 200;
    apply(0, +p2, 0, +p4, true, true, false, false);
}
void KANAN_BAWAH()
{
    int p1 = 240, p3 = 230;
    apply(-p1, 0, -p3, 0, false, true, false, true);
}
void KIRI_ATAS()
{
    uint8_t p = 200;
    apply(+p, 0, +p, 0, true, false, true, false);
}
void KIRI_BAWAH()
{
    uint8_t p = 200;
    apply(0, -p, 0, -p, false, false, true, true);
}

void STOP_COAST()
{
    for (int i = 0; i < 4; i++) motorCoast(i);
    setLED(false, false, false, false);
}
void STOP_BRAKE()
{
    for (int i = 0; i < 4; i++) motorBrake(i);
    setLED(false, false, false, false);
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
    setLED(false, false, false, false);

    // Encoder (ingat: 34..39 tak punya pull-up internal)
    pinMode(PIN_ENC1_M1, INPUT);
    pinMode(PIN_ENC2_M2, INPUT);
    pinMode(PIN_ENC3_M3, INPUT);
    pinMode(PIN_ENC4_M4, INPUT);

    // LEDC setup & attach
    for (int ch = 0; ch < 8; ch++)
    {
        ledcSetup(ch, PWM_FREQ, PWM_RES);
    }
    ledcAttachPin(M[0].pinFwd, M[0].chFwd);
    ledcAttachPin(M[0].pinRev, M[0].chRev);
    ledcAttachPin(M[1].pinFwd, M[1].chFwd);
    ledcAttachPin(M[1].pinRev, M[1].chRev);
    ledcAttachPin(M[2].pinFwd, M[2].chFwd);
    ledcAttachPin(M[2].pinRev, M[2].chRev);
    ledcAttachPin(M[3].pinFwd, M[3].chFwd);
    ledcAttachPin(M[3].pinRev, M[3].chRev);

    STOP_COAST(); // keadaan aman saat boot

    Serial.begin(115200); // sinkronkan dengan monitor serial
}

// ====== LOOP ======
void loop()
{
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
        }
    }
}
