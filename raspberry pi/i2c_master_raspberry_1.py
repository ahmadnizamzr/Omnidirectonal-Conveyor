from smbus2 import SMBus
import time

BUS = 1

SLAVE_1 = 0x01  # 1
SLAVE_2 = 0x0B  # 11
SLAVE_3 = 0x15  # 21

POLL_DELAY = 0.05

# valid commands
VALID_CELL_1 = {4, 8}  # slave 1, 4 kanan, 8 kiri
VALID_CELL_2 = {14, 18}  # slave 2, 14 kanan, 18 kiri
VALID_CELL_3 = {24, 28}  # slave 3, 24 kanan, 28 kiri


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
        if prox == 0:  # kalau 0 maka clear/lanjut
            return
        time.sleep(POLL_DELAY)


def process_input(bus, val):

    # =====================
    # CELL 1
    # =====================
    if val in VALID_CELL_1:

        wait_prox_clear(bus, SLAVE_1)
        send(bus, SLAVE_1, 2)

        wait_prox(bus, SLAVE_1)
        send(bus, SLAVE_1, val)

        time.sleep(2)
        send(bus, SLAVE_1, 10)

    # =====================
    # CELL 2
    # =====================
    elif val in VALID_CELL_2:

        wait_prox_clear(bus, SLAVE_1)
        wait_prox_clear(bus, SLAVE_2)

        send(bus, SLAVE_1, 2)
        send(bus, SLAVE_2, 12)

        wait_prox(bus, SLAVE_2)  # tunggu 1 prox pada slave 2

        time.sleep(0.4)  # beri delay sebentar sebelum kirim
        send(bus, SLAVE_2, val)  # jika sudah prox aktif, kirim arah final

        time.sleep(2)
        send(bus, SLAVE_1, 10)
        send(bus, SLAVE_2, 10)

    # =====================
    # CELL 3
    # =====================
    elif val in VALID_CELL_3:

        wait_prox_clear(bus, SLAVE_1)
        wait_prox_clear(bus, SLAVE_2)
        wait_prox_clear(bus, SLAVE_3)

        send(bus, SLAVE_1, 2)
        send(bus, SLAVE_2, 12)
        send(bus, SLAVE_3, 22)

        wait_prox(bus, SLAVE_3)  # tunggu 1 prox
        send(bus, SLAVE_3, val)  # kirim arah final

        time.sleep(2)
        send(bus, SLAVE_1, 10)
        send(bus, SLAVE_2, 10)
        send(bus, SLAVE_3, 10)

    else:
        print("Input tidak valid!")
        print("Gunakan:")
        print("Slave 1 → 4 / 8")
        print("Slave 2 → 14 / 18")
        print("Slave 3 → 24 / 28")


def main():
    with SMBus(BUS) as bus:
        print("I2C Master Ready")
        print("Slave 1 → 4 / 8")
        print("Slave 2 → 14 / 18")
        print("Slave 3 → 24 / 28")

        while True:
            try:
                val = int(input("Masukkan kode: "))
                process_input(bus, val)
            except ValueError:
                print("Masukkan angka valid")


if __name__ == "__main__":
    main()
