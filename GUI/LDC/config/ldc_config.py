from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List
import json
from LDC.ldc_controller import SrsLdc502

@dataclass
class LDCConfiguration:
    """
    Configuration for SRS LDC502 controller at 347. Does not support LD control
   
    TODO:
        For other stages, the additional configuration needs to be done to support LD control
        constants.
    """
   
    visa_address: str = 'ASRL5::INSTR' # my laptop for now
    sensor_type: str = "1"           # temperature sensor channel
    pid_coeffs: List[float] = field(
        default_factory=lambda: [-1.669519, 0.2317650, 1.078678] # [P, I, D]
    )      
    model_coeffs: List[float] = field(
        default_factory=lambda: [1.204800e-3, 2.417000e-4, 1.482700e-7]
    )                            
    setpoint: float = 25.0              # temperature set point      
    driver_types: Dict[str, SrsLdc502] = field(
        default_factory=lambda: {
            "srs_ldc_502": SrsLdc502 
        }
    )      
    driver_key = "srs_ldc_502"                             
    driver_cls = SrsLdc502
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converts self -> JSON-safe dict.
        """
        d = asdict(self)
        # Convert driver_types to string representation for JSON serialization
        d["driver_types"] = {name: dt.__name__ for name, dt in self.driver_types.items()}
        return d
   
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LDCConfiguration":
        """
        Reconstruct from a dict (e.g. JSON-loaded).
        """
        # Handle driver_types reconstruction if needed
        driver_types = data.get("driver_types", {"srs_ldc_502": SrsLdc502})
        if isinstance(list(driver_types.values())[0], str):
            # If driver_types are stored as strings, convert back to actual classes
            # This would require a registry or import mapping
            driver_types = {"srs_ldc_502": SrsLdc502}  # Default fallback
       
        return cls(
            visa_address=data.get("visa_address", 'ASRL5::INSTR'),
            sensor_type=data.get("sensor_type", "1"),
            pid_coeffs=data.get("pid_coeffs", [-1.669519, 0.2317650, 1.078678]),
            model_coeffs=data.get("model_coeffs", [1.204800e-3, 2.417000e-4, 1.482700e-7]),
            setpoint=data.get("setpoint", 25.0),
            driver_types=driver_types
        )
   
    def get_controller_attributes(self) -> Dict[str, Any]:
        """
        Returns all attributes for the LDC controller in a structured format.
       
        Returns:
            Dict containing all controller configuration attributes:
            {
                'visa_address': str,
                'sensor_type': str,
                'pid_coeffs': List[float],
                'model_coeffs': List[float],
                'setpoint': float,
                'driver_type': str
            }
        """
        return {
            'visa_address': self.visa_address,
            'sensor_type': self.sensor_type,
            'pid_coeffs': self.pid_coeffs.copy(),  # Return copy to prevent mutation
            'model_coeffs': self.model_coeffs.copy(),
            'setpoint': self.setpoint,
            'driver_type': list(self.driver_types.keys())[0] if self.driver_types else None
        }