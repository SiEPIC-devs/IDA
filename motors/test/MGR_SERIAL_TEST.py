import pyvisa as visa

rm = visa.ResourceManager()
print(rm.list_resources())
inst = rm.open_resource('ASRL4::INSTR')
# inst.baudrate = 38400
# print(inst.query('*IDN?'))
rm.close()