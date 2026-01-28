#include <Arduino.h>
#include <Wire.h>
#define SLAVE_ADDRESS 9
#define SLAVE_ADDRESS2 10

String dataTerima;

void setup()
{
    Serial.begin(115200);
    Wire.begin(21, 22); // ESP32 master: SDA=21, SCL=22
    Wire.setClock(100000);
}

void loop()
{
    if (Serial.available() > 0)
    {
        dataTerima = Serial.readStringUntil('\n');
        int angka = dataTerima.toInt();
        uint8_t err;
        // 1) Kirim command
        if (angka < 5)
        {
            Wire.beginTransmission(SLAVE_ADDRESS); // kirim ke slave 1
            Wire.write((uint8_t)angka);            // kirim 1 byte
            err = Wire.endTransmission();
        }
        if (angka < 15 && angka > 9)
        {
            Wire.beginTransmission(SLAVE_ADDRESS2); // kirim ke slave 2
            Wire.write((uint8_t)angka);             // kirim 1 byte
            err = Wire.endTransmission();
        }
        Serial.print("data terkirim = ");
        Serial.print(angka);
        Serial.print(" | i2c err = ");
        Serial.println(err);

        // Kalau kirim sukses, 2) Minta respon dari slave
        if (err == 0)
        {
            // minta 1 byte respon
            uint8_t n = Wire.requestFrom(SLAVE_ADDRESS, (uint8_t)1);
            if (n == 1 && Wire.available())
            {
                uint8_t resp = Wire.read();
                Serial.print("respon slave = ");
                Serial.println(resp);
            }
            else
            {
                Serial.println("respon slave tidak ada / timeout");
            }
        }
    }

    delay(10);
}
