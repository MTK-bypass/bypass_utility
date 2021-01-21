#!/bin/python3

from src.config import Config
from src.device import Device
from src.exploit import exploit
from src.logger import log

import argparse
import os

DEFAULT_CONFIG = "default_config.json5"
PAYLOAD_DIR = "payloads/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Device config")
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
        config = Config().default(hw_code)

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

        payload = open(PAYLOAD_DIR + config.payload, "rb")
        exploit(device, config.watchdog_address, config.var_0, config.var_1, payload)
        payload.close()

        log("Protection disabled")


if __name__ == "__main__":
    main()
