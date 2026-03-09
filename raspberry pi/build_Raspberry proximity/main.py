# from pathlib import Path
# import tkinter as tk
# from tkinter import ttk, messagebox
# from PIL import Image, ImageTk
# import json
# import threading
# import queue
# import cv2
# from threading import Lock
# import subprocess

# from camera import QRScanner
# import routing

# # =========================
# # PATHS (Raspberry Pi / Linux friendly)
# # =========================
# BASE_DIR = Path(__file__).resolve().parent
# ASSETS_PATH = BASE_DIR / "frame0"  # <--- folder frame0 di sebelah main.py
# CITY_FILE = (
#     BASE_DIR / "DataCitySetting.json"
# )
# I2C_CONFIG_FILE = BASE_DIR / "I2C.json"

# def load_i2c_config() -> dict:
#     try:
#         with I2C_CONFIG_FILE.open("r", encoding="utf-8") as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         # Default jika I2C.json belum ada
#         return {"omni_1": "0x01", "omni_2": "0x05", "omni_3": "0x08", "conveyor": "0x0A"}

# def save_i2c_config(data: dict):
#     with I2C_CONFIG_FILE.open("w", encoding="utf-8") as f:
#         json.dump(data, f, indent=4)

# def relative_to_assets(path: str) -> Path:
#     return ASSETS_PATH / Path(path)

# window = tk.Tk()
# window.title("Pemilihan Kota Paket")
# window.configure(bg="#B28F8F")

# # ICON_PATH = r"E:\TA\I2C Raspberry_Esp32\raspberry pi\GUI_SetCity\build_to_git\assets\frame0\Logo.png"
# ICON_PATH = relative_to_assets("Logo.png")

# try:
#     LANCZOS = Image.Resampling.LANCZOS
# except Exception:
#     LANCZOS = Image.LANCZOS

# try:
#     img_icon = Image.open(ICON_PATH).convert("RGBA").resize((32, 32), LANCZOS)
#     icon = ImageTk.PhotoImage(img_icon)
#     window.iconphoto(True, icon)
# except Exception:
#     pass

# window_width = 1000
# window_height = 500
# offset_y = 17
# offset_x = 8
# screen_width = window.winfo_screenwidth()
# screen_height = window.winfo_screenheight()
# center_x = int((screen_width - window_width) / 2) - offset_x
# center_y = int((screen_height - window_height) / 2) - offset_y
# window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
# window.minsize(window_width, window_height)


# # =========================
# # WINDOW MODE MANAGER
# # =========================
# class WindowModeManager:
#     def __init__(self, root: tk.Tk):
#         self.root = root
#         self.mode = "normal"
#         self._internal = False
#         self.normal_geom = root.geometry()
#         root.after(120, self._poll)

#     def _screen_geom(self):
#         w = self.root.winfo_screenwidth()
#         h = self.root.winfo_screenheight()
#         return f"{w}x{h}+0+0"

#     def enter_fullscreen_decorated(self):
#         def do():
#             self.mode = "fullscreen"
#             self.root.state("normal")
#             self.root.geometry(self._screen_geom())

#         self._run_internal(do)

#     def _run_internal(self, fn):
#         self._internal = True
#         fn()
#         self.root.after(200, lambda: setattr(self, "_internal", False))

#     def _poll(self):
#         try:
#             st = self.root.state()
#         except Exception:
#             return

#         if st == "iconic":
#             self.root.after(120, self._poll)
#             return

#         if not self._internal:
#             if self.mode == "normal" and st == "zoomed":
#                 self.mode = "maximized"
#             elif self.mode == "maximized" and st == "normal":
#                 self.enter_fullscreen_decorated()
#             elif self.mode == "fullscreen" and st == "zoomed":
#                 self.mode = "maximized"

#         self.root.after(120, self._poll)


# window.update_idletasks()
# # mode_mgr = WindowModeManager(window)


# def back_to_normal(event=None):
#     mode_mgr.mode = "normal"
#     window.state("normal")
#     window.geometry(mode_mgr.normal_geom)


# window.bind("<Escape>", back_to_normal)


# # =========================
# # RESPONSIVE LAYOUT BASE
# # =========================
# BASE_W, BASE_H = 700, 550
# Tinggi_Header = 50
# ui = {"s": 1.0, "px": 0.0, "cy0": 0.0, "job": None}


# def T(x, y):
#     return ui["px"] + x * ui["s"], ui["cy0"] + (y - Tinggi_Header) * ui["s"]


# def FS(sz):
#     return max(8, int(sz * ui["s"]))


# def quantize_scale(s: float, step: float = 0.05) -> float:
#     return round(s / step) * step


# # =========================
# # IMAGE CACHE
# # =========================
# _pil_cache = {}
# _tk_cache = {}

# try:
#     RESAMPLE = Image.Resampling.BILINEAR
# except Exception:
#     RESAMPLE = Image.BILINEAR


# def get_pil(name: str) -> Image.Image:
#     if name not in _pil_cache:
#         _pil_cache[name] = Image.open(relative_to_assets(name)).convert("RGBA")
#     return _pil_cache[name]


# def make_tk(name: str, s: float) -> ImageTk.PhotoImage:
#     s = round(float(s), 2)
#     base = get_pil(name)
#     w = max(1, int(base.width * s))
#     h = max(1, int(base.height * s))
#     key = (name, w, h)

#     if key not in _tk_cache:
#         if len(_tk_cache) > 400:
#             _tk_cache.clear()
#         _tk_cache[key] = ImageTk.PhotoImage(base.resize((w, h), RESAMPLE))

#     return _tk_cache[key]


# btn_img_refs = {}
# canvas_img_refs = {}


# # =========================
# # BIG IMAGE (CONVEYOR)
# # =========================
# BIG_FILE = "image_1.png"
# BIG_W, BIG_H = get_pil(BIG_FILE).size
# BIG_BASE_CX = 320.0
# BIG_BASE_CY = 318.0

# # jarak (gap) antara konveyor (image_1) dan frame kamera (base px, ikut skala)
# CONVEYOR_GAP_BASE = 5

# PAD = 8
# safe_w = max(1.0, (2.0 * min(BIG_BASE_CX, BASE_W - BIG_BASE_CX)) - 2.0 * PAD)
# safe_h = max(
#     1.0, (2.0 * min(BIG_BASE_CY - Tinggi_Header, BASE_H - BIG_BASE_CY)) - 2.0 * PAD
# )
# BIG_BASE_SCALE = min(safe_w / BIG_W, safe_h / BIG_H)


# # =========================
# # BUTTON/LABEL POSITIONS (BASE)
# # =========================
# posisi_tombol = {
#     "button_1": (200.0, 130.0, "atas"),
#     "button_2": (290.0, 130.0, "atas"),
#     "button_3": (370.0, 130.0, "atas"),
#     "button_4": (200.0, 460.0, "bawah"),
#     "button_5": (290.0, 460.0, "bawah"),
#     "button_6": (370.0, 460.0, "bawah"),
# }

# # posisi label
# BTN_WH = {
#     "button_1": (70.0, 34.0),
#     "button_2": (70.0, 34.0),
#     "button_3": (90.0, 34.0),
#     "button_4": (70.0, 34.0),
#     "button_5": (70.0, 34.0),
#     "button_6": (90.0, 34.0),
# }
# LABEL_PAD_Y = 6
# # =========================
# # CITY DATA
# # =========================
# cities = [
#     "SBY",
#     "JKT",
#     "MLG",
#     "SDA",
#     "BWI",
#     "JBR",
#     "BWS",
#     "PPA",
# ]
# CUSTOM_OPTION = "Custom..."

# city_combobox = None
# label_kota_terpilih_dict = {}
# state_label_aktif = {}

# combo_ctx = None
# combo_open_for = None
# selection_buttons = set()


# # =========================
# # CAMERA + ROUTING
# # =========================
# CAM_INDEX = 0

# camera_scanner = None
# camera_on = False

# routing_q = queue.Queue()
# routing_busy = False
# last_qr_text = ""

# ui_status_var = tk.StringVar(value="Status: siap")
# ui_qr_var = tk.StringVar(value="QR: -")


# def _routing_worker():
#     global routing_busy
#     while True:
#         qr_text = routing_q.get()
#         ok = True
#         err = ""
#         try:
#             routing.run_routing_for_qr(qr_text, final_delay_sec=2)
#         except Exception as e:
#             ok = False
#             err = str(e)

#         def _finish():
#             global routing_busy
#             routing_busy = False
#             ui_status_var.set(
#                 "Status: routing selesai" if ok else f"Status: routing error: {err}"
#             )

#         window.after(0, _finish)


# threading.Thread(target=_routing_worker, daemon=True).start()


# def handle_qr_in_gui(text: str):
#     global routing_busy, last_qr_text
#     t = (text or "").strip()
#     if not t:
#         return
#     if t == last_qr_text:
#         return
#     last_qr_text = t

#     ui_qr_var.set(f"QR: {t}")

#     if routing_busy:
#         ui_status_var.set("Status: routing masih berjalan (QR diabaikan)")
#         return

#     routing_busy = True
#     ui_status_var.set("Status: QR diterima, mulai routing...")
#     routing_q.put(t)


# def _on_qr_from_camera(text: str):
#     window.after(0, lambda: handle_qr_in_gui(text))


# video_img_ref = None
# latest_frame = None
# frame_lock = Lock()


# def _on_frame_from_camera(frame):
#     global latest_frame
#     with frame_lock:
#         latest_frame = frame.copy()


# def toggle_camera():
#     global camera_scanner, camera_on

#     if camera_on:
#         try:
#             if camera_scanner:
#                 camera_scanner.stop()
#         except Exception:
#             pass
#         camera_scanner = None
#         camera_on = False
#         btn_cam.config(text="Aktifkan Kamera")
#         ui_status_var.set("Status: kamera dimatikan")

#         with frame_lock:
#             global latest_frame
#             latest_frame = None

#         video_lbl.configure(image="")
#         return

#     try:
#         camera_scanner = QRScanner(
#             cam_index=CAM_INDEX,
#             on_qr=_on_qr_from_camera,
#             on_frame=_on_frame_from_camera,
#             fps_limit=20,
#             same_qr_cooldown_sec=1.0,
#         )
#         camera_scanner.start()
#         camera_on = True
#         btn_cam.config(text="Matikan Kamera")
#         ui_status_var.set("Status: kamera aktif, menunggu QR...")
#     except Exception as e:
#         camera_scanner = None
#         camera_on = False
#         messagebox.showerror("Kamera error", str(e))


# # def toogle_Lampu():


# def _refresh_video():
#     global latest_frame, video_img_ref

#     frame = None
#     with frame_lock:
#         if latest_frame is not None:
#             frame = latest_frame
#             latest_frame = None

#     if frame is not None:
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#         w = video_lbl.winfo_width()
#         h = video_lbl.winfo_height()
#         if w > 1 and h > 1:
#             rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)

#         img = Image.fromarray(rgb)
#         video_img_ref = ImageTk.PhotoImage(img)
#         video_lbl.configure(image=video_img_ref)

#     window.after(80, _refresh_video)


# # =========================
# # BOX MAPPING
# # =========================
# BUTTON_TO_BOX = {
#     "button_1": "box3.2",
#     "button_2": "box2.2",
#     "button_3": "box1.2",
#     "button_4": "box3.1",
#     "button_5": "box2.1",
#     "button_6": "box1.1",
# }
# BOX_ORDER = ["box1.1", "box2.1", "box3.1", "box3.2", "box2.2", "box1.2"]
# BOX_TO_BUTTON = {v: k for k, v in BUTTON_TO_BOX.items()}


# def _normalize_city_data(raw: dict) -> dict:
#     if not isinstance(raw, dict):
#         raw = {}

#     if any(str(k).startswith("button_") for k in raw.keys()):
#         converted = {}
#         for b, val in raw.items():
#             if b in BUTTON_TO_BOX:
#                 converted[BUTTON_TO_BOX[b]] = val
#         raw = converted

#     for k in BOX_ORDER:
#         raw.setdefault(k, "NONE")

#     return {k: raw.get(k, "NONE") for k in BOX_ORDER}


# def _read_city_file() -> dict:
#     try:
#         with CITY_FILE.open("r", encoding="utf-8") as f:
#             raw = json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         raw = {}
#     return _normalize_city_data(raw)


# def _write_city_file(data: dict) -> None:
#     data = _normalize_city_data(data)
#     with CITY_FILE.open("w", encoding="utf-8") as f:
#         json.dump(data, f, indent=4)


# def simpan_kota_ke_file(button_id, selected):
#     data = _read_city_file()
#     box_id = BUTTON_TO_BOX.get(button_id, button_id)
#     data[box_id] = selected if selected else "NONE"
#     _write_city_file(data)


# def close_combobox():
#     global city_combobox, combo_ctx, combo_open_for
#     if city_combobox and city_combobox.winfo_exists():
#         city_combobox.destroy()
#     city_combobox = None
#     combo_ctx = None
#     combo_open_for = None


# def prompt_custom_city(parent: tk.Tk) -> str | None:
#     top = tk.Toplevel(parent)
#     top.title("Custom City")
#     top.configure(bg="#B28F8F")
#     top.resizable(False, False)
#     top.transient(parent)
#     top.grab_set()

#     w, h = 320, 140
#     px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
#     py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
#     top.geometry(f"{w}x{h}+{px}+{py}")

#     tk.Label(
#         top, text="Masukkan nama kota (bebas):", bg="#B28F8F", font=("Arial", 11)
#     ).pack(pady=(12, 6))
#     entry = tk.Entry(top, font=("Arial", 12))
#     entry.pack(padx=14, fill="x")
#     entry.focus_set()

#     result = {"val": None}

#     def ok():
#         val = entry.get().strip()
#         if not val:
#             messagebox.showwarning("Input kosong", "Nama kota tidak boleh kosong.")
#             return
#         result["val"] = val.upper()
#         top.destroy()

#     def cancel():
#         result["val"] = None
#         top.destroy()

#     btns = tk.Frame(top, bg="#B28F8F")
#     btns.pack(pady=12)
#     tk.Button(btns, text="OK", width=10, command=ok).pack(side="left", padx=6)
#     tk.Button(btns, text="Batal", width=10, command=cancel).pack(side="left", padx=6)

#     top.bind("<Return>", lambda e: ok())
#     top.bind("<Escape>", lambda e: cancel())

#     parent.wait_window(top)
#     return result["val"]


# def place_city_label(button_id: str, text: str):
#     if button_id not in posisi_tombol:
#         return

#     x, y, posisi = posisi_tombol[button_id]
#     bw, bh = BTN_WH.get(button_id, (75.0, 34.0))
#     bx = x + bw / 2.0

#     if posisi == "atas":
#         by = y - LABEL_PAD_Y
#         anchor = "s"
#     else:
#         by = y + bh + LABEL_PAD_Y
#         anchor = "n"

#     lx, ly = T(bx, by)

#     lbl = label_kota_terpilih_dict.get(button_id)
#     if lbl is None or not lbl.winfo_exists():
#         lbl = tk.Label(window, bg="#B28F8F", fg="black")
#         label_kota_terpilih_dict[button_id] = lbl

#     lbl.config(text=text, font=("Arial", FS(10)))
#     lbl.place(x=lx, y=ly, anchor=anchor)


# def apply_selection(
#     button_id: str, base_x: float, base_y: float, posisi: str, selected: str
# ):
#     place_city_label(button_id, selected)
#     state_label_aktif[button_id] = True
#     simpan_kota_ke_file(button_id, selected)


# def load_kota_dari_file():
#     data_terpakai = _read_city_file()
#     for box_id, kota in data_terpakai.items():
#         button_id = BOX_TO_BUTTON.get(box_id)
#         if not button_id:
#             continue
#         if kota == "NONE":
#             state_label_aktif[button_id] = False
#             continue
#         place_city_label(button_id, kota)
#         state_label_aktif[button_id] = True


# def toggle_combobox(x, y, posisi="atas", button_id=""):
#     global city_combobox, combo_ctx, combo_open_for

#     if state_label_aktif.get(button_id, False):
#         if button_id in label_kota_terpilih_dict:
#             label_kota_terpilih_dict[button_id].destroy()
#             del label_kota_terpilih_dict[button_id]
#         state_label_aktif[button_id] = False
#         simpan_kota_ke_file(button_id, "NONE")
#         return

#     if city_combobox and city_combobox.winfo_exists() and combo_open_for == button_id:
#         close_combobox()
#         return

#     if city_combobox and city_combobox.winfo_exists():
#         close_combobox()

#     data_terpakai = _read_city_file()
#     kota_terpakai = {v for v in data_terpakai.values() if v and v != "NONE"}

#     box_id = BUTTON_TO_BOX.get(button_id)
#     if box_id and box_id in data_terpakai:
#         kota_terpakai.discard(data_terpakai[box_id])

#     kota_tersisa = [k for k in cities if k not in kota_terpakai]
#     values = [CUSTOM_OPTION] + kota_tersisa

#     city_combobox = ttk.Combobox(
#         window, values=values, font=("Arial", FS(10)), state="readonly"
#     )
#     city_combobox.set("Pilih")

#     cx, cy = T(x, y + 38)
#     city_combobox.place(x=cx, y=cy, width=max(80, int(120 * ui["s"])))

#     combo_ctx = (x, y)
#     combo_open_for = button_id

#     def on_select(event):
#         cb = event.widget
#         selected = cb.get()
#         close_combobox()

#         if selected == CUSTOM_OPTION:
#             custom = prompt_custom_city(window)
#             if not custom:
#                 return
#             if custom in kota_terpakai:
#                 messagebox.showwarning(
#                     "Duplikat", f"Kota '{custom}' sudah dipakai tombol lain."
#                 )
#                 return
#             apply_selection(button_id, x, y, posisi, custom)
#             return

#         apply_selection(button_id, x, y, posisi, selected)

#     city_combobox.bind("<<ComboboxSelected>>", on_select)


# def _close_combo_if_click_outside(event):
#     global city_combobox
#     if not (city_combobox and city_combobox.winfo_exists()):
#         return

#     w = event.widget

#     # kalau klik bukan combobox dan bukan anaknya
#     if w is not city_combobox:
#         try:
#             if (
#                 city_combobox.winfo_containing(event.x_root, event.y_root)
#                 != city_combobox
#             ):
#                 close_combobox()
#         except Exception:
#             close_combobox()


# window.bind("<Button-1>", _close_combo_if_click_outside)

# def open_i2c_config_window():
#     top = tk.Toplevel(window)
#     top.title("Config I2C & Omni")
#     top.geometry("380x400")  # Ukuran fix dari Anda
#     top.configure(bg="#B28F8F")
#     top.resizable(False, False)
#     top.transient(window)
#     top.grab_set()

#     font_lbl = ("Arial", 8, "bold")
#     bg_color = "#B28F8F"

#     # State untuk menyimpan address mana yang diklik
#     selected_addr = {"hex": None}
#     btn_refs = []  # Menyimpan referensi tombol address

#     # ==========================
#     # 1. KOTAK ABU-ABU (HASIL SCAN)
#     # ==========================
#     scan_frame = tk.Frame(top, bg="#D9D9D9", bd=0)
#     # Diset agar memiliki margin 10px di kiri dan kanan (380 - 20 = 360)
#     scan_frame.place(x=10, y=10, width=360, height=125)

#     btn_container = tk.Frame(scan_frame, bg="#D9D9D9")
#     btn_container.pack(padx=5, pady=5, fill="both", expand=True)
#     tk.Label(btn_container, text="Klik 'scan i2c' untuk cari address I2C", bg="#D9D9D9").pack(pady=35)

#     def select_address(addr_str, btn_widget):
#         for b in btn_refs:
#             b.config(bg="#E0E0E0", fg="black")
#         btn_widget.config(bg="#007BFF", fg="white")
#         selected_addr["hex"] = addr_str

#     def scan_i2c():
#         for widget in btn_container.winfo_children():
#             widget.destroy()
#         btn_refs.clear()
#         selected_addr["hex"] = None

#         try:
#             import subprocess
#             output = subprocess.check_output(["i2cdetect", "-y", "1"], universal_newlines=True)

#             found_addrs = []
#             lines = output.strip().split('\n')[1:]
#             for line in lines:
#                 parts = line.split(':')[1:]
#                 if parts:
#                     for val in parts[0].split():
#                         if val not in ('--', 'UU'):
#                             found_addrs.append(f"0x{val}")

#             if not found_addrs:
#                 tk.Label(btn_container, text="Tidak ada device I2C terdeteksi!", bg="#D9D9D9", fg="red").pack(pady=35)
#                 return

#             col, row = 0, 0
#             for addr in found_addrs:
#                 btn = tk.Button(btn_container, text=addr, bg="#E0E0E0", font=("Arial", 8, "bold"),
#                                 relief="flat", width=6)
#                 btn.grid(row=row, column=col, padx=7, pady=6)

#                 btn.config(command=lambda a=addr, b=btn: select_address(a, b))
#                 btn_refs.append(btn)

#                 col += 1
#                 if col > 4:
#                     col = 0
#                     row += 1

#         except Exception as e:
#             tk.Label(btn_container, text=f"Gagal scan:\n{e}", bg="#D9D9D9").pack(pady=10)

#     # ==========================
#     # 2. MIDDLE AREA (CMD & SEND)
#     # ==========================
#     # y dinaikkan agar muat ke tinggi 400
#     y_mid = 145
#     tk.Label(top, text="TEST KIRIM DATA I2C", bg=bg_color, font=font_lbl).place(x=15, y=y_mid)

#     # x digeser ke kiri (280) agar tidak melebihi lebar 380
#     tk.Button(top, text="scan i2c", bg="#E0E0E0", relief="flat", font=font_lbl,
#               command=scan_i2c, width=10).place(x=280, y=y_mid-3)

#     y_cmd = 185
#     tk.Label(top, text="CMD", bg=bg_color, font=font_lbl).place(x=15, y=y_cmd)

#     # Lebar CMD dikurangi sedikit (205) supaya muat
#     entry_cmd = tk.Entry(top, font=("Arial", 12), relief="flat", bg="#D9D9D9")
#     entry_cmd.place(x=60, y=y_cmd, width=205, height=25)

#     def send_data():
#         if not selected_addr["hex"]:
#             messagebox.showwarning("Peringatan", "Pilih/klik alamat I2C di kotak atas terlebih dahulu!")
#             return

#         cmd_text = entry_cmd.get().strip()
#         if not cmd_text:
#             messagebox.showwarning("Peringatan", "Masukkan CMD terlebih dahulu!")
#             return

#         try:
#             from smbus2 import SMBus, i2c_msg
#             addr_int = int(selected_addr["hex"], 16)

#             parts = cmd_text.split(',')
#             dir_val = int(parts[0].strip())
#             delay_val = int(parts[1].strip()) if len(parts) > 1 else 2

#             with SMBus(1) as bus:
#                 msg = i2c_msg.write(addr_int, [dir_val & 0xFF, delay_val & 0xFF])
#                 bus.i2c_rdwr(msg)

#             messagebox.showinfo("Sukses", f"Data [{dir_val}, {delay_val}] terkirim ke {selected_addr['hex']}")
#         except ValueError:
#             messagebox.showerror("Error", "Format CMD harus angka!\nContoh: 1\nAtau: 1, 2")
#         except Exception as e:
#             messagebox.showerror("Error", f"Gagal kirim:\n{e}")

#     # x digeser ke kiri (280)
#     tk.Button(top, text="SEND", bg="#E0E0E0", relief="flat", font=font_lbl,
#               command=send_data, width=10).place(x=280, y=y_cmd-2)

#     # ==========================
#     # 3. BOTTOM AREA (SET ADDRESS)
#     # ==========================
#     y_bot = 230
#     tk.Label(top, text="SET ADDRES OMNI & CONVEYOR", bg=bg_color, font=font_lbl).place(x=15, y=y_bot)

#     current_cfg = load_i2c_config()
#     entries = {}

#     # --- BARIS 1 ---
#     # Posisi y dinaikkan (265) dan x disesuaikan agar jadi 2 kolom yang presisi
#     tk.Label(top, text="CELL 1", bg=bg_color, font=font_lbl).place(x=15, y=265)
#     ent_c1 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
#     ent_c1.place(x=70, y=265, width=90, height=24)
#     ent_c1.insert(0, current_cfg.get("omni_1", ""))
#     entries["omni_1"] = ent_c1

#     tk.Label(top, text="CELL 2", bg=bg_color, font=font_lbl).place(x=190, y=265)
#     ent_c2 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
#     ent_c2.place(x=250, y=265, width=100, height=24)
#     ent_c2.insert(0, current_cfg.get("omni_2", ""))
#     entries["omni_2"] = ent_c2

#     # --- BARIS 2 ---
#     # Posisi y dinaikkan (305)
#     tk.Label(top, text="CELL 3", bg=bg_color, font=font_lbl).place(x=15, y=305)
#     ent_c3 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
#     ent_c3.place(x=70, y=305, width=90, height=24)
#     ent_c3.insert(0, current_cfg.get("omni_3", ""))
#     entries["omni_3"] = ent_c3

#     tk.Label(top, text="Konveyor", bg=bg_color, font=font_lbl).place(x=180, y=305)
#     ent_conv = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
#     ent_conv.place(x=250, y=305, width=100, height=24)
#     ent_conv.insert(0, current_cfg.get("conveyor", ""))
#     entries["conveyor"] = ent_conv

#     # --- TOMBOL SAVE ---
#     def save_config():
#         new_cfg = {k: ent.get().strip() for k, ent in entries.items()}
#         save_i2c_config(new_cfg)
#         messagebox.showinfo("Tersimpan", "Konfigurasi Address berhasil disimpan ke I2C.json!")

#     # Posisi y di set ke 355 (agar aman dan memiliki jarak bawah sekitar 15px dari batas window 400)
#     tk.Button(top, text="SAVE", bg="#E0E0E0", relief="flat", font=("Arial", 9, "bold"),
#               command=save_config, width=12).place(x=15, y=355)

# # =========================
# # BUILD UI (CANVAS + RIGHT PANEL)
# # =========================
# canvas = tk.Canvas(window, bg="#B28F8F", bd=0, highlightthickness=0, relief="ridge")
# canvas.place(x=0, y=0, relwidth=1, relheight=1)

# header_rect = canvas.create_rectangle(0, 0, 700, 92, fill="#A57373", outline="")
# title_text = canvas.create_text(
#     350,
#     46,
#     anchor="center",
#     text="Pemilihan Kota Paket",
#     fill="#FFFFFF",
#     # font=("Jura Regular", -32),
#     font=("DejaVu Sans", -32),
# )


# def _dummy(msg):
#     messagebox.showinfo("Info", msg)


# btn_cam = tk.Button(
#     window,
#     text="Aktifkan Kamera",
#     command=toggle_camera,
#     bg="#D9D9D9",
#     fg="black",
#     relief="flat",
#     bd=0,
# )
# btn_i2c = tk.Button(
#     window,
#     text="Config I2C Cell",
#     # command=lambda: _dummy("Buka menu config I2C (buat nanti)"),
#     command=open_i2c_config_window,
#     bg="#D9D9D9",
#     fg="black",
#     relief="flat",
#     bd=0,
# )
# btn_light = tk.Button(
#     window,
#     text="Aktifkan Cahaya",
#     command=lambda: _dummy("Lampu menyala"),
#     bg="#D9D9D9",
#     fg="black",
#     relief="flat",
#     bd=0,
# )
# btn_pwm = tk.Button(
#     window,
#     text="Adjust PWM Conv",
#     command=lambda: _dummy("Buka menu PWM (buat nanti)"),
#     bg="#D9D9D9",
#     fg="black",
#     relief="flat",
#     bd=0,
# )

# preview_frame = tk.Frame(
#     window, bg="#D9D9D9", highlightbackground="black", highlightthickness=3
# )
# video_lbl = tk.Label(preview_frame, bg="#D9D9D9")
# video_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

# status_lbl = tk.Label(window, textvariable=ui_status_var, bg="#B28F8F", fg="black")
# qr_lbl = tk.Label(window, textvariable=ui_qr_var, bg="#B28F8F", fg="black")


# # =========================
# # CANVAS ASSETS (dibuat sekali via loop)
# # =========================
# CANVAS_DEF = [
#     (BIG_FILE, BIG_BASE_CX, BIG_BASE_CY, BIG_BASE_SCALE),
#     ("image_2.png", 240.0, 420.0, 1.0),
#     ("image_3.png", -10.0, 325.0, 1.0),
#     ("image_4.png", 420.0, 420.0, 1.0),
#     ("image_5.png", 327.0, 420.0, 1.0),
#     ("image_6.png", 240.0, 200.0, 1.0),
#     ("image_7.png", 420.0, 200.0, 1.0),
#     ("image_8.png", 327.0, 200.0, 1.0),
# ]

# canvas_assets = []
# big_item = None

# for fname, cx, cy, base_scale in CANVAS_DEF:
#     img = make_tk(fname, base_scale)
#     item_id = canvas.create_image(cx, cy, image=img)
#     canvas_img_refs[item_id] = img
#     canvas_assets.append((item_id, fname, cx, cy, base_scale))
#     if fname == BIG_FILE:
#         big_item = item_id

# # pastikan big_item ketemu
# if big_item is None:
#     raise RuntimeError("BIG_FILE tidak ditemukan di CANVAS_DEF")


# # =========================
# # SELECTION BUTTONS (box)
# # =========================
# def mk_btn(fname, cmd):
#     img = make_tk(fname, 1.0)
#     b = tk.Button(
#         window,
#         image=img,
#         borderwidth=0,
#         highlightthickness=0,
#         command=cmd,
#         relief="flat",
#         bg="#B28F8F",
#         activebackground="#B28F8F",
#     )
#     btn_img_refs[b] = img
#     return b


# button_1 = mk_btn(
#     "button_1.png", lambda: toggle_combobox(270.0, 130.0, "atas", "button_1")
# )
# button_2 = mk_btn(
#     "button_2.png", lambda: toggle_combobox(360.0, 130.0, "atas", "button_2")
# )
# button_3 = mk_btn(
#     "button_3.png", lambda: toggle_combobox(440.0, 130.0, "atas", "button_3")
# )
# button_4 = mk_btn(
#     "button_4.png", lambda: toggle_combobox(270.0, 460.0, "bawah", "button_4")
# )
# button_5 = mk_btn(
#     "button_5.png", lambda: toggle_combobox(360.0, 460.0, "bawah", "button_5")
# )
# button_6 = mk_btn(
#     "button_6.png", lambda: toggle_combobox(440.0, 460.0, "bawah", "button_6")
# )

# selection_buttons.update({button_1, button_2, button_3, button_4, button_5, button_6})

# button_assets = [
#     (button_1, "button_1.png", 200.0, 130.0, 75.0, 34.0),
#     (button_2, "button_2.png", 290.0, 130.0, 75.0, 34.0),
#     (button_3, "button_3.png", 380.0, 130.0, 75.0, 34.0),
#     (button_4, "button_4.png", 200.0, 460.0, 76.0, 34.0),
#     (button_5, "button_5.png", 290.0, 460.0, 77.0, 34.0),
#     (button_6, "button_6.png", 380.0, 460.0, 76.0, 34.0),
# ]


# PANEL_SCALE_CAP = 1.20  # panel kanan jangan ikut membesar terus saat fullscreen


# def panel_metrics(s_panel: float):
#     pad = max(10, int(14 * s_panel))
#     right_pad = max(16, int(20 * s_panel))

#     btn_w = max(130, int(170 * s_panel))
#     btn_h = max(28, int(34 * s_panel))
#     gap_x = max(10, int(14 * s_panel))
#     gap_y = max(8, int(10 * s_panel))

#     panel_w = (btn_w * 2) + gap_x
#     return pad, right_pad, btn_w, btn_h, gap_x, gap_y, panel_w


# # =========================
# # LAYOUT (auto-shift konveyor mendekati panel kamera)
# # =========================
# # def compute_scale_fit(w: int, h: int) -> float:
# #     # skala ideal dari layar
# #     s0 = quantize_scale(min(w / BASE_W, h / BASE_H), 0.05)

# #     # panel kanan dibatasi supaya tidak "makan" lebar kiri saat fullscreen
# #     s_panel = min(s0, PANEL_SCALE_CAP)
# #     pad, right_pad, btn_w, btn_h, gap_x, gap_y, panel_w = panel_metrics(s_panel)

# #     reserved_right = panel_w + right_pad + pad
# #     left_area_w = max(1, w - reserved_right)

# #     # konten kiri harus muat di area kiri
# #     s_max_by_left = left_area_w / BASE_W

# #     s = min(s0, s_max_by_left)
# #     s = quantize_scale(s, 0.05)
# #     return max(0.2, s)


# def compute_scale_fit(w: int, h: int) -> float:
#     # skala berdasarkan tinggi dulu
#     s0 = min(w / BASE_W, h / BASE_H)

#     s_panel = min(s0, PANEL_SCALE_CAP)
#     pad, right_pad, btn_w, btn_h, gap_x, gap_y, panel_w = panel_metrics(s_panel)

#     reserved_right = panel_w + right_pad + pad
#     left_area_w = max(1, w - reserved_right)

#     # === BATASI BERDASARKAN LEBAR KONVEYOR SEBENARNYA ===
#     # lebar conveyor display = BIG_W * (s * BIG_BASE_SCALE)
#     # harus <= left_area_w

#     s_max_by_conveyor = left_area_w / (BIG_W * BIG_BASE_SCALE)

#     s = min(s0, s_max_by_conveyor)

#     return max(0.2, quantize_scale(s, 0.05))


# def apply_layout(w, h):
#     # s_raw = min(w / BASE_W, h / BASE_H)
#     # s = quantize_scale(s_raw, 0.05)
#     # ui["s"] = s

#     s = compute_scale_fit(w, h)
#     ui["s"] = s

#     s_panel = min(s, PANEL_SCALE_CAP)

#     header_h = max(50, int(Tinggi_Header * s))
#     canvas.coords(header_rect, 0, 0, w, header_h)
#     canvas.coords(title_text, w / 2, header_h / 2)
#     # canvas.itemconfig(title_text, font=("Jura Regular", -max(10, int(32 * s))))
#     canvas.itemconfig(title_text, font=("DejaVu Sans", -max(10, int(32 * s))))

#     content_base_h = BASE_H - Tinggi_Header
#     content_win_h = max(1, h - header_h)

#     # ===== RIGHT SIDE METRICS =====
#     pad = max(10, int(14 * s))
#     right_pad = max(16, int(20 * s))

#     btn_w = max(130, int(170 * s))
#     btn_h = max(28, int(34 * s))
#     gap_x = max(10, int(14 * s))
#     gap_y = max(8, int(10 * s))

#     x2 = w - right_pad - btn_w
#     x1 = x2 - gap_x - btn_w
#     y1 = header_h + max(14, int(18 * s))
#     y2 = y1 + btn_h + gap_y

#     panel_x = x1
#     panel_w = (btn_w * 2) + gap_x

#     # ===== LEFT AREA + AUTO SHIFT =====
#     reserved_right = panel_w + right_pad + pad
#     left_area_w = max(1, w - reserved_right)

#     # ui["px"] = max(pad, (left_area_w - BASE_W * s) / 2)
#     ui["cy0"] = header_h + (content_win_h - content_base_h * s) / 2

#     desired_gap = max(10, int(CONVEYOR_GAP_BASE * s))

#     big_disp_w = BIG_W * (s * BIG_BASE_SCALE)
#     # cur_big_right = ui["px"] + (BIG_BASE_CX * s) + (big_disp_w / 2)
#     # target_big_right = panel_x - desired_gap

#     # delta = target_big_right - cur_big_right
#     # if delta > 0:
#     #     ui["px"] = ui["px"] + delta

#     # ===== CENTER VERTIKAL DULU =====
#     # ui["cy0"] = header_h + (content_win_h - content_base_h * s) / 2

#     # # ===== HITUNG GAP =====
#     # desired_gap = max(10, int(CONVEYOR_GAP_BASE * s))

#     # # ===== HITUNG LEBAR KONVEYOR DI DISPLAY =====
#     # big_disp_w = BIG_W * (s * BIG_BASE_SCALE)

#     # ===== POSISI PX AGAR KONVEYOR SEJAJAR DENGAN FRAME =====
#     # target: right edge image_1 = panel_x - gap
#     ui["px"] = panel_x - desired_gap - (BIG_BASE_CX * s) - (big_disp_w / 2)

#     # Tambahan offset kecil supaya agak ke kanan (tweak halus)
#     ui["px"] += int(10 * s)

#     # ===== JANGAN SAMPAI KELUAR LAYAR KIRI =====
#     ui["px"] = max(pad, ui["px"])

#     # ===== UPDATE CANVAS ASSETS =====
#     for item_id, fname, cx, cy, base_scale in canvas_assets:
#         x1c, y1c = T(cx, cy)
#         canvas.coords(item_id, x1c, y1c)
#         img = make_tk(fname, s * base_scale)
#         canvas.itemconfig(item_id, image=img)
#         canvas_img_refs[item_id] = img

#     canvas.tag_lower(big_item)
#     canvas.tag_raise(header_rect)
#     canvas.tag_raise(title_text)

#     # ===== UPDATE BUTTON ASSETS =====
#     for btn, fname, bx0, by0, bw, bh in button_assets:
#         img = make_tk(fname, s)
#         btn.configure(image=img)
#         btn_img_refs[btn] = img
#         bx1p, by1p = T(bx0, by0)
#         btn.place(x=bx1p, y=by1p, width=max(1, int(bw * s)), height=max(1, int(bh * s)))

#     # update labels kota
#     for bid, lbl in list(label_kota_terpilih_dict.items()):
#         if lbl.winfo_exists():
#             place_city_label(bid, lbl.cget("text"))

#     # update combobox posisi + font
#     global city_combobox, combo_ctx
#     if city_combobox and city_combobox.winfo_exists() and combo_ctx:
#         bx0, by0 = combo_ctx
#         cxp, cyp = T(bx0, by0 + 38)
#         city_combobox.place(x=cxp, y=cyp, width=max(80, int(120 * s)))
#         city_combobox.config(font=("Arial", FS(10)))

#     # ===== PLACE RIGHT BUTTONS =====
#     fnt_btn = ("Arial", FS(10))
#     for b in (btn_cam, btn_i2c, btn_light, btn_pwm):
#         b.config(font=fnt_btn)

#     btn_cam.place(x=x1, y=y1, width=btn_w, height=btn_h)
#     btn_i2c.place(x=x2, y=y1, width=btn_w, height=btn_h)
#     btn_light.place(x=x1, y=y2, width=btn_w, height=btn_h)
#     btn_pwm.place(x=x2, y=y2, width=btn_w, height=btn_h)

#     # ===== PLACE CAMERA PANEL =====
#     panel_gap = max(14, int(18 * s))
#     panel_y = y2 + btn_h + panel_gap

#     reserve_bottom = max(38, int(46 * s))
#     max_panel_h = h - panel_y - pad - reserve_bottom
#     panel_h = max(160, min(int(300 * s), max_panel_h))

#     preview_frame.place(x=panel_x, y=panel_y, width=panel_w, height=panel_h)

#     status_lbl.config(font=("Arial", FS(10)))
#     qr_lbl.config(font=("Arial", FS(10)))
#     status_y = panel_y + panel_h + max(6, int(8 * s))
#     status_lbl.place(x=panel_x, y=status_y, anchor="nw")
#     qr_lbl.place(x=panel_x, y=status_y + max(18, int(20 * s)), anchor="nw")


# def _on_resize(event):
#     if event.widget != window:
#         return
#     if ui["job"] is not None:
#         window.after_cancel(ui["job"])
#     ui["job"] = window.after(
#         120, lambda: apply_layout(window.winfo_width(), window.winfo_height())
#     )


# def _on_close():
#     global camera_scanner
#     try:
#         if camera_scanner:
#             camera_scanner.stop()
#     except Exception:
#         pass
#     window.destroy()


# window.protocol("WM_DELETE_WINDOW", _on_close)
# window.bind("<Configure>", _on_resize)


# window.after(
#     0,
#     lambda: (
#         apply_layout(window.winfo_width(), window.winfo_height()),
#         load_kota_dari_file(),
#         _refresh_video(),
#     ),
# )

# window.mainloop()


from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import json
import threading
import queue
import cv2
from threading import Lock
import subprocess

from camera import QRScanner
import routing

# =========================
# PATHS (Raspberry Pi / Linux friendly)
# =========================
BASE_DIR = Path(__file__).resolve().parent
ASSETS_PATH = BASE_DIR / "frame0"  # <--- folder frame0 di sebelah main.py
CITY_FILE = BASE_DIR / "DataCitySetting.json"
I2C_CONFIG_FILE = BASE_DIR / "I2C.json"


def load_i2c_config() -> dict:
    try:
        with I2C_CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default jika I2C.json belum ada
        return {
            "omni_1": "0x01",
            "omni_2": "0x05",
            "omni_3": "0x08",
            "conveyor": "0x0A",
        }


def save_i2c_config(data: dict):
    with I2C_CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


window = tk.Tk()
window.title("Pemilihan Kota Paket")
window.configure(bg="#B28F8F")

ICON_PATH = relative_to_assets("Logo.png")

try:
    LANCZOS = Image.Resampling.LANCZOS
except Exception:
    LANCZOS = Image.LANCZOS

try:
    img_icon = Image.open(ICON_PATH).convert("RGBA").resize((32, 32), LANCZOS)
    icon = ImageTk.PhotoImage(img_icon)
    window.iconphoto(True, icon)
except Exception:
    pass

window_width = 1000
window_height = 500
offset_y = 17
offset_x = 8
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
center_x = int((screen_width - window_width) / 2) - offset_x
center_y = int((screen_height - window_height) / 2) - offset_y
window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
window.minsize(window_width, window_height)


# =========================
# WINDOW MODE MANAGER
# =========================
class WindowModeManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.mode = "normal"
        self._internal = False
        self.normal_geom = root.geometry()
        root.after(120, self._poll)

    def _screen_geom(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        return f"{w}x{h}+0+0"

    def enter_fullscreen_decorated(self):
        def do():
            self.mode = "fullscreen"
            self.root.state("normal")
            self.root.geometry(self._screen_geom())

        self._run_internal(do)

    def _run_internal(self, fn):
        self._internal = True
        fn()
        self.root.after(200, lambda: setattr(self, "_internal", False))

    def _poll(self):
        try:
            st = self.root.state()
        except Exception:
            return

        if st == "iconic":
            self.root.after(120, self._poll)
            return

        if not self._internal:
            if self.mode == "normal" and st == "zoomed":
                self.mode = "maximized"
            elif self.mode == "maximized" and st == "normal":
                self.enter_fullscreen_decorated()
            elif self.mode == "fullscreen" and st == "zoomed":
                self.mode = "maximized"

        self.root.after(120, self._poll)


window.update_idletasks()
# mode_mgr = WindowModeManager(window)


def back_to_normal(event=None):
    mode_mgr.mode = "normal"
    window.state("normal")
    window.geometry(mode_mgr.normal_geom)


window.bind("<Escape>", back_to_normal)


# =========================
# RESPONSIVE LAYOUT BASE
# =========================
BASE_W, BASE_H = 700, 550
Tinggi_Header = 50
ui = {"s": 1.0, "px": 0.0, "cy0": 0.0, "job": None}


def T(x, y):
    return ui["px"] + x * ui["s"], ui["cy0"] + (y - Tinggi_Header) * ui["s"]


def FS(sz):
    return max(8, int(sz * ui["s"]))


def quantize_scale(s: float, step: float = 0.05) -> float:
    return round(s / step) * step


# =========================
# IMAGE CACHE
# =========================
_pil_cache = {}
_tk_cache = {}

try:
    RESAMPLE = Image.Resampling.BILINEAR
except Exception:
    RESAMPLE = Image.BILINEAR


def get_pil(name: str) -> Image.Image:
    if name not in _pil_cache:
        _pil_cache[name] = Image.open(relative_to_assets(name)).convert("RGBA")
    return _pil_cache[name]


def make_tk(name: str, s: float) -> ImageTk.PhotoImage:
    s = round(float(s), 2)
    base = get_pil(name)
    w = max(1, int(base.width * s))
    h = max(1, int(base.height * s))
    key = (name, w, h)

    if key not in _tk_cache:
        if len(_tk_cache) > 400:
            _tk_cache.clear()
        _tk_cache[key] = ImageTk.PhotoImage(base.resize((w, h), RESAMPLE))

    return _tk_cache[key]


btn_img_refs = {}
canvas_img_refs = {}


# =========================
# BIG IMAGE (CONVEYOR)
# =========================
BIG_FILE = "image_1.png"
BIG_W, BIG_H = get_pil(BIG_FILE).size
BIG_BASE_CX = 320.0
BIG_BASE_CY = 318.0

CONVEYOR_GAP_BASE = 5

PAD = 8
safe_w = max(1.0, (2.0 * min(BIG_BASE_CX, BASE_W - BIG_BASE_CX)) - 2.0 * PAD)
safe_h = max(
    1.0, (2.0 * min(BIG_BASE_CY - Tinggi_Header, BASE_H - BIG_BASE_CY)) - 2.0 * PAD
)
BIG_BASE_SCALE = min(safe_w / BIG_W, safe_h / BIG_H)


# =========================
# BUTTON/LABEL POSITIONS (BASE)
# =========================
posisi_tombol = {
    "button_1": (200.0, 130.0, "atas"),
    "button_2": (290.0, 130.0, "atas"),
    "button_3": (370.0, 130.0, "atas"),
    "button_4": (200.0, 460.0, "bawah"),
    "button_5": (290.0, 460.0, "bawah"),
    "button_6": (370.0, 460.0, "bawah"),
}

BTN_WH = {
    "button_1": (70.0, 34.0),
    "button_2": (70.0, 34.0),
    "button_3": (90.0, 34.0),
    "button_4": (70.0, 34.0),
    "button_5": (70.0, 34.0),
    "button_6": (90.0, 34.0),
}
LABEL_PAD_Y = 6
# =========================
# CITY DATA
# =========================
cities = [
    "SBY",
    "JKT",
    "MLG",
    "SDA",
    "BWI",
    "JBR",
    "BWS",
    "PPA",
]
CUSTOM_OPTION = "Custom..."

city_combobox = None
label_kota_terpilih_dict = {}
state_label_aktif = {}

combo_ctx = None
combo_open_for = None
selection_buttons = set()


# =========================
# CAMERA + ROUTING
# =========================
CAM_INDEX = 0

camera_scanner = None
camera_on = False

routing_q = queue.Queue()
routing_busy = False
last_qr_text = ""

ui_status_var = tk.StringVar(value="Status: siap")
ui_qr_var = tk.StringVar(value="QR: -")


def _routing_worker():
    global routing_busy
    while True:
        qr_text = routing_q.get()
        ok = True
        err = ""
        try:
            routing.run_routing_for_qr(qr_text, final_delay_sec=2)
        except Exception as e:
            ok = False
            err = str(e)

        def _finish():
            global routing_busy
            routing_busy = False
            ui_status_var.set(
                "Status: routing selesai" if ok else f"Status: routing error: {err}"
            )

        window.after(0, _finish)


threading.Thread(target=_routing_worker, daemon=True).start()


def handle_qr_in_gui(text: str):
    global routing_busy, last_qr_text
    t = (text or "").strip()
    if not t:
        return
    if t == last_qr_text:
        return
    last_qr_text = t

    ui_qr_var.set(f"QR: {t}")

    if routing_busy:
        ui_status_var.set("Status: routing masih berjalan (QR diabaikan)")
        return

    routing_busy = True
    ui_status_var.set("Status: QR diterima, mulai routing...")
    routing_q.put(t)


def _on_qr_from_camera(text: str):
    window.after(0, lambda: handle_qr_in_gui(text))


video_img_ref = None
latest_frame = None
frame_lock = Lock()


def _on_frame_from_camera(frame):
    global latest_frame
    with frame_lock:
        latest_frame = frame.copy()


def toggle_camera():
    global camera_scanner, camera_on

    if camera_on:
        try:
            if camera_scanner:
                camera_scanner.stop()
        except Exception:
            pass
        camera_scanner = None
        camera_on = False
        btn_cam.config(text="Aktifkan Kamera")
        ui_status_var.set("Status: kamera dimatikan")

        with frame_lock:
            global latest_frame
            latest_frame = None

        video_lbl.configure(image="")
        return

    try:
        camera_scanner = QRScanner(
            cam_index=CAM_INDEX,
            on_qr=_on_qr_from_camera,
            on_frame=_on_frame_from_camera,
            fps_limit=20,
            same_qr_cooldown_sec=1.0,
        )
        camera_scanner.start()
        camera_on = True
        btn_cam.config(text="Matikan Kamera")
        ui_status_var.set("Status: kamera aktif, menunggu QR...")
    except Exception as e:
        camera_scanner = None
        camera_on = False
        messagebox.showerror("Kamera error", str(e))


def _refresh_video():
    global latest_frame, video_img_ref

    frame = None
    with frame_lock:
        if latest_frame is not None:
            frame = latest_frame
            latest_frame = None

    if frame is not None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        w = video_lbl.winfo_width()
        h = video_lbl.winfo_height()
        if w > 1 and h > 1:
            rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)

        img = Image.fromarray(rgb)
        video_img_ref = ImageTk.PhotoImage(img)
        video_lbl.configure(image=video_img_ref)

    window.after(80, _refresh_video)


# =========================
# BOX MAPPING
# =========================
BUTTON_TO_BOX = {
    "button_1": "box3.2",
    "button_2": "box2.2",
    "button_3": "box1.2",
    "button_4": "box3.1",
    "button_5": "box2.1",
    "button_6": "box1.1",
}
BOX_ORDER = ["box1.1", "box2.1", "box3.1", "box3.2", "box2.2", "box1.2"]
BOX_TO_BUTTON = {v: k for k, v in BUTTON_TO_BOX.items()}


def _normalize_city_data(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raw = {}

    if any(str(k).startswith("button_") for k in raw.keys()):
        converted = {}
        for b, val in raw.items():
            if b in BUTTON_TO_BOX:
                converted[BUTTON_TO_BOX[b]] = val
        raw = converted

    for k in BOX_ORDER:
        raw.setdefault(k, "NONE")

    return {k: raw.get(k, "NONE") for k in BOX_ORDER}


def _read_city_file() -> dict:
    try:
        with CITY_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    return _normalize_city_data(raw)


def _write_city_file(data: dict) -> None:
    data = _normalize_city_data(data)
    with CITY_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def simpan_kota_ke_file(button_id, selected):
    data = _read_city_file()
    box_id = BUTTON_TO_BOX.get(button_id, button_id)
    data[box_id] = selected if selected else "NONE"
    _write_city_file(data)


def close_combobox():
    global city_combobox, combo_ctx, combo_open_for
    if city_combobox and city_combobox.winfo_exists():
        city_combobox.destroy()
    city_combobox = None
    combo_ctx = None
    combo_open_for = None


def prompt_custom_city(parent: tk.Tk) -> str | None:
    top = tk.Toplevel(parent)
    top.title("Custom City")
    top.configure(bg="#B28F8F")
    top.resizable(False, False)
    top.transient(parent)
    top.grab_set()

    w, h = 320, 140
    px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    top.geometry(f"{w}x{h}+{px}+{py}")

    tk.Label(
        top, text="Masukkan nama kota (bebas):", bg="#B28F8F", font=("Arial", 11)
    ).pack(pady=(12, 6))
    entry = tk.Entry(top, font=("Arial", 12))
    entry.pack(padx=14, fill="x")
    entry.focus_set()

    result = {"val": None}

    def ok():
        val = entry.get().strip()
        if not val:
            messagebox.showwarning("Input kosong", "Nama kota tidak boleh kosong.")
            return
        result["val"] = val.upper()
        top.destroy()

    def cancel():
        result["val"] = None
        top.destroy()

    btns = tk.Frame(top, bg="#B28F8F")
    btns.pack(pady=12)
    tk.Button(btns, text="OK", width=10, command=ok).pack(side="left", padx=6)
    tk.Button(btns, text="Batal", width=10, command=cancel).pack(side="left", padx=6)

    top.bind("<Return>", lambda e: ok())
    top.bind("<Escape>", lambda e: cancel())

    parent.wait_window(top)
    return result["val"]


def place_city_label(button_id: str, text: str):
    if button_id not in posisi_tombol:
        return

    x, y, posisi = posisi_tombol[button_id]
    bw, bh = BTN_WH.get(button_id, (75.0, 34.0))
    bx = x + bw / 2.0

    if posisi == "atas":
        by = y - LABEL_PAD_Y
        anchor = "s"
    else:
        by = y + bh + LABEL_PAD_Y
        anchor = "n"

    lx, ly = T(bx, by)

    lbl = label_kota_terpilih_dict.get(button_id)
    if lbl is None or not lbl.winfo_exists():
        lbl = tk.Label(window, bg="#B28F8F", fg="black")
        label_kota_terpilih_dict[button_id] = lbl

    lbl.config(text=text, font=("Arial", FS(10)))
    lbl.place(x=lx, y=ly, anchor=anchor)


def apply_selection(
    button_id: str, base_x: float, base_y: float, posisi: str, selected: str
):
    place_city_label(button_id, selected)
    state_label_aktif[button_id] = True
    simpan_kota_ke_file(button_id, selected)


def load_kota_dari_file():
    data_terpakai = _read_city_file()
    for box_id, kota in data_terpakai.items():
        button_id = BOX_TO_BUTTON.get(box_id)
        if not button_id:
            continue
        if kota == "NONE":
            state_label_aktif[button_id] = False
            continue
        place_city_label(button_id, kota)
        state_label_aktif[button_id] = True


def toggle_combobox(x, y, posisi="atas", button_id=""):
    global city_combobox, combo_ctx, combo_open_for

    if state_label_aktif.get(button_id, False):
        if button_id in label_kota_terpilih_dict:
            label_kota_terpilih_dict[button_id].destroy()
            del label_kota_terpilih_dict[button_id]
        state_label_aktif[button_id] = False
        simpan_kota_ke_file(button_id, "NONE")
        return

    if city_combobox and city_combobox.winfo_exists() and combo_open_for == button_id:
        close_combobox()
        return

    if city_combobox and city_combobox.winfo_exists():
        close_combobox()

    data_terpakai = _read_city_file()
    kota_terpakai = {v for v in data_terpakai.values() if v and v != "NONE"}

    box_id = BUTTON_TO_BOX.get(button_id)
    if box_id and box_id in data_terpakai:
        kota_terpakai.discard(data_terpakai[box_id])

    kota_tersisa = [k for k in cities if k not in kota_terpakai]
    values = [CUSTOM_OPTION] + kota_tersisa

    city_combobox = ttk.Combobox(
        window, values=values, font=("Arial", FS(10)), state="readonly"
    )
    city_combobox.set("Pilih")

    cx, cy = T(x, y + 38)
    city_combobox.place(x=cx, y=cy, width=max(80, int(120 * ui["s"])))

    combo_ctx = (x, y)
    combo_open_for = button_id

    def on_select(event):
        cb = event.widget
        selected = cb.get()
        close_combobox()

        if selected == CUSTOM_OPTION:
            custom = prompt_custom_city(window)
            if not custom:
                return
            if custom in kota_terpakai:
                messagebox.showwarning(
                    "Duplikat", f"Kota '{custom}' sudah dipakai tombol lain."
                )
                return
            apply_selection(button_id, x, y, posisi, custom)
            return

        apply_selection(button_id, x, y, posisi, selected)

    city_combobox.bind("<<ComboboxSelected>>", on_select)


def _close_combo_if_click_outside(event):
    global city_combobox
    if not (city_combobox and city_combobox.winfo_exists()):
        return

    w = event.widget
    if w is not city_combobox:
        try:
            if (
                city_combobox.winfo_containing(event.x_root, event.y_root)
                != city_combobox
            ):
                close_combobox()
        except Exception:
            close_combobox()


window.bind("<Button-1>", _close_combo_if_click_outside)


def open_i2c_config_window():
    top = tk.Toplevel(window)
    top.title("Config I2C & Omni")
    top.geometry("380x400")  # Ukuran fix dari Anda
    top.configure(bg="#B28F8F")
    top.resizable(False, False)
    top.transient(window)
    top.grab_set()

    font_lbl = ("Arial", 8, "bold")
    bg_color = "#B28F8F"

    # State untuk menyimpan address mana yang diklik
    selected_addr = {"hex": None}
    btn_refs = []  # Menyimpan referensi tombol address

    # ==========================
    # 1. KOTAK ABU-ABU (HASIL SCAN)
    # ==========================
    scan_frame = tk.Frame(top, bg="#D9D9D9", bd=0)
    scan_frame.place(x=10, y=10, width=360, height=125)

    btn_container = tk.Frame(scan_frame, bg="#D9D9D9")
    btn_container.pack(padx=5, pady=5, fill="both", expand=True)
    tk.Label(
        btn_container, text="Klik 'scan i2c' untuk cari address I2C", bg="#D9D9D9"
    ).pack(pady=35)

    def select_address(addr_str, btn_widget):
        for b in btn_refs:
            b.config(bg="#E0E0E0", fg="black")
        btn_widget.config(bg="#007BFF", fg="white")
        selected_addr["hex"] = addr_str

    def scan_i2c():
        for widget in btn_container.winfo_children():
            widget.destroy()
        btn_refs.clear()
        selected_addr["hex"] = None

        try:
            import subprocess

            # PERBAIKAN: Menambahkan argumen "-a" untuk memindai semua alamat (0x00 - 0x7F)
            output = subprocess.check_output(
                ["i2cdetect", "-y", "-a", "1"], universal_newlines=True
            )

            found_addrs = []
            lines = output.strip().split("\n")[1:]
            for line in lines:
                parts = line.split(":")[1:]
                if parts:
                    for val in parts[0].split():
                        if val not in ("--", "UU"):
                            found_addrs.append(f"0x{val}")

            if not found_addrs:
                tk.Label(
                    btn_container,
                    text="Tidak ada device I2C terdeteksi!",
                    bg="#D9D9D9",
                    fg="red",
                ).pack(pady=35)
                return

            col, row = 0, 0

            # Jika alamat yang ditemukan sangat banyak, tombol akan otomatis mengecil
            # dan bertambah per baris agar tidak tumpah ke bawah
            max_cols = 5 if len(found_addrs) > 10 else 4
            btn_width = 5 if len(found_addrs) > 10 else 6

            for addr in found_addrs:
                btn = tk.Button(
                    btn_container,
                    text=addr,
                    bg="#E0E0E0",
                    font=("Arial", 8, "bold"),
                    relief="flat",
                    width=btn_width,
                )
                btn.grid(row=row, column=col, padx=5, pady=4)

                btn.config(command=lambda a=addr, b=btn: select_address(a, b))
                btn_refs.append(btn)

                col += 1
                if col > max_cols:
                    col = 0
                    row += 1

        except Exception as e:
            tk.Label(btn_container, text=f"Gagal scan:\n{e}", bg="#D9D9D9").pack(
                pady=10
            )

    # ==========================
    # 2. MIDDLE AREA (CMD & SEND)
    # ==========================
    y_mid = 145
    tk.Label(top, text="TEST KIRIM DATA I2C", bg=bg_color, font=font_lbl).place(
        x=15, y=y_mid
    )

    tk.Button(
        top,
        text="scan i2c",
        bg="#E0E0E0",
        relief="flat",
        font=font_lbl,
        command=scan_i2c,
        width=10,
    ).place(x=280, y=y_mid - 3)

    y_cmd = 185
    tk.Label(top, text="CMD", bg=bg_color, font=font_lbl).place(x=15, y=y_cmd)

    # Lebar CMD dikurangi dari 205 menjadi 190 untuk memberi ruang bagi tanda centang
    entry_cmd = tk.Entry(top, font=("Arial", 12), relief="flat", bg="#D9D9D9")
    entry_cmd.place(x=60, y=y_cmd, width=190, height=25)

    # Label untuk indikator sukses (default kosong)
    lbl_success = tk.Label(
        top, text="", fg="#000000", bg=bg_color, font=("Arial", 14, "bold")
    )
    lbl_success.place(x=254, y=y_cmd - 3)

    def send_data():
        if not selected_addr["hex"]:
            messagebox.showwarning(
                "Peringatan", "Pilih/klik alamat I2C di kotak atas terlebih dahulu!"
            )
            return

        cmd_text = entry_cmd.get().strip()
        if not cmd_text:
            messagebox.showwarning("Peringatan", "Masukkan CMD terlebih dahulu!")
            return

        try:
            from smbus2 import SMBus, i2c_msg

            addr_int = int(selected_addr["hex"], 16)

            byte_data = []

            # --- LOGIKA SMART PARSING DATA I2C ---
            if "," in cmd_text and all(
                part.strip().lstrip("-").isdigit() for part in cmd_text.split(",")
            ):
                byte_data = [int(part.strip()) & 0xFF for part in cmd_text.split(",")]
            elif cmd_text.lstrip("-").isdigit():
                val = int(cmd_text)
                if 0 <= val <= 255:
                    byte_data = [val]
                else:
                    byte_data = list(cmd_text.encode("utf-8"))
            else:
                byte_data = list(cmd_text.encode("utf-8"))

            # --- KIRIM DATA ---
            with SMBus(1) as bus:
                msg = i2c_msg.write(addr_int, byte_data)
                bus.i2c_rdwr(msg)

            # Tampilkan centang hijau
            lbl_success.config(text="✔")

            # Hilangkan centang setelah 2000 ms (2 detik)
            top.after(2000, lambda: lbl_success.config(text=""))

        except Exception as e:
            messagebox.showerror("Error", f"Gagal kirim:\n{e}")

    tk.Button(
        top,
        text="SEND",
        bg="#E0E0E0",
        relief="flat",
        font=font_lbl,
        command=send_data,
        width=10,
    ).place(x=280, y=y_cmd - 2)

    # ==========================
    # 3. BOTTOM AREA (SET ADDRESS)
    # ==========================
    y_bot = 230
    tk.Label(top, text="SET ADDRES OMNI & CONVEYOR", bg=bg_color, font=font_lbl).place(
        x=15, y=y_bot
    )

    current_cfg = load_i2c_config()
    entries = {}

    # --- BARIS 1 ---
    tk.Label(top, text="CELL 1", bg=bg_color, font=font_lbl).place(x=15, y=265)
    ent_c1 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
    ent_c1.place(x=70, y=265, width=90, height=24)
    ent_c1.insert(0, current_cfg.get("omni_1", ""))
    entries["omni_1"] = ent_c1

    tk.Label(top, text="CELL 2", bg=bg_color, font=font_lbl).place(x=190, y=265)
    ent_c2 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
    ent_c2.place(x=250, y=265, width=100, height=24)
    ent_c2.insert(0, current_cfg.get("omni_2", ""))
    entries["omni_2"] = ent_c2

    # --- BARIS 2 ---
    tk.Label(top, text="CELL 3", bg=bg_color, font=font_lbl).place(x=15, y=305)
    ent_c3 = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
    ent_c3.place(x=70, y=305, width=90, height=24)
    ent_c3.insert(0, current_cfg.get("omni_3", ""))
    entries["omni_3"] = ent_c3

    tk.Label(top, text="Konveyor", bg=bg_color, font=font_lbl).place(x=180, y=305)
    ent_conv = tk.Entry(top, font=("Arial", 11), relief="flat", bg="#D9D9D9")
    ent_conv.place(x=250, y=305, width=100, height=24)
    ent_conv.insert(0, current_cfg.get("conveyor", ""))
    entries["conveyor"] = ent_conv

    # --- TOMBOL SAVE ---
    def save_config():
        new_cfg = {k: ent.get().strip() for k, ent in entries.items()}
        save_i2c_config(new_cfg)
        messagebox.showinfo(
            "Tersimpan", "Konfigurasi Address berhasil disimpan ke I2C.json!"
        )

    tk.Button(
        top,
        text="SAVE",
        bg="#E0E0E0",
        relief="flat",
        font=("Arial", 9, "bold"),
        command=save_config,
        width=12,
    ).place(x=15, y=355)


# =========================
# BUILD UI (CANVAS + RIGHT PANEL)
# =========================
canvas = tk.Canvas(window, bg="#B28F8F", bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0, relwidth=1, relheight=1)

header_rect = canvas.create_rectangle(0, 0, 700, 92, fill="#A57373", outline="")
title_text = canvas.create_text(
    350,
    46,
    anchor="center",
    text="Pemilihan Kota Paket",
    fill="#FFFFFF",
    font=("DejaVu Sans", -32),
)


def _dummy(msg):
    messagebox.showinfo("Info", msg)


# =========================
# INISIALISASI TOMBOL KANAN (Hanya Kamera & I2C)
# =========================
btn_cam = tk.Button(
    window,
    text="Aktifkan Kamera",
    command=toggle_camera,
    bg="#D9D9D9",
    fg="black",
    relief="flat",
    bd=0,
)
btn_i2c = tk.Button(
    window,
    text="Config I2C Cell",
    command=open_i2c_config_window,
    bg="#D9D9D9",
    fg="black",
    relief="flat",
    bd=0,
)

preview_frame = tk.Frame(
    window, bg="#D9D9D9", highlightbackground="black", highlightthickness=3
)
video_lbl = tk.Label(preview_frame, bg="#D9D9D9")
video_lbl.place(relx=0, rely=0, relwidth=1, relheight=1)

status_lbl = tk.Label(window, textvariable=ui_status_var, bg="#B28F8F", fg="black")
qr_lbl = tk.Label(window, textvariable=ui_qr_var, bg="#B28F8F", fg="black")


# =========================
# CANVAS ASSETS
# =========================
CANVAS_DEF = [
    (BIG_FILE, BIG_BASE_CX, BIG_BASE_CY, BIG_BASE_SCALE),
    ("image_2.png", 240.0, 420.0, 1.0),
    ("image_3.png", -10.0, 325.0, 1.0),
    ("image_4.png", 420.0, 420.0, 1.0),
    ("image_5.png", 327.0, 420.0, 1.0),
    ("image_6.png", 240.0, 200.0, 1.0),
    ("image_7.png", 420.0, 200.0, 1.0),
    ("image_8.png", 327.0, 200.0, 1.0),
]

canvas_assets = []
big_item = None

for fname, cx, cy, base_scale in CANVAS_DEF:
    img = make_tk(fname, base_scale)
    item_id = canvas.create_image(cx, cy, image=img)
    canvas_img_refs[item_id] = img
    canvas_assets.append((item_id, fname, cx, cy, base_scale))
    if fname == BIG_FILE:
        big_item = item_id

if big_item is None:
    raise RuntimeError("BIG_FILE tidak ditemukan di CANVAS_DEF")


# =========================
# SELECTION BUTTONS (box)
# =========================
def mk_btn(fname, cmd):
    img = make_tk(fname, 1.0)
    b = tk.Button(
        window,
        image=img,
        borderwidth=0,
        highlightthickness=0,
        command=cmd,
        relief="flat",
        bg="#B28F8F",
        activebackground="#B28F8F",
    )
    btn_img_refs[b] = img
    return b


button_1 = mk_btn(
    "button_1.png", lambda: toggle_combobox(270.0, 130.0, "atas", "button_1")
)
button_2 = mk_btn(
    "button_2.png", lambda: toggle_combobox(360.0, 130.0, "atas", "button_2")
)
button_3 = mk_btn(
    "button_3.png", lambda: toggle_combobox(440.0, 130.0, "atas", "button_3")
)
button_4 = mk_btn(
    "button_4.png", lambda: toggle_combobox(270.0, 460.0, "bawah", "button_4")
)
button_5 = mk_btn(
    "button_5.png", lambda: toggle_combobox(360.0, 460.0, "bawah", "button_5")
)
button_6 = mk_btn(
    "button_6.png", lambda: toggle_combobox(440.0, 460.0, "bawah", "button_6")
)

selection_buttons.update({button_1, button_2, button_3, button_4, button_5, button_6})

button_assets = [
    (button_1, "button_1.png", 200.0, 130.0, 75.0, 34.0),
    (button_2, "button_2.png", 290.0, 130.0, 75.0, 34.0),
    (button_3, "button_3.png", 380.0, 130.0, 75.0, 34.0),
    (button_4, "button_4.png", 200.0, 460.0, 76.0, 34.0),
    (button_5, "button_5.png", 290.0, 460.0, 77.0, 34.0),
    (button_6, "button_6.png", 380.0, 460.0, 76.0, 34.0),
]

PANEL_SCALE_CAP = 1.20


def panel_metrics(s_panel: float):
    pad = max(10, int(14 * s_panel))
    right_pad = max(16, int(20 * s_panel))

    btn_w = max(130, int(170 * s_panel))
    btn_h = max(28, int(34 * s_panel))
    gap_x = max(10, int(14 * s_panel))
    gap_y = max(8, int(10 * s_panel))

    panel_w = (btn_w * 2) + gap_x
    return pad, right_pad, btn_w, btn_h, gap_x, gap_y, panel_w


def compute_scale_fit(w: int, h: int) -> float:
    s0 = min(w / BASE_W, h / BASE_H)
    s_panel = min(s0, PANEL_SCALE_CAP)
    pad, right_pad, btn_w, btn_h, gap_x, gap_y, panel_w = panel_metrics(s_panel)

    reserved_right = panel_w + right_pad + pad
    left_area_w = max(1, w - reserved_right)

    s_max_by_conveyor = left_area_w / (BIG_W * BIG_BASE_SCALE)
    s = min(s0, s_max_by_conveyor)
    return max(0.2, quantize_scale(s, 0.05))


def apply_layout(w, h):
    s = compute_scale_fit(w, h)
    ui["s"] = s

    s_panel = min(s, PANEL_SCALE_CAP)

    header_h = max(50, int(Tinggi_Header * s))
    canvas.coords(header_rect, 0, 0, w, header_h)
    canvas.coords(title_text, w / 2, header_h / 2)
    canvas.itemconfig(title_text, font=("DejaVu Sans", -max(10, int(32 * s))))

    content_base_h = BASE_H - Tinggi_Header
    content_win_h = max(1, h - header_h)

    # ===== RIGHT SIDE METRICS =====
    pad = max(10, int(14 * s))
    right_pad = max(16, int(20 * s))

    btn_w = max(130, int(170 * s))
    btn_h = max(28, int(34 * s))
    gap_x = max(10, int(14 * s))

    # Hanya ada 1 baris tombol sekarang
    x2 = w - right_pad - btn_w
    x1 = x2 - gap_x - btn_w
    y1 = header_h + max(14, int(18 * s))

    panel_x = x1
    panel_w = (btn_w * 2) + gap_x

    # ===== LEFT AREA + AUTO SHIFT =====
    reserved_right = panel_w + right_pad + pad
    left_area_w = max(1, w - reserved_right)

    ui["cy0"] = header_h + (content_win_h - content_base_h * s) / 2

    desired_gap = max(10, int(CONVEYOR_GAP_BASE * s))
    big_disp_w = BIG_W * (s * BIG_BASE_SCALE)
    ui["px"] = panel_x - desired_gap - (BIG_BASE_CX * s) - (big_disp_w / 2)
    ui["px"] += int(10 * s)
    ui["px"] = max(pad, ui["px"])

    for item_id, fname, cx, cy, base_scale in canvas_assets:
        x1c, y1c = T(cx, cy)
        canvas.coords(item_id, x1c, y1c)
        img = make_tk(fname, s * base_scale)
        canvas.itemconfig(item_id, image=img)
        canvas_img_refs[item_id] = img

    canvas.tag_lower(big_item)
    canvas.tag_raise(header_rect)
    canvas.tag_raise(title_text)

    for btn, fname, bx0, by0, bw, bh in button_assets:
        img = make_tk(fname, s)
        btn.configure(image=img)
        btn_img_refs[btn] = img
        bx1p, by1p = T(bx0, by0)
        btn.place(x=bx1p, y=by1p, width=max(1, int(bw * s)), height=max(1, int(bh * s)))

    for bid, lbl in list(label_kota_terpilih_dict.items()):
        if lbl.winfo_exists():
            place_city_label(bid, lbl.cget("text"))

    global city_combobox, combo_ctx
    if city_combobox and city_combobox.winfo_exists() and combo_ctx:
        bx0, by0 = combo_ctx
        cxp, cyp = T(bx0, by0 + 38)
        city_combobox.place(x=cxp, y=cyp, width=max(80, int(120 * s)))
        city_combobox.config(font=("Arial", FS(10)))

    # ===== PLACE RIGHT BUTTONS =====
    fnt_btn = ("Arial", FS(10))
    for b in (btn_cam, btn_i2c):
        b.config(font=fnt_btn)

    btn_cam.place(x=x1, y=y1, width=btn_w, height=btn_h)
    btn_i2c.place(x=x2, y=y1, width=btn_w, height=btn_h)

    # ===== PLACE CAMERA PANEL (Dibuat Mepet dengan Tombol) =====
    panel_gap = max(6, int(8 * s))  # <--- Nilai margin ini diperkecil agar mepet
    panel_y = y1 + btn_h + panel_gap

    reserve_bottom = max(38, int(46 * s))
    max_panel_h = h - panel_y - pad - reserve_bottom
    panel_h = max(160, min(int(300 * s), max_panel_h))

    preview_frame.place(x=panel_x, y=panel_y, width=panel_w, height=panel_h)

    status_lbl.config(font=("Arial", FS(10)))
    qr_lbl.config(font=("Arial", FS(10)))
    status_y = panel_y + panel_h + max(6, int(8 * s))
    status_lbl.place(x=panel_x, y=status_y, anchor="nw")
    qr_lbl.place(x=panel_x, y=status_y + max(18, int(20 * s)), anchor="nw")


def _on_resize(event):
    if event.widget != window:
        return
    if ui["job"] is not None:
        window.after_cancel(ui["job"])
    ui["job"] = window.after(
        120, lambda: apply_layout(window.winfo_width(), window.winfo_height())
    )


def _on_close():
    global camera_scanner
    try:
        if camera_scanner:
            camera_scanner.stop()
    except Exception:
        pass
    window.destroy()


window.protocol("WM_DELETE_WINDOW", _on_close)
window.bind("<Configure>", _on_resize)


window.after(
    0,
    lambda: (
        apply_layout(window.winfo_width(), window.winfo_height()),
        load_kota_dari_file(),
        _refresh_video(),
    ),
)

window.mainloop()
