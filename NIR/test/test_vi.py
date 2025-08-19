from NIR.lambda_sweep import LambdaScanProtocol
from NIR.nir_controller import Agilent8163Controller
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration

def main():
    laser = NIRManager(config = NIRConfiguration())
    laser.connect()
    wl ,c1, c2 = laser.sweep(start_nm=1545,stop_nm=1560, step_nm=0.1,laser_power_dbm=-3)
    print(wl)
    print(c1)
    print(c2)
    print(len(c1), len(c2), len(wl))

    laser.disconnect()

if __name__ == '__main__':
    main()