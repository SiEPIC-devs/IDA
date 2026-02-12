from dataclasses import dataclass, field
from typing import List

"""
NIR Configuration
Cameron Basara, 2025
"""

@dataclass
class NIRConfiguration:
    """Simple configuration for NIR system"""
    
    # Connection settings
    laser_slot: str = 'GPIB0::20::INSTR'  # Default
    detector_slots: List[str] = field(default_factory=lambda: ['USB0::0x0957::0x3718::MY48102149::INSTR'])  # Default detector
    driver_types: str = '8164B_NIR'
    safety_password: str = "1234"
    timeout: int = 3000  # long for lambda sweep
    
    # Default settings
    initial_wavelength_nm: float = 1550.0
    initial_power_dbm: float = -1.0

    # Sweep settings
    start_nm = 1545
    stop_nm = 1565
    step_nm = 0.1 
    laser_power_dbm = -5.0
    
    @property
    def visa_address(self) -> str:
        """Get VISA address"""
        return self.laser_slot
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'laser_slot': self.laser_slot,
            'detector_slots': self.detector_slots,
            'driver_types': self.driver_types,
            'safety_password': self.safety_password,
            'timeout': self.timeout,
            'initial_wavelength_nm': self.initial_wavelength_nm,
            'initial_power_dbm': self.initial_power_dbm,
            'start_nm': self.start_nm,
            'stop_nm': self.stop_nm,
            'step_nm': self.step_nm,
            'laser_power_dbm': self.laser_power_dbm,
        }
    
    @classmethod
    def default(cls) -> 'NIRConfiguration':
        """Create default configuration"""
        return cls()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NIRConfiguration':
        """Create from dictionary"""
        return cls(**data)