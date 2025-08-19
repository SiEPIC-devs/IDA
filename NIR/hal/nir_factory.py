from typing import Type, Dict
import inspect
from NIR.hal.nir_hal import LaserHAL # import hardware abstraction  


"""
NIR factory for registring Laser / detectors

Made by: Cameron Basara, 2025

"""

_registry: Dict[str, Type[LaserHAL]] = {}

def register_driver(name: str, cls: Type[LaserHAL]) -> None:
    """Call once in each driver module to make it discoverable."""
    _registry[name] = cls

def create_driver(name: str, **params) -> LaserHAL:
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