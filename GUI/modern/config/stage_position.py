from typing import Dict, Optional
from time import monotonic

from dataclasses import dataclass, fields
import ctypes

from modern.hal.motors_hal import AxisType

"""
Stage position memory
"""

@dataclass
class AxisPosition:
    """
    Holds a single axis's current position and homing status.
    """
    position: Optional[float]
    is_homed: bool
    timestamp: Optional[float]
    units: str = "um"

class StagePositionStruct(ctypes.Structure):
    """
    Low-level ctypes struct for ipc memory sharing.
    """
    # Max n of axis supported
    MAX_AXES = 5

    _fields_ = [
        ('timestamp', ctypes.c_double),
        ('units', ctypes.c_char * 16), # fixed size

        # Axis data
        ('positions', ctypes.c_double * MAX_AXES),
        ('is_homed', ctypes.c_bool * MAX_AXES),
    ]

    def __init__(self):
        super().__init__()
        self.timestamp = monotonic()
        self.units = b'um'

        # Init motors
        for i in range(self.MAX_AXES):
            self.positions[i] = 0.0
            self.is_homed[i] = False

class StagePosition:
    """
    High-level wrapper, easier to interract with
    """
    
    def __init__(self, shared_struct: Optional[StagePositionStruct] = None):
        if shared_struct is None:
            self._struct = StagePositionStruct()
        else:
            self._struct = shared_struct
    
    @property
    def position(self) -> Dict[AxisType, float]:
        """Get current position of homed axis as dict"""
        result = {}
        for idx, axis in enumerate(AxisType):
            if axis == AxisType.ALL:
                continue
            result[axis] = self._struct.positions[idx]
        return result

    def get_positions(self):
        positions = [float(p) for p in self._struct.positions]
        return positions
    
    def set_positions(self, axis: AxisType, value: float):
        self._struct.positions[axis.value] = value
        return self._struct.positions[axis.value]
    
    def get_homed(self):
        result = {}
        for axis in AxisType:
            if axis == AxisType.ALL:
                continue
            result[axis] = self._struct.is_homed[axis.value] 
        return result
    
    def set_homed(self, axis: AxisType):
        self._struct.is_homed[axis.value] = True
        return self._struct.is_homed[axis.value]
    
    def get(self, axis : AxisType) -> AxisPosition:
        idx = axis.value
        if idx >= self._struct.MAX_AXES:
            return AxisPosition(position=None, is_homed=False, timestamp=None)
        
        return AxisPosition(position=self._struct.positions[idx], 
                            is_homed=self._struct.is_homed[idx],
                            timestamp=monotonic())
    
    def __getitem__(self, axis: AxisType) -> AxisPosition:
        """Enable indexing: stage_pos[AxisType.X]"""
        return self.get(axis)

    @property
    def units(self) -> str:
        """Get units string."""
        return self._struct.units.decode('utf-8').rstrip('\x00')
    
    @units.setter
    def units(self, value: str):
        """Set units string."""
        encoded = value.encode('utf-8')[:15]  # Leave room for null terminator
        self._struct.units = encoded + b'\x00' * (16 - len(encoded))
    
    @property
    def timestamp(self) -> float:
        """Get last update timestamp."""
        return self._struct.timestamp
    
    def get_struct(self) -> AxisPosition:
        """Get all data, metadata from struct"""
        return {
            axis: AxisPosition(
                position=float(self._struct.positions[axis.value]),
                is_homed=bool(self._struct.is_homed[axis.value]),
                timestamp=monotonic()
            )
            for axis in AxisType
            if axis != AxisType.ALL
        }

    def update(self,
               new_positions: Optional[Dict[AxisType, float]],
               new_homed: Optional[Dict[AxisType, bool]] = None
               ) -> AxisPosition:
        """Update all positions and is_homed"""
        # Update positions
        if new_positions:
            for axis, val in new_positions.items():
                self.set_positions(axis, val)

        # Update homed
        if new_homed:
            for axis, _ in new_homed.items():
                self.set_homed(axis)

        # Refresh timestamp
        self._struct.timestamp = monotonic()

        return self.get_struct()

    def __setattr__(self, name, value):
        try:
            axis = AxisType[name.upper()]
        except KeyError:
            return super().__setattr__(name, value)
        # caught one of ['X','Y','Z','ROTATION_FIBER','ROTATION_CHIP']
        self.set_positions(axis, float(value))
        self._struct.timestamp = monotonic()
        
    @property
    def x(self) -> AxisPosition:
        return self.get(AxisType.X)
    
    @property
    def y(self) -> AxisPosition:
        return self.get(AxisType.Y)
    
    @property
    def z(self) -> AxisPosition:
        return self.get(AxisType.Z)
    
    @property
    def fr(self) -> AxisPosition:
        return self.get(AxisType.ROTATION_FIBER)
    
    @property
    def cp(self) -> AxisPosition:
        return self.get(AxisType.ROTATION_CHIP)

# sp = StagePosition()
# # print(sp.get_struct())
# print(sp.x)
# setattr(sp, "x", 11.1)
# sp.set_homed(AxisType.X)
# print(sp.x)