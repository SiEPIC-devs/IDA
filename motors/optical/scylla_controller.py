import asyncio
import time
from typing import Optional, ClassVar
from motors.hal.motors_hal import (
    MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType
)

# Unhash if at Scylla, import using relative
# imports to the mlpPyAPI.api external package
# located within the Dreamlabs env
# from mlpPyAPI.api import connect_to_api

"""
Limited capabilites

Implements MotorHAL for Scylla controller with initialization 
and relative movement support.


Cameron Basara, 2025
"""


class ScyllaController(MotorHAL):
    """Scylla motor controller implementing relative movement only."""
    # Axis Mapping
    AXIS_MAP = {
        AxisType.X: 'dx',
        AxisType.Y: 'dy', 
        AxisType.Z: 'dz',
        AxisType.ROTATION_CHIP: 'dzRot',
        AxisType.ROTATION_FIBER: 'dxRot'
    }
    counter: ClassVar[int] = 0
    api_inst: ClassVar = None

    def __init__(self, axis: AxisType):
        """
        Initialize Scylla controller.
        
        Args:
            axis: Axis type this controller manages
        """
        super().__init__(axis)
        self.instrument = None  # Motor connection to call API
        self._serial = None
        self._position = 0.0
        self._state = MotorState.IDLE
        self._callbacks = []
    
    def add_callback(self, callback):
        """Add event callback"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    # Initialization
    async def connect(self) -> bool:
        """Connect to Scylla controller."""
        try:
            # Init axis using API
            if ScyllaController.counter == 0:
                print('Connecting to API, please ensure Fonotina API is running...')
                ScyllaController.api_inst = connect_to_api()

            ScyllaController.counter += 1
            time.sleep(0.3)

            if self.axis in [AxisType.X, AxisType.Y, AxisType.Z,
                             AxisType.ROTATION_FIBER]:
                self.instrument = ScyllaController.api_inst.fiber_stage[0]
            else:
                # ROTATION_CHIP only
                self.instrument = ScyllaController.api_inst.chip_stage
                           
            if self.instrument is None:
                raise

            # Connect to device
            if self.counter == 1:
                self.instrument.connect()

            return True
        except Exception as e:
            print(f'[Connect] Exception: {e}')
            return False
    
    async def disconnect(self) -> Optional[bool]:
        """Disconnect from controller."""
        try:
            ScyllaController.counter -= 1
            self.instrument.disconnect()  # May be?
            if ScyllaController.counter == 0:
                self.api_inst = None
            return True
        except:
            return False
    
    # Movement
    async def move_absolute(self, position: float, velocity: Optional[float] = None,
                            wait_for_completion: bool = True) -> bool:
        """Not implemented - Scylla uses relative moves only."""
        raise NotImplementedError("Scylla controller only supports relative moves")
    
    async def move_relative(self, 
                            distance: float,
                            velocity: Optional[float] = None,
                            wait_for_completion: bool = True) -> bool:
        """
        Execute relative move.
        
        Args:
            distance: Distance to move in current units
            velocity: Optional velocity override
            
        Returns:
            True if move command accepted
        """
        # For now, use MLPMotor implementation
        if self.axis in [AxisType.X, AxisType.Y]:
            distance *= -1  # Flipped on gui
        self.instrument.move_relative(**{self.AXIS_MAP[self.axis]: distance})
        return True
    
    async def stop(self) -> bool:
        """Stop current movement."""
        # TODO: Send stop command
        print(f'[Scylla Controller] Cautious: NotImplementedYet')
        self._state = MotorState.STOPPED
        self._emit_event(MotorEventType.MOVE_STOPPED)
        return True
    
    async def emergency_stop(self) -> bool:
        """Emergency stop - fastest possible halt."""
        # TODO: Send emergency stop command
        return await self.stop()
    
    # Status
    async def get_position(self) -> Position:
        """Get current position."""
        pos_map = {
            AxisType.X: 0,
            AxisType.Y: 1,
            AxisType.Z: 2,
            AxisType.ROTATION_FIBER: 3,
            AxisType.ROTATION_CHIP: 5,
        }
        self._position = self.instrument.get_position()[pos_map[self.axis]]

        return Position(
            theoretical=self._position,
            actual=self._position,
            units="um",
            timestamp=asyncio.get_event_loop().time()
        )
    
    async def get_state(self) -> MotorState:
        """Get controller state."""
        # TODO: Query actual state from controller
        return self._state
    
    async def is_moving(self) -> bool:
        """Check if motor is moving."""
        return self._state == MotorState.MOVING
    
    # Configuration
    async def set_velocity(self, velocity: float) -> bool:
        """Set movement velocity."""
        # TODO: Send velocity command
        return True
    
    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration."""
        # TODO: Send acceleration command
        return True
    
    async def get_config(self) -> MotorConfig:
        """Get motor configuration."""
        # TODO: Return actual config from controller
        return MotorConfig(
            max_velocity=1000.0,
            max_acceleration=500.0,
            position_limits=(-10000.0, 10000.0),
            units="um",
            step_size_x=0.1,
            step_size_y=0.1,
            step_size_z=0.1,
            step_size_fr=0.01,
            step_size_cr=0.01
        )
    
    # Homing
    async def home(self, direction: int = 0) -> bool:
        """Not implemented - Scylla uses relative positioning."""
        raise NotImplementedError("Scylla does not support homing")
    
    async def home_limits(self) -> bool:
        """Not implemented."""
        raise NotImplementedError("Scylla does not support limit homing")
    
    async def set_zero(self) -> bool:
        """Set current position as zero."""
        # TODO: Send zero command or reset internal tracking
        self._position = 0.0
        return True
    
# Register driver
from motors.hal.stage_factory import register_driver
register_driver("scylla_controller", ScyllaController)
