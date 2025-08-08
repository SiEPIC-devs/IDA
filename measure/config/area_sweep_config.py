from dataclasses import dataclass, field
from typing import List

"""
Area Sweep Configuration
Cameron Basara, 2025
"""

@dataclass
class AreaSweepConfiguration:
    """
    Size: width/height of area sweep
    step: size in microns of each step
    """
    x_size = 50 # microns
    x_step = 1 # microns
    y_size = 50 # microns
    y_step = 1 # microns

    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'step_size': self.step_size,
            'scan_window': self.scan_window,
            'threshold': self.threshold,
            'max_gradient_iters': self.max_gradient_iters,
            'use_crosshair': self.use_crosshair
        }
    
    @classmethod
    def default(cls) -> 'AreaSweepConfiguration':
        """Create default configuration"""
        return cls()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AreaSweepConfiguration':
        """Create from dictionary"""
        return cls(**data)