import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any, Set
from dataclasses import dataclass, field, fields
from enum import Enum
import time
from time import monotonic

# local API calls
from modern.hal.motors_hal import AxisType, MotorState, Position, MotorEvent, MotorEventType
from modern.modern_stage import StageControl
# from modern.modern_stage import StageControl 
from modern.hal.stage_factory import create_driver
from modern.config.stage_position import *
from modern.config.stage_config import *
from modern.utils.update_stage import update_stage_position
from modern.utils.shared_memory import *

"""
Made by: Cameron Basara, 6/17/2025

Stage manager, intended to interface with the GUI to give high level commands to the modern stage

TODO:
    Ensure that the other stages behave nicely. Concerned about movement patterns : will they be different logic at different stages?
    Implement cominterface ? may not be useful
    Implement interactions with other hardware devices: lasers, detectors, TECs, Cams
    Implement interactions with gui
    Document control flow

"""

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - \n %(message)s'
)

logger = logging.getLogger(__name__)

STAGE_LIST = [347] # placeholder

class StageManager:
    def __init__(self, profile_config: StageConfiguration, create_shm: bool = True):
        # self.config = config
        self.motors: Dict[AxisType, StageControl] = {}
        self._event_callbacks: List[Callable[[MotorEvent], None]] = []
        self._last_positions: Dict[AxisType, float] = {}
        self._homed_axes: Dict[AxisType, bool] = {axis: False for axis in AxisType if axis != AxisType.ALL}
        self._changed_axes: List[AxisType] = [] # cheeky changed axis queue

        if create_shm:
            # Shared-memory configuration and stage positioning
            self.shm_position, self.raw_position = create_shared_stage_position()
            self.shm_config = create_shared_stage_config() # create
            write_shared_stage_config(self.shm_config, profile_config) # load preset
        else:
            # If an shm has been created, simply access the open memory block
            self.shm_position, self.raw_position = open_shared_stage_position()
            self.shm_config = open_shared_stage_config()

        # Read config from shared mem for consistency
        self.config = read_shared_stage_config(self.shm_config)
        self.shared_stage_position = StagePosition(shared_struct=self.raw_position)

        # Background loops
        self._tasks = []

    # Async helpers
    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Proper async cleanup with context manager exit"""
        await self.cleanup()

    # Helper decorator to ensure SHM is properly cleaned
    async def cleanup(self):
        """Cleanup method for tasks and shm"""

        # Cancel Background tasks first
        cleanup_tasks = []
        for task in self._tasks:
            if not task.done():
                task.cancel()
                cleanup_tasks.append(task)
        
        # Wait for tasks to cancel
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                logger.warning(f"Task cleanup had exceptions: {e}")
        
        # Disconnect motors
        await self.disconnect_all()

        # Cleanup SHM (BUT don't unlink, that is the main process responsibility)
        try:
            # Destroy instances of shared memory access buffers
            if hasattr(self, 'shared_stage_position'):
                del self.shared_stage_position
            if hasattr(self, 'raw_position'):
                del self.raw_position
            if hasattr(self, 'config'):
                del self.config

            # Close shm
            if hasattr(self, 'shm_position'):
                self.shm_position.close()
                self.shm_position.unlink()
            if hasattr(self, 'shm_config'):
                self.shm_config.close()
                self.shm_config.unlink()    
        except (FileNotFoundError, AttributeError):
            pass # Cleared mem or never existed
        except Exception as e:
            logger.error(f"Shared memory cleanup error: {e}")
        
    # Position poll loop
    async def _position_poll_loop(self):
        """Background loop to poll motor positions and update shared memory"""
        logger.info("Starting position poll loop")

        while True:
            try:
                # Don't poll if no motors connected
                if not self.motors:
                    await asyncio.sleep(1.0)
                    continue
                
                # Take a snapshot of to ensure it isn't changed in concurrent coroutines
                motors_snapshot = dict(self.motors)
                
                # Poll each motor position
                for axis, motor in motors_snapshot.items():
                    try:
                        logger.debug(f"Polling {motor}.{axis}")
                        position = await motor.get_position()
                        logger.debug(f"Position: {position}")
                        if position is not None:
                            logger.info(f"Testing position: {position.actual:.3f}")
                            # Update local cache
                            self._last_positions[axis] = position.actual

                            # Updated shared mem
                            setattr(self.shared_stage_position, axis.name.lower(), position.actual) # eg self.shared_stage_position.x = position.actual

                            # Check for positional drift
                            exp = self._last_positions.get(axis, 0.0)
                            if abs(position.actual - exp) > self.config.position_tolerance:
                                # OFC this does not work right now since they will be identical at each call
                                logger.warning(f"Positional drift on {axis.name}: expected: {exp:.3f} actual: {position.actual:.3f}")
                    
                    except Exception as e:
                        logger.debug(f"Failed to poll {axis.name} position: {e}")
                
                # Poll at configured interval
                await asyncio.sleep(self.config.status_poll_interval)
            
            except asyncio.CancelledError:
                logger.info("Position poll loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in position poll loop: {e}")
                await asyncio.sleep(1.0)  # Prevent tight error loop
    
    async def start_background_tasks(self):
        """Start all background tasks call after initialization"""
        if self._tasks:
            logger.warning("Background tasks already running")
            return
        
        try:
            # Start pos polling
            self._tasks.append(
                asyncio.create_task(self._position_poll_loop(), name="position_poll")
            )

            # Add more when needed
            logger.info(f"started {len(self._tasks) } bgtasks")
        
        except Exception as e:
            logger.error(f"Failed to start background tasks: {e}")
            raise

    # Helper decorator to ensure axis is initialized
    def requires_motor(func):
        """Before method runs, checks is this an axis in self.motors"""
        async def wrapper(self, axis, *args, **kwargs):
            if axis not in self.motors:
                logger.error(f"{axis.name} not initialized")
                return False
            return await func(self, axis, *args, **kwargs)
        # For improved debugging 
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    # Helper to catch exceptions
    async def _safe_execute(self, desc: str, coro, default=False):
        """Runs awaits a coroutine passed, try + except log in 1 line"""
        try:
            logger.info(f"{desc}")
            return await coro
        except Exception as e:
            logger.error(f"Error {desc}: {e}")
            logger.debug("Traceback:", exc_info=True)
            return default

    # Helper functions for events
    def add_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Register callback for motor events."""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Remove event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def _handle_stage_event(self, event: MotorEvent) -> None:
        """Internal meth to forward motor event emitted"""
        for cb in self._event_callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"[{event.axis.name}] Error in manager-level callback: {e}")

    # Configuration and helpers
    def _check_changes(self, cfg: StageConfiguration) -> bool:
        """Updates self._changed_axes"""
        # Clear previous changed axis
        self._changed_axes.clear()

        # Check for static changes, if these change we have to reinitialize the stage
        scalar_fields = ['com_port', 'baudrate', 'timeout', 'position_tolerance', 
                     'status_poll_interval', 'move_timeout']
        for field_name in scalar_fields:
            old_val = getattr(self.config, field_name)
            new_val = getattr(cfg, field_name)
            if old_val != new_val:
                return True
            
        new_attrs = cfg.get_axis_attributes()
        old_attrs = self.config.get_axis_attributes()
        
        # Check for removed axes
        for axis in old_attrs:
            if axis not in new_attrs:
                logger.info(f"Axis {axis.name} removed from config")
                self._changed_axes.append(axis)
        
        # Check for added or modified axes
        for axis in new_attrs:
            if axis not in old_attrs:
                logger.info(f"Axis {axis.name} added to config")
                self._changed_axes.append(axis)
            elif old_attrs[axis] != new_attrs[axis]:
                logger.info(f"Axis {axis.name} configuration changed")
                self._changed_axes.append(axis)
        
        return False

    async def reload_config(self) -> StageConfiguration:
        """Reload config from shared memory"""
        try:
            cfg = read_shared_stage_config(self.shm_config)
            if cfg == self.config:
                return self.config
            else:
                full = self._check_changes(cfg)
                if full:
                    # If a static param changes, reinitialize stage
                    self.config = cfg
                    ok = await self.initialize([axis for axis in AxisType if axis != AxisType.ALL])
                    return ok
                
                self.config = cfg
                ok = await self._apply_config_changes()
                return ok
        except Exception as e:
            logger.error(f"Error reading config: {e}")
            raise
    
    async def update_config(self, new_config: StageConfiguration) -> None:
        """Update configuration in shared memory"""
        try:
            write_shared_stage_config(self.shm_config, new_config)
            if new_config == self.config:
                return None
            else:
                full = self._check_changes(new_config)
                if full:
                    # If a static param changes, reinitialize stage
                    self.config = new_config
                    await self.initialize([axis for axis in AxisType if axis != AxisType.ALL])

                self.config = new_config
                await self._apply_config_changes()
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            raise
    
    async def _apply_config_changes(self):
        """Apply config changes to stage instance"""
        # Succesful initialization
        results = {}

        for axis in self._changed_axes:
            # Retrive config
            cfg = self.config

            # Instantiate motors through the the factory
            driver_key = cfg.driver_types[axis]
            params = dict(
                axis=axis,
                com_port=cfg.com_port,
                baudrate=cfg.baudrate,
                timeout=cfg.timeout,
                velocity=cfg.velocities[axis],
                acceleration=cfg.accelerations[axis],
                position_limits=cfg.position_limits[axis],
                position_tolerance=cfg.position_tolerance,
                status_poll_interval=cfg.status_poll_interval
            )
            motor = create_driver(driver_key, **params)

            # Catch exceptions
            ok = await self._safe_execute(f"connect {axis.name}", motor.connect()) # motor connects from abstracted stage driver
            if ok:
                self.motors[axis] = motor
                self._last_positions[axis] = 0.0
                motor.add_event_callback(self._handle_stage_event)
                
            results[axis] = ok
        
        self._changed_axes.clear()
        return all(results.values())

        
    @update_stage_position
    async def initialize(self, axes):
        """
        Initialize all stage axes
        """
        # Succesful initialization
        results = {}

        for axis in axes:
            # Retrive config
            cfg = self.config

            # Instantiate motors through the the factory
            driver_key = cfg.driver_types[axis]
            params = dict(
                axis=axis,
                com_port=cfg.com_port,
                baudrate=cfg.baudrate,
                timeout=cfg.timeout,
                velocity=cfg.velocities[axis],
                acceleration=cfg.accelerations[axis],
                position_limits=cfg.position_limits[axis],
                position_tolerance=cfg.position_tolerance,
                status_poll_interval=cfg.status_poll_interval
            )
            motor = create_driver(driver_key, **params)

            # Catch exceptions
            ok = await self._safe_execute(f"connect {axis.name}", motor.connect()) # motor connects from abstracted stage driver
            if ok:
                self.motors[axis] = motor
                self._last_positions[axis] = 0.0
                motor.add_event_callback(self._handle_stage_event)
                
            results[axis] = ok

        return all(results.values())
    
    @update_stage_position
    async def update_params(self) -> bool:
        """
        Updates params of a stage from shared memory
        """
        # Check if homed
        for axis, motor in self.motors.items():
            if not self.motors[axis]._is_homed:
                logger.error(f"{axis.name} isn't homed - aborting load of params")
                break

        # Intialize params
        cfg = self.config
        
        # Apply profiles
        for axis, target in cfg.initial_positions.items():
            print(f"axis: {axis.name} target: {target}")
            ok = await self._safe_execute(f"move_absolute {axis.name}",
                    self.motors[axis].move_absolute(target, velocity=cfg.velocities[axis], wait_for_completion=True))
            if not ok:
                return ok
        
        return True

    @update_stage_position
    async def load_params(self) -> bool:
        """
        Loads preset params of a stage
        """
        # Check if homed
        for axis, motor in self.motors.items():
            if not self.motors[axis]._is_homed:
                logger.error(f"{axis.name} isn't homed - aborting load of params")
                break

        # Intialize params
        cfg = self.config
        
        # Apply profiles
        for axis, target in cfg.initial_positions.items():
            print(f"axis: {axis.name} target: {target}")
            ok = await self._safe_execute(f"move_absolute {axis.name}",
                    self.motors[axis].move_absolute(target, velocity=cfg.velocities[axis], wait_for_completion=True))
            if not ok:
                return ok
        
        return True
    
    # HOMING
    @requires_motor
    async def _update_homing_state(self, axis: AxisType, is_homed: bool):
        """Internal tool to update homing state tracking"""
        # Update internal cache
        self._homed_axes[axis] = is_homed

        # Update shared memory
        self.shared_stage_position.set_homed(axis)

        # Emit homing event
        event = MotorEvent(
            axis=axis,
            event_type=MotorEventType.HOMED if is_homed else MotorEventType.ERROR_OCCURRED,
            timestamp=monotonic(),
            data={'homed': is_homed}
        )
        self._handle_stage_event(event)

    @update_stage_position
    @requires_motor
    async def home_axis(self, axis: AxisType, direction: int = 0) -> bool:
        ok = await self._safe_execute(f"home {axis.name}", self.motors[axis].home(direction))
       
        # # Wait for home to complete
        # while self.motors[axis]._move_in_progress:
        #     await asyncio.sleep(0.1)
        
        if ok:
            self._last_positions[axis] = 0.0
            await self._update_homing_state(axis, True)
        else:
            await self._update_homing_state(axis, False)
        return ok
    
    @update_stage_position
    @requires_motor
    async def git(self, axis: AxisType) -> bool:
        if (axis == AxisType.Z):
            # Ensure safe homing of Z axis
            aok = await self._safe_execute(f"", self.motors[AxisType.Y].move_absolute(
                self.config.position_limits[AxisType.Y][1],
                wait_for_completion=True
            ))
            if aok:
                pass
            else:
                return False
        ok, pos_lims = await self._safe_execute(f"home {axis.name} limits", self.motors[axis].home_limits())
        if ok:
            self.config.position_limits[axis] = pos_lims
            await self._update_homing_state(axis, True)
        else:
            await self._update_homing_state(axis, False)            
        return ok

    @requires_motor
    async def wait_for_home_completion(self, axis: AxisType) -> bool:
        ok = await self._safe_execute(f"home {axis.name} status", self.motors[axis]._wait_for_home_completion())
        return ok
    
    # MOVEMENT
    @update_stage_position
    @requires_motor
    async def move_single_axis(self, axis: AxisType, position: float,
                               relative=False, velocity=None,
                               wait_for_completion=True) -> bool:
        """
        Move a single axis command. 

        Args:
            axis[AxisType]: axis you want to move eg. AxisType.X (or something nice like x_axis = AxisType.X)
            position[float]: Desired position for absolute or relative distance (+/-) 
            relative[bool]: False by default, set true if you want to send a relative movement command
            velocity: Optional velocity override, useless right now
            wait_for_completion: If True, wait for move to complete and emit MOVE_COMPLETED event

        Returns:
            Position if successful else False  
        """
        if relative:
            ok = await self._safe_execute(f"move_relative {axis.name}", 
                    self.motors[axis].move_relative(position, velocity, wait_for_completion)) 
            if ok:
                self._last_positions[axis] += position
        else:
            ok = await self._safe_execute(f"move_absolute {axis.name}",
                    self.motors[axis].move_absolute(position, velocity, wait_for_completion))
            if ok:
                self._last_positions[axis] = position
        return ok

    @update_stage_position
    async def move_xy_rel(self, xy_distance: Tuple[float, float], wait_for_completion = True):
        """
        MMC Supports multi-axes movement. Move only xy in tandem for safety. Relative movement
        
        Args:
            xy_distance: (x,y) Distance you want to move in microns 
            wait_for_completion: 
        """
        # Need xy to be initialized
        if (AxisType.X not in self.motors) or (AxisType.Y not in self.motors):
            logger.error(f"Axis XY not initialized")
            return False
        # Move the axis synchronously with asyncio
        tx = asyncio.create_task(
            self._safe_execute(f"move x axis: {xy_distance[0]}",
                                       self.motors[AxisType.X].move_relative(distance=(xy_distance[0]), 
                                                                             wait_for_completion=wait_for_completion)))
        ty = asyncio.create_task(self._safe_execute(f"move x axis: {xy_distance[1]}",
                                       self.motors[AxisType.Y].move_relative(distance=(xy_distance[1]), 
                                                                             wait_for_completion=wait_for_completion)))
        # Wait for each task to finish
        aok, bok = await asyncio.gather(tx, ty)

        # report failure
        if not (aok and bok):
            logger.error(f"move_xy failed: X ok?{aok} Y ok?{bok}")
            return False

        # Update last pos
        self._last_positions[AxisType.X] += xy_distance[0]
        self._last_positions[AxisType.Y] += xy_distance[1]

        return (aok, bok)
    
    @update_stage_position
    async def move_xy_absolute(self, xy_distance: Tuple[float, float], wait_for_completion = True):
        """
        MMC Supports multi-axes movement. Move only xy in tandem for safety. Absolute movement
        
        Args:
            xy_distance: (x,y) Distance you want to move in microns 
            wait_for_completion: key to set for wait for completion, currently only works with key set to True
        """
        # Need xy to be initialized
        if (AxisType.X not in self.motors) or (AxisType.Y not in self.motors):
            logger.error(f"Axis XY not initialized")
            return False
        
        # Move the axis synchronously with asyncio
        tx = asyncio.create_task(
            self._safe_execute(f"move x axis: {xy_distance[0]}",
                                       self.motors[AxisType.X].move_absolute(position=(xy_distance[0]), 
                                                                             wait_for_completion=wait_for_completion)))
        ty = asyncio.create_task(self._safe_execute(f"move x axis: {xy_distance[1]}",
                                       self.motors[AxisType.Y].move_absolute(position=(xy_distance[1]), 
                                                                             wait_for_completion=wait_for_completion)))
        # Wait for each task to finish
        aok, bok = await asyncio.gather(tx, ty)

        # report failure
        if not (aok and bok):
            logger.error(f"move_xy failed: X ok?{aok} Y ok?{bok}")
            return False

        # Update last pos
        self._last_positions[AxisType.X] = xy_distance[0]
        self._last_positions[AxisType.Y] = xy_distance[1]

        return (aok, bok)
    
    @update_stage_position
    @requires_motor
    async def stop_axis(self, axis):
        return await self._safe_execute(f"stop {axis.name}", self.motors[axis].stop())

    @update_stage_position
    async def stop_all_axes(self):
        return {axis: await self.stop_axis(axis) for axis in self.motors}

    @update_stage_position
    async def emergency_stop(self):
        if not self.motors:
            return False
        for axis in AxisType:
            if axis in self.motors:
                await self._safe_execute(f"emergency_stop axis {self.motors[axis]}", self.motors[axis].emergency_stop())
        return True
        
    @requires_motor
    async def get_position(self, axis: AxisType) -> Optional[Position]:
        return await self._safe_execute(f"get_position {axis.name}", self.motors[axis].get_position(), default=None)

    async def get_all_positions(self):
        data = {}
        for axis in AxisType:
            if axis in self.motors:
                pos = await self.get_position(axis)
                data[axis] = pos.actual if pos else 0.0
            else:
                data[axis] = 0.0
        return data

    @requires_motor
    async def get_state(self, axis: AxisType) -> Optional[MotorState]:
        return await self._safe_execute(f"get_state {axis.name}", self.motors[axis].get_state(), default=None)

    async def is_any_axis_moving(self):
        for motor in self.motors.values():
            try:
                if await motor.is_moving():
                    return True
            except:
                pass
        return False

    async def wait_for_all_moves_complete(self, timeout=60.0):
        start = time.time()
        while time.time() - start < timeout:
            if not await self.is_any_axis_moving():
                return True
            await asyncio.sleep(0.1)
        return False

    def get_status(self):
        return {
            'connected': bool(self.motors),
            'initialized_axes': list(self.motors),
            'last_positions': self._last_positions,
            'configuration': self.config.__dict__
        }

    async def disconnect_all(self):
        """Disconnect all motors"""
        for m in self.motors.values():
            await self._safe_execute("disconnect", m.disconnect())
        self.motors.clear()
        self._last_positions.clear()

    @requires_motor
    async def disconnect(self, axis: AxisType):
        """
        Disconnect a single motor

        Args:
            axis[AxisType]: axis you wish to disconnect
        """
        await self._safe_execute("disconnect", axis.disconnect())
        del self.motors[axis]
        del self._last_positions[axis]
