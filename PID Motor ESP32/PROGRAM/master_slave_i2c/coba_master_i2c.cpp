#include <Arduino.h>
#include <Wire.h>

// ===== I2C SLAVE ADDRESSES =====
#define ADDR_S1 1  // conveyor + scan / prox1
#define ADDR_S2 11 // prox2
#define ADDR_S3 21 // prox3

// ===== PROX RESPONSE VALUE (assumption) =====
#define PROX_DETECTED 1

// ===== I2C PINS (ESP32 master) =====
#define SDA_PIN 21
#define SCL_PIN 22

// ===== TIMEOUT WAIT PROX (ms) =====
const uint32_t PROX_TIMEOUT_MS = 3000;

// ----------------------------------------------------
// Helper: send 1 byte to I2C slave
// return: err (0 = success)
// ----------------------------------------------------
uint8_t sendI2C(uint8_t addr, uint8_t data)
{
    Wire.beginTransmission(addr);
    Wire.write(data);
    return Wire.endTransmission(); // 0 success
}

// ----------------------------------------------------
// Helper: request 1 byte from I2C slave
// return: true if got 1 byte, output in resp
// ----------------------------------------------------
bool readI2CByte(uint8_t addr, uint8_t &resp)
{
    uint8_t n = Wire.requestFrom(addr, (uint8_t)1);
    if (n == 1 && Wire.available())
    {
        resp = Wire.read();
        return true;
    }
    return false;
}

// ===== JOB STATE MACHINE =====
enum JobStage
{
    IDLE,
    SEND_PREP,
    WAIT_PROX,
    SEND_FINAL,
    DONE,
    ERROR_STAGE
};

struct Job
{
    bool active = false;
    bool invalid = false;

    int cmd = 0;

    // list of prep steps (max 3)
    uint8_t prepAddr[3];
    uint8_t prepData[3];
    uint8_t prepCount = 0;
    uint8_t prepIndex = 0;

    bool needWait = false;
    uint8_t waitAddr = 0;  // which slave to read prox from
    uint8_t finalAddr = 0; // where to send final
    uint8_t finalData = 0; // final command data

    uint32_t waitStartMs = 0;

    JobStage stage = IDLE;
};

Job job;

// ----------------------------------------------------
// Build job from serial input command
// ----------------------------------------------------
void buildJob(int cmd)
{
    job = Job(); // reset all
    job.active = true;
    job.cmd = cmd;

    auto addPrep = [&](uint8_t addr, uint8_t data)
    {
        if (job.prepCount < 3)
        {
            job.prepAddr[job.prepCount] = addr;
            job.prepData[job.prepCount] = data;
            job.prepCount++;
        }
    };

    // ===== SPECIAL CASES =====
    if (cmd == 4 || cmd == 8)
    {
        addPrep(ADDR_S1, 2); // prepare
        job.needWait = true;
        job.waitAddr = ADDR_S1;
        job.finalAddr = ADDR_S1;
        job.finalData = (uint8_t)cmd;
        job.stage = SEND_PREP;
        return;
    }

    if (cmd == 14 || cmd == 18)
    {
        addPrep(ADDR_S1, 2);
        addPrep(ADDR_S2, 12);
        job.needWait = true;
        job.waitAddr = ADDR_S2;
        job.finalAddr = ADDR_S2;
        job.finalData = (uint8_t)cmd;
        job.stage = SEND_PREP;
        return;
    }

    if (cmd == 24 || cmd == 28)
    {
        addPrep(ADDR_S1, 2);
        addPrep(ADDR_S2, 12);
        addPrep(ADDR_S3, 22);
        job.needWait = true;
        job.waitAddr = ADDR_S3;
        job.finalAddr = ADDR_S3;
        job.finalData = (uint8_t)cmd;
        job.stage = SEND_PREP;
        return;
    }

    // ===== INPUT 22 SPECIAL (no waiting, just send 2->12->22) =====
    if (cmd == 22)
    {
        addPrep(ADDR_S1, 2);
        addPrep(ADDR_S2, 12);
        addPrep(ADDR_S3, 22);
        job.needWait = false;
        job.stage = SEND_PREP;
        return;
    }

    // ===== NORMAL RANGE RULES =====
    if (cmd >= 2 && cmd <= 10)
    {
        addPrep(ADDR_S1, (uint8_t)cmd);
        job.needWait = false;
        job.stage = SEND_PREP;
        return;
    }

    if (cmd >= 12 && cmd <= 20)
    {
        addPrep(ADDR_S2, (uint8_t)cmd);
        job.needWait = false;
        job.stage = SEND_PREP;
        return;
    }

    if (cmd >= 22 && cmd <= 30)
    {
        addPrep(ADDR_S3, (uint8_t)cmd);
        job.needWait = false;
        job.stage = SEND_PREP;
        return;
    }

    // ===== INVALID INPUT =====
    job.invalid = true;
    job.stage = ERROR_STAGE;
}

// ----------------------------------------------------
// Run job state machine (non-blocking)
// ----------------------------------------------------
void runJob()
{
    if (!job.active) return; // no active job

    switch (job.stage)
    {
    case SEND_PREP:
    {
        // send one prep step per loop (lebih aman, tidak blocking)
        if (job.prepIndex < job.prepCount)
        {
            uint8_t addr = job.prepAddr[job.prepIndex];
            uint8_t data = job.prepData[job.prepIndex];

            uint8_t err = sendI2C(addr, data);

            Serial.print("[PREP] addr=");
            Serial.print(addr);
            Serial.print(" data=");
            Serial.print(data);
            Serial.print(" err=");
            Serial.println(err);

            if (err != 0)
            {
                job.stage = ERROR_STAGE;
                return;
            }

            job.prepIndex++;
            return; // kirim step berikutnya di loop selanjutnya
        }

        // prep selesai
        if (job.needWait)
        {
            job.waitStartMs = millis();
            job.stage = WAIT_PROX;
        }
        else
        {
            job.stage = DONE;
        }
        return;
    }

    case WAIT_PROX:
    {
        // timeout
        if (millis() - job.waitStartMs > PROX_TIMEOUT_MS)
        {
            Serial.println("[WAIT] timeout proximity!");
            job.stage = ERROR_STAGE;
            return;
        }

        uint8_t resp = 0;
        if (readI2CByte(job.waitAddr, resp))
        {
            Serial.print("[WAIT] addr=");
            Serial.print(job.waitAddr);
            Serial.print(" resp=");
            Serial.println(resp);

            if (resp == PROX_DETECTED)
            {
                job.stage = SEND_FINAL;
            }
        }
        // kalau belum ada data, tetap lanjut loop (non-blocking)
        return;
    }

    case SEND_FINAL:
    {
        uint8_t err = sendI2C(job.finalAddr, job.finalData);

        Serial.print("[FINAL] addr=");
        Serial.print(job.finalAddr);
        Serial.print(" data=");
        Serial.print(job.finalData);
        Serial.print(" err=");
        Serial.println(err);

        if (err != 0)
        {
            job.stage = ERROR_STAGE;
        }
        else
        {
            job.stage = DONE;
        }
        return;
    }

    case DONE:
    {
        Serial.print("[DONE] cmd=");
        Serial.println(job.cmd);
        job.active = false;
        job.stage = IDLE;
        return;
    }

    case ERROR_STAGE:
    {
        if (job.invalid)
        {
            Serial.print("[ERROR] invalid cmd: ");
            Serial.println(job.cmd);
        }
        else
        {
            Serial.print("[ERROR] cmd failed: ");
            Serial.println(job.cmd);
        }
        job.active = false;
        job.stage = IDLE;
        return;
    }

    case IDLE:
    default:
        return;
    }
}

void setup()
{
    Serial.begin(115200);

    Wire.begin(SDA_PIN, SCL_PIN);
    Wire.setClock(100000);

    Serial.println("ESP32 I2C Master ready.");
    Serial.println("Input number then ENTER (newline).");
}

void loop()
{
    // 1) cek input serial dan buat job baru jika idle
    if (!job.active && Serial.available() > 0) // jika job tidak aktif dan ada input serial
    {
        String s = Serial.readStringUntil('\n');
        s.trim();
        if (s.length() > 0)
        {
            int cmd = s.toInt();
            Serial.print("[NEW] cmd=");
            Serial.println(cmd);
            buildJob(cmd);
        }
    }

    // 2) jalankan state machine job
    runJob();

    delay(5);
}
