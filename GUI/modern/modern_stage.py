import asyncio
import time
from typing import Optional, Dict, Any, Tuple, Callable
# from dataclasses import replace
import threading
from concurrent.futures import ThreadPoolExecutor
# import numpy as np

from modern.hal.motors_hal import MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType, MotorEvent
import serial


"""
Made by: Cameron Basara, 5/30/2025

Prototype implementation of Stage control at 347 using more modern Python features and the motor hardward abstraction layer
"""

# CONSTANTS
_GLOBAL_COM_PORT = "/dev/ttyUSB0"
_GLOBAL_BAUDRATE = 38400
_GLOBAL_TIMEOUT = 0.3  # seconds

_serial_lock = threading.Lock() # Guard read / write at serial port
_global_serial_port = None

def _get_shared_serial(): 
    """
    Open or return the shared lock, all axis use this since they share a serial port
    """
    global _global_serial_port

    if _global_serial_port is None:
        _global_serial_port = serial.Serial(
            port=_GLOBAL_COM_PORT,
            baudrate=_GLOBAL_BAUDRATE,
            timeout=_GLOBAL_TIMEOUT
        )
    return _global_serial_port


class StageControl(MotorHAL):
    """
    Each StageControl instance drives exactly one axis (AxisType.x, etc) through
    an MMC100 style serial protocol. Internally, blocking I/O calls are offloaded 
    to a single thread ThreadPoolExecutor, but all instances share a single serial
    port, and hence share a serial lock so that r/w overlap never happens.

    Emits MOVE_STARTED, MOVE_COMPLETED and HOMED events for higher layers. 
    """
    # Axis Mapping
    AXIS_MAP = {
            AxisType.X: 1,
            AxisType.Y: 2,
            AxisType.Z: 3,
            AxisType.ROTATION_FIBER: 4,
            AxisType.ROTATION_CHIP: 5,
            AxisType.ALL: 0
            }
    
    def __init__(self, axis : AxisType, com_port: str = _GLOBAL_COM_PORT,
                 baudrate: int = _GLOBAL_BAUDRATE, timeout: float = _GLOBAL_TIMEOUT,
                 velocity: float = 1000.0, acceleration: float = 5000.0,
                 position_limits: Tuple[float, float] = (-50000.0, 50000.0),
                 step_size: Dict[str, float] = {'step_size_x': 1,
                                                'step_size_y': 1,
                                                'step_size_z': 1,
                                                'step_size_fr': 0.1,
                                                'step_size_cr': 0.1},
                 position_tolerance: float = 1.0,  # um tolerance for move completion
                 status_poll_interval: float = 0.05):  # seconds between status checks
        
        super().__init__(axis)
        
        # Serial config 
        self.com_port = com_port
        self.baudrate = baudrate
        self.timeout = timeout

        # Thread pool for blocking operations
        self._executor = ThreadPoolExecutor(max_workers=1)
        
        # Serial connection (shared across all axes)
        self._serial_lock = _serial_lock
        self._serial_port = None
        self._is_connected = False
        
        # Passing params
        self._velocity = velocity  # um/s default
        self._acceleration = acceleration  # um/s^2 default
        self._position_limits = position_limits  # um
        self._step_size = step_size # (um, um)
        self._position_tolerance = position_tolerance  # um
        self._status_poll_interval = status_poll_interval  # seconds
        
        # State tracking
        self._last_position = 0.0 
        self._is_homed = False
        self._move_in_progress = False
        self._target_position = None
        self._placeholder = ''
        # self._axis_grid: Tuple[float, float] = ()
    
    async def connect(self):
        """ 
        Built to match the SiEPIC code base setup, more simple approach
        
        Initialize connection to the global serial port
        """
        def _connect():
            try:
                if not self._serial_port:
                    self._serial_port = _get_shared_serial()
                
                if not self._serial_port.is_open:
                    self._serial_port.open()

                # Init axis
                self._send_command(f"{self.AXIS_MAP[self.axis]}FBK3")  # Closed loop mode
                time.sleep(0.1)
                self._send_command(f"{self.AXIS_MAP[self.axis]}VEL{self._velocity * 0.001}")  # Set velocity
                time.sleep(0.1)

                # Connection successful
                self._is_connected = True 
                return True
            
            except Exception as e:
                print(f"Connection unsuccessful {e}")
                return False
        
        return await asyncio.get_event_loop().run_in_executor(self._executor, _connect)
    
    async def disconnect(self):
        """
        Clean up resources, SiEPIC Stage compatible
        """
        if self._serial_port and self._serial_port.is_open:
            self._serial_port.close()
        self._executor.shutdown(wait=True) 
    
    def _send_command(self, cmd : str) -> str:
        """
        Send a command to the motor drivers via serial, opt receive response
        """
        with self._serial_lock:
            if not self._serial_port or not self._serial_port.is_open:
                raise ConnectionError("Serial port not connected")

            # print(f"cmd: {cmd}")
            self._serial_port.write((cmd + "\r").encode('ascii')) # maybe
            time.sleep(0.05)  # Small delay for command processing
            
            # Read response if available
            response = ""
            if self._serial_port.in_waiting > 0:
                response = self._serial_port.read_until(b'\r\n').decode('ascii').strip()
                
            return response
     
    def _query_command(self, cmd : str) -> str:
        """
        Send query command and wait for response
        """
        with self._serial_lock:
            if not self._serial_port or not self._serial_port.is_open:
                raise ConnectionError("Serial port not connected")
            
            # Clear everything first
            self._serial_port.reset_input_buffer()
            self._serial_port.reset_output_buffer()

            # print(f"Querying {cmd}")
            self._serial_port.write((cmd + "\r").encode('ascii'))   
            time.sleep(0.05)
            self._serial_port.flush()          
            time.sleep(0.05)  # Small delay for command processing

            if "STA?" in cmd:
                raw = self._serial_port.read_until(b"\n\r")
                text = raw.decode('ascii').strip()
                
                if len(text) == 0:
                    return str(0)  # Default to moving if no response
                
                # Parse status number (remove # prefix)
                status_number = int(text.strip('#'))
                status_bit = (status_number >> 3) & 1 # bit 3 is stopped when 1
                return str(status_bit)

            elif "POS?" in cmd:
                raw = self._serial_port.read_until(b"\n\r")
                text = raw.decode('ascii').strip()
                # print(f"POS raw: {text}")
                
                if len(text) == 0:
                    raise Exception("No data received")
                
                # Remove # prefix and split
                clean_text = text.strip('#')
                values = clean_text.split(',')
                return values

    # MOVEMENT
    async def move_absolute(self, position, velocity=None, wait_for_completion=True):
        """
        Move to absolute position in microns
        
        Args:
            position: Target position in microns
            velocity: Optional velocity override
            wait_for_completion: If True, wait for move to complete and emit MOVE_COMPLETED event
        """
        def _move():
            try:
                if velocity:
                    self._send_command(f"{self.AXIS_MAP[self.axis]}VA{velocity:.6f}")

                if self.axis == AxisType.ROTATION_FIBER:
                    # Map from deg to mm
                    lim = self._position_limits[1]
                    distance = (45 - position) * (lim / 45) 
                    position_mm = distance * 0.001
                    print(position_mm)
                else:
                    # Convert um to mm
                    position_mm = position * 0.001

                # Safety (Previously handled m way, don't know why)
                lo, hi = self._position_limits
                # if abs(position_mm) >= 1e-6 and abs(position_mm) <= (1000-1e-6):
                if position >= lo and position <= hi: 
                    self._send_command(f"{self.AXIS_MAP[self.axis]}MVA{position_mm:.6f}")

                    # Wait for movement
                    if wait_for_completion:
                        while True:
                            response = self._query_command(f"{self.AXIS_MAP[self.axis]}STA?") 
                            status = int(response)
                            if status == 1:
                                break
                            time.sleep(0.1) 
                else:
                    raise Exception(f"Distance entered exceeds softlimits, must be within bounds : {lo} <= {position} <= {hi}")

                # Update state tracking
                self._move_in_progress = True
                self._target_position = position

                # Event handling
                self._emit_event(MotorEventType.MOVE_STARTED, {
                    'target_position': position,
                    'velocity': velocity or self._velocity,
                    'operation': 'absolute_move'
                })

                return True 
            
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False
        
        return await asyncio.get_event_loop().run_in_executor(self._executor, _move)
        
    async def move_relative(self, distance, velocity=None, wait_for_completion=True):
        """
        Move to rel pos in microns
        
        Args:
            distance: Distance to move in microns
            velocity: Optional velocity override  
            wait_for_completion: If True, wait for move to complete and emit MOVE_COMPLETED event
        """
        def _move_rel():
            try:
                if velocity:
                    self._send_command(f"{self.AXIS_MAP[self.axis]}VA{velocity:.6f}")
                
                
                # Convert um to mm
                distance_mm = distance * 0.001

                # Safety
                lo, hi = self._position_limits
                pos = self._last_position + distance  

                # Event handling
                self._emit_event(MotorEventType.MOVE_STARTED, {
                    "target_position": pos,
                    "distance": distance,
                    "velocity": velocity or self._velocity,
                    "operation": "relative_move"
                })
                
                if pos >= lo and pos <= hi:  
                    self._send_command(f"{self.AXIS_MAP[self.axis]}MVR{distance_mm:.6f}") 
                    # Wait for movement
                    if wait_for_completion:
                        while True:
                            response = self._query_command(f"{self.AXIS_MAP[self.axis]}STA?") 
                            status = int(response)
                            if status == 1:
                                break
                            time.sleep(0.1)
                else:
                    raise Exception(f"Relative distance entered exceeds softlimits, must be within bounds : {lo} <= {distance} <= {hi}")

                self._target_position = pos
                self._last_position = pos
                self._emit_event(MotorEventType.MOVE_COMPLETE, {
                    "target_position": pos,
                    "distance": distance, # this isnt right
                    "velocity": velocity or self._velocity,
                    "operation": "relative_move"
                })

                return pos
                    
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return None
        
        return await asyncio.get_event_loop().run_in_executor(self._executor, _move_rel)
    
    async def stop(self):
        """
        Stop motor motion
        """
        def _stop():
            try:
                self._send_command(f"{self.AXIS_MAP[self.axis]}STP")
                self._move_in_progress = False
                self._target_position = None
                return True
            except Exception as e:
                print(f"Stop error: {e}")
                return False
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _stop)

    async def emergency_stop(self):
        """
        Emergency stop axis
        """
        def _estop():
            try:
                self._send_command(f"{self.AXIS_MAP[self.axis]}EST")  # Stop axes
                self._move_in_progress = False
                self._target_position = None
                return True
            except Exception as e:
                print(f"Emergency stop error: {e}")
                return False
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _estop)

    # Status and Position
    async def get_position(self):
        """
        Get current position
        """
        def _get_pos():
            try:
                response = self._query_command(f"{self.AXIS_MAP[self.axis]}POS?")

                
                # Parse response: "position,encoder_position"
                # parts = response.split(',')
                theoretical_mm = float(response[0])
                actual_mm = float(response[1])  
                
                # Convert mm to um
                theoretical_um = theoretical_mm * 1000
                actual_um = actual_mm * 1000
                
                # Update cached position
                self._last_position = actual_um
                
                return Position(
                    theoretical=theoretical_um,
                    actual=actual_um,
                    units="um",
                    timestamp=time.time()
                )
                
            except Exception as e:
                print(f"Position read error: {e}")
                return Position(0.0, 0.0, "um", time.time())
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get_pos)

    async def get_state(self):
        """
        Get current motor state
        """
        def _get_state():
            try:
                response = self._query_command(f"{self.AXIS_MAP[self.axis]}STA?")
                status_int = int(response)
                
                # Check bit 3 (moving[0]/stopped[1])
                if status_int == 1:
                    return MotorState.IDLE
                
                return MotorState.MOVING # else
                    
            except Exception as e:
                print(f"State read error: {e}")
                return MotorState.ERROR
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _get_state)

    async def is_moving(self):
        """
        Check if motor is moving
        """
        state = await self.get_state()
        return state == MotorState.MOVING
    
    # Configuration
    async def set_velocity(self, velocity):
        """
        Set velocity in um/s
        """
        def _set_vel():
            try:
                # Convert um/s to mm/s for controller
                vel_mm_s = velocity * 0.001
                self._send_command(f"{self.AXIS_MAP[self.axis]}VEL{vel_mm_s:.6f}")
                self._velocity = velocity
                return True
            
            except Exception as e:
                print(f"Set velocity error: {e}")
                return False
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _set_vel)
    
    async def set_acceleration(self, acceleration):
        """
        Set acceleration in um/s2
        """
        def _set_acc():
            try:
                # Convert um/s2 to mm/s2 for controller
                acc_mm_s2 = acceleration * 0.001
                self._send_command(f"{self.AXIS_MAP[self.axis]}ACC{acc_mm_s2:.6f}")
                self._acceleration = acceleration
                return True
            
            except Exception as e:
                print(f"Set acceleration error: {e}")
                return False
        return await asyncio.get_event_loop().run_in_executor(self._executor, _set_acc)
    
    async def get_config(self):
        """
        Get motor configuration
        """
        units = "degrees" if self.axis in [AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP] else "um"
        
        return MotorConfig (
            max_velocity=self._velocity,
            max_acceleration=self._acceleration,
            position_limits=self._position_limits,
            units=units,
            **self._step_size
        )
    
    # Home and limits
    async def home(self, direction=0):
        """
        Home the axis
        """
        def _home():
            try:
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing'})
                self._move_in_progress = True # Set move to true
                self._is_homed = False # Set homed to false
                start_time = time.time()

                if direction == 0:
                    self._send_command(f"{self.AXIS_MAP[self.axis]}MLN")  # Move to negative limit
                else:
                    self._send_command(f"{self.AXIS_MAP[self.axis]}MLP")  # Move to positive limit
                
                # Wait for completion
                while True:
                    response = self._query_command(f"{self.AXIS_MAP[self.axis]}STA?") 
                    status = int(response)
                    if status == 1: break
                    time.sleep(0.3)
                    if abs(time.time() - start_time) > 30.0:
                        break
                
                # Set zero point
                if direction == 0:
                    print("Set zero point")
                    self._send_command(f"{self.AXIS_MAP[self.axis]}ZRO")
                    self._is_homed = True # todo: check if homed is for specific axis, check super config may be fine
                    self._last_position = 0.0   # Reset position tracking
                else:
                    # For homing purposes, it should always be the negative limit
                    print("Set positive limit")
                    pos = self._query_command(f"{self.AXIS_MAP[self.axis]}POS?")
                    self._last_position = float(pos[0]) * 1000.0 # mm to um
                    self._position_limits = (self._position_limits[0], self._last_position)
                    print(f"last pos: {self._last_position}")
                    self._is_homed = True

                self._emit_event(MotorEventType.HOMED, {'direction': direction})
                return True
                
            except Exception as e:
                if self._is_homed == True:
                    print("Exception caught but homing complete")
                    return True
                
                print(f"Homing error: {e}\n")
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _home)
    
    async def home_limits(self):
        """
        Home both ends of this axis, and set self._position_limits accordingly.
        After this runs, `neg_limit_um` will be 0.0 (since we ZRO there),
        and `pos_limit_um` will be the travel length in um.
        """
        # Declare axis for each private method usage
        axis_num = self.AXIS_MAP[self.axis]

        def _get_limits():
            """Get limit positions"""
            try:
                # Homing is starting
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing_limits'})

                
                # Send MLN to drive until negative limit is hit
                self._send_command(f"{axis_num}MLN")

                # Wait for completion
                while True:
                    response = self._query_command(f"{axis_num}STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    time.sleep(0.1)

                # Zero neg limit, zeros by default so becomes 0 mm
                self._send_command(f"{axis_num}ZRO")

                # After ZRO, the controller’s internal position registers read zero at this point
                bottom_zero_um = 0.0 # set bottom limit as controllers iternal position limit register
                self._last_position = bottom_zero_um 

                # Move pos limit switch
                self._send_command(f"{axis_num}MLP")

                # Wait for completion
                while True:
                    response = self._query_command(f"{axis_num}STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    time.sleep(0.1)

                # Read position at positive end
                pos_resp2 = self._query_command(f"{axis_num}POS?")
                top_mm = float(pos_resp2[0])
                top_um = top_mm * 1000.0 # Convert
                self._last_position = top_um

                # Software lims set
                self._position_limits = (bottom_zero_um, top_um)

                # Notify that homing, limit-finding is complete
                self._emit_event(MotorEventType.HOMED, {'limits_um': self._position_limits})
                return True

            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False
            
        def _mid_point():
            """Go to mid point"""
            try:
                mid_point = (self._position_limits[1] - self._position_limits[0]) / 2
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'middling'})
                self._send_command(f"{axis_num}MVA{(mid_point/1000):.6f}")
                
                # Wait for completion
                while True:
                    response = self._query_command(f"{axis_num}STA?")
                    status = int(response)
                    pos = self._query_command(f"{axis_num}POS?")
                    pos = float(pos[1])
                    pos_um = pos * 1000.0 # Convert
                    
                    # If position reaches mid point, or movement has stopped and its accurate to 0.001 mm 
                    if (pos_um == mid_point) or (status == 1): # messy
                        break
                    time.sleep(0.1)

                # Get current position
                self._emit_event(MotorEventType.MOVE_COMPLETE, {'pos': self._position_limits})
                self._last_position = pos_um
                return True
        
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False
        
        def _home_limits():
            """Get position limits, go to mid point"""
            try:
                while not _get_limits():
                    continue
                while not _mid_point():
                    continue
                return True, self._position_limits
            
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False, None

        return await asyncio.get_event_loop().run_in_executor(self._executor, _home_limits)

    async def set_zero(self):
        """Set current position as zero"""
        def _set_zero():
            try:
                self._send_command(f"{self.AXIS_MAP[self.axis]}ZRO")
                self._last_position = 0.0  # Reset position tracking
                return True
            except Exception as e:
                print(f"Set zero error: {e}")
                return False
                
        return await asyncio.get_event_loop().run_in_executor(self._executor, _set_zero)

    # Additional utility methods
    async def wait_for_move_completion(self, timeout: float = 30.0) -> bool:
        """
        Wait for any current move to complete
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if move completed successfully, False if timeout or error
        """
        start_time = time.time()
        
        while self._move_in_progress and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        return not self._move_in_progress
    
    def get_move_status(self) -> Dict[str, Any]:
        """
        Get current move status
        
        Returns:
            Dictionary with move status information
        """
        return {
            'move_in_progress': self._move_in_progress,
            'target_position': self._target_position,
            'last_position': self._last_position,
            'position_tolerance': self._position_tolerance
        }

from modern.hal.stage_factory import register_driver

# Register 347 motor stage
register_driver("stage_control", StageControl)