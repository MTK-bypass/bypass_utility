#!/bin/python3

from src.device import Device
from src.exploit import exploit
from src.logger import log

import argparse
import json5
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Device config", required=True)
    parser.add_argument("-p", "--payload", help="Payload file", required=True)
    arguments = parser.parse_args()

    if not os.path.exists(arguments.config):
        log("Config file {} doesn't exist".format(arguments.config))
        return

    if not os.path.exists(arguments.payload):
        log("Payload file {} doesn't exist".format(arguments.payload))
        return

    with open(arguments.config) as config:
        config = json5.load(config)

        hw_code = config["hw_code"]
        watchdog_address = config["watchdog_address"]
        var_0 = config["var_0"] if "var_0" in config else None
        var_1 = config["var_1"]

    device = Device().find()
    device.handshake()

    device_hw_code = device.get_hw_code()
    hw_sub_code, hw_ver, sw_ver = device.get_hw_dict()
    secure_boot, serial_link_authorization, download_agent_authorization = device.get_target_config()

    if hw_code != device_hw_code:
        log("Incorrect hw code, expected {}, found {}".format(hex(hw_code), hex(device_hw_code)))
        return

    print()
    log("Device hw code: {}".format(hex(device_hw_code)))
    log("Device hw sub code: {}".format(hex(hw_sub_code)))
    log("Device hw version: {}".format(hex(hw_ver)))
    log("Device sw version: {}".format(hex(sw_ver)))
    log("Device secure boot: {}".format(secure_boot))
    log("Device serial link authorization: {}".format(serial_link_authorization))
    log("Device download agent authorization: {}".format(download_agent_authorization))
    print()

    log("Disabling watchdog timer")
    device.write32(watchdog_address, 0x22000064)

    if serial_link_authorization or download_agent_authorization:
        log("Disabling protection")
        exploit(device, watchdog_address, var_0, var_1, arguments.payload)
        log("Protection disabled")


if __name__ == "__main__":
    main()
