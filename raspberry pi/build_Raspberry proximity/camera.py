import time
import threading
import cv2
import subprocess
from collections import deque
from pyzbar.pyzbar import decode, ZBarSymbol


class QRScanner:

    def __init__(
        self,
        cam_index: int = 0,
        on_qr=None,
        on_frame=None,
        fps_limit: int = 30,
        same_qr_cooldown_sec: float = 1.0,
        show_preview: bool = False,
        window_name: str = "Camera QR",
    ):
        self.cam_index = cam_index
        self.on_qr = on_qr
        self.on_frame = on_frame
        self.fps_limit = max(1, int(fps_limit))
        self.same_qr_cooldown_sec = float(same_qr_cooldown_sec)

        self._thr = None
        self._stop = threading.Event()
        self._running = False

        self._last_text = None
        self._last_time = 0.0

        # buffer frame
        self.frame_buffer = deque(maxlen=2)

        # trigger capture
        self.trigger_time = None
        self.waiting_capture = False
        self.capture_delay = 0.3

    def is_running(self):
        return self._running and self._thr and self._thr.is_alive()

    def start(self):

        # ======================
        # SET CAMERA (shutter cepat)
        # ======================
        subprocess.call(
            f"v4l2-ctl -d /dev/video{self.cam_index} -c auto_exposure=1", shell=True
        )
        subprocess.call(
            f"v4l2-ctl -d /dev/video{self.cam_index} -c exposure_time_absolute=30",
            shell=True,
        )
        subprocess.call(
            f"v4l2-ctl -d /dev/video{self.cam_index} -c gain=120", shell=True
        )

        time.sleep(1)

        if self.is_running():
            return

        self._stop.clear()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()
        if self._thr:
            self._thr.join(timeout=2.0)

    def trigger_scan(self):
        """dipanggil dari main.py saat proximity detect"""
        self.trigger_time = time.time()
        self.waiting_capture = True

    def _loop(self):

        self._running = True

        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_V4L2)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            self._running = False
            return

        min_dt = 1.0 / self.fps_limit

        try:
            while not self._stop.is_set():

                t0 = time.time()

                ret, frame = cap.read()
                if not ret:
                    continue

                # kirim frame ke GUI
                if self.on_frame:
                    self.on_frame(frame)

                # simpan ke buffer
                self.frame_buffer.append(frame)

                # ======================
                # scan setelah delay
                # ======================
                if (
                    self.waiting_capture
                    and (time.time() - self.trigger_time) > self.capture_delay
                ):

                    frames_to_scan = list(self.frame_buffer)
                    qr_found = False

                    for f in frames_to_scan:

                        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
                        decoded = decode(gray, symbols=[ZBarSymbol.QRCODE])

                        for obj in decoded:

                            text = obj.data.decode("utf-8").strip()

                            now = time.time()

                            if text and (
                                text != self._last_text
                                or (now - self._last_time) > self.same_qr_cooldown_sec
                            ):

                                self._last_text = text
                                self._last_time = now

                                if self.on_qr:
                                    self.on_qr(text)

                                qr_found = True
                                break

                        if qr_found:
                            break

                    self.waiting_capture = False

                dt = time.time() - t0
                if dt < min_dt:
                    time.sleep(min_dt - dt)

        finally:
            cap.release()
            self._running = False
