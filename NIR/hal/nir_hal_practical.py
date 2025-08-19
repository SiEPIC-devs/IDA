from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List
import asyncio
import time
from dataclasses import dataclass

"""
Practical Laser Hardware Abstraction Layer

Cameron Basara, 2025

This HAL provides a unified interface for controlling various laser instruments
with async only where it provides genuine benefit.
"""

# Enums
class LaserState(Enum):
    """Laser operational states"""
    IDLE = "idle"
    SWEEPING = "sweeping" 
    ERROR = "error"
    WARMING_UP = "warming_up"
    READY = "ready"


class SweepState(Enum):
    """Sweep operational states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


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
class SweepConfig:
    """Sweep configuration parameters"""
    range: WavelengthRange
    speed: float  # nm/s
    step_size: Optional[float] = None  # nm (for stepped sweeps)
    cycles: int = 1
    bidirectional: bool = False


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


class LaserHALPractical(ABC):
    """
    Practical laser HAL interface - async only where beneficial
    """
    def __init__(self, instrument_id: str = None):
        self.instrument_id = instrument_id
        self._event_callbacks: List[callable] = []
        self._is_connected = False

    # CONNECTION MANAGEMENT - Sync since it's setup
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
    
    # LASER SOURCE - Sync for fast operations
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

    # SWEEP CONTROL - Mixed: config is sync, long operations are async
    @abstractmethod
    def set_sweep_range(self, start_nm: float, stop_nm: float) -> bool:
        """Set start/stop wavelength range for sweep"""
        pass
    
    @abstractmethod
    def get_sweep_range(self) -> WavelengthRange:
        """Get configured sweep range"""
        pass
    
    @abstractmethod
    def set_sweep_speed(self, speed: float) -> bool:
        """Set wavelength sweep speed in nm/s"""
        pass
    
    @abstractmethod
    def get_sweep_speed(self) -> float:
        """Get current sweep speed in nm/s"""
        pass

    @abstractmethod
    def get_sweep_state(self) -> SweepState:
        """Get current sweep state"""
        pass
    
    # ASYNC sweep operations - these take time
    @abstractmethod
    async def start_sweep(self) -> bool:
        """Start a wavelength sweep - async because it takes time"""
        pass
    
    @abstractmethod
    def stop_sweep(self) -> bool:
        """Stop a wavelength sweep - sync because it's immediate"""
        pass

    # DETECTORS - Sync for single readings
    @abstractmethod
    def read_power(self, channel: int = 1) -> PowerReading:
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
    def set_power_range(self, range_dbm: float, channel: int = 1) -> bool:
        """Set fixed power measurement range for detector channel"""
        pass
    
    @abstractmethod
    def get_power_range(self, channel: int = 1) -> float:
        """Get current power measurement range for detector channel"""
        pass
    
    @abstractmethod
    def enable_autorange(self, enable: bool = True, channel: int = 1) -> bool:
        """Enable automatic range switching for detector channel"""
        pass
    
    # DATA LOGGING - Async for large datasets
    @abstractmethod
    def start_logging(self, samples: int, averaging_time: float, channel: int = 1) -> bool:
        """Start timed or triggered power logging"""
        pass
    
    @abstractmethod
    def stop_logging(self, channel: int = 1) -> bool:
        """Stop ongoing power logging"""
        pass
    
    @abstractmethod
    async def get_logged_data(self, channel: int = 1) -> List[PowerReading]:
        """Retrieve logged power data - async because large datasets take time"""
        pass

    # STATUS AND CONFIG - Sync
    @abstractmethod
    def get_laser_state(self) -> LaserState:
        """Get current laser operational state"""
        pass
    
    @abstractmethod
    def get_wavelength_limits(self) -> Tuple[float, float]:
        """Get minimum and maximum wavelength limits in nm"""
        pass
    
    @abstractmethod
    def get_power_limits(self) -> Tuple[float, float]:
        """Get minimum and maximum power limits"""
        pass

    # ADVANCED SWEEP METHODS
    def configure_sweep(self, config: SweepConfig) -> bool:
        """Configure sweep with comprehensive params"""
        success = True
        success &= self.set_sweep_range(config.range.start, config.range.stop)
        success &= self.set_sweep_speed(config.speed)
        return success
    
    def set_sweep_state(self, enable: bool) -> bool:
        """Enable/disable sweep - sync wrapper"""
        if enable:
            # Note: This returns a coroutine that needs to be awaited
            # Users should call start_sweep() directly for async operation
            return False  # Cannot start async operation from sync method
        else:
            return self.stop_sweep()

    async def wait_for_sweep_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for current sweep to complete"""
        start_time = time.monotonic()
        while True:
            state = self.get_sweep_state()
            if state in [SweepState.STOPPED, SweepState.COMPLETED]:
                return True
            if timeout and (time.monotonic() - start_time) > timeout:
                return False
            await asyncio.sleep(0.05)  # 50ms polling
    
    # Utility Methods
    def safe_shutdown(self) -> bool:
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

    # Event System
    def add_event_callback(self, callback: callable):
        """Register callback for laser events"""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: callable):
        """Remove event callback"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def _emit_event(self, event_type: LaserEventType, data: Dict[str, Any] = None):
        """Emit event to all registered callbacks"""
        event = LaserEvent(
            event_type=event_type,
            data=data or {}
        )
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")