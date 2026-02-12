from typing import Type, Dict
import inspect
from motors.hal.motors_hal import MotorHAL # import hardware abstraction  

_registry: Dict[str, Type[MotorHAL]] = {}

def register_driver(name: str, cls: Type[MotorHAL]) -> None:
    """Call once in each driver module to make it discoverable."""
    _registry[name] = cls

def create_driver(name: str, **params) -> MotorHAL:
    """Instantiate a registered driver 'name'; raises if driver not registered"""
    try: 
        driver = _registry[name]
    except KeyError:
        raise ValueError(f"Driver not yet registered named '{name}'")
    # return driver(**params) 

    sig = inspect.signature(driver.__init__)
    
    # Filter params to only include those the driver accepts
    filtered_params = {}
    for param_name, param_value in params.items():
        if param_name in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
            filtered_params[param_name] = param_value
    
    return driver(**filtered_params)