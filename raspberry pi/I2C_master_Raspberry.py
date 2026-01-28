from smbus2 import SMBus
import time

BUS = 1

SLAVE_1 = 0x01  # 1
SLAVE_2 = 0x0B  # 11
SLAVE_3 = 0x15  # 21

POLL_DELAY = 0.05
MOVE_DELAY = 0.1


# valid commands
VALID_CELL_1 = {4, 8}
VALID_CELL_2 = {14, 18}
VALID_CELL_3 = {24, 28}


def send(bus, addr, data):
    bus.write_byte(addr, data)
    print(f"Kirim {data} ke slave {addr}")


def read_prox(bus, addr):
    try:
        return bus.read_byte(addr)
    except OSError:
        return None


def wait_prox(bus, addr):
    while True:
        prox = read_prox(bus, addr)
        if prox == 1:
            print(f"Prox aktif di slave {addr}")
            return
        time.sleep(POLL_DELAY)


def wait_prox_clear(bus, addr):
    print(f"Menunggu proximity slave {addr} reset...")
    while True:
        prox = read_prox(bus, addr)
        if prox == 0:
            return
        time.sleep(POLL_DELAY)


def process_input(bus, val):

    # =====================
    # CELL 1 ONLY
    # =====================
    if 2 <= val <= 10:

        # pastikan proximity OFF dulu
        wait_prox_clear(bus, SLAVE_1)
        # selalu kirim 2 dulu
        send(bus, SLAVE_1, 2)
        if val in (4, 8):
            # tunggu proximity kena
            wait_prox(bus, SLAVE_1)
            # kirim arah
            send(bus, SLAVE_1, val)
            # delay 2 detik
            time.sleep(2)
            # stop roda
            send(bus, SLAVE_1, 10)

    # =====================
    # CELL 2
    # =====================
    elif 12 <= val <= 20:
        send(bus, SLAVE_1, 2)
        send(bus, SLAVE_2, 12)

        if val in (14, 18):
            # tunggu proximity kena
            wait_prox(bus, SLAVE_2)
            # kirim arah
            send(bus, SLAVE_2, val)
            # delay 2 detik
            time.sleep(2)
            # stop roda
            send(bus, SLAVE_1, 10)
            send(bus, SLAVE_2, 10)

    # =====================
    # CELL 3
    # =====================
    elif 22 <= val <= 30:
        send(bus, SLAVE_1, 2)
        send(bus, SLAVE_2, 12)
        send(bus, SLAVE_3, 22)

        if val in (24, 28):
            wait_prox(bus, SLAVE_3)
            send(bus, SLAVE_3, val)
            # delay 2 detik
            time.sleep(2)
            # stop roda
            send(bus, SLAVE_1, 10)
            send(bus, SLAVE_2, 10)
            send(bus, SLAVE_3, 10)

    else:
        print("Input tidak valid")


def main():
    with SMBus(BUS) as bus:
        print("I2C Master Ready")

        while True:
            try:
                val = int(input("Masukkan kode: "))
                process_input(bus, val)
            except ValueError:
                print("Masukkan angka valid")


if __name__ == "__main__":
    main()
