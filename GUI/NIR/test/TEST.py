import pyvisa
import time

# Configure VISA
rm = pyvisa.ResourceManager()
instr = rm.open_resource(
    'ASRL5::INSTR',       # Change COM number as needed
    baud_rate=9600,      
    timeout=5000,
    write_termination='\n',
    read_termination=None  # Disable enforced termination
)

# Clear buffer
instr.clear()
time.sleep(0.2)

# Configure Prologix GPIB-USB
instr.write('++mode 1')         # Controller mode
time.sleep(0.1)
instr.write('++addr 20')        # Target GPIB address
time.sleep(0.1)
instr.write('++auto 1')         # Manual query mode
time.sleep(0.1)
instr.write('++eos 2')          # LF termination
time.sleep(0.1)
instr.write('++read_tmo_ms 3000')  # Timeout
time.sleep(0.1)

resp = instr.query('*IDN?')
print(resp.strip())



instr.close()
rm.close()
