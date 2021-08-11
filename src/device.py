from src.common import to_bytes, from_bytes
from src.logger import log
import usb
import usb.backend.libusb1
import usb.backend.libusb0
from ctypes import c_void_p, c_int
import array
import os

import time

BAUD = 115200
TIMEOUT = 1
VID = "0E8D"
PID = "0003"


class Device:
    def __init__(self, port=None):
        self.udev = None
        self.dev = None
        self.rxbuffer = array.array('B')
        self.preloader = False
        self.timeout = TIMEOUT
        self.usbdk = False
        self.libusb0 = False

        if os.name == 'nt':
            try:
                file_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..")
                try:
                    os.add_dll_directory(file_dir)
                except Exception:
                    pass
                os.environ['PATH'] = file_dir + ';' + os.environ['PATH']
            except Exception:
                pass

    def find(self, wait=False):
        if self.dev:
            raise RuntimeError("Device already found")

        try:
            self.backend = usb.backend.libusb1.get_backend(find_library=lambda x: "libusb-1.0.dll")
            if self.backend:
                try:
                    self.backend.lib.libusb_set_option.argtypes = [c_void_p, c_int]
                    self.backend.lib.libusb_set_option(self.backend.ctx, 1)  # <--- this is the magic call to enable usbdk mode
                    self.usbdk = True
                except ValueError:
                    log("Failed enabling UsbDk mode, please use 64-Bit Python and 64-Bit UsbDk")
            else:
                self.backend = usb.backend.libusb1.get_backend()
        except usb.core.USBError:
            self.backend = usb.backend.libusb1.get_backend()

        log("Waiting for device")
        if wait:
            self.udev = usb.core.find(idVendor=int(VID, 16), backend=self.backend)
            while self.udev:
                time.sleep(0.25)
                self.udev = usb.core.find(idVendor=int(VID, 16), backend=self.backend)
        self.udev = None
        while not self.udev:
            self.udev = usb.core.find(idVendor=int(VID, 16), backend=self.backend)
            if self.udev:
                break
            time.sleep(0.25)

        log("Found device = {0:04x}:{1:04x}".format(self.udev.idVendor, self.udev.idProduct))
        self.dev = self

        try:
            if self.udev.is_kernel_driver_active(0):
                self.udev.detach_kernel_driver(0)

            if self.udev.is_kernel_driver_active(1):
                self.udev.detach_kernel_driver(1)

        except (NotImplementedError, usb.core.USBError):
            pass

        try:
            self.configuration = self.udev.get_active_configuration()
        except (usb.core.USBError, NotImplementedError) as e:
            if type(e) is usb.core.USBError and e.errno == 13 or type(e) is NotImplementedError:
                log("Failed to enable libusb1, is UsbDk installed?")
                log("Falling back to libusb0 (kamakiri only)")
                self.backend = usb.backend.libusb0.get_backend()
                self.udev = usb.core.find(idVendor=int(VID, 16), backend=self.backend)
                self.libusb0 = True
            try:
                self.udev.set_configuration()
            except AttributeError:
                log("Failed to enable libusb0")
                exit(1)

        if self.udev.idProduct != int(PID, 16):
            self.preloader = True
        else:
            try:
                self.udev.set_configuration(1)
                usb.util.claim_interface(self.udev, 0)
                usb.util.claim_interface(self.udev, 1)
            except usb.core.USBError:
                pass

        cdc_if = usb.util.find_descriptor(self.udev.get_active_configuration(), bInterfaceClass=0xA)
        self.ep_in = usb.util.find_descriptor(cdc_if, custom_match=lambda x: usb.util.endpoint_direction(x.bEndpointAddress) == usb.util.ENDPOINT_IN)
        self.ep_out = usb.util.find_descriptor(cdc_if, custom_match=lambda x: usb.util.endpoint_direction(x.bEndpointAddress) == usb.util.ENDPOINT_OUT)

        try:
            self.udev.ctrl_transfer(0x21, 0x20, 0, 0, array.array('B', to_bytes(BAUD, 4 , '<') + b"\x00\x00\x08"))
        except usb.core.USBError:
            pass

        return self

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

    def close(self):
        self.dev = None
        self.rxbuffer = array.array('B')
        try:
            usb.util.release_interface(self.udev, 0)
            usb.util.release_interface(self.udev, 1)
        except Exception:
            pass
        if not self.usbdk:
            try:
                self.udev.reset()
            except Exception:
                pass
        try:
            self.udev.attach_kernel_driver(0)
        except Exception:
            pass
        try:
            self.udev.attach_kernel_driver(1)
        except Exception:
            pass
        if not self.usbdk:
            try:
                usb.util.dispose_resources(self.udev)
            except Exception:
                pass
        self.udev = None
        time.sleep(1)

    def handshake(self):
        sequence = b"\xA0\x0A\x50\x05"
        i = 0
        while i < len(sequence):
            self.write(sequence[i])
            reply = self.read(1)
            if reply and reply[0] == ~sequence[i] & 0xFF:
                i += 1
            else:
                i = 0

    def echo(self, words, size=1):
        self.write(words, size)
        self.check(from_bytes(self.read(size), size), words)

    def read(self, size=1):
        offset = 0
        data = b""
        while len(self.rxbuffer) < size:
            try:
                self.rxbuffer.extend(self.ep_in.read(self.ep_in.wMaxPacketSize, self.timeout * 1000))
            except usb.core.USBError as e:
                if e.errno == 110:
                    self.udev.reset()
                break
        if size <= len(self.rxbuffer):
            result = self.rxbuffer[:size]
            self.rxbuffer = self.rxbuffer[size:]
        else:
            result = self.rxbuffer
            self.rxbuffer = array.array('B')
        return bytes(result)

    def read32(self, addr, size=1):
        result = []

        self.echo(0xD1)
        self.echo(addr, 4)
        self.echo(size, 4)

        status = self.dev.read(2)
        if from_bytes(status, 2) > 0xff:
            raise RuntimeError("status is {}".format(status.hex()))

        for _ in range(size):
            data = from_bytes(self.dev.read(4), 4)
            result.append(data)

        status = self.dev.read(2)
        if from_bytes(status, 2) > 0xff:
            raise RuntimeError("status is {}".format(status.hex()))

        # support scalar
        if len(result) == 1:
            return result[0]
        else:
            return result

    def write(self, data, size=1):
        if type(data) != bytes:
            data = to_bytes(data, size)
        offset = 0
        while offset < len(data):
            self.ep_out.write(data[offset:][:self.ep_out.wMaxPacketSize if len(data) - offset > self.ep_out.wMaxPacketSize else len(data) - offset], self.timeout * 1000)
            offset += self.ep_out.wMaxPacketSize

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

    def cmd_da(self, direction, offset, length, data=None, check_status = True):
        self.echo(0xDA)

        self.echo(direction, 4)
        self.echo(offset, 4)
        self.echo(length, 4)

        status = self.dev.read(2)

        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        if (direction & 1) == 1:
            self.dev.write(data)
        else:
            data = self.dev.read(length)

        if check_status:
            status = self.dev.read(2)

            if from_bytes(status, 2) != 0:
                raise RuntimeError("status is {}".format(status.hex()))

        return data
