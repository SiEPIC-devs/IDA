import json
import struct
from multiprocessing import shared_memory
from dataclasses import dataclass, field, asdict
from typing import Dict, Tuple, Any

from modern.hal.motors_hal import AxisType

@dataclass
class StageConfiguration:
    """Stage config data class to load data to manager"""
    com_port: str = "/dev/ttyUSB0"
    baudrate: int = 38400
    timeout: float = 0.3
    velocities: Dict[AxisType, float] = field(default_factory=lambda:
        {ax:2000.0 for ax in AxisType if ax.name!="ALL"}
    ) # field dict values
    accelerations: Dict[AxisType, float] = field(default_factory=lambda:
        {ax:100.0 for ax in AxisType if ax.name!="ALL"}
    ) # field dict values
    position_limits: Dict[AxisType, Tuple[float,float]] = field(default_factory=lambda:
        {ax:(0.0,10000.0) for ax in AxisType if ax.name!="ALL"}
    ) # field dict values

    # Completion detection settings (placeholder)
    position_tolerance: float = 1.0  # um
    status_poll_interval: float = 0.05  # seconds
    move_timeout: float = 30.0  # seconds

    # factory config 
    driver_types: Dict[AxisType, str] = field(default_factory=lambda: {
        AxisType.X: "stage_control", 
        AxisType.Y: "stage_control",
        AxisType.Z: "stage_control",
        AxisType.ROTATION_FIBER: "stage_control",
        AxisType.ROTATION_CHIP: "stage_control"
    })

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts self -> JSON-safe dict, turning any AxisType keys
        into string names.
        """
        d = asdict(self)
        # rewrite the two dicts with string keys
        d["velocities"] = {ax.name: v for ax, v in self.velocities.items()}
        d["accelerations"] = {ax.name: a for ax, a in self.accelerations.items()}
        d["position_limits"] = {ax.name: tuple(lim)
                                 for ax, lim in self.position_limits.items()}
        d["driver_types"] = {ax.name: dt for ax, dt in self.driver_types.items()}
        print(d)
        return d

    # Need to convert to and from JSON from SHM
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageConfiguration":
        """
        Reconstruct from a dict (e.g. JSON-loaded). Converts string
        keys back to AxisType.
        """
        # extract stage config properties
        vel = {AxisType[name]: v for name, v in data["velocities"].items()} 
        accel = {AxisType[name]: a for name, a in data["accelerations"].items()}
        lim = {AxisType[name]: tuple(lim)
               for name, lim in data["position_limits"].items()}
        driver_types = {AxisType[name]: dt for name, dt in data["driver_types"].items()}
        
        
        return cls(
            com_port=data["com_port"],
            baudrate=data["baudrate"],
            timeout=data["timeout"],
            velocities=vel,
            accelerations=accel,
            position_limits=lim,
            driver_types=driver_types
        )

    def get_axis_attributes(self) -> Dict[AxisType, Dict[str, Any]]:
        """
        Returns all attributes for each axis in a structured format.
    
        Returns:
            Dict mapping each AxisType to a dictionary of its attributes:
            {
                AxisType.X: {
                    'velocity': float,
                    'acceleration': float, 
                    'position_limits': Tuple[float, float],
                    'driver_type': str
                },
                ...
            }
        """
        axis_attrs = {}
    
        # Get all axes that have attributes (exclude ALL)
        axes = [ax for ax in AxisType if ax.name != "ALL"]
        
        for axis in axes:
            axis_attrs[axis] = {
                'velocity': self.velocities.get(axis),
                'acceleration': self.accelerations.get(axis),
                'position_limits': self.position_limits.get(axis),
                'driver_type': self.driver_types.get(axis)
            }
        
        return axis_attrs