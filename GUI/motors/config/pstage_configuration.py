from dataclasses import dataclass, field
from typing import Dict, Tuple
from motors.hal.motors_hal import AxisType

@dataclass
class StageConfiguration():
    """
    Configuration parameters for the stage, this will later be altered to be passed through the GUI
    """
    # Communication settings
    com_port: str = '/dev/ttyUSB0'
    baudrate: int = 38400
    timeout: float = 0.3
    
    # Motion parameters (per axis)
    velocities: Dict[AxisType, float] = field(default_factory=lambda: {
        AxisType.X: 2000.0, # From zero xyz
        AxisType.Y: 2000.0,
        AxisType.Z: 2000.0,
        AxisType.ROTATION_FIBER: 1000.0, # default : 100.0
        AxisType.ROTATION_CHIP: 100.0 
    })
    
    accelerations: Dict[AxisType, float] = field(default_factory=lambda: {
        AxisType.X: 100.0, # No Idea
        AxisType.Y: 100.0,
        AxisType.Z: 100.0,
        AxisType.ROTATION_FIBER: 500.0,
        AxisType.ROTATION_CHIP: 500.0
    })
    
    position_limits: Dict[AxisType, Tuple[float, float]] = field(default_factory=lambda: {
        AxisType.X: (-24940.0, 20000.0), # From zero_xyz, exp shows (0.0, 30406.57) 
        AxisType.Y: (-30400.0, 20000.0), # (0.0, 30441.85)
        AxisType.Z: (-11100.0, 20000.0), # (0.0, 10922.302)
        AxisType.ROTATION_FIBER: (-180.0, 180.0), # (0.0, 13108.784)
        AxisType.ROTATION_CHIP: (-180.0, 180.0) # (0.0, 3.6)
    })

    # Completion detection settings
    position_tolerance: float = 1.0  # um
    status_poll_interval: float = 0.05  # seconds
    move_timeout: float = 30.0  # seconds

    # Intial position settings TODO: connect other features into a big data class, for laser tec etc.
    # x_pos: Dict[AxisType, float] = {AxisType.X: position_limits[AxisType.X][1] / 2} # start pt in um PLACEHOLDER 
    # y_pos: Dict[AxisType, float] = {AxisType.Y: position_limits[AxisType.Y][1] / 2} # um
    # z_pos: Dict[AxisType, float] = {AxisType.Z: position_limits[AxisType.Z][1] * (2/3)} # um
    # chip_angle: Dict[AxisType, float] = {AxisType.ROTATION_FIBER: 1.8} # from 0.0 - 3.6?
    # fiber_angle: Dict[AxisType, float] = {AxisType.ROTATION_FIBER: 8.0} # degrees should be mapped to 0-90 inverted so 90 degrees corresponds to 0 endpt

    # factory config 
    driver_types: Dict[AxisType, str] = field(default_factory=lambda: {
        AxisType.X: "stage_control", 
        AxisType.Y: "stage_control",
        AxisType.Z: "stage_control",
        AxisType.ROTATION_FIBER: "stage_control",
        AxisType.ROTATION_CHIP: "stage_control"
    })