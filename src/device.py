from src.common import to_bytes, from_bytes
from src.logger import log

import serial.tools.list_ports
import time

BAUD = 115200
TIMEOUT = 5
VID = "0E8D"
PID = "0003"


class Device:
    def __init__(self, port=None):
        self.dev = None
        self.preloader = False
        if port:
            self.dev = serial.Serial(port, BAUD, timeout=TIMEOUT)

    def find(self):
        if self.dev:
            raise RuntimeError("Device already found")

        log("Waiting for device")

        old = self.serial_ports()
        while True:
            new = self.serial_ports()

            # port added
            if new > old:
                port = (new - old).pop()
                break
            # port removed
            elif old > new:
                old = new

            time.sleep(0.25)

        log("Found port = {}".format(port.device))

        if not PID in port.hwid:
            self.preloader = True

        self.dev = serial.Serial(port.device, BAUD, timeout=TIMEOUT)

        return self

    @staticmethod
    def serial_ports():
        """ Lists available serial ports
            :returns:
                A set containing the serial ports available on the system
        """

        result = set()
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            if hasattr(port, "hwid"):
                port_hwid = port.hwid
                port_device = port.device
            else:
                port_hwid = port[2]
                port_device = port[0]
            if VID in port_hwid:
                try:
                    s = serial.Serial(port_device, timeout=TIMEOUT)
                    s.close()
                    result.add(port)
                except (OSError, serial.SerialException):
                    pass

        return result

    @staticmethod
    def check(test, gold):
        if test != gold:
            if type(test) == bytes:
                test = "0x" + test.hex()
            else:
                test = hex(test)

            if type(gold) == bytes:
                gold = "0x" + gold.hex()
            else:
                gold = hex(gold)

            raise RuntimeError("Unexpected output, expected {} got {}".format(gold, test))

    def handshake(self):
        while True:
            self.write(0xA0)
            if self.read(1) == to_bytes(0x5F):
                self.dev.flushInput()
                self.dev.flushOutput()
                break
            self.dev.flushInput()
            self.dev.flushOutput()

        #self.write(0xA0)
        #self.check(self.read(1), to_bytes(0x5F))

        self.write(0x0A)
        self.check(self.read(1), to_bytes(0xF5))

        self.write(0x50)
        self.check(self.read(1), to_bytes(0xAF))

        self.write(0x05)
        self.check(self.read(1), to_bytes(0xFA))

    def echo(self, words, size=1):
        self.write(words, size)
        self.check(from_bytes(self.read(size), size), words)

    def read(self, size=1):
        return self.dev.read(size)

    def read32(self, addr, size=1):
        result = []

        self.echo(0xD1)
        self.echo(addr, 4)
        self.echo(size, 4)

        self.check(self.dev.read(2), to_bytes(0, 2))  # arg check

        for _ in range(size):
            data = from_bytes(self.dev.read(4), 4)
            result.append(data)

        self.check(self.dev.read(2), to_bytes(0, 2))  # status

        # support scalar
        if len(result) == 1:
            return result[0]
        else:
            return result

    def write(self, data, size=1):
        if type(data) != bytes:
            data = to_bytes(data, size)

        self.dev.write(data)

    def write32(self, addr, words, check_status=True):
        # support scalar
        if not isinstance(words, list):
            words = [words]

        self.echo(0xD4)
        self.echo(addr, 4)
        self.echo(len(words), 4)

        self.check(self.dev.read(2), to_bytes(1, 2))  # arg check

        for word in words:
            self.echo(word, 4)

        if check_status:
            self.check(self.dev.read(2), to_bytes(1, 2))  # status

    def get_target_config(self):
        self.echo(0xD8)

        target_config = self.dev.read(4)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        target_config = from_bytes(target_config, 4)

        secure_boot = target_config & 1
        serial_link_authorization = target_config & 2
        download_agent_authorization = target_config & 4

        # noinspection PyCallByClass
        return bool(secure_boot), bool(serial_link_authorization), bool(download_agent_authorization)

    def get_hw_code(self):
        self.echo(0xFD)

        hw_code = self.dev.read(2)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        return from_bytes(hw_code, 2)

    def get_hw_dict(self):
        self.echo(0xFC)

        hw_sub_code = self.dev.read(2)
        hw_ver = self.dev.read(2)
        sw_ver = self.dev.read(2)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        return from_bytes(hw_sub_code, 2), from_bytes(hw_ver, 2), from_bytes(sw_ver, 2)

    def send_da(self, da_address, da_len, sig_len, da):
        self.echo(0xD7)

        self.echo(da_address, 4)
        self.echo(da_len, 4)
        self.echo(sig_len, 4)

        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        self.dev.write(da)

        checksum = self.dev.read(2)
        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        return from_bytes(checksum, 2)

    def jump_da(self, da_address):
        self.echo(0xD5)

        self.echo(da_address, 4)

        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))
