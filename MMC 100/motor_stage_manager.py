import asyncio
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from motors_hal import AxisType, MotorState, Position, MotorEvent, MotorEventType
from modern_stage import StageControl

"""
Made by: Cameron Basara, 5/30/2025
(PROTOTYPE)
Multi-axis stage manager, intended to interface with the GUI to give high level commands to the modern stage
"""

@dataclass
class StagePosition:
    """
    Current position of stage
    """
    x: float
    y: float
    z: float
    fiber_rotation: float
    chip_rotation: float
    timestamp: float
    units: str = "um"
    is_homed: bool = False

@dataclass
class MoveCommand:
    """
    Multi-axis movement command with options
    """
    axes: Dict[AxisType, float]  # axis -> target position/distance
    velocity: Optional[float] = None
    coordinated_motion: bool = False  # Move all axes simultaneously
    relative: bool = False  # True for relative moves, False for absolute

@dataclass
class StageConfiguration:
    """
    Configuration parameters for the stage, this will later be altered to be passed through the GUI
    """
    # Communication settings
    com_port: str = '/dev/ttyUSB0'
    baudrate: int = 38400
    timeout: float = 0.3
    
    # Motion parameters (per axis)
    velocities: Dict[AxisType, float] = field(default_factory=lambda: {
        AxisType.X: 2000.0, # From zero xyz
        AxisType.Y: 2000.0,
        AxisType.Z: 2000.0,
        AxisType.ROTATION_FIBER: 100.0,
        AxisType.ROTATION_CHIP: 100.0
    })
    
    accelerations: Dict[AxisType, float] = field(default_factory=lambda: {
        AxisType.X: 100.0, # No Idea
        AxisType.Y: 100.0,
        AxisType.Z: 100.0,
        AxisType.ROTATION_FIBER: 500.0,
        AxisType.ROTATION_CHIP: 500.0
    })
    
    position_limits: Dict[AxisType, Tuple[float, float]] = field(default_factory=lambda: {
        AxisType.X: (-24940.0, 20000.0), # From zero_xyz
        AxisType.Y: (-30400.0, 20000.0),
        AxisType.Z: (-11100.0, 20000.0),
        AxisType.ROTATION_FIBER: (-180.0, 180.0),
        AxisType.ROTATION_CHIP: (-180.0, 180.0)
    })

    # Completion detection settings
    position_tolerance: float = 1.0  # um
    status_poll_interval: float = 0.05  # seconds
    move_timeout: float = 30.0  # seconds

class StageManager:
    """
    High level manager that provides easy control over the motors
    Offers both multi-axis control and single axis control with event handling
    """
    
    def __init__(self, config: Optional[StageConfiguration] = None):
        self.config = config or StageConfiguration()
        self.motors: Dict[AxisType, StageControl] = {}
        self._event_callbacks: List[Callable[[MotorEvent], None]] = []
        self._is_connected = False
        self._initialized_axes: Dict[AxisType, bool] = {}
        self._last_positions: Dict[AxisType, float] = {}
    
    def add_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Add a callback for motor events"""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Remove an event callback"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    async def initialize(self, axes: List[AxisType]) -> bool:
        """
        Initialize specific motor axes
        
        Args:
            axes: List of axes to initialize
            
        Returns:
            True if all axes initialized successfully
        """
        success_count = 0
        
        for axis in axes:
            try:
                # Create StageControl instance for this axis
                motor = StageControl(
                    axis=axis,
                    com_port=self.config.com_port,
                    baudrate=self.config.baudrate,
                    timeout=self.config.timeout,
                    velocity=self.config.velocities.get(axis, 2000.0),
                    acceleration=self.config.accelerations.get(axis, 100.0),
                    position_limits=self.config.position_limits.get(axis, (-10000.0, 20000.0)),
                    position_tolerance=self.config.position_tolerance,
                    status_poll_interval=self.config.status_poll_interval
                )
                
                # Connect to the motor
                if await motor.connect():
                    self.motors[axis] = motor
                    self._initialized_axes[axis] = True
                    self._last_positions[axis] = 0.0
                    
                    # Subscribe to motor events
                    motor.add_event_listener(self._handle_motor_event)
                    
                    success_count += 1
                    print(f"Successfully initialized {axis.name}")
                else:
                    print(f"Failed to initialize {axis.name}")
                    self._initialized_axes[axis] = False
                    
            except Exception as e:
                print(f"Error initializing {axis.name}: {e}")
                self._initialized_axes[axis] = False
        
        self._is_connected = success_count > 0
        print(f"Initialized {success_count}/{len(axes)} axes")
        return success_count == len(axes)
    
    def _handle_motor_event(self, event: MotorEvent):
        """Handle events from individual motors"""
        # Forward events to registered callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")
    
    async def configure_axis(self, axis: AxisType, velocity: Optional[float] = None, 
                           acceleration: Optional[float] = None) -> bool:
        """
        Configure specific axis parameters
        
        Args:
            axis: Axis to configure
            velocity: New velocity in um/s (or degrees/s for rotation axes)
            acceleration: New acceleration in um/s2 (or degrees/s2 for rotation axes)
            
        Returns:
            True if configuration successful
        """
        if axis not in self.motors:
            print(f"Axis {axis.name} not initialized")
            return False
        
        motor = self.motors[axis]
        success = True
        
        try:
            if velocity is not None:
                if await motor.set_velocity(velocity):
                    self.config.velocities[axis] = velocity
                    print(f"Set {axis.name} velocity to {velocity}")
                else:
                    success = False
                    
            if acceleration is not None:
                if await motor.set_acceleration(acceleration):
                    self.config.accelerations[axis] = acceleration
                    print(f"Set {axis.name} acceleration to {acceleration}")
                else:
                    success = False
                    
        except Exception as e:
            print(f"Error configuring axis {axis.name}: {e}")
            success = False
        
        return success
    
    async def configure_all_axes(self, velocity: Optional[float] = None,
                               acceleration: Optional[float] = None) -> Dict[AxisType, bool]:
        """
        Configure all initialized axes with the same parameters
        
        Returns:
            Dictionary mapping each axis to its configuration success status
        """
        results = {}
        
        for axis in self.motors.keys():
            results[axis] = await self.configure_axis(axis, velocity, acceleration)
        
        return results
    
    async def home_axis(self, axis: AxisType, direction: int = 0) -> bool:
        """
        Home a specific axis
        
        Args:
            axis: Axis to home
            direction: 0 for negative limit, 1 for positive limit
            
        Returns:
            True if homing successful
        """
        if axis not in self.motors:
            print(f"Axis {axis.name} not initialized")
            return False
        
        try:
            success = await self.motors[axis].home(direction)
            if success:
                self._last_positions[axis] = 0.0
                print(f"Homed {axis.name} successfully")
            return success
        except Exception as e:
            print(f"Error homing {axis.name}: {e}")
            return False
    
    async def home_all_axes(self, direction: int = 0) -> Dict[AxisType, bool]:
        """
        Home all initialized axes
        
        Returns:
            Dictionary mapping each axis to its homing success status
        """
        results = {}
        
        # Home axes sequentially to avoid conflicts
        for axis in self.motors.keys():
            results[axis] = await self.home_axis(axis, direction)
        
        return results
    
    async def move_single_axis(self, axis: AxisType, position: float, 
                              relative: bool = False, velocity: Optional[float] = None,
                              wait_for_completion: bool = True) -> bool:
        """
        Move a single axis
        
        Args:
            axis: Axis to move
            position: Target position (absolute) or distance (relative)
            relative: True for relative move, False for absolute
            velocity: Optional velocity override
            wait_for_completion: Whether to wait for move completion
            
        Returns:
            True if move command sent successfully
        """
        if axis not in self.motors:
            print(f"Axis {axis.name} not initialized")
            return False
        
        try:
            motor = self.motors[axis]
            
            if relative:
                success = await motor.move_relative(position, velocity, wait_for_completion)
                if success:
                    self._last_positions[axis] += position
            else:
                success = await motor.move_absolute(position, velocity, wait_for_completion)
                if success:
                    self._last_positions[axis] = position
            
            return success
            
        except Exception as e:
            print(f"Error moving {axis.name}: {e}")
            return False
    
    async def move_multiple_axes(self, move_cmd: MoveCommand) -> Dict[AxisType, bool]:
        """
        Move multiple axes
        
        Args:
            move_cmd: MoveCommand containing axes and parameters
            
        Returns:
            Dictionary mapping each axis to its move success status
        """
        results = {}
        
        if move_cmd.coordinated_motion:
            # Start all moves simultaneously
            tasks = []
            for axis, position in move_cmd.axes.items():
                if axis in self.motors:
                    task = self.move_single_axis(
                        axis, position, move_cmd.relative, 
                        move_cmd.velocity, wait_for_completion=True
                    )
                    tasks.append((axis, task))
            
            # Wait for all moves to complete
            for axis, task in tasks:
                try:
                    results[axis] = await task
                except Exception as e:
                    print(f"Error in coordinated move for {axis.name}: {e}")
                    results[axis] = False
        else:
            # Move axes sequentially
            for axis, position in move_cmd.axes.items():
                if axis in self.motors:
                    results[axis] = await self.move_single_axis(
                        axis, position, move_cmd.relative, 
                        move_cmd.velocity, wait_for_completion=True
                    )
        
        return results
    
    async def stop_axis(self, axis: AxisType) -> bool:
        """Stop a specific axis"""
        if axis not in self.motors:
            return False
        
        try:
            return await self.motors[axis].stop()
        except Exception as e:
            print(f"Error stopping {axis.name}: {e}")
            return False
    
    async def stop_all_axes(self) -> Dict[AxisType, bool]:
        """Stop all axes"""
        results = {}
        
        for axis in self.motors.keys():
            results[axis] = await self.stop_axis(axis)
        
        return results
    
    async def emergency_stop(self) -> bool:
        """Emergency stop all axes"""
        try:
            # Use the first available motor to send emergency stop
            if self.motors:
                first_motor = next(iter(self.motors.values()))
                return await first_motor.emergency_stop()
            return False
        except Exception as e:
            print(f"Error in emergency stop: {e}")
            return False
    
    async def get_position(self, axis: AxisType) -> Optional[Position]:
        """Get position of a specific axis"""
        if axis not in self.motors:
            return None
        
        try:
            return await self.motors[axis].get_position()
        except Exception as e:
            print(f"Error getting position for {axis.name}: {e}")
            return None
    
    async def get_all_positions(self) -> StagePosition:
        """Get positions of all axes"""
        positions = {}
        timestamp = time.time()
        
        for axis in [AxisType.X, AxisType.Y, AxisType.Z, 
                    AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP]:
            if axis in self.motors:
                pos = await self.get_position(axis)
                positions[axis] = pos.actual if pos else 0.0
            else:
                positions[axis] = 0.0
        
        return StagePosition(
            x=positions.get(AxisType.X, 0.0),
            y=positions.get(AxisType.Y, 0.0),
            z=positions.get(AxisType.Z, 0.0),
            fiber_rotation=positions.get(AxisType.ROTATION_FIBER, 0.0),
            chip_rotation=positions.get(AxisType.ROTATION_CHIP, 0.0),
            timestamp=timestamp,
            is_homed=all(self._initialized_axes.values())
        )
    
    async def get_state(self, axis: AxisType) -> Optional[MotorState]:
        """Get state of a specific axis"""
        if axis not in self.motors:
            return None
        
        try:
            return await self.motors[axis].get_state()
        except Exception as e:
            print(f"Error getting state for {axis.name}: {e}")
            return None
    
    async def is_any_axis_moving(self) -> bool:
        """Check if any axis is currently moving"""
        for motor in self.motors.values():
            try:
                if await motor.is_moving():
                    return True
            except Exception:
                continue
        return False
    
    async def wait_for_all_moves_complete(self, timeout: float = 30.0) -> bool:
        """Wait for all axes to complete their moves"""
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if not await self.is_any_axis_moving():
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall stage status"""
        return {
            'connected': self._is_connected,
            'initialized_axes': list(self._initialized_axes.keys()),
            'configuration': {
                'com_port': self.config.com_port,
                'velocities': self.config.velocities,
                'accelerations': self.config.accelerations,
                'position_limits': self.config.position_limits
            },
            'last_positions': self._last_positions
        }
    
    async def disconnect(self):
        """Disconnect all motors and clean up resources"""
        for motor in self.motors.values():
            try:
                await motor.disconnect()
            except Exception as e:
                print(f"Error disconnecting motor: {e}")
        
        self.motors.clear()
        self._initialized_axes.clear()
        self._is_connected = False
        print("Stage manager disconnected")