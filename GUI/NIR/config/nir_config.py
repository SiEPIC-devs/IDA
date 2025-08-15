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
    com_port: int = 3
    laser_slot: int = 0
    detector_slots: List[int] = field(default_factory=lambda: [1])
    safety_password: str = "1234"
    timeout: int = 30000 # long for lambda sweep
    
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
        return f"ASRL{self.com_port}::INSTR"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'com_port': self.com_port,
            'laser_slot': self.laser_slot,
            'detector_slots': self.detector_slots,
            'safety_password': self.safety_password,
            'timeout': self.timeout,
            'initial_wavelength_nm': self.initial_wavelength_nm,
            'initial_power_dbm': self.initial_power_dbm,
            'visa_address': self.visa_address,
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