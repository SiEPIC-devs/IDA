# The MIT License (MIT)

# Copyright (c) 2015 Michael Caverley

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
CorvusEco motor controller HAL implementation.

Based on PyOptomip CorvusEco driver:
https://github.com/SiEPIC/SiEPIClab/blob/master/pyOptomip/CorvusEco.py

Original author: Stephen Lin (2014)
HAL adaptation: Cameron Basara (2025)

Aided by Claude for integration and formatting
"""

import asyncio
import time
from typing import Optional, Dict, Tuple, ClassVar, Any
from numpy import nan
import pyvisa as visa

from motors.hal.motors_hal import (
    MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType
)


class CorvusController(MotorHAL):
    """
    Hardware abstraction layer for ITL09 Corvus Eco multi-axis controller.
    
    Manages up to 3 axes (X, Y, Z) with shared VISA connection.
    Multiple instances can be created for different axes on the same controller.
    """
    
    # Shared VISA connections across all instances
    _shared_connections: ClassVar[Dict[str, Any]] = {}
    _shared_rm: ClassVar[Dict[str, visa.ResourceManager]] = {}
    
    AXIS_MAPPING = {
        AxisType.X: 0,
        AxisType.Y: 1,
        AxisType.Z: 2,
    }

    def __init__(
        self,
        axis: AxisType,
        enabled_axes: list[AxisType] = [ax for ax in AXIS_MAPPING.keys()],
        visa_address: str = 'ASRL7::INSTR',
        velocity: float = 5000.0,
        acceleration: float = 20000.0,
        position_limits: Tuple[float, float] = (-50000.0, 50000.0),
        step_size: Optional[Dict[str, float]] = None,
        status_poll_interval: float = 0.05,
        enable_closed_loop: bool = True,
        resource_manager: Optional[visa.ResourceManager] = None,
    ):
        """
        Initialize Corvus HAL interface.
        
        Args:
            axis: The axis THIS instance controls (X, Y, or Z)
            enabled_axes: ALL axes physically connected on the controller
            visa_address: VISA resource string (e.g., 'ASRL3::INSTR')
            velocity: Default velocity in um/s
            acceleration: Default acceleration in um/s²
            position_limits: Software limits (min, max) in um
            step_size: Step sizes per axis (optional)
            status_poll_interval: Motion status polling period in seconds
            enable_closed_loop: Enable encoder closed-loop control
            resource_manager: Existing VISA ResourceManager to reuse (optional)
        """
        super().__init__(axis)
        
        # Dummy axis for connections
        self.dummy_axis = False
        if axis not in (AxisType.X, AxisType.Y, AxisType.Z):
            print(f"CorvusController supports X/Y/Z only, got {axis}")
            print(f"{axis} is a dummy axis")
            self.dummy_axis = True
        
        if not self.dummy_axis:
            for ax in enabled_axes:
                if ax not in (AxisType.X, AxisType.Y, AxisType.Z):
                    raise ValueError(f"enabled_axes must contain only X/Y/Z")
            
            if axis not in enabled_axes:
                raise ValueError(f"axis {axis} must be in enabled_axes {enabled_axes}")
            
            if not 1 <= len(enabled_axes) <= 3:
                raise ValueError(f"enabled_axes must have 1-3 axes, got {len(enabled_axes)}")
        
        self._axes = enabled_axes
        self._num_axes = len(enabled_axes)

        # Configuration
        self._addr = visa_address
        self._vel = float(velocity)
        self._acc = float(acceleration)
        self._limits = position_limits
        self._poll_dt = status_poll_interval
        self._closed_loop = enable_closed_loop
        
        # Step sizes
        default_steps = {
            "step_size_x": 1.0,
            "step_size_y": 1.0,
            "step_size_z": 1.0,
            "step_size_fr": 0.1,
            "step_size_cr": 0.1
        }
        if step_size:
            default_steps.update(step_size)
        self._step = default_steps

        # VISA resources (shared across instances)
        self._external_rm = resource_manager
        self._rm: Optional[visa.ResourceManager] = None
        self._inst = None
        self._connected = False
        
        # State tracking
        self._position_um = [0.0, 0.0, 0.0]
        self._move_in_progress = False

        self._callbacks = []

    def add_callback(self, callback):
        """Add event callback"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def _write(self, cmd: str) -> None:
        """Write command to controller."""
        if not self._inst:
            raise RuntimeError("Not connected")
        self._inst.write(cmd)

    def _query(self, cmd: str) -> str:
        """Query controller and return response."""
        if not self._inst:
            raise RuntimeError("Not connected")
        return self._inst.query(cmd)

    def _read(self) -> str:
        """Read response from controller."""
        if not self._inst:
            raise RuntimeError("Not connected")
        return self._inst.read()

    def _get_error(self) -> str:
        """Get error code from controller."""
        try:
            self._write('ge')
            error_code = self._read().strip()
            return f"Error Code: {error_code} (Refer to Manual Page 165)"
        except Exception as e:
            return f"Failed to retrieve error: {e}"

    def _build_triplet(self, **axis_values) -> str:
        """
        Build position triplet string for Corvus commands.
        
        Args:
            axis_values: Keyword args like x=10.0, y=5.0, z=0.0
            
        Returns:
            Formatted string like "10.000000 5.000000 0.000000"
        """
        triplet = [
            axis_values.get('x', 0.0),
            axis_values.get('y', 0.0),
            axis_values.get('z', 0.0)
        ]
        return f"{triplet[0]:.6f} {triplet[1]:.6f} {(-1)*triplet[2]:.6f}"

    async def connect(self) -> bool:
        """
        Connect to Corvus controller.
        
        First instance to connect performs full hardware initialization.
        Subsequent instances reuse the existing VISA connection.
        """
        if self.dummy_axis:
            print(f"[CorvusController] Dummy axis connected")
            return True
        if self._addr in CorvusController._shared_connections:
            print(f"[CorvusController] {self.axis.name} reusing existing connection")
            self._inst = CorvusController._shared_connections[self._addr]
            self._rm = CorvusController._shared_rm.get(self._addr)
            print(self._inst, self._rm)
            self._connected = True
            return True
        outstr = ("[CorvusController] {self.axis.name} initializing controller for axes:"
                  f"{[ax.name for ax in self._axes]}")
        print(outstr)
        try:
            self._rm = self._external_rm or visa.ResourceManager()
            self._inst = self._rm.open_resource(self._addr)
            
            try:
                self._inst.baud_rate = 57600
            except Exception:
                pass

            # Identify controller - this verifies actual communication
            self._write('identify')
            try:
                id_response = self._read()
                print(f"[CorvusController] Connected: {id_response.strip()}")
            except Exception as e:
                print(f"[CorvusController] Failed to identify controller: {e}")
                raise  # Re-raise to trigger connection failure
            
            # Set dimension and enable axes
            self._write(f'{self._num_axes} setdim')
            
            all_axes = [AxisType.X, AxisType.Y, AxisType.Z]
            enabled_set = set(self._axes)
            
            for axis_type in all_axes:
                axis_num = self.AXIS_MAPPING[axis_type] + 1
                enable = 1 if axis_type in enabled_set else 0
                self._write(f'{enable} {axis_num} setaxis')
            
            print(f"[CorvusController] Enabled {self._num_axes} axes: {[ax.name for ax in self._axes]}")

            # Set units to microns
            for axis_num in range(0, 4):
                self._write(f'1 {axis_num} setunit')
            print("[CorvusController] Units set to microns (um)")

            # Configure acceleration function
            self._write('0 setaccelfunc')
            self._write('1 setout')  # Digital output
            self._write('10 0 1 ot')   # Trigger out

            # Enable closed-loop control
            if self._closed_loop:
                for axis_num in range(1, self._num_axes + 1):
                    self._write(f'1 {axis_num} setcloop')
                print("[CorvusController] Closed-loop enabled")

            # Set velocity and acceleration
            self._write(f'{self._vel:.6f} sv')
            self._write(f'{self._acc:.6f} sa')
            
            try:
                vel_readback = self._query('gv').strip()
                acc_readback = self._query('ga').strip()
                print(f"[CorvusController] Velocity: {vel_readback} um/s, Accel: {acc_readback} um/s2")
            except Exception:
                pass

            # Store shared connection
            CorvusController._shared_connections[self._addr] = self._inst
            CorvusController._shared_rm[self._addr] = self._rm
            
            self._connected = True
            return True

        except Exception as e:
            print(f"[CorvusController] Connection failed: {e}")
            if self._inst:
                try:
                    self._inst.close()
                except Exception:
                    pass
            if self._rm and not self._external_rm:
                try:
                    self._rm.close()
                except Exception:
                    pass
            return False

    async def disconnect(self) -> Optional[bool]:
        """
        Disconnect from controller.
        
        Note: Shared connection remains open if other axis instances are using it.
        """
        try:
            if self.dummy_axis:
                print(f"[CorvusController] Dummy axis disconnected")
                return True
            self._connected = False
            print(f"[CorvusController] {self.axis.name} disconnected (shared connection remains)")
            return True
        except Exception as e:
            print(f"[CorvusController] Disconnect error: {e}")
            return False

    async def move_absolute(
            self, position: float, velocity: Optional[float] = None,
            wait_for_completion = None) -> bool:
        """Move to absolute position."""
        if self.dummy_axis:
            print(f"[CorvusController] Dummy axis m_a")
            return True
        current_pos = await self.get_position()
        delta = position - current_pos.actual
        return await self.move_relative(delta, velocity, wait_for_completion=None)

    async def move_relative(
            self, distance: float, velocity: Optional[float] = None,
            wait_for_completion = None) -> bool:
        """Move relative distance.
            POS Z down, NEG Z up"""
        if self.dummy_axis:
            print(f"[CorvusController] Dummy axis m_r")
            return True
        try:
            axis_idx = self.AXIS_MAPPING[self.axis]
            current = self._position_um[axis_idx]
            target = current + distance

            # Check software limits
            lo, hi = self._limits
            if not (lo <= target <= hi):
                error_msg = f"Move to {target:.2f} um violates limits [{lo}, {hi}]"
                self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
                return False

            # Override velocity if specified
            if velocity is not None:
                self._write(f'{velocity:.6f} sv')

            self._emit_event(MotorEventType.MOVE_STARTED, {
                "axis": self.axis.name,
                "distance_um": distance,
                "target_um": target
            })

            self._move_in_progress = True

            # Build and send move command
            kwargs = {['x', 'y', 'z'][axis_idx]: distance}
            cmd = f"{self._build_triplet(**kwargs)} r"
            self._write(cmd)

            # Wait for move completion
            start_time = time.time()
            timeout = 60.0
            
            while True:
                try:
                    status = self._query('st').strip()
                    moving = (int(status) & 1) == 1
                    if not moving:
                        break
                except Exception:
                    try:
                        positions = self._read_position_triplet()
                        if abs(positions[axis_idx] - target) <= 0.5:
                            break
                    except Exception:
                        pass
                
                if time.time() - start_time > timeout:
                    error_msg = f"Move timeout after {timeout}s"
                    self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
                    self._move_in_progress = False
                    return False
                
                await asyncio.sleep(self._poll_dt)

            # Update position
            self._position_um[axis_idx] = target

            self._move_in_progress = False
            self._emit_event(MotorEventType.MOVE_COMPLETE, {"position_um": target})
            
            return True

        except Exception as e:
            error_msg = f"Move failed: {e}\n{self._get_error()}"
            print(f"[CorvusController] {error_msg}")
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
            self._move_in_progress = False
            return False

    async def stop(self) -> bool:
        """Stop motion immediately."""
        if self.dummy_axis:
            print(f"[CorvusController] Dummy axis stop")
            return True
        try:
            self._write('0 sv')
            await asyncio.sleep(0.1)
            self._write(f'{self._vel:.6f} sv')
            
            self._move_in_progress = False
            self._emit_event(MotorEventType.MOVE_STOPPED, {})
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"Stop failed: {e}"})
            return False

    async def emergency_stop(self) -> bool:
        """Emergency stop."""
        if self.dummy_axis:
            print(f"[CorvusController] Dummy axis estop")
            return True
        return await self.stop()

    async def get_position(self) -> Position:
        """Get current position for this axis."""
        if self.dummy_axis:
            # print(f"[CorvusController] Dummy axis enabled")
            return Position(
                theoretical=nan,
                actual=nan,
                units='um',
                timestamp=time.time()
            )
        try:
            positions = self._read_position_triplet()
            self._position_um = positions
            
            axis_idx = self.AXIS_MAPPING[self.axis]
            actual = positions[axis_idx]
            
            return Position(
                theoretical=actual,
                actual=actual,
                units="um",
                timestamp=time.time()
            )
        except Exception as e:
            print(f"[CorvusController] get_position error ({self.axis}): {e}")
            axis_idx = self.AXIS_MAPPING[self.axis]
            cached = self._position_um[axis_idx]
            return Position(cached, cached, "um", time.time())

    def _read_position_triplet(self) -> list[float]:
        """Read position triplet from controller."""
        self._write('pos')
        response = self._read().strip()
        values = list(map(float, response.split()))
        
        while len(values) < 3:
            values.append(0.0)
        
        return values[:3]

    async def get_state(self) -> MotorState:
        """Query motion state."""
        try:
            status = self._query('st').strip()
            moving = (int(status) & 1) == 1
            return MotorState.MOVING if moving else MotorState.IDLE
        except Exception:
            return MotorState.MOVING if self._move_in_progress else MotorState.IDLE

    async def is_moving(self) -> bool:
        """Check if motor is moving."""
        return (await self.get_state()) == MotorState.MOVING

    async def set_velocity(self, velocity: float) -> bool:
        """Set velocity (applies to all axes on controller)."""
        try:
            self._write(f'{velocity:.6f} sv')
            self._vel = velocity
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"set_velocity failed: {e}"})
            return False

    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration (applies to all axes on controller)."""
        try:
            self._write(f'{acceleration:.6f} sa')
            self._acc = acceleration
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"set_acceleration failed: {e}"})
            return False

    async def get_config(self) -> MotorConfig:
        """Return current motor configuration."""
        return MotorConfig(
            max_velocity=self._vel,
            max_acceleration=self._acc,
            position_limits=self._limits,
            units="um",
            **self._step
        )

    async def home(self, direction: int = 0) -> bool:
        """Home axis (not supported by Corvus Eco hardware)."""
        print("[CorvusController] Homing not supported by Corvus Eco hardware")
        raise NotImplementedError(
            "Corvus Eco controller does not provide homing commands. "
            "Manual homing or physical limit switches may be required."
        )

    async def home_limits(self) -> bool:
        """Home to limits (not supported by Corvus Eco hardware)."""
        print("[CorvusController] Limit homing not supported by Corvus Eco hardware")
        raise NotImplementedError(
            "Corvus Eco controller does not provide limit homing. "
            "Use manual positioning or external limit detection."
        )

    async def set_zero(self) -> bool:
        """Set current position as zero (software only)."""
        axis_idx = self.AXIS_MAPPING[self.axis]
        self._position_um[axis_idx] = 0.0
        print(f"[CorvusController] Zero position set for {self.axis.name}")
        return True

# Register driver with factory
from motors.hal.stage_factory import register_driver
register_driver("Corvus_controller", CorvusController)