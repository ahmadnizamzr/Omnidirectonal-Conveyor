# # routing.py (cross-platform: real I2C di Raspberry Pi, mock/simulasi di Windows)
# import json
# import time
# import sys
# import argparse
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Optional, Dict, List

# # --- optional import smbus2 (hanya ada/berguna di Raspberry Pi) ---
# try:
#     from smbus2 import SMBus, i2c_msg
# except Exception:
#     SMBus = None
#     i2c_msg = None


# # =========================
# # I2C SETUP (Raspberry Pi)
# # =========================
# BUS_ID = 1
# SLAVE_1 = 0x01
# SLAVE_2 = 0x05
# SLAVE_3 = 0x09

# POLL_DELAY = 0.05  # 50 ms

# # =========================
# # COMMAND (sesuai ESP32 kamu)
# # =========================
# CMD_MAJU = 1
# CMD_KANAN = 3
# CMD_KIRI = 7
# CMD_STOP_BRAKE = 9

# DEFAULT_FINAL_DELAY_SEC = 2  # 1..8

# # =========================
# # BOX -> (target cell, arah final)
# # =========================
# BOX_ROUTE = {
#     "box1.1": (1, CMD_KIRI),
#     "box1.2": (1, CMD_KANAN),
#     "box2.1": (2, CMD_KIRI),
#     "box2.2": (2, CMD_KANAN),
#     "box3.1": (3, CMD_KIRI),
#     "box3.2": (3, CMD_KANAN),
# }

# UNKNOWN_ROUTE = (3, CMD_MAJU)

# # pakai file setting kamu, aman walau run dari folder lain
# # DB_FILE = str(Path(__file__).with_name("DataCitySetting.json"))

# DB_FILE = str(Path(__file__).resolve().parent / "DataCitySetting.json")


# @dataclass
# class RouteDecision:
#     qr_text: str
#     box_id: Optional[str]
#     target_cell: int
#     final_cmd: int
#     final_delay_sec: int


# # =========================
# # BACKEND INTERFACE
# # =========================
# class BaseCells:
#     def send_cmd(self, cell: int, direction: int, delay_sec: int = 0):
#         raise NotImplementedError

#     def read_prox(self, cell: int) -> Optional[int]:
#         raise NotImplementedError

#     def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
#         raise NotImplementedError

#     def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
#         raise NotImplementedError


# # =========================
# # REAL I2C BACKEND (Raspberry Pi)
# # =========================
# class I2CCells(BaseCells):
#     def __init__(self, bus):
#         self.bus = bus
#         self.addr_by_cell = {1: SLAVE_1, 2: SLAVE_2, 3: SLAVE_3}

#     def send_cmd(self, cell: int, direction: int, delay_sec: int = 0):
#         delay_sec = max(0, min(int(delay_sec), 8))
#         addr = self.addr_by_cell[cell]

#         msg = i2c_msg.write(addr, [direction & 0xFF, delay_sec & 0xFF])
#         self.bus.i2c_rdwr(msg)

#         print(
#             f"[I2C] -> cell{cell} addr=0x{addr:02X} dir={direction} delay={delay_sec}s"
#         )

#     def read_prox(self, cell: int) -> Optional[int]:
#         addr = self.addr_by_cell[cell]
#         try:
#             r = i2c_msg.read(addr, 1)
#             self.bus.i2c_rdwr(r)
#             return int(list(r)[0])
#         except OSError:
#             return None

#     def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
#         t0 = time.time()
#         while True:
#             p = self.read_prox(cell)
#             if p == 0:
#                 return True
#             if time.time() - t0 > timeout_s:
#                 print(f"[WARN] timeout menunggu prox clear di cell{cell}")
#                 return False
#             time.sleep(POLL_DELAY)

#     def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
#         t0 = time.time()
#         while True:
#             p = self.read_prox(cell)
#             if p == 1:
#                 print(f"[PROX] aktif di cell{cell}")
#                 return True
#             if time.time() - t0 > timeout_s:
#                 print(f"[WARN] timeout menunggu prox aktif di cell{cell}")
#                 return False
#             time.sleep(POLL_DELAY)


# # =========================
# # MOCK BACKEND (Windows / test)
# # =========================
# class MockCells(BaseCells):
#     """
#     Simulasi:
#     - send_cmd hanya print log
#     - wait_prox_set: prox aktif setelah beberapa detik (simulasi paket sampai)
#     """

#     def __init__(self, simulate_hit_after_sec: float = 2.0):
#         self.simulate_hit_after_sec = float(simulate_hit_after_sec)
#         self._prox_state = {1: 0, 2: 0, 3: 0}

#     def send_cmd(self, cell: int, direction: int, delay_sec: int = 0):
#         delay_sec = max(0, min(int(delay_sec), 8))
#         print(f"[MOCK] -> cell{cell} dir={direction} delay={delay_sec}s")

#         # kalau perintah stop, reset prox (simulasi)
#         if direction == CMD_STOP_BRAKE:
#             self._prox_state[cell] = 0

#     def read_prox(self, cell: int) -> Optional[int]:
#         return self._prox_state.get(cell, 0)

#     def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
#         # di mock anggap selalu clear (atau reset)
#         self._prox_state[cell] = 0
#         print(f"[MOCK] prox cell{cell}=0 (clear)")
#         return True

#     def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
#         print(
#             f"[MOCK] menunggu prox aktif di cell{cell} (simulasi {self.simulate_hit_after_sec:.1f}s)..."
#         )
#         time.sleep(min(self.simulate_hit_after_sec, timeout_s))
#         self._prox_state[cell] = 1
#         print(f"[MOCK] prox cell{cell}=1 (aktif)")
#         return True


# def load_database(path: str = DB_FILE) -> Dict[str, str]:
#     with open(path, "r", encoding="utf-8") as f:
#         raw = json.load(f)
#     return {str(k).strip().lower(): str(v).strip().lower() for k, v in raw.items()}


# def decide_route(
#     qr_text: str, db: Dict[str, str], final_delay_sec: int = DEFAULT_FINAL_DELAY_SEC
# ) -> RouteDecision:
#     q = (qr_text or "").strip().lower()

#     matched_box = None
#     for box_id, city in db.items():
#         if city and city != "none" and city in q:
#             matched_box = box_id
#             break

#     if matched_box and matched_box in BOX_ROUTE:
#         cell, final_cmd = BOX_ROUTE[matched_box]
#         return RouteDecision(
#             qr_text=qr_text,
#             box_id=matched_box,
#             target_cell=cell,
#             final_cmd=final_cmd,
#             final_delay_sec=max(0, min(int(final_delay_sec), 8)),
#         )

#     cell, final_cmd = UNKNOWN_ROUTE
#     return RouteDecision(
#         qr_text=qr_text,
#         box_id=None,
#         target_cell=cell,
#         final_cmd=final_cmd,
#         final_delay_sec=max(0, min(int(final_delay_sec), 8)),
#     )


# def _use_mock(force_mock: bool) -> bool:
#     if force_mock:
#         return True
#     # auto: di Windows atau smbus2 tidak ada => mock
#     if sys.platform.startswith("win"):
#         return True
#     if SMBus is None or i2c_msg is None:
#         return True
#     return False


# def run_routing_for_qr(
#     qr_text: str,
#     final_delay_sec: int = DEFAULT_FINAL_DELAY_SEC,
#     force_mock: bool = False,
#     mock_hit_after_sec: float = 2.0,
# ):
#     db = load_database(DB_FILE)
#     decision = decide_route(qr_text, db, final_delay_sec)

#     print("\n=== ROUTE DECISION ===")
#     print(f"QR: {decision.qr_text}")
#     print(f"BOX: {decision.box_id if decision.box_id else '(UNKNOWN / tidak terscan)'}")
#     print(f"TARGET CELL: {decision.target_cell}")
#     print(f"FINAL CMD: {decision.final_cmd}")
#     print(f"FINAL DELAY: {decision.final_delay_sec}s")
#     print("======================\n")

#     use_mock = _use_mock(force_mock)

#     # pilih backend
#     if use_mock:
#         cells: BaseCells = MockCells(simulate_hit_after_sec=mock_hit_after_sec)
#         _run_sequence(cells, decision)
#         return

#     # real I2C
#     with SMBus(BUS_ID) as bus:
#         cells = I2CCells(bus)
#         _run_sequence(cells, decision)


# def _run_sequence(cells: BaseCells, decision: RouteDecision):
#     # 1) pastikan prox clear untuk cell yang dilalui
#     for c in range(1, decision.target_cell + 1):
#         cells.wait_prox_clear(c, timeout_s=10.0)

#     # 2) TRANSIT: MAJU pada cell yang dilalui (1..target)
#     path: List[int] = list(range(1, decision.target_cell + 1))
#     for _ in range(3):
#         for c in path:
#             cells.send_cmd(c, CMD_MAJU, delay_sec=0)
#             time.sleep(0.03)

#     # 3) tunggu prox aktif pada cell target
#     ok = cells.wait_prox_set(decision.target_cell, timeout_s=25.0)
#     if not ok:
#         for c in path:
#             cells.send_cmd(c, CMD_STOP_BRAKE, delay_sec=0)
#         return

#     # 4) stop upstream cells
#     for c in path[:-1]:
#         cells.send_cmd(c, CMD_STOP_BRAKE, delay_sec=0)

#     # 5) gerakan final pada cell target + auto-stop (delay dieksekusi ESP32)
#     cells.send_cmd(
#         decision.target_cell, decision.final_cmd, delay_sec=decision.final_delay_sec
#     )

#     # 6) opsional: tunggu prox clear target
#     cells.wait_prox_clear(decision.target_cell, timeout_s=10.0)


# # =========================
# # TEST MANUAL
# # =========================
# if __name__ == "__main__":
#     ap = argparse.ArgumentParser()
#     ap.add_argument(
#         "--mock", action="store_true", help="paksa mode simulasi (untuk Windows/test)"
#     )
#     ap.add_argument("--delay", type=int, default=2, help="final delay 0..8")
#     ap.add_argument(
#         "--hit",
#         type=float,
#         default=2.0,
#         help="simulasi prox aktif setelah N detik (mock)",
#     )
#     args = ap.parse_args()

#     while True:
#         s = input(
#             "Masukkan QR text (contoh: SBY / KOTA:SBY-001), kosong=keluar: "
#         ).strip()
#         if not s:
#             break
#         run_routing_for_qr(
#             s,
#             final_delay_sec=args.delay,
#             force_mock=args.mock,
#             mock_hit_after_sec=args.hit,
#         )


# routing.py (cross-platform: real I2C di Raspberry Pi, mock/simulasi di Windows)


# routing.py (cross-platform: real I2C di Raspberry Pi, mock/simulasi di Windows)
import json
import time
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List

# --- optional import smbus2 (hanya ada/berguna di Raspberry Pi) ---
try:
    from smbus2 import SMBus, i2c_msg
except Exception:
    SMBus = None
    i2c_msg = None


# =========================
# I2C SETUP (Raspberry Pi)
# =========================
BUS_ID = 1
POLL_DELAY = 0.05  # 50 ms

# =========================
# COMMAND (sesuai ESP32 kamu)
# =========================
CMD_MAJU = 1
CMD_KANAN = 3
CMD_KIRI = 7
CMD_STOP_BRAKE = 9

DEFAULT_FINAL_DELAY_SEC = 2  # 1..8

# =========================
# BOX -> (target cell, arah final)
# =========================
BOX_ROUTE = {
    "box1.1": (1, CMD_KIRI),
    "box1.2": (1, CMD_KANAN),
    "box2.1": (2, CMD_KIRI),
    "box2.2": (2, CMD_KANAN),
    "box3.1": (3, CMD_KIRI),
    "box3.2": (3, CMD_KANAN),
}

UNKNOWN_ROUTE = (3, CMD_MAJU)

DB_FILE = str(Path(__file__).resolve().parent / "DataCitySetting.json")
I2C_FILE = str(Path(__file__).resolve().parent / "I2C.json")


@dataclass
class RouteDecision:
    qr_text: str
    box_id: Optional[str]
    target_cell: int
    final_cmd: int
    final_delay_sec: int


# =========================
# FUNGSI MEMBACA ALAMAT DARI I2C.JSON
# =========================
def get_i2c_addresses() -> dict:
    addrs = {1: 0x01, 2: 0x05, 3: 0x08, "conveyor": 0x0A}
    try:
        with open(I2C_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            def to_int(val_str, default):
                try:
                    return (
                        int(val_str, 16)
                        if "x" in str(val_str).lower()
                        else int(val_str)
                    )
                except:
                    return default

            addrs[1] = to_int(data.get("omni_1", ""), 0x01)
            addrs[2] = to_int(data.get("omni_2", ""), 0x05)
            addrs[3] = to_int(data.get("omni_3", ""), 0x08)
            addrs["conveyor"] = to_int(data.get("conveyor", ""), 0x0A)
    except Exception as e:
        print(f"[WARN] Gagal membaca I2C.json, pakai default. ({e})")

    return addrs


# =========================
# BACKEND INTERFACE
# =========================
class BaseCells:
    # PERBAIKAN: delay_sec dihapus dari parameter inti karena ESP32 pakai timer internal
    def send_cmd(self, cell: int, direction: int):
        raise NotImplementedError

    def read_prox(self, cell: int) -> Optional[int]:
        raise NotImplementedError

    def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
        raise NotImplementedError

    def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
        raise NotImplementedError


# =========================
# REAL I2C BACKEND (Raspberry Pi)
# =========================
class I2CCells(BaseCells):
    def __init__(self, bus):
        self.bus = bus
        config_addrs = get_i2c_addresses()

        # PERBAIKAN: Masukkan ID 0 sebagai ID untuk Conveyor Utama
        self.addr_by_cell = {
            0: config_addrs["conveyor"],  # ID 0 = Konveyor
            1: config_addrs[1],  # ID 1 = Omni 1
            2: config_addrs[2],  # ID 2 = Omni 2
            3: config_addrs[3],  # ID 3 = Omni 3
        }

    def send_cmd(self, cell: int, direction: int):
        addr = self.addr_by_cell.get(cell)
        if addr is None:
            return

        # PERBAIKAN: Hanya kirim 1 Byte (Direction) agar ESP32 tidak salah baca menjadi Stop (0)
        msg = i2c_msg.write(addr, [direction & 0xFF])
        self.bus.i2c_rdwr(msg)

        if cell == 0:
            print(f"[I2C] -> CONVEYOR UTAMA addr=0x{addr:02X} dir={direction}")
        else:
            print(f"[I2C] -> CELL {cell} addr=0x{addr:02X} dir={direction}")

    def read_prox(self, cell: int) -> Optional[int]:
        addr = self.addr_by_cell.get(cell)
        if addr is None:
            return None
        try:
            r = i2c_msg.read(addr, 1)
            self.bus.i2c_rdwr(r)
            return int(list(r)[0])
        except OSError:
            return None

    def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
        t0 = time.time()
        while True:
            p = self.read_prox(cell)
            if p == 0:
                return True
            if time.time() - t0 > timeout_s:
                print(f"[WARN] timeout menunggu prox clear di cell{cell}")
                return False
            time.sleep(POLL_DELAY)

    def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
        t0 = time.time()
        while True:
            p = self.read_prox(cell)
            if p == 1:
                print(f"[PROX] aktif di cell{cell}")
                return True
            if time.time() - t0 > timeout_s:
                print(f"[WARN] timeout menunggu prox aktif di cell{cell}")
                return False
            time.sleep(POLL_DELAY)


# =========================
# MOCK BACKEND (Windows / test)
# =========================
class MockCells(BaseCells):
    def __init__(self, simulate_hit_after_sec: float = 2.0):
        self.simulate_hit_after_sec = float(simulate_hit_after_sec)
        self._prox_state = {1: 0, 2: 0, 3: 0}
        self.addrs = get_i2c_addresses()
        self.addr_by_cell = {
            0: self.addrs["conveyor"],
            1: self.addrs[1],
            2: self.addrs[2],
            3: self.addrs[3],
        }

    def send_cmd(self, cell: int, direction: int):
        addr = self.addr_by_cell.get(cell, 0x00)
        name = "CONVEYOR" if cell == 0 else f"CELL {cell}"
        print(f"[MOCK] -> {name} (0x{addr:02X}) dir={direction}")

        if direction == CMD_STOP_BRAKE and cell != 0:
            self._prox_state[cell] = 0

    def read_prox(self, cell: int) -> Optional[int]:
        return self._prox_state.get(cell, 0)

    def wait_prox_clear(self, cell: int, timeout_s: float = 10.0) -> bool:
        if cell == 0:
            return True
        self._prox_state[cell] = 0
        print(f"[MOCK] prox cell{cell}=0 (clear)")
        return True

    def wait_prox_set(self, cell: int, timeout_s: float = 20.0) -> bool:
        if cell == 0:
            return True
        print(
            f"[MOCK] menunggu prox aktif di cell{cell} (simulasi {self.simulate_hit_after_sec:.1f}s)..."
        )
        time.sleep(min(self.simulate_hit_after_sec, timeout_s))
        self._prox_state[cell] = 1
        print(f"[MOCK] prox cell{cell}=1 (aktif)")
        return True


def load_database(path: str = DB_FILE) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {str(k).strip().lower(): str(v).strip().lower() for k, v in raw.items()}


def decide_route(
    qr_text: str, db: Dict[str, str], final_delay_sec: int = DEFAULT_FINAL_DELAY_SEC
) -> RouteDecision:
    q = (qr_text or "").strip().lower()

    matched_box = None
    for box_id, city in db.items():
        if city and city != "none" and city in q:
            matched_box = box_id
            break

    if matched_box and matched_box in BOX_ROUTE:
        cell, final_cmd = BOX_ROUTE[matched_box]
        return RouteDecision(
            qr_text=qr_text,
            box_id=matched_box,
            target_cell=cell,
            final_cmd=final_cmd,
            final_delay_sec=final_delay_sec,
        )

    cell, final_cmd = UNKNOWN_ROUTE
    return RouteDecision(
        qr_text=qr_text,
        box_id=None,
        target_cell=cell,
        final_cmd=final_cmd,
        final_delay_sec=final_delay_sec,
    )


def _use_mock(force_mock: bool) -> bool:
    if force_mock:
        return True
    if sys.platform.startswith("win"):
        return True
    if SMBus is None or i2c_msg is None:
        return True
    return False


def run_routing_for_qr(
    qr_text: str,
    final_delay_sec: int = DEFAULT_FINAL_DELAY_SEC,
    force_mock: bool = False,
    mock_hit_after_sec: float = 2.0,
):
    db = load_database(DB_FILE)
    decision = decide_route(qr_text, db, final_delay_sec)

    print("\n=== ROUTE DECISION ===")
    print(f"QR: {decision.qr_text}")
    print(f"BOX: {decision.box_id if decision.box_id else '(UNKNOWN / tidak terscan)'}")
    print(f"TARGET CELL: {decision.target_cell}")
    print(f"FINAL CMD: {decision.final_cmd}")
    print("======================\n")

    use_mock = _use_mock(force_mock)

    if use_mock:
        cells: BaseCells = MockCells(simulate_hit_after_sec=mock_hit_after_sec)
        _run_sequence(cells, decision)
        return

    # real I2C
    with SMBus(BUS_ID) as bus:
        cells = I2CCells(bus)
        _run_sequence(cells, decision)


def _run_sequence(cells: BaseCells, decision: RouteDecision):
    # 1. Pastikan jalur kosong (sensor mati)
    for c in range(1, decision.target_cell + 1):
        cells.wait_prox_clear(c, timeout_s=10.0)

    # 2. PERBAIKAN: NYALAKAN CONVEYOR UTAMA DULU AGAR PAKET JALAN (ID 0)
    cells.send_cmd(0, CMD_MAJU)

    # 3. NYALAKAN OMNI CELL YANG AKAN DILEWATI AGAR MEMBANTU PAKET MAJU
    path: List[int] = list(range(1, decision.target_cell + 1))
    for _ in range(3):
        for c in path:
            cells.send_cmd(c, CMD_MAJU)
            time.sleep(0.03)

    # 4. TUNGGU PAKET MENYENTUH SENSOR DI CELL TARGET
    ok = cells.wait_prox_set(decision.target_cell, timeout_s=25.0)

    # 5. PERBAIKAN: MATIKAN CONVEYOR UTAMA SETELAH PAKET SAMPAI (ATAU JIKA GAGAL)
    cells.send_cmd(0, CMD_STOP_BRAKE)

    if not ok:
        for c in path:
            cells.send_cmd(c, CMD_STOP_BRAKE)
        return

    # 6. MATIKAN OMNI CELL SEBELUMNYA (YANG SUDAH DILEWATI)
    for c in path[:-1]:
        cells.send_cmd(c, CMD_STOP_BRAKE)

    # 7. EKSEKUSI PERINTAH FINAL (EJECT KANAN/KIRI) PADA TARGET CELL
    cells.send_cmd(decision.target_cell, decision.final_cmd)

    # 8. Tunggu sampai paket benar-benar jatuh (sensor kembali clear)
    cells.wait_prox_clear(decision.target_cell, timeout_s=10.0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mock", action="store_true", help="paksa mode simulasi (untuk Windows/test)"
    )
    ap.add_argument(
        "--hit",
        type=float,
        default=2.0,
        help="simulasi prox aktif setelah N detik (mock)",
    )
    args = ap.parse_args()

    while True:
        s = input(
            "Masukkan QR text (contoh: SBY / KOTA:SBY-001), kosong=keluar: "
        ).strip()
        if not s:
            break
        run_routing_for_qr(s, force_mock=args.mock, mock_hit_after_sec=args.hit)
