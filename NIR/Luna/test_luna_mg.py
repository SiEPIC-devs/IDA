from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration

cfg = NIRConfiguration()
cfg.driver_types = 'luna_controller'
luna = NIRManager(cfg)
luna.connect()
d = luna.sweep(
    start_nm=1520,
    stop_nm=1580,
    step_nm=0.1,
    laser_power_dbm=1,
    num_scans=0)
print(d)