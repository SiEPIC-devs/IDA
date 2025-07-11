import threading, webview, signal, lab_coordinates, asyncio
from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration

configure = StageConfiguration()
stage_manager = StageManager(configure, create_shm=True)