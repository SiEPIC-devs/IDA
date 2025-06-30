from modern.stage_manager import StageManager
from modern.config.stage_config import StageConfiguration
from multiprocessing import Process
from time import sleep, monotonic
from modern.config.stage_position import *
from modern.config.stage_config import *
from modern.utils.shared_memory import *
from modern.hal.motors_hal import AxisType

if __name__ == '__main__':
    configure = StageConfiguration()
    stage_manager = StageManager(configure, create_shm=True)