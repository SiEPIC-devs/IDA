from NIR.lambda_sweep import LambdaScanProtocol
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration
import pyvisa as visa
import time
def main():
    
    laser = NIRManager(config = NIRConfiguration())
    laser.connect()
    # # laser.controller._verify_slots()
    # time.sleep(1.0)
    # print("#############################")
    # Set laser source to dBm
    # GOOD:
    # laser.controller.write("SOUR0:POW:UNIT 0")
    # laser.controller.write("SENS1:CHAN1:POW:UNIT 0")
    # laser.controller.write("SENS1:CHAN2:POW:UNIT 0")

    # source_unit = laser.controller.query("SOUR0:POW:UNIT?")
    # det1_unit   = laser.controller.query("SENS1:CHAN1:POW:UNIT?")
    # det2_unit   = laser.controller.query("SENS1:CHAN2:POW:UNIT?")


        
    # print(f"Units configured - Source: {source_unit}, Det1: {det1_unit}, Det2: {det2_unit}")
    # test read channels
    # ch1, ch2 = laser.read_power()
    # print(ch1,ch2)
    wl ,c1, c2 = laser.sweep(start_nm=1545,stop_nm=1560, step_nm=0.1,laser_power_dbm=-3)
    print(wl)
    print(c1)
    print(c2)
    print(len(c1), len(c2), len(wl))

    laser.disconnect()

if __name__ == '__main__':
    main()