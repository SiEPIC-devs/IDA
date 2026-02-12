from dataclasses import dataclass, field, asdict
from typing import Dict, Any
from SMU.keithley2600_controller import Keithley2600BController

@dataclass
class SMUConfiguration:
    """
    Configuration for Keithley 2600 Series SMU
    
    Cameron Basara, 2025
    """
    
    visa_address: str = 'GPIB0::26::INSTR'
    nplc: float = 0.1
    off_mode: str = "NORMAL"  # NORMAL | ZERO | HI-Z
    polling_interval: float = 1.0  # seconds
    use_shared_memory: bool = False
    debug: bool = False
    
    # Driver configuration
    driver_types: Dict[str, type] = field(
        default_factory=lambda: {
            "keithley2600B_smu": Keithley2600BController
        }
    )
    driver_key: str = "keithley2600B_smu"
    driver_cls: type = Keithley2600BController
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converts self -> JSON-safe dict.
        """
        d = asdict(self)
        # Convert driver_types to string representation for JSON serialization
        d["driver_types"] = {name: dt.__name__ for name, dt in self.driver_types.items()}
        d["driver_cls"] = self.driver_cls.__name__
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SMUConfiguration":
        """
        Reconstruct from a dict (e.g. JSON-loaded).
        """
        # Handle driver_types reconstruction if needed
        driver_types = data.get("driver_types", {"keithley2600B_smu": Keithley2600BController})
        if isinstance(list(driver_types.values())[0], str):
            # If driver_types are stored as strings, convert back to actual classes
            driver_types = {"keithley2600B_smu": Keithley2600BController}
        
        # Create new instance with data
        config = cls(**{k: v for k, v in data.items() if k not in ["driver_types", "driver_cls"]})
        config.driver_types = driver_types
        config.driver_cls = Keithley2600BController
        
        return config
    
    def validate(self) -> bool:
        """
        Validate configuration parameters.
        """
        if self.nplc <= 0:
            return False
        if self.off_mode not in ["NORMAL", "ZERO", "HI-Z"]:
            return False
        if self.polling_interval <= 0:
            return False
        if not self.visa_address:
            return False
        return True