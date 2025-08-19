import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum
import time

# Local imports
from motors.hal.motors_hal import AxisType, MotorState, Position, MotorEvent, MotorEventType
#from motors.stage_controller import StageController
from motors.modern_stage import StageControl as StageController
import motors.modern_stage
from motors.hal.stage_factory import create_driver
from motors.config.stage_config import StageConfiguration
from motors.utils.shared_memory import *

"""
Simplified Stage Manager - Fixed Implementation
Cameron Basara, 2025

Key simplifications:
- Removed complex decorators and mixed responsibilities  
- Clear separation of concerns
- Simple event handling
- Reliable shared memory management
- Easy to understand control flow
"""

logger = logging.getLogger(__name__)

class StageManager:
    """
    Simplified stage manager with clear responsibilities:
    1. Motor lifecycle management (connect/disconnect)
    2. High-level movement coordination  
    3. Position monitoring and shared memory updates
    4. Event handling and forwarding
    """
    
    def __init__(self, config: StageConfiguration, create_shm: bool = True, port: int = 8):
        # Core components
        self.config = config
        motors.modern_stage._GLOBAL_COM_PORT = f"COM{port}"
        self.motors: Dict[AxisType, StageController] = {}
        self._event_callbacks: List[Callable[[MotorEvent], None]] = []
        
        # State tracking
        self._last_positions: Dict[AxisType, float] = {}
        self._homed_axes: Dict[AxisType, bool] = {}
        self._is_running = False
        
        # Shared memory setup
        self.create_shm = create_shm
        if create_shm:
            try:
                self.shm_position, self.position_struct = create_shared_stage_position()
                self.shm_config = create_shared_stage_config()
                write_shared_stage_config(self.shm_config, config)
                logger.info("Shared memory initialized")
            except Exception as e:
                logger.warning(f"Shared memory initialization failed: {e}")
                self.create_shm = False
        
        # Background tasks
        self._position_task = None

    # === Context Management ===
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()

    async def startup(self):
        """Start the stage manager"""
        if self._is_running:
            return
            
        self._is_running = True
        
        # Start position monitoring
        if self.create_shm:
            self._position_task = asyncio.create_task(self._position_monitor_loop())
            
        logger.info("Stage manager started")

    async def shutdown(self):
        """Shutdown the stage manager"""
        if not self._is_running:
            return
            
        self._is_running = False
        
        # Stop position monitoring
        if self._position_task:
            self._position_task.cancel()
            try:
                await self._position_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all motors
        await self.disconnect_all()
        
        # Clean up shared memory
        if self.create_shm:
            try:
                if hasattr(self, 'shm_position'):
                    self.shm_position.close()
                    self.shm_position.unlink()
                if hasattr(self, 'shm_config'):
                    self.shm_config.close()
                    self.shm_config.unlink()
            except Exception as e:
                logger.debug(f"Shared memory cleanup: {e}")
        
        logger.info("Stage manager shutdown complete")

    # === Motor Lifecycle ===
    
    async def initialize_axis(self, axis: AxisType) -> bool:
        """Initialize a single axis"""
        try:
            # Get axis configuration
            axis_config = self.config.get_axis_attributes().get(axis)
            if not axis_config:
                logger.error(f"No configuration found for {axis.name}")
                return False
            
            # Create motor controller
            driver_key = axis_config['driver_types']
            motor = create_driver(driver_key, **axis_config)
            
            # Add event callback
            motor.add_callback(self._handle_motor_event)
            
            # Connect motor
            success = await motor.connect()
            if success:
                self.motors[axis] = motor
                self._last_positions[axis] = 0.0
                self._homed_axes[axis] = False
                logger.info(f"Axis {axis.name} initialized successfully")
            else:
                logger.error(f"Failed to connect axis {axis.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing axis {axis.name}: {e}")
            return False

    async def initialize_all(self, axes: List[AxisType] = None) -> bool:
        """Initialize all specified axes"""
        if axes is None:
            axes = [ax for ax in AxisType if ax != AxisType.ALL]
        
        results = []
        for axis in axes:
            result = await self.initialize_axis(axis)
            results.append(result)
        
        success = all(results)
        if success:
            logger.info("All axes initialized successfully")
        else:
            logger.warning("Some axes failed to initialize")
        
        return success

    async def disconnect_axis(self, axis: AxisType) -> bool:
        """Disconnect a single axis"""
        if axis not in self.motors:
            return True
            
        try:
            await self.motors[axis].disconnect()
            del self.motors[axis]
            del self._last_positions[axis]
            del self._homed_axes[axis]
            logger.info(f"Axis {axis.name} disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting axis {axis.name}: {e}")
            return False

    async def disconnect_all(self) -> bool:
        """Disconnect all axes"""
        axes = list(self.motors.keys())
        results = []
        
        for axis in axes:
            result = await self.disconnect_axis(axis)
            results.append(result)
        
        return all(results)

    # === Movement Commands ===
    
    async def move_axis(
        self,
        axis: AxisType,
        position: float,
        relative: bool = False,
        velocity: Optional[float] = None,
        wait_for_completion: bool = True
    ) -> bool:
        """Move a single axis"""
        if axis not in self.motors:
            logger.error(f"Axis {axis.name} not initialized")
            return False
        
        try:
            motor = self.motors[axis]
            
            if relative:
                success = await motor.move_relative(
                    distance=position,
                    velocity=velocity,
                    wait_for_completion=wait_for_completion
                )
                if success:
                    self._last_positions[axis] += position
            else:
                success = await motor.move_absolute(
                    position=position,
                    velocity=velocity,
                    wait_for_completion=wait_for_completion
                )
                if success:
                    self._last_positions[axis] = position
            
            return success
            
        except Exception as e:
            logger.error(f"Move error for axis {axis.name}: {e}")
            return False

    async def move_xy(
        self,
        x_pos: float,
        y_pos: float,
        relative: bool = False,
        wait_for_completion: bool = True
    ) -> bool:
        """Move X and Y axes together"""
        if AxisType.X not in self.motors or AxisType.Y not in self.motors:
            logger.error("X or Y axis not initialized")
            return False
        
        try:
            # Create movement tasks
            x_task = asyncio.create_task(
                self.move_axis(AxisType.X, x_pos, relative, wait_for_completion=wait_for_completion)
            )
            y_task = asyncio.create_task(
                self.move_axis(AxisType.Y, y_pos, relative, wait_for_completion=wait_for_completion)
            )
            
            # Execute moves simultaneously
            x_result, y_result = await asyncio.gather(x_task, y_task)
            
            success = x_result and y_result
            if success:
                logger.info(f"XY move completed: ({x_pos}, {y_pos}) {'relative' if relative else 'absolute'}")
            else:
                logger.error(f"XY move failed: X={x_result}, Y={y_result}")
            
            return success
            
        except Exception as e:
            logger.error(f"XY move error: {e}")
            return False

    async def stop_axis(self, axis: AxisType) -> bool:
        """Stop a single axis"""
        if axis not in self.motors:
            return False
        
        try:
            return await self.motors[axis].stop()
        except Exception as e:
            logger.error(f"Stop error for axis {axis.name}: {e}")
            return False

    async def stop_all(self) -> bool:
        """Stop all axes"""
        results = []
        for axis in self.motors:
            result = await self.stop_axis(axis)
            results.append(result)
        return all(results)

    async def emergency_stop(self) -> bool:
        """Emergency stop all axes"""
        results = []
        for motor in self.motors.values():
            try:
                result = await motor.emergency_stop()
                results.append(result)
            except Exception as e:
                logger.error(f"Emergency stop error: {e}")
                results.append(False)
        return all(results)

    # === Homing ===
    
    async def home_axis(self, axis: AxisType, direction: int = 0) -> bool:
        """Home a single axis"""
        if axis not in self.motors:
            logger.error(f"Axis {axis.name} not initialized")
            return False
        
        try:
            success = await self.motors[axis].home(direction)
            if success:
                self._homed_axes[axis] = True
                self._last_positions[axis] = 0.0
                logger.info(f"Axis {axis.name} homed successfully")
            else:
                self._homed_axes[axis] = False
                logger.error(f"Failed to home axis {axis.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Homing error for axis {axis.name}: {e}")
            self._homed_axes[axis] = False
            return False

    async def home_limits(self, axis: AxisType) -> Tuple[bool, Optional[Tuple[float, float]]]:
        """Home axis limits"""
        if axis not in self.motors:
            logger.error(f"Axis {axis.name} not initialized")
            return False, None
        
        try:
            # Special handling for Z axis safety
            if axis == AxisType.Z and AxisType.Y in self.motors:
                # Move Y to safe position before homing Z
                y_limits = self.config.position_limits.get(AxisType.Y, (0, 10000))
                await self.move_axis(AxisType.Y, y_limits[1], wait_for_completion=True)
            
            success, limits = await self.motors[axis].home_limits()
            if success:
                self._homed_axes[axis] = True
                # Update configuration with new limits
                self.config.position_limits[axis] = limits
                logger.info(f"Axis {axis.name} limits homed: {limits}")
            else:
                self._homed_axes[axis] = False
            
            return success, limits
            
        except Exception as e:
            logger.error(f"Home limits error for axis {axis.name}: {e}")
            self._homed_axes[axis] = False
            return False, None

    # === Status and Position ===
    
    async def get_position(self, axis: AxisType) -> Optional[Position]:
        """Get position of a single axis"""
        if axis not in self.motors:
            return None
        
        try:
            return await self.motors[axis].get_position()
        except Exception as e:
            logger.error(f"Position read error for axis {axis.name}: {e}")
            return None

    async def get_all_positions(self) -> Dict[AxisType, float]:
        """Get positions of all axes"""
        positions = {}
        for axis in self.motors:
            pos = await self.get_position(axis)
            positions[axis] = pos.actual if pos else 0.0
        return positions

    async def get_state(self, axis: AxisType) -> Optional[MotorState]:
        """Get state of a single axis"""
        if axis not in self.motors:
            return None
        
        try:
            return await self.motors[axis].get_state()
        except Exception as e:
            logger.error(f"State read error for axis {axis.name}: {e}")
            return None

    async def is_any_moving(self) -> bool:
        """Check if any axis is moving"""
        for motor in self.motors.values():
            try:
                if await motor.is_moving():
                    return True
            except Exception:
                pass
        return False

    async def wait_for_all_complete(self, timeout: float = 60.0) -> bool:
        """Wait for all moves to complete"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not await self.is_any_moving():
                return True
            await asyncio.sleep(0.1)
        return False

    # === Event Handling ===
    
    def add_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Add event callback"""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[MotorEvent], None]):
        """Remove event callback"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def _handle_motor_event(self, event: MotorEvent):
        """Handle events from motor controllers"""
        # Update position cache if it's a move completion
        if event.event_type == MotorEventType.MOVE_COMPLETE:
            if 'position' in event.data:
                self._last_positions[event.axis] = event.data['position']
        
        # Forward event to all callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    # === Background Tasks ===
    
    async def _position_monitor_loop(self):
        """Background task to monitor positions and update shared memory"""
        logger.info("Position monitor started")
        
        while self._is_running:
            try:
                if not self.motors:
                    await asyncio.sleep(1.0)
                    continue
                
                # Update positions in shared memory
                for axis, motor in self.motors.items():
                    try:
                        pos = await motor.get_position()
                        if pos:
                            self._last_positions[axis] = pos.actual
                            # Update shared memory position
                            if self.create_shm:
                                shm, raw = open_shared_stage_position()
                                sp = StagePosition(shared_struct=raw)
                                sp.set_positions(axis, pos.actual)
                                del sp
                                del raw
                                shm.close()
                    except Exception as e:
                        logger.debug(f"Position monitor error for {axis.name}: {e}")
                
                await asyncio.sleep(0.1)  # 10Hz update rate
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(1.0)
        logger.info("Position monitor stopped")

    # === Status and Info ===
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        return {
            'is_running': self._is_running,
            'connected_axes': list(self.motors.keys()),
            'homed_axes': {axis: homed for axis, homed in self._homed_axes.items() if homed},
            'last_positions': self._last_positions.copy(),
            'create_shm': self.create_shm
        }

    def is_axis_homed(self, axis: AxisType) -> bool:
        """Check if axis is homed"""
        return self._homed_axes.get(axis, False)

    def is_axis_connected(self, axis: AxisType) -> bool:
        """Check if axis is connected"""
        return axis in self.motors