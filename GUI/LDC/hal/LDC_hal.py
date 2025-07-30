from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass
from time import time

class LDCEventType(Enum):
    """Events that Laser Diode can emit"""
    TEC_ON = "tec_on"
    TEC_OFF = "tec_off"
    TEMP_CHANGED = "temp_changed"
    TEMP_SETPOINT_CHANGED = "temp_setpoint_changed"
    CONFIG_CHANGED = "config_changed"
    CONNECTION_CHANGED = "connection_changed"
    ERROR = "error"

@dataclass
class LDCEvent:
    """Laser Diode event data"""
    event_type: LDCEventType
    data: Dict[str, Any]
    timestamp: float

class LdcHAL(ABC):
    """
    Abstract base class for hardware abstraction layers of LDC devices.
    
    Supports LDC & TEC control
    """
    def __init__(self):
        self.connected: bool = False
        self._event_callbacks: List[Callable[[LDCEvent], None]] = []
    
    def register_event_callback(self, event_type: LDCEventType, callback):
        """Register a callback for specific event types (deprecated - use add_event_callback)"""
        # Keep for backward compatibility but use the unified callback system
        self.add_event_callback(callback)
    
    def emit_event(self, event: LDCEvent):
        """Emit an event to registered callbacks (deprecated - use _emit_event)"""
        # Keep for backward compatibility
        self._emit_event(event.event_type, event.data)

    @abstractmethod
    def connect(self) -> bool:
        """Connect to LDC"""
        pass
   
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the LDC"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get all configuration settings for LDC / TEC"""
        pass
    
    # TEC methods
    @abstractmethod
    def tec_on(self) -> bool:
        """Turn on TEC"""
        pass
    
    @abstractmethod
    def tec_off(self) -> bool:
        """Turn off TEC"""
        pass
    
    @abstractmethod
    def tec_status(self) -> bool:
        """Return TEC status, True if on False if off"""
        pass
    
    @abstractmethod
    def get_temp(self) -> float:
        """Get current temperature"""
        pass
   
    @abstractmethod
    def set_temp(self, temperature: float) -> bool:
        """Set desired temperature"""
        pass
   
    @abstractmethod
    def set_sensor_type(self, sensor_type: str) -> bool:
        """Configure for sensor models on LDC 50x devices"""
        pass
    
    @abstractmethod
    def configure_sensor_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for whichever sensor model is configured"""
        pass

    @abstractmethod
    def configure_PID_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for PID control"""
        pass
    
    # LDC methods
    @abstractmethod
    def ldc_on(self) -> bool:
        """Turn LDC on"""
        pass
    
    @abstractmethod
    def ldc_off(self) -> bool:
        """Turn LDC off"""
        pass
    
    @abstractmethod
    def ldc_state(self) -> str:
        """Check state of LDC"""
        pass
    
    @abstractmethod
    def set_voltage_limit(self, limit: float) -> bool:
        """Set voltage limit"""
        pass
    
    @abstractmethod
    def get_voltage_limit(self) -> float:
        """Get voltage limit"""
        pass
    
    @abstractmethod
    def set_current_limit(self, limit: float) -> bool:
        """Set current limit"""
        pass
    
    @abstractmethod
    def get_current_limit(self) -> float:
        """Get current limit"""
        pass
    
    @abstractmethod
    def set_current(self, current: float) -> bool:
        """Configure current setpoints"""
        pass
    
    @abstractmethod
    def get_current(self) -> float:
        """Read current"""
        pass
    
    @abstractmethod
    def get_voltage(self) -> float:
        """Read voltage"""
        pass
    
    @abstractmethod
    def set_current_range(self, toggle: int) -> bool:
        """Set range to be either High or Low"""
        pass

    #  Event System 
    def add_event_callback(self, callback: Callable[[LDCEvent], None]):
        """Register callback for LDC events."""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[LDCEvent], None]):
        """Remove event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def _emit_event(self, event_type: LDCEventType, data: Dict[str, Any] = None):
        """Emit event to all registered callbacks."""
        event = LDCEvent(
            event_type=event_type,
            data=data or {},
            timestamp=time()
        )
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")