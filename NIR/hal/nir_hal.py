from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List
import asyncio
import time
from dataclasses import dataclass
import numpy as np

"""
Laser Hardware Abstraction Layer

Made by: Cameron Basara, 2025

This HAL provides a unified interface for controlling various laser instruments
including tunable lasers and optical power detectors.
"""

# Enums

class PowerUnit(Enum):
    """Power measurement units"""
    DBM = "dBm"
    WATTS = "W"
    MW = "mW"


@dataclass
class WavelengthRange:
    """Wavelength range specification"""
    start: float  # nm
    stop: float   # nm
    units: str = "nm"

@dataclass
class PowerReading:
    """Power measurement with metadata"""
    value: float
    unit: PowerUnit
    wavelength: Optional[float] = None  # nm
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class LaserEventType(Enum):
    """Events that lasers can emit"""
    OUTPUT_ENABLED = "output_enabled"
    OUTPUT_DISABLED = "output_disabled"
    WAVELENGTH_CHANGED = "wavelength_changed"
    POWER_CHANGED = "power_changed"
    SWEEP_STARTED = "sweep_started"
    SWEEP_STOPPED = "sweep_stopped"
    SWEEP_COMPLETED = "sweep_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class LaserEvent:
    """Laser event data"""
    event_type: LaserEventType
    data: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.monotonic()


class LaserHAL(ABC):
    """
    Abstract base class defining the laser HAL interface.
    Supports both tunable laser sources and optical power detectors.
    """
    def __init__(self):
        self._event_callbacks: List[callable] = []
        self._is_connected = False

    # CONNECTION MANAGEMENT
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the laser instrument"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the laser instrument"""
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if instrument is connected"""
        return self._is_connected
    
    def configure_units(self):
        """ Configure your units """
        pass
    
######################################################################
# Laser functions 
######################################################################

    @abstractmethod
    def set_wavelength(self, wavelength: float) -> bool:
        """Set the output laser wavelength in nm"""
        pass
    
    @abstractmethod
    def get_wavelength(self) -> float:
        """Get the current output laser wavelength in nm"""
        pass
    
    @abstractmethod
    def set_power(self, power: float, unit: PowerUnit = PowerUnit.DBM) -> bool:
        """Set the output laser power"""
        pass
    
    @abstractmethod
    def get_power(self) -> Tuple[float, PowerUnit]:
        """Get the current output laser power"""
        pass
    
    @abstractmethod
    def enable_output(self, enable: bool = True) -> bool:
        """Enable or disable laser emission"""
        pass
    
    @abstractmethod
    def get_output_state(self) -> bool:
        """Get current laser output enable state"""
        pass

######################################################################
# Detector functions 
######################################################################

    @abstractmethod
    def read_power(self, channel: int = 1, mf: int = 0) -> float:
        """Read optical power from detector channel"""
        pass
    
    @abstractmethod
    def set_power_unit(self, unit: PowerUnit, channel: int = 1) -> bool:
        """Set power measurement unit for detector channel"""
        pass
    
    @abstractmethod
    def get_power_unit(self, channel: int = 1) -> PowerUnit:
        """Get power measurement unit for detector channel"""
        pass
    
    @abstractmethod
    def set_power_range(self, range_dbm: float, channel: int = 1, mf: int = 0) -> bool:
        """Set fixed power measurement range for detector channel"""
        pass
    
    @abstractmethod
    def get_power_range(self, channel: int = 1) -> float:
        """Get current power measurement range for detector channel"""
        pass
    
    @abstractmethod
    def enable_autorange(self, enable: bool = True, channel: int = 1, mf: int = 0) -> bool:
        """Enable automatic range switching for detector channel"""
        pass
    
    # DATA LOGGING 
    # @abstractmethod
    # def start_logging(self, samples: int, averaging_time: float, channel: int = 1) -> bool:
    #     """Start timed or triggered power logging"""
    #     pass
    
    # @abstractmethod
    # def stop_logging(self, channel: int = 1) -> bool:
    #     """Stop ongoing power logging"""
    #     pass
    
    # @abstractmethod
    # async def get_logged_data(self, channel: int = 1) -> List[PowerReading]:
    #     """Retrieve logged power data"""
    #     pass


######################################################################
# Sweep functions 
# Keysight devices require arming and configuring the
# Trigger as well, see nir.py in Probe_Stage for an example of
# How to do internal triggering for a continous lambda 
# Sweep
######################################################################
    def set_sweep_range_nm(self, start_nm: float, stop_nm: float) -> None:
        pass

    def set_sweep_step_nm(self, step_nm: float) -> None:
        pass
    def start_sweep(self) -> None:
        pass
    def stop_sweep(self) -> None:
        pass
    def get_sweep_state(self) -> str:
        pass
######################################################################
# Lambda scan functions
######################################################################

    def optical_sweep(
        self, start_nm: float, stop_nm: float, step_nm: float,
        laser_power_dbm: float, averaging_time_s: float = 0.02
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Implement stitching, and use configure, execute and 
        retrive for organizational purposes
        """
        pass

    def cleanup_scan(self) -> None:
        """Post scan cleanup"""
        pass
    
######################################################################
# Utility functions 
######################################################################
    async def safe_shutdown(self) -> bool:
        """Safely shutdown the laser (disable output, stop sweeps)"""
        success = True
        try:
            success &= self.stop_sweep()
            success &= self.enable_output(False)
            success &= self.disconnect()
        except Exception as e:
            print(f"Error during safe shutdown: {e}")
            success = False
        return success

    # # Event System
    # def add_event_callback(self, callback: callable):
    #     """Register callback for laser events"""
    #     self._event_callbacks.append(callback)
    
    # def remove_event_callback(self, callback: callable):
    #     """Remove event callback"""
    #     if callback in self._event_callbacks:
    #         self._event_callbacks.remove(callback)
    
    # def _emit_event(self, event_type: LaserEventType, data: Dict[str, Any] = None):
    #     """Emit event to all registered callbacks"""
    #     event = LaserEvent(
    #         event_type=event_type,
    #         data=data or {}
    #     )
    #     for callback in self._event_callbacks:
    #         try:
    #             callback(event)
    #         except Exception as e:
    #             print(f"Error in event callback: {e}")
