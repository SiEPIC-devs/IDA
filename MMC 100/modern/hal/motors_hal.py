from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
import asyncio
import time
from dataclasses import dataclass

"""
Hardware Abstraction Layer for Multi-Axis Stage Control 

Cameron Basara, 5/29/2025

This HAL provides a clean, unified interface for controlling various motor stages
while hiding the complexity of the underlying legacy drivers.
"""

class AxisType(Enum):
    """Standardized axis types across all motor systems"""
    X = 0
    Y = 1 
    Z = 2
    ROTATION_FIBER = 3  # Fiber rotation
    ROTATION_CHIP = 4   # Chip rotation
    ALL = 5


class MotorState(Enum):
    """Motor operational states"""
    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"
    HOMING = "homing"
    STOPPED = "stopped"


@dataclass
class Position:
    """Position data with metadata"""
    theoretical: float  # Commanded position
    actual: float      # Encoder/actual position  
    units: str         # "um", "mm", "degrees"
    timestamp: float   # When reading was taken


@dataclass
class MotorConfig:
    """Motor configuration parameters"""
    max_velocity: float
    max_acceleration: float
    position_limits: tuple  # (min, max)
    units: str
    step_size_x: float
    step_size_y: float
    step_size_z: float
    step_size_fr: float
    step_size_cr: float



class MotorEventType(Enum):
    """Events that motors can emit"""
    MOVE_COMPLETE = "move_complete"
    MOVE_STARTED = "move_started"
    MOVE_STOPPED = "move_stopped"
    ERROR_OCCURRED = "error_occurred"
    LIMIT_REACHED = "limit_reached"
    HOMED = "homed"


@dataclass
class MotorEvent:
    """Motor event data"""
    axis: AxisType
    event_type: MotorEventType
    data: Dict[str, Any]
    timestamp: float


class MotorHAL(ABC):
    """
    Abstract base class defining the motor HAL interface.
    
    """
    
    def __init__(self, axis: AxisType):
        self.axis = axis
        self._event_callbacks: List[Callable[[MotorEvent], None]] = []
        self._config: Optional[MotorConfig] = None
    
    #  Init
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to a motor"""
        pass

    @abstractmethod
    async def disconnect(self) -> Optional[bool]:
        """Disconnect from a motor"""
        pass
        
    #  Core Movement Interface 
    @abstractmethod
    async def move_absolute(self, position: float, velocity: Optional[float] = None) -> bool:
        """Move to absolute position. Returns True on success."""
        pass
    
    @abstractmethod
    async def move_relative(self, distance: float, velocity: Optional[float] = None) -> bool:
        """Move relative distance. Returns True on success."""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop motor immediately. Returns True on success."""
        pass
    
    @abstractmethod
    async def emergency_stop(self) -> bool:
        """Emergency stop - fastest possible halt."""
        pass
    
    #  Status and Position 
    @abstractmethod
    async def get_position(self) -> Position:
        """Get current position with metadata."""
        pass
    
    @abstractmethod
    async def get_state(self) -> MotorState:
        """Get current motor state."""
        pass
    
    @abstractmethod
    async def is_moving(self) -> bool:
        """Quick check if motor is currently moving."""
        pass
    
    #  Configuration 
    @abstractmethod
    async def set_velocity(self, velocity: float) -> bool:
        """Set default velocity for moves."""
        pass
        
    @abstractmethod
    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration/deceleration."""
        pass
    
    @abstractmethod
    async def get_config(self) -> MotorConfig:
        """Get motor configuration."""
        pass
    
    #  Homing and Limits 
    @abstractmethod
    async def home(self, direction: int = 0) -> bool:
        """Home the axis. direction: 0=negative limit, 1=positive limit"""
        pass

    @abstractmethod
    async def home_limits(self) -> bool:
        """Home the software limits, if available. Zeros at negative limit"""
        pass
    
    @abstractmethod
    async def set_zero(self) -> bool:
        """Set current position as zero reference."""
        pass
    
    # Utility Methods 
    async def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for current move to complete."""
        start_time = time.time()
        while await self.is_moving():
            if timeout and (time.time() - start_time) > timeout:
                return False
            await asyncio.sleep(0.01)  # 10ms polling
        return True
    
    #  Event System 
    def add_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Register callback for motor events."""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Remove event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def _emit_event(self, event_type: MotorEventType, data: Dict[str, Any] = None):
        """Emit event to all registered callbacks."""
        event = MotorEvent(
            axis=self.axis,
            event_type=event_type,
            data=data or {},
            timestamp=time.time()
        )
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")

