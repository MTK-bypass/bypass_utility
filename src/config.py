import json5


class Config:
    watchdog_address: int = 0x10007000
    uart_base: int = 0x11002000
    payload_address: int = 0x100A00
    var_0: int = None
    var_1: int = 0xA
    payload: str
    crash_method: int = 0

    def default(self, hw_code):
        config = open("default_config.json5")
        self.from_file(config, hw_code)
        config.close()

        return self

    def from_file(self, config, hw_code):
        hw_code = hex(hw_code)

        config = json5.load(config)

        if hw_code in config:
            self.from_dict(config[hw_code])
        else:
            raise NotImplementedError("Can't find {} hw_code in config".format(hw_code))

        return self

    def from_dict(self, entry):
        if "watchdog_address" in entry:
            self.watchdog_address = entry["watchdog_address"]

        if "uart_base" in entry:
            self.uart_base = entry["uart_base"]

        if "payload_address" in entry:
            self.payload_address = entry["payload_address"]

        if "var_0" in entry:
            self.var_0 = entry["var_0"]

        if "var_1" in entry:
            self.var_1 = entry["var_1"]

        if "crash_method" in entry:
            self.crash_method = entry["crash_method"]

        self.payload = entry["payload"]

        return self
