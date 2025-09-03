from dataclasses import dataclass, field
from typing import List

"""
Fine Align Configuration
Cameron Basara, 2025
"""

@dataclass
class FineAlignConfiguration:
    step_size: float = 0.1          # microns
    scan_window: float = 10.0       # microns
    threshold: float = -10.0        # dBm 
    gradient_iters: int = 10        
    min_gradient_ss: float = 0.2    # microns
    primary_detector: str = "ch1"   # "ch1" or "ch2"
    ref_wl: float = 1550.0          # nm
    timeout_s: float = 60.0        # seconds

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'step_size': self.step_size,
            'scan_window': self.scan_window,
            'threshold': self.threshold,
            'gradient_iters': self.gradient_iters,
            'min_gradient_ss': self.min_gradient_ss,
            'primary_detector': self.primary_detector,
            'ref_wl': self.ref_wl,
            'timeout_s': self.timeout_s,
        }
    
    @classmethod
    def default(cls) -> 'FineAlignConfiguration':
        """Create default configuration"""
        return cls()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FineAlignConfiguration':
        """Create from dictionary"""
        return cls(**data)