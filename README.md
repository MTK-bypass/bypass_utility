# Bypass utility
Small utility to disable bootrom protection(sla and daa)

## Usage
To use this you need [FireISO](https://github.com/amonet-kamakiri/fireiso/releases) or other linux with [this patch](https://github.com/amonet-kamakiri/kamakiri/blob/master/kernel.patch)

1. Run this as root  
You should get "Protection disabled" at the end  
```
./main.py -c <config file> -p <payload file>
```
2. After that, without disconnecting phone, run SP Flash Tool in UART Connection mode

## Credits
- [@chaosmaster](https://github.com/chaosmaster)
- [@xyzz](https://github.com/xyzz)
