# Bypass utility
Small utility to disable bootrom protection(sla and daa)

## Payloads
https://github.com/MTK-bypass/exploits_collection

## Usage on Windows
Skip steps 1-5 after first usage

1. Install [python](https://www.python.org/downloads)(select "Add Python X.X to PATH")
2. Install [libusb-win32](https://sourceforge.net/projects/libusb-win32/files/libusb-win32-releases/1.2.6.0/libusb-win32-devel-filter-1.2.6.0.exe/download)
3. Lunch filter wizard, click next
4. Connect powered off phone with volume+ button, you should see new serial device in the list. Select it and click install
5. Install pyusb, pyserial, json5 with command:
```
pip install pyusb pyserial json5
```
6. Run this command and connect your powered off phone with volume+ button, you should get "Protection disabled" at the end
```
python main.py
```
7. After that, without disconnecting phone, run SP Flash Tool


## Usage on Linux
Skip steps 1-2 after first usage
To use this you need [FireISO](https://github.com/amonet-kamakiri/fireiso/releases) or [this patch](https://github.com/amonet-kamakiri/kamakiri/blob/master/kernel.patch) for your kernel

1. Install python
2. Install pyusb, pyserial, json5 as root with command:
```
pip install pyusb pyserial json5
```
3. Run this command as root and connect your powered off phone with volume+ button, you should get "Protection disabled" at the end
```
./main.py
```
4. After that, without disconnecting phone, run SP Flash Tool in UART Connection mode


Advanced use :
usage: main.py [-h] [-c CONFIG] [-t] [-w WATCHDOG] [-u UART] [-v VAR_1] [-a PAYLOAD_ADDRESS] [-p PAYLOAD]
               [-s SERIAL_PORT] [-f] [-n]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Device config
  -t, --test            Testmode
  -w WATCHDOG, --watchdog WATCHDOG
                        Watchdog address(in hex)
  -u UART, --uart UART  UART base address(in hex)
  -v VAR_1, --var_1 VAR_1
                        var_1 value(in hex)
  -a PAYLOAD_ADDRESS, --payload_address PAYLOAD_ADDRESS
                        payload_address value(in hex)
  -p PAYLOAD, --payload PAYLOAD
                        Payload to use
  -s SERIAL_PORT, --serial_port SERIAL_PORT
                        Connect to existing serial port
  -f, --force           Force exploit on insecure device
  -n, --no_handshake    Skip handshake

## Credits
- [@chaosmaster](https://github.com/chaosmaster)
- [@xyzz](https://github.com/xyzz)
