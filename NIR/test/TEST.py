import pyvisa
import time

rm = pyvisa.ResourceManager()
prologix = rm.open_resource("ASRL5::INSTR", 
                            baud_rate=9600,
                            timeout=5000,
                            read_termination='\n',
                            write_termination='\n')

# Configure Prologix
prologix.write('++mode 1')  # Controller mode
prologix.write(f'++addr {20}')  # Set GPIB address
prologix.write('++auto 0')  # IMPORTANT: Disable auto-read
prologix.write('++eos 2')  # Append LF
prologix.write('++eoi 1')  # Assert EOF
prologix.write('*IDN?')
print(prologix.query("*IDN?"))
prologix.close()
time.sleep(0.5)

# For Prologix, use GPIB address format for the DLL
# visa_address = f"GPIB0::{20}::INSTR"
# print(visa_address)

# instr = rm.open_resource(visa_address)

# instr.query("*IDN?")

# instr.close()
rm.close()
