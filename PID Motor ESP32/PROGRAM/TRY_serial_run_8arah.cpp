
#include <Arduino.h>

// 2      |       1
//   panah ke atas
// 3      |       4

// (MX1508 = pin esp32)
// pin motor 1
int PIN_M1_A1 = 27;
int PIN_M1_A2 = 14;
// pin motor 2
int PIN_M2_A3 = 12;
int PIN_M2_A4 = 13;
// pin motor 3
int PIN_M3_A1 = 26;
int PIN_M3_A2 = 25;
// pin motor 4
int PIN_M4_A3 = 33;
int PIN_M4_A4 = 32;

// PIN ENCODER
// encoder motor 1
int PIN_ENC1_M1 = 35;
// encoder motor 2
int PIN_ENC2_M2 = 34;
// encoder motor 3
int PIN_ENC3_M3 = 39;
//  encoder motor 4
int PIN_ENC4_M4 = 36;

// pin proximity depan
int PIN_PROXIMITY = 23;
#define PROX_ACTIVE LOW

// PIN LED
// maju
int L_MAJU = 19;
// kanan
int L_KANAN = 18;
// mundur
int L_MUNDUR = 5;
// kiri
int L_KIRI = 15;

enum GERAK
{
    DIAM,
    MAJU_GERAK,
    LAINNYA
};

GERAK statusGerak = DIAM;

void setup()
{
    delay(50);
    pinMode(PIN_M1_A1, OUTPUT); // motor
    pinMode(PIN_M1_A2, OUTPUT);
    pinMode(PIN_M2_A3, OUTPUT);
    pinMode(PIN_M2_A4, OUTPUT);
    pinMode(PIN_M3_A1, OUTPUT);
    pinMode(PIN_M3_A2, OUTPUT);
    pinMode(PIN_M4_A3, OUTPUT);
    pinMode(PIN_M4_A4, OUTPUT);
    // delay(100);
    pinMode(L_MAJU, OUTPUT); // LED
    pinMode(L_KANAN, OUTPUT);
    pinMode(L_MUNDUR, OUTPUT);
    pinMode(L_KIRI, OUTPUT);
    digitalWrite(L_MAJU, 0); // nyala led
    digitalWrite(L_KANAN, 0);
    digitalWrite(L_MUNDUR, 0);
    digitalWrite(L_KIRI, 0);
    pinMode(PIN_ENC1_M1, INPUT); // encoder
    pinMode(PIN_ENC2_M2, INPUT);
    pinMode(PIN_ENC3_M3, INPUT);
    pinMode(PIN_ENC4_M4, INPUT);
    Serial.begin(9600); // BUKA KOMUNIKASI SERIABAUD RATE 115200
    delay(800);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_MUNDUR, 1);
    digitalWrite(L_KIRI, 1);
}

void MAJU()
{
    statusGerak = MAJU_GERAK;

    uint8_t PWM1 = 150;
    uint8_t PWM2 = 150;
    uint8_t PWM3 = 150;
    uint8_t PWM4 = 150;

    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, PWM1);
    analogWrite(PIN_M2_A3, PWM2);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, PWM3);
    analogWrite(PIN_M4_A3, PWM4);
    analogWrite(PIN_M4_A4, 0);

    digitalWrite(L_MAJU, 0);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 1);
}

void KANAN_ATAS()
{
    uint8_t PWM1 = 240;
    uint8_t PWM2 = 200;
    uint8_t PWM3 = 230;
    uint8_t PWM4 = 200;
    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, PWM2);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, PWM4);
    analogWrite(PIN_M4_A4, 0);
    digitalWrite(L_MAJU, 0);
    digitalWrite(L_KANAN, 0);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 1);
}

void KANAN()
{
    uint8_t PWM1 = 200;
    uint8_t PWM2 = 200;
    uint8_t PWM3 = 230;
    uint8_t PWM4 = 150;
    analogWrite(PIN_M1_A1, PWM1);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, PWM2);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, PWM3);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, PWM4);
    analogWrite(PIN_M4_A4, 0);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 0);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 1);
}

void KANAN_BAWAH()
{
    uint8_t PWM1 = 240;
    uint8_t PWM2 = 200;
    uint8_t PWM3 = 230;
    uint8_t PWM4 = 100;
    analogWrite(PIN_M1_A1, PWM1);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, PWM3);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, 0);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 0);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 0);
}

void MUNDUR()
{
    uint8_t PWM1 = 150;
    uint8_t PWM2 = 150;
    uint8_t PWM3 = 150;
    uint8_t PWM4 = 150;
    analogWrite(PIN_M1_A1, PWM1);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, PWM2);
    analogWrite(PIN_M3_A1, PWM3);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, PWM4);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 0);
}

void KIRI_BAWAH()
{
    uint8_t PWM1 = 150;
    uint8_t PWM2 = 150;
    uint8_t PWM3 = 150;
    uint8_t PWM4 = 150;
    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, PWM2);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, PWM4);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 0);
    digitalWrite(L_MUNDUR, 0);
}

void KIRI()
{
    uint8_t PWM1 = 150;
    uint8_t PWM2 = 150;
    uint8_t PWM3 = 150;
    uint8_t PWM4 = 150;
    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, PWM1);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, PWM2);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, PWM3);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, PWM4);
    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 0);
    digitalWrite(L_MUNDUR, 1);
}

void KIRI_ATAS()
{
    uint8_t PWM1 = 150;
    uint8_t PWM2 = 150;
    uint8_t PWM3 = 150;
    uint8_t PWM4 = 150;
    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, PWM1);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, PWM3);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, 0);
    digitalWrite(L_MAJU, 0);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 0);
    digitalWrite(L_MUNDUR, 1);
}
void STOP()
{
    statusGerak = DIAM;

    analogWrite(PIN_M1_A1, 0);
    analogWrite(PIN_M1_A2, 0);
    analogWrite(PIN_M2_A3, 0);
    analogWrite(PIN_M2_A4, 0);
    analogWrite(PIN_M3_A1, 0);
    analogWrite(PIN_M3_A2, 0);
    analogWrite(PIN_M4_A3, 0);
    analogWrite(PIN_M4_A4, 0);

    digitalWrite(L_MAJU, 1);
    digitalWrite(L_KANAN, 1);
    digitalWrite(L_KIRI, 1);
    digitalWrite(L_MUNDUR, 1);
}

void loop()
{
    // ===== CEK SENSOR PROXIMITY =====
    if (statusGerak == MAJU_GERAK)
    {
        if (digitalRead(PIN_PROXIMITY) == PROX_ACTIVE)
        {
            STOP();
            Serial.println("STOP: Paket terdeteksi");
        }
    }

    // ===== CEK SERIAL =====
    if (Serial.available())
    {
        char c = Serial.read();

        if (c == '1')
            MAJU();
        else if (c == '2')
        {
            statusGerak = LAINNYA;
            KANAN_ATAS();
        }
        else if (c == '3')
        {
            statusGerak = LAINNYA;
            KANAN();
        }
        else if (c == '4')
        {
            statusGerak = LAINNYA;
            KANAN_BAWAH();
        }
        else if (c == '5')
        {
            statusGerak = LAINNYA;
            MUNDUR();
        }
        else if (c == '6')
        {
            statusGerak = LAINNYA;
            KIRI_BAWAH();
        }
        else if (c == '7')
        {
            statusGerak = LAINNYA;
            KIRI();
        }
        else if (c == '8')
        {
            statusGerak = LAINNYA;
            KIRI_ATAS();
        }
        else if (c == '0')
            STOP();
    }
}
