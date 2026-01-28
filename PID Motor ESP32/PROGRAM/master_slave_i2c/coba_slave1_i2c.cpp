// set manual pwm / open loop untuk 4 motor
// baca encoder tiap 1 ms, rata2 rpm tiap 1 detik
// + NVS save/load PWM via Serial: "[1]200" dst

#include "driver/ledc.h" // sudah ada di core ESP32
#include <Arduino.h>
#include <Preferences.h> // <-- NVS ESP32
#include <Wire.h>

// ====== KONFIG ======
static constexpr uint32_t PWM_FREQ = 20000; // 20 kHz (silent)
static constexpr uint8_t PWM_RES = 8;       // 8-bit (0..255)

// ==== KONFIG AVERAGE ====
static constexpr uint32_t SPEED_REPORT_MS = 1000; // cetak tiap 1 s
static constexpr uint8_t SPEED_AVG_SEC = 3;       // rata 3 detik
static constexpr float PULSES_PER_REV = 2.0f;

#define LED_ON LOW
#define LED_OFF HIGH

// alamat I2C slave
#define I2C_SLAVE_ADDR 0x01 // ganti 0x0B / 0x15 untuk slave lain

// Data	Arti
// 2	MAJU (jalan awal / transit)
// 4	KANAN_BAWAH
// 8	KIRI_ATAS
// 0	STOP

// Value	Arti
// 0	proximity BELUM
// 1	proximity TERDETEKSI

#define PIN_PROX 23 // sesuaikan

volatile uint8_t lastCommand = 0;
volatile bool proxDetected = false;

void onReceive(int len)
{
    if (len < 1) return;
    lastCommand = Wire.read();

    switch (lastCommand)
    {
    case 2: MAJU(); break;
    case 4: KANAN_BAWAH(); break;
    case 8: KIRI_ATAS(); break;
    case 0: STOP_COAST(); break;
    default: STOP_COAST(); break;
    }
}

void onRequest()
{
    Wire.write(proxDetected ? 1 : 0);
}

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

Preferences prefs;

// pwm default tiap motor (bisa diubah via serial)
uint8_t p = 212;
uint8_t p2 = 255;
uint8_t p3 = 210;
uint8_t p4 = 208;

void loadPWMfromNVS()
{
    prefs.begin("pwm", true); // read-only
    p = prefs.getUChar("pwm1", p);
    p2 = prefs.getUChar("pwm2", p2);
    p3 = prefs.getUChar("pwm3", p3);
    p4 = prefs.getUChar("pwm4", p4);
    prefs.end();

    Serial.println("PWM loaded from NVS:");
    Serial.printf("M1=%d | M2=%d | M3=%d | M4=%d\n", p, p2, p3, p4);
}

enum MoveMode
{
    MODE_STOP,
    MODE_MAJU,
    MODE_MUNDUR,
    MODE_KANAN,
    MODE_KIRI,
    MODE_KANAN_ATAS,
    MODE_KANAN_BAWAH,
    MODE_KIRI_ATAS,
    MODE_KIRI_BAWAH
};

volatile MoveMode currentMode = MODE_STOP;

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
    currentMode = MODE_MAJU;
    apply(+p, +p2, +p3, +p4, true, false, false, false);
}

void MUNDUR()
{
    currentMode = MODE_MUNDUR;
    apply(-p, -p2, -p3, -p4, false, false, false, true);
}

void KANAN()
{
    currentMode = MODE_KANAN;
    apply(-p, +p2, -p3, +p4, false, true, false, false);
}

void KIRI()
{
    currentMode = MODE_KIRI;
    apply(+p, -p2, +p3, -p4, false, false, true, false);
}

void KANAN_ATAS()
{
    currentMode = MODE_KANAN_ATAS;
    apply(0, +p2, 0, +p4, true, true, false, false);
}
void KANAN_BAWAH()
{
    currentMode = MODE_KANAN_BAWAH;
    apply(-p, 0, -p3, 0, false, true, false, true);
}
void KIRI_ATAS()
{
    currentMode = MODE_KIRI_ATAS;
    apply(+p, 0, +p3, 0, true, false, true, false);
}
void KIRI_BAWAH()
{
    // uint8_t p = 200;
    currentMode = MODE_KIRI_BAWAH;
    apply(0, -p2, 0, -p4, false, false, true, true);
}

void STOP_COAST()
{
    currentMode = MODE_STOP;
    for (int i = 0; i < 4; i++) motorCoast(i);
    setLED(false, false, false, false);
}
void STOP_BRAKE()
{
    currentMode = MODE_STOP;
    for (int i = 0; i < 4; i++) motorBrake(i);
    setLED(false, false, false, false);
}

void reApplyMotion()
{
    switch (currentMode)
    {
    case MODE_MAJU: MAJU(); break;
    case MODE_MUNDUR: MUNDUR(); break;
    case MODE_KANAN: KANAN(); break;
    case MODE_KIRI: KIRI(); break;
    case MODE_KANAN_ATAS: KANAN_ATAS(); break;
    case MODE_KANAN_BAWAH: KANAN_BAWAH(); break;
    case MODE_KIRI_ATAS: KIRI_ATAS(); break;
    case MODE_KIRI_BAWAH: KIRI_BAWAH(); break;
    default: break; // STOP
    }
}

void savePWMtoNVS(uint8_t motor, uint8_t value)
{
    prefs.begin("pwm", false);
    switch (motor)
    {
    case 1:
        prefs.putUChar("pwm1", value);
        p = value;
        break;
    case 2:
        prefs.putUChar("pwm2", value);
        p2 = value;
        break;
    case 3:
        prefs.putUChar("pwm3", value);
        p3 = value;
        break;
    case 4:
        prefs.putUChar("pwm4", value);
        p4 = value;
        break;
    }
    prefs.end();

    Serial.println("berhasil disimpan");

    // 🔥 AUTO APPLY
    reApplyMotion();
}

void handlePWMCommand(String cmd)
{
    Serial.print("CMD MASUK: ");
    Serial.println(cmd);
    cmd.trim();

    if (cmd.length() < 4) return;
    if (cmd[0] != '[') return;

    int closeIdx = cmd.indexOf(']');
    if (closeIdx < 0) return;

    int motor = cmd.substring(1, closeIdx).toInt();
    int pwm = cmd.substring(closeIdx + 1).toInt();

    if (motor < 1 || motor > 4) return;
    if (pwm < 0 || pwm > 255) return;

    savePWMtoNVS(motor, pwm);
}

// void handlePWMCommand(String cmd)
// {
//     cmd.trim();

//     if (cmd.length() < 4) return;
//     if (cmd[0] != '[') return;

//     int closeIdx = cmd.indexOf(']');
//     if (closeIdx < 0) return;

//     int motor = cmd.substring(1, closeIdx).toInt();
//     int pwm = cmd.substring(closeIdx + 1).toInt();

//     if (motor < 1 || motor > 4) return;
//     if (pwm < 0 || pwm > 255) return;

//     savePWMtoNVS(motor, pwm);
// }

// ====== ENCODER COUNTERS (ISR) ======
volatile uint32_t encCount[4] = {0, 0, 0, 0};
// OPTIONAL: anti-bounce sederhana di ISR (unit: microseconds)
volatile uint32_t lastEdgeUs[4] = {0, 0, 0, 0};
static inline bool edge_ok(uint8_t i, uint32_t now)
{
    // ignore pulsa < 1000 us (1 ms) setelah edge terakhir -> filter noise
    uint32_t dt = now - lastEdgeUs[i];
    if (dt < 1000) return false;
    lastEdgeUs[i] = now;
    return true;
}

// ---- state untuk sliding window ----
uint32_t snap[4][SPEED_AVG_SEC + 1];
uint8_t ringIdx = 0;
uint32_t lastReportMs = 0;

void initSpeedAverager()
{
    // isi buffer awal dengan nilai sekarang supaya delta pertama = 0
    uint32_t nowCount[4];
    noInterrupts();
    for (int i = 0; i < 4; i++) nowCount[i] = encCount[i];
    interrupts();
    for (int s = 0; s <= SPEED_AVG_SEC; s++)
        for (int i = 0; i < 4; i++) snap[i][s] = nowCount[i];
    lastReportMs = millis();
}

void IRAM_ATTR isrEnc0()
{
    uint32_t t = micros();
    if (edge_ok(0, t)) encCount[0]++;
}
void IRAM_ATTR isrEnc1()
{
    uint32_t t = micros();
    if (edge_ok(1, t)) encCount[1]++;
}
void IRAM_ATTR isrEnc2()
{
    uint32_t t = micros();
    if (edge_ok(2, t)) encCount[2]++;
}
void IRAM_ATTR isrEnc3()
{
    uint32_t t = micros();
    if (edge_ok(3, t)) encCount[3]++;
}

// ====== SPEED COMPUTE STATE ======
uint32_t prevCount[4] = {0, 0, 0, 0};
uint32_t lastSpeedMs = 0;

// ====== SETUP ======
void setup()
{
    delay(50);
    // LEDC setup & attach

    // === I2C SLAVE ===
    Wire.begin(I2C_SLAVE_ADDR);
    Wire.onReceive(onReceive);
    Wire.onRequest(onRequest);

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
    // LED
    pinMode(L_MAJU, OUTPUT);
    pinMode(L_KANAN, OUTPUT);
    pinMode(L_MUNDUR, OUTPUT);
    pinMode(L_KIRI, OUTPUT);
    setLED(true, true, true, true);

    // === PROXIMITY ===
    pinMode(PIN_PROX, INPUT);

    // Encoder (ingat: 34..39 tak punya pull-up internal)
    pinMode(PIN_ENC1_M1, INPUT);
    pinMode(PIN_ENC2_M2, INPUT);
    pinMode(PIN_ENC3_M3, INPUT);
    pinMode(PIN_ENC4_M4, INPUT);

    // Attach interrupt (ubah RISING->FALLING jika logika sensormu kebalik)
    attachInterrupt(digitalPinToInterrupt(PIN_ENC1_M1), isrEnc0, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC2_M2), isrEnc1, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC3_M3), isrEnc2, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC4_M4), isrEnc3, RISING);

    initSpeedAverager();
    Serial.begin(9600); // sinkronkan dengan monitor serial
    delay(1000);
    setLED(false, false, false, false);
    loadPWMfromNVS();
}

void updateAndPrintRPM()
{
    uint32_t curMs = millis();
    if (curMs - lastReportMs < SPEED_REPORT_MS) return;
    lastReportMs += SPEED_REPORT_MS;

    // ambil counter terkini (atomik)
    uint32_t nowCount[4];
    noInterrupts();
    for (int i = 0; i < 4; i++) nowCount[i] = encCount[i];
    interrupts();

    // posisi data ter-tua yang akan di-overwrite
    int oldPos = ringIdx;

    // hitung delta selama N detik terakhir (sliding)
    float rpm[4];
    for (int i = 0; i < 4; i++)
    {
        uint32_t delta = nowCount[i] - snap[i][oldPos]; // N detik
        // RPM = (delta/PPR) * (60/N)
        rpm[i] = (delta / PULSES_PER_REV) * (60.0f / SPEED_AVG_SEC);
        snap[i][oldPos] = nowCount[i]; // tulis snapshot baru (geser jendela)
    }

    ringIdx = (ringIdx + 1) % (SPEED_AVG_SEC + 1);

    // cetak (bulatkan biar rapi)
    Serial.print("roda 1 : ");
    Serial.print((int)lroundf(rpm[0]));
    Serial.print(" | roda 2 : ");
    Serial.print((int)lroundf(rpm[1]));
    Serial.print(" | roda 3 : ");
    Serial.print((int)lroundf(rpm[2]));
    Serial.print(" | roda 4 : ");
    Serial.println((int)lroundf(rpm[3]));
}

String pwmBuffer = "";
bool pwmMode = false;
uint32_t lastPwmCharMs = 0;

void loop()
{
    proxDetected = digitalRead(PIN_PROX);

    while (Serial.available())
    {
        char c = Serial.read();
        uint32_t now = millis();

        // ===== PWM MODE =====
        if (pwmMode)
        {
            if (c == '\n' || c == '\r')
            {
                handlePWMCommand(pwmBuffer);
                pwmBuffer = "";
                pwmMode = false;
                continue;
            }

            pwmBuffer += c;
            lastPwmCharMs = now;
            continue;
        }

        // ===== START PWM CMD =====
        if (c == '[')
        {
            pwmBuffer = "[";
            pwmMode = true;
            lastPwmCharMs = now;
            continue;
        }

        // ===== FAST CMD =====
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
        case '9': STOP_BRAKE(); break;
        case '0': STOP_COAST(); break;
        }
    }

    // ===== AUTO FINISH PWM (timeout 30 ms) =====
    if (pwmMode && millis() - lastPwmCharMs > 30)
    {
        handlePWMCommand(pwmBuffer);
        pwmBuffer = "";
        pwmMode = false;
    }

    delay(2); // biar gak 100% CPU

    updateAndPrintRPM();
}
