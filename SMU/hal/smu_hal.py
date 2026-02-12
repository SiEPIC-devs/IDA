from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from time import monotonic
"""
Source Measurement Unit (SMU) Hardware abstraction layer base class
first iteration created based on the Keithley 2x00B series 
                                     -- 2600B, 2400B

Cameron Basara, 2025

"""

class SMUEventType(Enum):
    """SMU Events"""
    SMU_ON = "smu_on"
    SMU_OFF = "smu_off"
    IV_SWEEP = "iv_sweep"
    CONFIG_CHANGED = "config_changed"
    ERROR = "error"

@dataclass
class SMUEvent:
    """SMU event data"""
    event_type: SMUEventType
    data: Dict[str, Any]
    timestamp: float

class SMUHal(ABC):
    """
    Abstract base class for SMUs
    """
    def __init__(self):
        self.connected: bool = False
        self._event_callbacks: List[Callable[[SMUEvent], None]] = []
    
    # --- Initialization ---
    @abstractmethod
    def connect(self) -> bool:
        """Connect to an instance of SMU"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from an instance of SMU"""
        pass

    @abstractmethod
    def get_config(self) -> Dict:
        """
        Get all configuration information from the SMU
        This includes all the getters information stored
        in the configuration file
        """
        pass

    ####################################################
    #  Configuration 
    ####################################################
    # --- Getters ---
    @abstractmethod
    def get_current(self) -> Dict:
        """Get current from all channels"""
        pass

    @abstractmethod
    def get_current_limits(self) -> Dict:
        """Get current limits from all channels"""
        pass

    @abstractmethod
    def get_voltage(self) -> Dict:
        """Get voltage from all channels"""
        pass
    
    @abstractmethod
    def get_voltage_limits(self) -> Dict:
        """Get voltage limits from all channels"""
        pass

    @abstractmethod
    def get_resistance(self) -> Dict:
        """Get resistance from all channels"""
        pass
        
    @abstractmethod
    def get_power_limits(self) -> Dict:
        """Get power limits for all channels"""
        pass

    @abstractmethod
    def get_state(self) -> Dict:
        """Return states of SMUs for all channels"""
        pass

    # --- Setters --- 
    @abstractmethod
    def set_source_mode(self, mode: str, channel: str) -> bool:
        """Set source mode to V/I for a selected channel"""
        pass

    @abstractmethod
    def set_current(self, val: float, channel: str) -> bool:
        """Set current for selected channel"""
        pass
    
    @abstractmethod
    def set_current_limit(self, lim: float, channel: str) -> bool:
        """Set current limit for a selected channel"""
        pass

    @abstractmethod
    def set_voltage(self, val: float, channel: str) -> bool:
        """Set voltage for selected channel"""
        pass
    
    @abstractmethod
    def set_voltage_limit(self, lim: float, channel: str) -> bool:
        """Set voltage limit for a selected channel"""
        pass

    @abstractmethod
    def set_power_limit(self, lim: float, channel: str) -> bool:
        """Set power limit for a selected channel"""
        pass

    # --- Functional Methods ---
    @abstractmethod
    def output_on(self, channel: str) -> bool:
        """Turn a selected channel on"""
        pass
    
    @abstractmethod
    def output_off(self, channel: str) -> bool:
        """Turn a selected channel off"""
        pass

    @abstractmethod
    def output_level(self, output: float, channel: str) -> bool:
        """
        Set output level for a selected channel in SI units
        Intended for both current and voltage, ie for when
        whichever source_mode is set to
        """
        pass

    @abstractmethod
    def iv_sweep(self,
                 start: float,
                 stop: float,
                 step: float,
                 channel: List[str],
                 type: str  # Literal["V", "I"] or something
            ) -> Dict:
        """
        Current vs Voltage sweep, with some
        type representing the independant var
        in the sweep.

            :param start[float]: Minimum value of ind var during sweep
            :param stop[float]: Maximum value of ind var during sweep
            :param step[float]: Step size / Resolution of device
            :param channel[List]: List of channels that are swept
            :param type[str]: Representing ind. var ("voltage" or "current")

        returns Dict containing IV sweep results and hyperparams
                {V: np.ndarray, I: np.ndarray, t:np.ndarray,
                 Resolution(step_size): float, ...}    
        """
        # Could assert
        # type == "current" or "voltage"
        pass
  
    # --- Event Handling ---
    def add_event_callback(self, callback: Callable[[SMUEvent], None]):
        """Register callback for LDC events."""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[SMUEvent], None]):
        """Remove event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    def _emit_event(self, event_type: SMUEventType, data: Dict[str, Any]):
        """Emit event to all registered callbacks."""
        event = SMUEvent(
            event_type=event_type,
            data=data or {},
            timestamp=monotonic()
        )
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")        






