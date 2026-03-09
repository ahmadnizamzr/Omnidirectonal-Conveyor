# auto set konfig shutter speed tinggi

import cv2
from pyzbar.pyzbar import decode
import smbus
import time
from collections import deque
import subprocess

# ======================
# SET CAMERA USING v4l2-ctl
# ======================
subprocess.call("v4l2-ctl -d /dev/video0 -c auto_exposure=1", shell=True)
subprocess.call("v4l2-ctl -d /dev/video0 -c exposure_time_absolute=30", shell=True)
subprocess.call("v4l2-ctl -d /dev/video0 -c gain=120", shell=True)

time.sleep(1)

# ======================
# I2C setup
# ======================
bus = smbus.SMBus(1)
address = 0x0A
last_proximity = 0

# ======================
# Camera setup
# ======================
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ======================
# Frame buffer
# ======================
frame_buffer = deque(maxlen=8)

print("System ready...")

while True:

    # ======================
    # kamera streaming
    # ======================
    ret, frame = cap.read()
    if not ret:
        continue

    frame_buffer.append(frame)

    # ======================
    # cek proximity dari I2C
    # ======================
    try:
        proximity = bus.read_byte(address)
    except:
        proximity = 0

    # ======================
    # trigger saat object datang
    # ======================
    if proximity == 1 and last_proximity == 0:

        print("Object detected → scanning QR")

        time.sleep(0.07)

        frames_to_scan = list(frame_buffer)
        qr_found = False

        for f in frames_to_scan:

            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)

            decoded_objects = decode(gray)

            for obj in decoded_objects:

                if obj.type == "QRCODE":

                    qr_data = obj.data.decode("utf-8")
                    print("QR Detected:", qr_data)

                    qr_found = True
                    break

            if qr_found:
                break

        if not qr_found:
            print("QR tidak terbaca")

    last_proximity = proximity

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
