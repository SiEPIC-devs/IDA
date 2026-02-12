# Complete Guide to Adding a new Driver

This is a complete guide on everything that needs to be done to use a new instrument within our GUI. I tried to design it so it is as simple and intuitive as possible, but if anything is unclear follow other examples of drivers that are wrapped of the same instrument type. I highly recommend testing your instrument with this methodology:

- Test all methods of your controller to work independantly
- Test your now wrapped controller with the respective manager (ind of GUI)
- Then add it to the GUI and ensure that it works as planned
    - Some measurement API code (like fine alignement) make use of features
      present in managers. As long as your format, return type follows our
      design, it should work. I recommend testing everything before proceeding

If you have not yet done so, please read HAL_Architecture_Documentation.md as I will assume you understand how our modular design works (roughly).

## Step 1. Wrapping your driver

For each type of instrument: motors (electrical OR optical), nir (lasers and detectors), LDC (a srs temperature and laser diode controller), or SMU (source measurement unit for electrical measurements)

There are distinct abstract base classes that you must inherit from. The purpose of these is that functionality is both preserved and consistent accross new instruments. This allows us to use an MMC-100 or corvus controller interfaces in our manager, irrelevant how commands are sent to the instrument. Let us use an optical motor as an example...

In each folder, a hal directory can be found. For optical motors, we choose the MotorHAL abstract base class. Take your instrument controller, and implement each method with its driver specific initilization and control. For optical motors, the registration is done per axis. As such, we need to connect to each axis however that is done. Two examples that can be handy to use as a reference are the ida_controller and the iris_controller. Iris uses a shared serial port, where each axis is intializated seperately whereas ida uses a shared connection. 

ex) let this be a new file called .\motors\optical\foo_controller.py

` 
from motors.hal.motors_hal import MotorHAL

class MotorFoo(MotorHAL):
    """
    For our __init__, implement the features that come from the motors configuration file.
    These are parameters specific to our motor driver, and can be ommited if some cases are
    not needed, due to the design of the factory.

    Furthermore, please use the stage_manager as a reference if you get stuck or confused on 
    what is necessary.
    """
    def __init__(self, axis : AxisType,
                 visa_addr: str = "ASRL4::INSTR",
                 timeout: float = 0.3,
                 velocity: float = 3000.0,
                 acceleration: float = 5000.0,
                 position_limits: Tuple[float, float] = (-50000.0, 50000.0),
                 position_tolerance: float = 1.0,      # um tolerance for move completion
                 status_poll_interval: float = 0.05):  # seconds between status checks
        super().__init__(axis)  #  <-- init the axis var in the superclass

        # State vars
        self._is_connected = False  #  <-- I like to track state, connection and homed
        . . .

        self._callbacks = []  #  <-- init your callbacks for the add_callback method

    def add_callback(self, callback):
        """Add event callback"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    """
    Then just implement the rest of the methods with commands on how to connect, query position etc
    """
    async def connect(self): ...

"""
Then finally, at the end of your file you need to register the driver such that it can be accessed by the manager
"""
from motors.hal.stage_factory import register_driver

# Register motor stage
# params: string-like tag, Class ClassName
register_driver("stage_controller", MotorFoo)
`

## Step 2. Initialize the tag

We need the class to exist, so that we can call it. In each hal subdirectory of a instrument folder, the __init__.py needs to be altered as so,

(.\motors\hal\__init__.py)
`
from motors.hal.motors_hal import MotorHAL
from motors.hal.stage_factory import register_driver, create_driver
from motors.hal.emotor_factory import register_driver, create_driver

from motors.optical import ida_controller, iris_controller, scylla_controller
from motors.optical import foo_controller  # <--- Here we import our controller
from motors.elec import BSC203_controller

__all__ = ['MotorHAL', 'register_driver', 'create_driver']
`

Once this is initialized as we've done, the manager uses the create_driver function in the respective factory. Have a look at a factory if your interested in how this works.


## Step 3. Import the Tag 

We now need to import the tag, so that it can be passed through the configuration as a property. Our StageControl found  in ..\GUI\mainframe_stage_control_gui.py handles the initialization once its been set in the GUI. This can be found in ..\GUI\main_instruments_gui.py (line:145)

`
 # DropDown
            setattr(self, f"{key}_dd", StyledDropDown(
                container=instruments_container,
                text={"stage": ["MMC100_controller", "Corvus_controller", "scylla_controller"],  # <--- Put your tag here
                    "sensor": ["8164B_NIR", "luna_controller", "Dummy_B"],
                    "tec": ["srs_ldc_502", "srs_ldc_501", "Dummy_B"],
                    "smu": ["stage_control", "Dummy_A", "Dummy_B"],
                    "motor": ["BSC203_emotor", "Dummy_A", "Dummy_B"]}[key],
                variable_name=f"set_{key}",
                left=160, top=10 + idx * 40, width=180, height=30
            ))
`

And now your controller can be set from the GUI.


## That's All!

Specifications can be added and passed or set at a controller level, ie. velocities, accelerations or whatnot. Furthermore, if your device does not require some feature that is needed from the HAL, feel free to omit it. That said, the abstract base class will raise an exception if you do not override all abstract methods, so wire it up as follows:

`
class Foo(HAL):
    ...
    
    def bar_method(self):
        print('Foo Does not support bar_method, returning True')
        return True
`

There is no guarentee that if you do not implement all the methods that the hal requires. That said some methods aren't strictly required.