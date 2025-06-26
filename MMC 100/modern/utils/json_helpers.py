import json
from dataclasses import asdict
from typing import Dict, Tuple

from modern.hal.motors_hal import AxisType
from modern.config.pstage_configuration import StageConfiguration

def save_config(cfg: StageConfiguration, path: str) -> None:
    """
    Save a config in json to a specific path
    """
