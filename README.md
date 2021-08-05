# Bypass utility
Small utility to disable bootrom protection(sla and daa)

## Payloads
https://github.com/MTK-bypass/exploits_collection

## Usage on Windows
Skip steps 1-3 after first usage

1. Install [python (64-bit)](https://www.python.org/downloads)(select "Add Python X.X to PATH")
2. Install [UsbDk (64-bit)](https://github.com/daynix/UsbDk/releases)
3. Install pyusb, json5 with command:
```
pip install pyusb json5
```
4. Run this command and connect your powered off phone with volume+ button, you should get "Protection disabled" at the end
```
python main.py
```
5. After that, without disconnecting phone, run SP Flash Tool


## Usage on Linux
Skip steps 1-2 after first usage
To use kamakiri you need [FireISO](https://github.com/amonet-kamakiri/fireiso/releases) or [this patch](https://github.com/amonet-kamakiri/kamakiri/blob/master/kernel.patch) for your kernel

Prebuilt kernels for various distros are available [here](https://github.com/amonet-kamakiri/prebuilt-kernels)

1. Install python
2. Install pyusb, json5 as root with command:
```
pip install pyusb json5
```
3. Run this command as root and connect your powered off phone with volume+ button, you should get "Protection disabled" at the end
```
./main.py
```
4. After that, without disconnecting phone, run SP Flash Tool in UART Connection mode

## Credits
- [@chaosmaster](https://github.com/chaosmaster)
- [@xyzz](https://github.com/xyzz)
