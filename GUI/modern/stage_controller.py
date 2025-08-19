import asyncio
import serial_asyncio
import logging
from typing import Optional, Dict, Any, Tuple, Callable
from time import monotonic

from modern.hal.motors_hal import MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType, MotorEvent

"""
Made by: Cameron Basara, 6/16/2025

Implementation of stage controller at 347 using asyncio for concurrent programming.

Inherits from the motor hardware abstraction layer.
"""

# CONSTANTS : To be changed later ?
GLOBAL_COM_PORT = "/dev/ttyUSB0"
GLOBAL_BAUDRATE = 38400
GLOBAL_TIMEOUT = 0.05  # seconds

# No shared serial lock, using asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)

class StageControl(MotorHAL):
    """
    Asyncio-based StageControl for MMC100 piezo stage found at 347.
    Eliminates ThreadPoolExecutor in favor of serial_asyncio and an asyncio.Lock
    to serialize moves (when desired)
    """
    AXIS_MAP = {
        AxisType.X: 1,
        AxisType.Y: 2,
        AxisType.Z: 3,
        AxisType.ROTATION_FIBER: 4,
        AxisType.ROTATION_CHIP: 5,
    }

    def __init__(self, axis : AxisType, com_port: str = GLOBAL_COM_PORT,
                 baudrate: int = GLOBAL_BAUDRATE, timeout: float = GLOBAL_TIMEOUT,
                 velocity: float = 2000.0, acceleration: float = 5000.0,
                 position_limits: Tuple[float, float] = (0.0, 10000.0), # arb
                 position_tolerance: float = 1.0,  # um tolerance for move completion
                 poll_interval: float = 0.05):  # seconds between status checks
        super().__init__(axis)

        # Serial + Asyncio config
        self.port = com_port
        self.baudrate = baudrate
        self.poll_interval = poll_interval
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None
        self._move_lock = asyncio.Lock() # Queue of waiters in the event loop
        self._io_lock = asyncio.Lock() # Queue for send or query commands 
        self._target_position: float = 0.0
        self._is_connected: bool = False

        # Passing params
        self._velocity = velocity  # um/s default
        self._acceleration = acceleration  # um/s^2 default
        self._position_limits = position_limits  # um
        self._position_tolerance = position_tolerance  # um
        self._status_poll_interval = poll_interval  # seconds

        # Helpers
        self._axis = self.AXIS_MAP[self.axis]

    async def connect(self):
        """
        Establish serial connection to a motor
        """
        try:
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.port, baudrate=self.baudrate
            )
            
            # Init axis
            await self._send_command(f"{self._axis}FBK3")  # Closed loop mode
            await asyncio.sleep(0.05)
            await self._send_command(f"{self._axis}VEL{self._velocity * 0.001}")  # Set velocity
            await asyncio.sleep(0.05)

            self._is_connected = True
            logger.info(f"Connection successful on axis {self._axis}")
            return True
        
        except Exception as e:
            logger.error(f"Connection error {e} on axis {self._axis}")
            return False
    
    async def disconnect(self): 
        """
        Close serial connection and clean up. 
        """
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            self._reader = None
            self._writer = None
            self._is_connected = False
    
    async def _send_command(self, cmd : str) -> str:
        """
        Send a command to the motor drivers via serial, opt receive response
        """
        # Call the lock in higher level methods, estop, abs move etc.
        async with self._io_lock:
            if not self._writer:
                raise ConnectionError(f"Serial port not connected at {self._axis}")

            # Write cmd to port with MMC100 style
            logger.info(f"cmd: {cmd}")
            self._writer.write((cmd + "\r").encode('ascii'))
            await self._writer.drain()  

            # Optional response
            try:
                response = await asyncio.wait_for(self._reader.read_until(b'\r\n'), timeout=0.01) 
                return response.decode('ascii').strip()
            except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                return ""
    
    async def _query_command(self, cmd: str) -> str:
        """
        Send query command and wait for response
        """
        # Call the lock in higher level methods, estop, abs move etc.
        async with self._io_lock:
            if not self._writer:
                raise ConnectionError(f"Serial port not connected at {self._axis}")
            
            # Write a query to serial port
            await self._writer.write((cmd + "\r").encode('ascii'))
            await asyncio.sleep(0.05) # small delay for cmd processing 
            await self._writer.drain()
            await asyncio.sleep(0.05)  

            # Status query
            if "STA?" in cmd:
                raw = await self._reader.read_until(b"\n\r")
                text = raw.decode('ascii').strip()

                if len(text) == 0:
                    return str(0) # Default to moving if no resp

                # Parse status number, remove # prefix
                status_num = int(text.strip('#'))
                status_bit = (status_num >> 3) & 1 # Bit 3 is status bit (1 == stopped)
                return str(status_bit)
            
            # Position query
            elif "POS?" in cmd:
                raw = await self._reader.read_until(b"\n\r")
                text = raw.decode('ascii').strip()

                if len(text) == 0:
                    raise Exception("No data received")

                # Remove # prefix, split data
                clean_text = text.strip('#')
                values = clean_text.split(',')
                return values

    #################################  MOVEMENT  #################################

    async def move_absolute(
            self,
            position: float,
            velocity: Optional[float] = None,
            wait_for_completion: bool = True,
            timeout: float = 60.0 # remember to update hal after
            ) -> bool:
        """
        Move to absolute position in microns
        
        Args:
            position: Target position in microns
            velocity: Optional velocity override
            wait_for_completion: If True, wait for move to complete and emit MOVE_COMPLETE event
        """
        # For timeout purpose
        loop = asyncio.get_event_loop()
        start = loop.time()

        try:
            # Set vel if given
            if velocity:
                await self._send_command(f"{self._axis}VA{velocity:.6f}")

            # Emit event and set target
            self._target_position = position
            self._emit_event(MotorEventType.MOVE_STARTED, {
                'target_position': position,
                'velocity': velocity or self._velocity,
                'operation': 'move_absolute'
            })

                # If axis is set to fiber rotation, we accept cmd in deg
            if self.axis == AxisType.ROTATION_FIBER:
                # Map from deg to mm
                lim = self._position_limits[1]
                distance = (45 - position) * (lim / 45) 
                position_mm = distance * 0.001
                logger.info(position_mm)
            else:
                # Convert um to mm for MMC cmd
                position_mm = position * 0.001

            # Verify bounds
            lo, hi = self._position_limits

            # Use blocking queue 
            async with self._move_lock:
                # Bounds
                if position >= lo and position <= hi: 
                    await self._send_command(f"{self._axis}MVA{position_mm:.6f}")
                else:
                    raise Exception(f"Distance entered exceeds softlimits, must be within bounds : {lo} <= {position} <= {hi}")
                
                # Wait for movement to complete
                if wait_for_completion:
                    while True:
                        response = await self._query_command(f"{self._axis}STA?") 
                        status = int(response)
                        if status == 1:
                            break
                        if loop.time() - start > timeout: # timeout claus
                            return False
                        await asyncio.sleep(0.1)
            
            # Event handling
            self._emit_event(MotorEventType.MOVE_COMPLETE, {
                'position': position,
                'operation': 'move_absolute',
                'status': True
            })
            return True
        
        except Exception as e:
            # Event handling
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': e,
                'operation': 'move_absolute',
                'status': False
            })
            logger.error(f"Move error {e} on axis {self._axis}")
            return False
        
    async def move_relative(
            self, 
            distance: float, 
            velocity: Optional[float] = None,
            wait_for_completion: bool = True,
            timeout: float = 60.0) -> bool:
        """
        Move to rel pos in microns
    
        Args:
            distance: Distance to move in microns
            velocity: Optional velocity override  
            wait_for_completion: If True, wait for move to complete and emit MOVE_COMPLETE event
        """
            # For timeout purpose
        loop = asyncio.get_event_loop()
        start = loop.time()

        try:
            # Set vel if given
            if velocity:
                await self._send_command(f"{self._axis}VA{velocity:.6f}")

            pos = self._last_position + distance

            # Emit event and set target
            self._target_position = pos
            self._emit_event(MotorEventType.MOVE_STARTED, {
                'target_position': pos,
                'velocity': velocity or self._velocity,
                'operation': 'move_relative'
            })

            # Use blocking queue 
            async with self._move_lock:
                # Verify bounds
                lo, hi = self._position_limits

                # If axis is set to fiber rotation, we accept cmd in deg
                if self.axis == AxisType.ROTATION_FIBER:
                    # Map from deg to mm
                    lim = self._position_limits[1]
                    distance = (45 - distance) * (lim / 45) 
                    position_mm = distance * 0.001
                else:
                    # Convert um to mm for MMC cmd
                    position_mm = distance * 0.001

                # Bounds
                if pos >= lo and pos <= hi: 
                    await self._send_command(f"{self._axis}MVR{position_mm:.6f}")
                else:
                    raise Exception(f"Distance entered exceeds softlimits, must be within bounds : {lo} <= {distance} <= {hi}")
                
                # Wait for movement to complete
                if wait_for_completion:
                    while True:
                        response = await self._query_command(f"{self._axis}STA?") 
                        status = int(response)
                        if status == 1:
                            break
                        if loop.time() - start > timeout: # timeout claus
                            return False
                        await asyncio.sleep(0.1)
            
            # Event handling
            self._emit_event(MotorEventType.MOVE_COMPLETE, {
                'distance': distance,
                'operation': 'move_relative',
                'status': True
            })
            return True
        
        except Exception as e:
            # Event handling
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': e,
                'operation': 'move_relative',
                'status': False
            })
            logger.error(f"Move error {e} on axis {self._axis}")
            return False
            
    async def stop(self):
        """
        Stop (single axis) motor motion
        """
        try:
            # Await stop and emit event
            await self._send_command(f"{self._axis}STP")
            self._target_position = None

            self._emit_event(MotorEventType.MOVE_STOPPED, {
                    'position': await self.get_position(),
                    'operation': 'move_stopped',
                    'status': True
                })
            return True
        
        except Exception as e:
            # Event handling
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': e,
                'operation': 'move_stopped',
                'status': False
            })
            logger.error(f"Error in stop {e} for axis {self._axis}")
            return False
        
    async def emergency_stop(self) -> bool:
        """
        Emergency stop axis
        """
        try:
            await self._send_command(f"{self._axis}EST")
            self._target_position = None

            self._emit_event(MotorEventType.MOVE_STOPPED, {
                    'position': await self.get_position(),
                    'operation': 'emergency_stop',
                    'status': True
                })
            return True
        
        except Exception as e:
            # Event handling
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': e,
                'operation': 'emergency_stop',
                'status': False
            })
            logger.error(f"Error in estop {e} for axis {self._axis}")
            return False
        
    #################################  Status and Position  #################################

    async def get_position(self):
        """
        Get current position
        """
        try:
            response = await self._query_command(f"{self._axis}POS?")

            # Response is split into theoretical and actual
            theoretical_mm = float(response[0])
            actual_mm = float(response[1])  
            
            # Convert mm to um
            theoretical_um = theoretical_mm * 1000
            actual_um = actual_mm * 1000
            
            # Update cached position
            self._last_position = actual_um

            # Return Position data class
            return Position(
                    theoretical=theoretical_um,
                    actual=actual_um,
                    units="um",
                    timestamp= monotonic()
                )
        except Exception as e: 
            logger.error(f"Position read error: {e}")
            return Position(0.0, 0.0, "um", monotonic())
    
    async def get_state(self):
        """
        Get movement status of motor
        """
        try:
            response = await self._query_command(f"{self._axis}STA?")
            status_int = int(response)
            
            # Check bit 3 (moving[0]/stopped[1])
            if status_int == 1:
                return MotorState.IDLE
            
            return MotorState.MOVING # else
                
        except Exception as e:
            logger.error(f"State read error: {e}")
            return MotorState.ERROR
        
    async def is_moving(self):
        """
        Check if motor is moving
        """
        state = await self.get_state()
        return state == MotorState.MOVING
    
    #################################  Configuration  #################################'

    async def set_velocity(self, velocity):
        """
        Set velocity in um/s
        """
        try:
            # Convert um/s to mm/s for controller
            vel_mm_s = velocity * 0.001
            await self._send_command(f"{self._axis}VEL{vel_mm_s:.6f}")
            self._velocity = velocity
            return True
        
        except Exception as e:
            logger.error(f"Set velocity error: {e}")
            return False
    
    async def set_acceleration(self, acceleration):
        """
        Set acceleration in um/s2
        """
        try:
            # Convert um/s2 to mm/s2 for controller
            acc_mm_s2 = acceleration * 0.001
            await self._send_command(f"{self._axis}ACC{acc_mm_s2:.6f}")
            self._acceleration = acceleration
            return True
        
        except Exception as e:
            logger.error(f"Set acceleration error: {e}")
            return False
    
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
    
    #################################  Homing  #################################'

    async def home(self, direction=0):
        """
        Home the axis
        """
        try:
            self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing'})
            self._move_in_progress = True # Set move to true
            self._is_homed = False # Set homed to false
            loop = asyncio.get_event_loop()
            start_time = loop.time()

            if direction == 0:
                await self._send_command(f"{self._axis}MLN")  # Move to negative limit
            else:
                await self._send_command(f"{self._axis}MLP")  # Move to positive limit
            
            # Wait for completion
            while True:
                response = await self._query_command(f"{self._axis}STA?") 
                status = int(response)
                if status == 1: break
                await asyncio.sleep(0.3)
                if abs(loop.time() - start_time) > 30.0:
                    break
            
            # Set zero point
            if direction == 0:
                logger.info("Set zero point")
                await self._send_command(f"{self._axis}ZRO")
                self._is_homed = True # todo: check if homed is for specific axis, check super config may be fine
                self._last_position = 0.0   # Reset position tracking
            else:
                # For homing purposes, it should always be the negative limit
                logger.info("Set positive limit")
                pos = await self._query_command(f"{self._axis}POS?")
                self._last_position = float(pos[0]) * 1000.0 # mm to um
                self._position_limits = (self._position_limits[0], self._last_position)
                logger.info(f"last pos: {self._last_position}")
                self._is_homed = True

            self._emit_event(MotorEventType.HOMED, {'direction': direction})
            return True
            
        except Exception as e:
            if self._is_homed == True:
                logger.debug("Exception caught but homing complete")
                return True
            
            logger.error(f"Homing error: {e}\n")
            self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
            return False
            
    async def home_limits(self):
        """
        Home both ends of this axis, and set self._position_limits accordingly.
        After this runs, `neg_limit_um` will be 0.0 (since we ZRO there),
        and `pos_limit_um` will be the travel length in um.
        """
        async def _get_limits():
            """Get limit positions"""
            try:
                # Homing is starting
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing_limits'})

                
                # Send MLN to drive until negative limit is hit
                await self._send_command(f"{self._axis}MLN")

                # Wait for completion
                while True:
                    response = await self._query_command(f"{self._axis}STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    await asyncio.sleep(0.1)

                # Zero neg limit, zeros by default so becomes 0 mm
                await self._send_command(f"{self._axis}ZRO")

                # After ZRO, the controller’s internal position registers read zero at this point
                bottom_zero_um = 0.0 # set bottom limit as controllers iternal position limit register
                self._last_position = bottom_zero_um 

                # Move pos limit switch
                await self._send_command(f"{self._axis}MLP")

                # Wait for completion
                while True:
                    response = await self._query_command(f"{self._axis}STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    await asyncio.sleep(0.1)

                # Read position at positive end
                pos_resp2 = await self._query_command(f"{self._axis}POS?")
                top_mm = float(pos_resp2[1])
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
            
        async def _mid_point():
            """Go to mid point"""
            try:
                mid_point = (self._position_limits[1] - self._position_limits[0]) / 2
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'middling'})
                await self._send_command(f"{self._axis}MVA{(mid_point/1000):.6f}")
                
                # Wait for completion
                while True:
                    response = await self._query_command(f"{self._axis}STA?")
                    status = int(response)
                    pos = await self._query_command(f"{self._axis}POS?")
                    pos = float(pos[1])
                    pos_um = pos * 1000.0 # Convert
                    
                    # If position reaches mid point, or movement has stopped and its accurate to 0.001 mm 
                    if (pos_um == mid_point) or (status == 1): # messy
                        break
                    await asyncio.sleep(0.1)

                # Get current position
                self._emit_event(MotorEventType.MOVE_COMPLETE, {'pos': self._position_limits})
                self._last_position = pos_um
                return True
        
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                return False
        
        """Get position limits, go to mid point"""
        try:
            # Asynchronously call these methods
            ok = await _get_limits()
            if not ok:
                raise Exception("Error getting limits")
            
            ok = await _mid_point()
            if not ok:
                raise Exception("Error going to midpts")
            
            return True, self._position_limits
        
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
            return False, None

    async def set_zero(self):
        """Set current position as zero"""
        try:
            await self._send_command(f"{self._axis}ZRO")
            self._last_position = 0.0  # Reset position tracking
            return True
        except Exception as e:
            logger.error(f"Set zero error: {e}")
            return False
    
    #################################  Additional Utility Methods  #################################'
    async def wait_for_move_completion(self, timeout: float = 30.0) -> bool:
        """
        Wait for any current move to complete
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if move completed successfully, False if timeout or error
        """
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        
        while self._move_in_progress and (loop.time() - start_time) < timeout:
            await asyncio.sleep(0.1)

        self._move_in_progress = False

        return self._move_in_progress
    
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