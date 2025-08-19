from typing import Type, Dict
from modern.hal.motors_hal import MotorHAL # import hardware abstraction  

"""
Made by: Cameron Basara, 6/10/2025
(PROTOTYPE)
Motor factory intended to link instance of hardware drivers (devices) to the manager. When a new driver is registered, the manager can call the factory
with this new driver to abstract away manager level logic and instantiation

When we change drivers between stages, we remove a manual step in the process. When we change and integrate new drivers with the HAL, we simply add
a functionality to this, removing additional hastle when integrating new stages

How to use:

Each driver must be registered. In your HAL subclassed driver call register_driver. This will allow the manager to access the different stages

The manager then creates an instance of the driver, so each registered device must be part of the config params, under driver_type and registered
with the same name from the gui. Gui should provide functionality for this link, so you must add the registered device there, or done automatically 
when a new device is registered as seen below.

TODO:
    Test to see if this works
    
    GUI integration -> this should be done automatically PSEUDOCODE
    ```
    from hal.factory import _registry

    def list_available_drivers():
        return list(_registry.keys())
    ```

"""

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
    return driver(**params) 