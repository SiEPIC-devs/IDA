import pyvisa

rm = pyvisa.ResourceManager()
resources = rm.list_resources()

print("已识别的 VISA 资源：")
for res in resources:
    print(res)

serial_ports = [r for r in resources if "ASRL" in r]
gpib_devices = [r for r in resources if "GPIB" in r]

print("\n串口设备：", serial_ports)
print("GPIB 设备：", gpib_devices)
