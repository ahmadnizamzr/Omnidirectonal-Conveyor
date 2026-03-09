import smbus


class ArduinoSlave:

    def __init__(self, address=0x0A, bus_id=1):
        self.address = address
        self.bus = smbus.SMBus(bus_id)

    def read_proximity(self):
        try:
            return self.bus.read_byte(self.address)
        except Exception as e:
            print("I2C Error:", e)
            return 0
