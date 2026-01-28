// #include <ESP32Servo.h>
// ESP32PWM PWMA;
// ESP32PWM PWMB;
// ESP32PWM PWMX;
// int freq = 1000;

#include <Arduino.h>
#include <Wire.h>
static const uint8_t I2C_ADDR = 10;

int prox = 23;

// int pwm3 = 33;
// int dir3 = 32;
// int pwm2 = 26;
// int dir2 = 25;
// int pwm1 = 14; // 27;
// int dir1 = 27; // 14;
// int pwm4 = 13; // 12;
// int dir4 = 12; // 13;

int pwm3 = 25;
int dir3 = 26;
int pwm2 = 12;
int dir2 = 13;
int pwm1 = 14; // 27;
int dir1 = 27; // 14;
int pwm4 = 33; // 12;
int dir4 = 32; // 13;

// const uint8_t PIN_M1_A1 = 27;
// const uint8_t PIN_M1_A2 = 14;
// const uint8_t PIN_M2_A3 = 12;
// const uint8_t PIN_M2_A4 = 13;
// const uint8_t PIN_M3_A1 = 26;
// const uint8_t PIN_M3_A2 = 25;
// const uint8_t PIN_M4_A3 = 33;
// const uint8_t PIN_M4_A4 = 32;

int led3 = 19;
int led2 = 18;
int led4 = 5;
int led1 = 15;

const int encoderPin2 = 36;
const int encoderPin3 = 39;
const int encoderPin4 = 34;
const int encoderPin1 = 35;

int setPWM = 200;

unsigned long lastTime = 0;
unsigned long currentTime;

unsigned long startMillis; // some global variables available anywhere in the program
unsigned long currentMillis;

volatile uint8_t lastResponse = 0;

int rpm = 0;
String dataTerima = "0";

const unsigned long interval = 1000; // Interval waktu dalam ms untuk pengukuran
unsigned long waktu;

// -------------------------------------------------------------

void move_maju()
{
    digitalWrite(dir1, 0);
    analogWrite(pwm1, setPWM);
    digitalWrite(dir2, 1);
    analogWrite(pwm2, 255 - setPWM);
    digitalWrite(dir3, 1);
    analogWrite(pwm3, 255 - setPWM);
    digitalWrite(dir4, 0);
    analogWrite(pwm4, setPWM);

    digitalWrite(led1, 0);
    digitalWrite(led2, 1);
    digitalWrite(led3, 1);
    digitalWrite(led4, 1);
}

void move_kanan()
{
    digitalWrite(dir1, 1);
    analogWrite(pwm1, 255 - setPWM);
    digitalWrite(dir2, 1);
    analogWrite(pwm2, 255 - setPWM);
    digitalWrite(dir3, 0);
    analogWrite(pwm3, setPWM);
    digitalWrite(dir4, 0);
    analogWrite(pwm4, setPWM);

    digitalWrite(led1, 1);
    digitalWrite(led2, 1);
    digitalWrite(led3, 1);
    digitalWrite(led4, 0);
}

void move_kiri()
{
    digitalWrite(dir1, 0);
    analogWrite(pwm1, setPWM);
    digitalWrite(dir2, 0);
    analogWrite(pwm2, setPWM);
    digitalWrite(dir3, 1);
    analogWrite(pwm3, 255 - setPWM);
    digitalWrite(dir4, 1);
    analogWrite(pwm4, 255 - setPWM);

    digitalWrite(led1, 1);
    digitalWrite(led2, 0);
    digitalWrite(led3, 1);
    digitalWrite(led4, 1);
}

void move_stop()
{
    digitalWrite(dir1, 0);
    analogWrite(pwm1, 0);
    digitalWrite(dir2, 0);
    analogWrite(pwm2, 0);
    digitalWrite(dir3, 0);
    analogWrite(pwm3, 0);
    digitalWrite(dir4, 0);
    analogWrite(pwm4, 0);

    digitalWrite(led1, 1);
    digitalWrite(led2, 1);
    digitalWrite(led3, 1);
    digitalWrite(led4, 1);
}

void requestEvent()
{
    // Dipanggil saat master melakukan Wire.requestFrom()
    Wire.write(lastResponse); // kirim 1 byte
                              // opsional: lastResponse = 0;  // kalau mau “sekali kirim”
}

void receiveEvent(int bytes)
{
    while (Wire.available())
    {
        uint8_t cmd = Wire.read();
        switch (cmd)
        {
        case 11:
            move_maju();
            lastResponse = digitalRead(prox); // LED1 nyala
            break;
        case 12:
            move_kanan();
            lastResponse = digitalRead(prox); // LED1 mati
            break;
        case 13:
            move_kiri();
            lastResponse = digitalRead(prox); // contoh pola: LED2 nyala
            break;
        case 10:
            move_stop();
            lastResponse = digitalRead(prox); // LED2 mati
            break;
        default:
            // command tidak dikenal
            lastResponse = 255;
            break;
        }
    }
}

// ---------------------------------------------

void cekSerial()
{

    // Serial.print(setPWM);Serial.println(";");
    Serial.println(dataTerima);
    if (dataTerima == "0")
    {
        digitalWrite(dir1, 0);
        analogWrite(pwm1, 0);
        digitalWrite(dir2, 0);
        analogWrite(pwm2, 0);
        digitalWrite(dir3, 0);
        analogWrite(pwm3, 0);
        digitalWrite(dir4, 0);
        analogWrite(pwm4, 0);

        digitalWrite(led1, 1);
        digitalWrite(led2, 1);
        digitalWrite(led3, 1);
        digitalWrite(led4, 1);

        // pulse1Count = 0;
        // pulse2Count = 0;
        // pulse3Count = 0;
        // pulse4Count = 0;
        // detachInterrupt(digitalPinToInterrupt(encoderPin1));
        // detachInterrupt(digitalPinToInterrupt(encoderPin2));
        // detachInterrupt(digitalPinToInterrupt(encoderPin3));
        // detachInterrupt(digitalPinToInterrupt(encoderPin4));
    }
    if (dataTerima == "1")
    {
        digitalWrite(dir1, 0);
        analogWrite(pwm1, setPWM);
        digitalWrite(dir2, 0);
        analogWrite(pwm2, 0);
        digitalWrite(dir3, 0);
        analogWrite(pwm3, 0);
        digitalWrite(dir4, 0);
        analogWrite(pwm4, 0);

        digitalWrite(led1, 0);
        digitalWrite(led2, 1);
        digitalWrite(led3, 1);
        digitalWrite(led4, 1);

        // attachInterrupt(digitalPinToInterrupt(encoderPin1), countPulse1, FALLING);
    }
    if (dataTerima == "2")
    {
        digitalWrite(dir1, 0);
        analogWrite(pwm1, 0);
        digitalWrite(dir2, 0);
        analogWrite(pwm2, setPWM);
        digitalWrite(dir3, 0);
        analogWrite(pwm3, 0);
        digitalWrite(dir4, 0);
        analogWrite(pwm4, 0);

        digitalWrite(led1, 1);
        digitalWrite(led2, 0);
        digitalWrite(led3, 1);
        digitalWrite(led4, 1);

        // attachInterrupt(digitalPinToInterrupt(encoderPin2), countPulse2, RISING);
    }
    if (dataTerima == "3")
    {
        digitalWrite(dir1, 0);
        analogWrite(pwm1, 0);
        digitalWrite(dir2, 0);
        analogWrite(pwm2, 0);
        digitalWrite(dir3, 0);
        analogWrite(pwm3, setPWM);
        digitalWrite(dir4, 0);
        analogWrite(pwm4, 0);

        digitalWrite(led1, 1);
        digitalWrite(led2, 1);
        digitalWrite(led3, 0);
        digitalWrite(led4, 1);

        // attachInterrupt(digitalPinToInterrupt(encoderPin3), countPulse3, RISING);
    }
    if (dataTerima == "4")
    {
        digitalWrite(dir1, 0);
        analogWrite(pwm1, 0);
        digitalWrite(dir2, 0);
        analogWrite(pwm2, 0);
        digitalWrite(dir3, 0);
        analogWrite(pwm3, 0);
        digitalWrite(dir4, 0);
        analogWrite(pwm4, setPWM);

        digitalWrite(led1, 1);
        digitalWrite(led2, 1);
        digitalWrite(led3, 1);
        digitalWrite(led4, 0);

        // attachInterrupt(digitalPinToInterrupt(encoderPin4), countPulse4, RISING);
    }
    // Serial.println(dataTerima);
}

void setup()
{
    Wire.begin(I2C_ADDR);
    Wire.onReceive(receiveEvent);
    Wire.onRequest(requestEvent);

    pinMode(dir1, OUTPUT);
    pinMode(pwm1, OUTPUT);
    pinMode(dir2, OUTPUT);
    pinMode(pwm2, OUTPUT);
    pinMode(dir3, OUTPUT);
    pinMode(pwm3, OUTPUT);
    pinMode(dir4, OUTPUT);
    pinMode(pwm4, OUTPUT);

    pinMode(encoderPin1, INPUT);
    pinMode(encoderPin2, INPUT);
    pinMode(encoderPin3, INPUT);
    pinMode(encoderPin4, INPUT);

    pinMode(led1, OUTPUT);
    pinMode(led2, OUTPUT);
    pinMode(led3, OUTPUT);
    pinMode(led4, OUTPUT);
    digitalWrite(led1, 0);
    digitalWrite(led2, 0);
    digitalWrite(led3, 0);
    digitalWrite(led4, 0);

    pinMode(prox, INPUT);
    Serial.begin(115200);
    // Serial.println("prepare");

    // attachInterrupt(digitalPinToInterrupt(encoderPin1), countPulse1, RISING);
    // attachInterrupt(digitalPinToInterrupt(encoderPin2), countPulse2, RISING);
    // attachInterrupt(digitalPinToInterrupt(encoderPin3), countPulse3, RISING);
    // attachInterrupt(digitalPinToInterrupt(encoderPin4), countPulse4, RISING);

    // attachInterrupt(digitalPinToInterrupt(encoderPin), countPulse, RISING);
    delay(1000);
    digitalWrite(led1, 1);
    digitalWrite(led2, 1);
    digitalWrite(led3, 1);
    digitalWrite(led4, 1);
}

void loop()
{
    // if (Serial.available() > 0)
    // {
    //     dataTerima = Serial.readStringUntil('\n');
    //     cekSerial();
    // }
    // cekRPM();
    delay(10);
}
