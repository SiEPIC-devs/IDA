import asyncio
import serial_asyncio
import logging
from typing import Optional, Dict, Any, Tuple, ClassVar, Callable, List
from time import monotonic

from motors.hal.motors_hal import (
    MotorHAL,
    AxisType,
    MotorState,
    Position,
    MotorConfig,
    MotorEventType,
    MotorEvent
)
from motors.hal.stage_factory import register_driver

# CONSTANTS
GLOBAL_COM_PORT = "/dev/ttyUSB0"
GLOBAL_BAUDRATE = 38400
GLOBAL_TIMEOUT = 0.05  # seconds

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

class StageControl(MotorHAL):
    """
    Asyncio-based StageControl using a single I/O worker to serialize all serial commands.
    """
    AXIS_MAP: ClassVar[Dict[AxisType, int]] = {
        AxisType.X: 1,
        AxisType.Y: 2,
        AxisType.Z: 3,
        AxisType.ROTATION_FIBER: 4,
        AxisType.ROTATION_CHIP: 5,
    }

    # Shared I/O queue and worker
    _cmd_queue: ClassVar[Optional[asyncio.Queue]] = None
    _worker_task: ClassVar[Optional[asyncio.Task]] = None
    _worker_reader: ClassVar[Optional[asyncio.StreamReader]] = None
    _worker_writer: ClassVar[Optional[asyncio.StreamWriter]] = None

    # Track active connections
    _connection_count: ClassVar[int] = 0

    def __init__(
        self,
        axis: AxisType,
        com_port: str = GLOBAL_COM_PORT,
        baudrate: int = GLOBAL_BAUDRATE,
        timeout: float = GLOBAL_TIMEOUT,
        velocity: float = 2000.0,
        acceleration: float = 5000.0,
        position_limits: Tuple[float, float] = (0.0, 10000.0),
        position_tolerance: float = 1.0,
        poll_interval: float = 0.05
    ):
        super().__init__(axis)

        # Event subscribers
        self._subscribers: List[Callable[[MotorEvent], None]] = []

        # Connection params
        self.port = com_port
        self.baudrate = baudrate
        self.timeout = timeout
        self._is_connected = False
        self._target_position: Optional[float] = None

        # Motion parameters
        self._velocity = velocity
        self._acceleration = acceleration
        self._position_limits = position_limits
        self._position_tolerance = position_tolerance
        self._status_poll_interval = poll_interval
        self._move_in_progress = False
        self._last_position: Optional[float] = None

        # Numeric axis code
        self._axis_num = self.AXIS_MAP[self.axis]

        # Ensure the I/O worker is running
        self._ensure_worker()

    def subscribe(self, callback: Callable[[MotorEvent], None]) -> None:
        """Register an event callback."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[MotorEvent], None]) -> None:
        """Unregister an event callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _emit_event(self, event_type: MotorEventType, data: Dict[str, Any]) -> None:
        """Override to notify local subscribers."""
        try:
            super()._emit_event(event_type, data)
        except Exception:
            pass
        event = MotorEvent(axis=self.axis, event_type=event_type, data=data, timestamp=monotonic())
        for cb in list(self._subscribers):
            try:
                cb(event)
            except Exception:
                logger.exception("Error in event subscriber")

    @classmethod
    def _ensure_worker(cls) -> None:
        """Start the background serial I/O worker once."""
        if cls._cmd_queue is None:
            cls._cmd_queue = asyncio.Queue()
            cls._worker_task = asyncio.create_task(cls._serial_worker())

    @classmethod
    async def _serial_worker(cls) -> None:
        """
        Open the serial port and service all commands in FIFO order.
        Queue entries are tuples (full_cmd, want_reply, timeout, Future).
        """
        reader, writer = await serial_asyncio.open_serial_connection(
            url=GLOBAL_COM_PORT,
            baudrate=GLOBAL_BAUDRATE
        )
        cls._worker_reader = reader
        cls._worker_writer = writer
        logger.info(f"Serial port open on {GLOBAL_COM_PORT}@{GLOBAL_BAUDRATE}")

        try:
            while True:
                full_cmd, want_reply, timeout, fut = await cls._cmd_queue.get()
                try:
                    logger.debug(f"Worker sending: {full_cmd}")
                    raw = (full_cmd + "\r").encode('ascii')
                    writer.write(raw)
                    await writer.drain()
                    
                    if want_reply:
                        if "STA?" in full_cmd:
                            # Status queries expect \n\r termination
                            resp = await asyncio.wait_for(
                                reader.readuntil(b"\n\r"),
                                timeout=timeout or 1.0
                            )
                        elif "POS?" in full_cmd:
                            # Position queries expect \n\r termination  
                            resp = await asyncio.wait_for(
                                reader.readuntil(b"\n\r"),
                                timeout=timeout or 1.0
                            )
                        else:
                            # Other commands expect \r\n termination
                            resp = await asyncio.wait_for(
                                reader.readuntil(b'\r\n'),
                                timeout=timeout or GLOBAL_TIMEOUT
                            )
                        fut.set_result(resp.decode('ascii').strip())
                    else:
                        # For commands that don't expect replies, try to read anyway with short timeout
                        try:
                            resp = await asyncio.wait_for(
                                reader.readuntil(b'\r\n'),
                                timeout=GLOBAL_TIMEOUT
                            )
                        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                            pass
                        fut.set_result("")
                        
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)
        except asyncio.CancelledError:
            writer.close()
            await writer.wait_closed()
            logger.info("Serial worker cancelled and port closed")

    async def _enqueue(self, full_cmd: str, want_reply: bool, timeout: Optional[float] = None) -> Optional[str]:
        """
        Enqueue a command and await its Future result.
        """
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        await self.__class__._cmd_queue.put((full_cmd, want_reply, timeout, fut))
        return await fut

    @classmethod
    def get_connection_count(cls) -> int:
        return cls._connection_count

    async def connect(self) -> bool:
        """Initialize connection count and send startup commands."""
        StageControl._connection_count += 1
        try:
            # Send initialization commands exactly like v1
            await self._enqueue(f"{self._axis_num}FBK3", False)
            await asyncio.sleep(0.05)
            vel_cmd = f"{self._axis_num}VEL{self._velocity * 0.001:.6f}"
            await self._enqueue(vel_cmd, False)
            await asyncio.sleep(0.05)

            self._is_connected = True
            logger.info(
                f"Axis {self._axis_num} initialized, count={StageControl._connection_count}"
            )
            return True
        except Exception as e:
            logger.error(f"Connection error for axis {self._axis_num}: {e}")
            return False

    async def disconnect(self) -> None:
        """Decrement connection count and shutdown worker on last disconnect."""
        if not self._is_connected:
            return
        StageControl._connection_count -= 1
        self._is_connected = False

        if StageControl._connection_count == 0 and StageControl._worker_task:
            StageControl._worker_task.cancel()
            try:
                await StageControl._worker_task
            except asyncio.CancelledError:
                pass
            # Reset class variables
            StageControl._cmd_queue = None
            StageControl._worker_task = None
            StageControl._worker_reader = None
            StageControl._worker_writer = None

    async def _send_command(self, cmd: str) -> str:
        """Send command through shared serial connection with locking - matches v1 behavior"""
        if not self._is_connected:
            raise ConnectionError(f"Serial port not connected at {self._axis_num}")

        full_cmd = f"{self._axis_num}{cmd}"
        logger.debug(f"Axis {self._axis_num} sending: {full_cmd}")
        
        # Optional response handling like v1
        try:
            response = await self._enqueue(full_cmd, True, GLOBAL_TIMEOUT)
            return response or ""
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            return ""

    async def _query_command(self, cmd: str) -> Any:
        """Send query command and wait for response with locking - matches v1 behavior"""
        if not self._is_connected:
            raise ConnectionError(f"Serial port not connected at {self._axis_num}")
        
        full_cmd = f"{self._axis_num}{cmd}"
        logger.debug(f"Axis {self._axis_num} querying: {full_cmd}")
        
        # Status query
        if "STA?" in cmd:
            raw = await self._enqueue(full_cmd, True, 1.0)
            text = raw.strip() if raw else ""
            
            if len(text) == 0:
                return str(0)  # Default to moving if no response

            # Parse status number, remove # prefix
            status_num = int(text.strip('#'))
            status_bit = (status_num >> 3) & 1  # Bit 3 is status bit (1 == stopped)
            return str(status_bit)
        
        # Position query
        elif "POS?" in cmd:
            raw = await self._enqueue(full_cmd, True, 1.0)
            text = raw.strip() if raw else ""
            
            if len(text) == 0:
                raise Exception("No data received")

            # Remove # prefix, split data
            clean_text = text.strip('#')
            values = clean_text.split(',')
            return values
        
        # Other queries
        else:
            raw = await self._enqueue(full_cmd, True, 1.0)
            return raw.strip() if raw else ""

    #################################  Status and Position  #################################

    async def get_position(self) -> Position:
        """Get current position"""
        try:
            response = await self._query_command("POS?")

            # Response is split into theoretical and actual
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
                timestamp=monotonic()
            )
        except Exception as e:
            logger.error(f"Position read error on axis {self._axis_num}: {e}")
            return Position(0.0, 0.0, "um", monotonic())

    async def get_state(self) -> MotorState:
        """Get movement status of motor"""
        try:
            response = await self._query_command("STA?")
            status_int = int(response)
            
            # Check bit 3 (moving[0]/stopped[1])
            if status_int == 1:
                return MotorState.IDLE
            return MotorState.MOVING
                
        except Exception as e:
            logger.error(f"State read error on axis {self._axis_num}: {e}")
            return MotorState.ERROR

    async def is_moving(self) -> bool:
        """Check if motor is moving"""
        state = await self.get_state()
        return state == MotorState.MOVING

    #################################  Movement  #################################

    async def move_absolute(
        self,
        position: float,
        velocity: Optional[float] = None,
        wait_for_completion: bool = True,
        timeout: float = 60.0
    ) -> bool:
        """Move to absolute position in microns"""
        loop = asyncio.get_event_loop()
        start = loop.time()

        try:
            # Set velocity if given
            if velocity:
                velocity_mm_s = velocity * 0.001
                await self._send_command(f"VEL{velocity_mm_s:.6f}")

            # Emit event and set target
            self._target_position = position
            self._move_in_progress = True
            self._emit_event(MotorEventType.MOVE_STARTED, {
                'target_position': position,
                'velocity': velocity or self._velocity,
                'operation': 'move_absolute'
            })

            # Handle rotation axis special case
            if self.axis == AxisType.ROTATION_FIBER:
                lim = self._position_limits[1]
                distance = (45 - position) * (lim / 45)
                position_mm = distance * 0.001
                logger.info(f"Rotation position: {position_mm}")
            else:
                position_mm = position * 0.001

            # Verify bounds
            lo, hi = self._position_limits
            if not (lo <= position <= hi):
                raise Exception(f"Position {position} exceeds limits [{lo}, {hi}]")

            # Send move command
            await self._send_command(f"MVA{position_mm:.6f}")
            
            # Wait for completion if requested
            if wait_for_completion:
                while True:
                    response = await self._query_command("STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    if loop.time() - start > timeout:
                        logger.warning(f"Move timeout for axis {self._axis_num}")
                        return False
                    await asyncio.sleep(0.1)
            
            # Success event
            self._emit_event(MotorEventType.MOVE_COMPLETE, {
                'position': position,
                'operation': 'move_absolute',
                'status': True
            })
            self._move_in_progress = False
            return True
        
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': str(e),
                'operation': 'move_absolute',
                'status': False
            })
            self._move_in_progress = False
            logger.error(f"Move error on axis {self._axis_num}: {e}")
            return False

    async def move_relative(
        self, 
        distance: float, 
        velocity: Optional[float] = None, 
        wait_for_completion: bool = True,
        timeout: float = 60.0) -> bool:
        """Move relative distance in microns"""
        loop = asyncio.get_event_loop()
        start = loop.time()

        try:
            # Get current position for bounds checking
            current_pos = await self.get_position()
            target_pos = current_pos.actual + distance

            # Set velocity if given
            if velocity:
                velocity_mm_s = velocity * 0.001
                await self._send_command(f"VEL{velocity_mm_s:.6f}")

            # Emit event and set target
            self._target_position = target_pos
            self._move_in_progress = True
            self._emit_event(MotorEventType.MOVE_STARTED, {
                'target_position': target_pos,
                'velocity': velocity or self._velocity,
                'operation': 'move_relative'
            })

            # Handle rotation axis special case
            if self.axis == AxisType.ROTATION_FIBER:
                lim = self._position_limits[1]
                distance_adj = (45 - distance) * (lim / 45)
                distance_mm = distance_adj * 0.001
            else:
                distance_mm = distance * 0.001

            # Verify bounds
            lo, hi = self._position_limits
            if not (lo <= target_pos <= hi):
                raise Exception(f"Target position {target_pos} exceeds limits [{lo}, {hi}]")

            # Send move command
            await self._send_command(f"MVR{distance_mm:.6f}")
            
            # Wait for completion if requested
            if wait_for_completion:
                while True:
                    response = await self._query_command("STA?")
                    status = int(response)
                    if status == 1:  # Stopped
                        break
                    if loop.time() - start > timeout:
                        logger.warning(f"Move timeout for axis {self._axis_num}")
                        return False
                    await asyncio.sleep(0.1)
            
            # Success event
            self._emit_event(MotorEventType.MOVE_COMPLETE, {
                'distance': distance,
                'operation': 'move_relative',
                'status': True
            })
            self._move_in_progress = False
            return True
        
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': str(e),
                'operation': 'move_relative',
                'status': False
            })
            self._move_in_progress = False
            logger.error(f"Relative move error on axis {self._axis_num}: {e}")
            return False

    async def stop(self) -> bool:
        """Stop motor motion"""
        try:
            await self._send_command("STP")
            self._target_position = None
            self._move_in_progress = False
            
            current_pos = await self.get_position()
            self._emit_event(MotorEventType.MOVE_STOPPED, {
                'position': current_pos.actual,
                'operation': 'move_stopped',
                'status': True
            })
            return True
        
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': str(e),
                'operation': 'move_stopped',
                'status': False
            })
            logger.error(f"Stop error on axis {self._axis_num}: {e}")
            return False

    async def emergency_stop(self) -> bool:
        """Emergency stop axis"""
        try:
            await self._send_command("EST")
            self._target_position = None
            self._move_in_progress = False
            
            current_pos = await self.get_position()
            self._emit_event(MotorEventType.MOVE_STOPPED, {
                'position': current_pos.actual,
                'operation': 'emergency_stop',
                'status': True
            })
            return True
        
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {
                'error': str(e),
                'operation': 'emergency_stop',
                'status': False
            })
            logger.error(f"Emergency stop error on axis {self._axis_num}: {e}")
            return False

    #################################  Configuration  #################################

    async def set_velocity(self, velocity: float) -> bool:
        """Set velocity in um/s"""
        try:
            vel_mm_s = velocity * 0.001
            await self._send_command(f"VEL{vel_mm_s:.6f}")
            self._velocity = velocity
            return True
        except Exception as e:
            logger.error(f"Set velocity error on axis {self._axis_num}: {e}")
            return False

    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration in um/s²"""
        try:
            acc_mm_s2 = acceleration * 0.001
            await self._send_command(f"ACC{acc_mm_s2:.6f}")
            self._acceleration = acceleration
            return True
        except Exception as e:
            logger.error(f"Set acceleration error on axis {self._axis_num}: {e}")
            return False

    async def get_config(self) -> MotorConfig:
        """Get motor configuration"""
        units = "degrees" if self.axis in [AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP] else "um"
        
        return MotorConfig(
            max_velocity=self._velocity,
            max_acceleration=self._acceleration,
            position_limits=self._position_limits,
            units=units
        )

    #################################  Homing  #################################

    async def home(self, direction: int = 0) -> bool:
        """Home the axis"""
        try:
            self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing'})
            self._move_in_progress = True
            self._is_homed = False
            
            loop = asyncio.get_event_loop()
            start_time = loop.time()

            # Send homing command
            if direction == 0:
                await self._send_command("MLN")  # Move to negative limit
            else:
                await self._send_command("MLP")  # Move to positive limit
            
            # Wait for completion
            while True:
                response = await self._query_command("STA?")
                status = int(response)
                if status == 1:
                    break
                await asyncio.sleep(0.3)
                if abs(loop.time() - start_time) > 30.0:
                    break
            
            # Set zero point or limits
            if direction == 0:
                logger.info("Setting zero point")
                await self._send_command("ZRO")
                self._is_homed = True
                self._last_position = 0.0
            else:
                logger.info("Setting positive limit")
                pos = await self._query_command("POS?")
                self._last_position = float(pos[0]) * 1000.0
                self._position_limits = (self._position_limits[0], self._last_position)
                self._is_homed = True

            self._move_in_progress = False
            self._emit_event(MotorEventType.HOMED, {'direction': direction})
            return True
            
        except Exception as e:
            self._move_in_progress = False
            if getattr(self, '_is_homed', False):
                logger.debug("Exception caught but homing complete")
                return True
            
            logger.error(f"Homing error on axis {self._axis_num}: {e}")
            self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
            return False

    async def home_limits(self) -> Tuple[bool, Optional[Tuple[float, float]]]:
        """Home both ends of axis and set position limits"""
        try:
            self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing_limits'})
            self._move_in_progress = True

            # Move to negative limit
            await self._send_command("MLN")
            while True:
                response = await self._query_command("STA?")
                if int(response) == 1:
                    break
                await asyncio.sleep(0.1)

            # Zero at negative limit
            await self._send_command("ZRO")
            bottom_zero_um = 0.0
            self._last_position = bottom_zero_um

            # Move to positive limit
            await self._send_command("MLP")
            while True:
                response = await self._query_command("STA?")
                if int(response) == 1:
                    break
                await asyncio.sleep(0.1)

            # Read position at positive end
            pos_resp = await self._query_command("POS?")
            top_mm = float(pos_resp[1])
            top_um = top_mm * 1000.0
            self._last_position = top_um

            # Set software limits
            self._position_limits = (bottom_zero_um, top_um)

            # Go to middle point
            mid_point = top_um / 2
            await self._send_command(f"MVA{(mid_point/1000):.6f}")
            while True:
                response = await self._query_command("STA?")
                if int(response) == 1:
                    break
                await asyncio.sleep(0.1)

            self._move_in_progress = False
            self._emit_event(MotorEventType.HOMED, {'limits_um': self._position_limits})
            return True, self._position_limits

        except Exception as e:
            self._move_in_progress = False
            self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
            logger.error(f"Home limits error on axis {self._axis_num}: {e}")
            return False, None

    async def set_zero(self) -> bool:
        """Set current position as zero"""
        try:
            await self._send_command("ZRO")
            self._last_position = 0.0
            return True
        except Exception as e:
            logger.error(f"Set zero error on axis {self._axis_num}: {e}")
            return False

    #################################  Utility Methods  #################################

    async def wait_for_move_completion(self, timeout: float = 30.0) -> bool:
        """Wait for any current move to complete"""
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        
        while self._move_in_progress and (loop.time() - start_time) < timeout:
            await asyncio.sleep(0.1)

        return not self._move_in_progress

    def get_move_status(self) -> Dict[str, Any]:
        """Get current move status"""
        return {
            'move_in_progress': self._move_in_progress,
            'target_position': self._target_position,
            'last_position': self._last_position,
            'position_tolerance': self._position_tolerance
        }

# Register driver
register_driver("347_stage_control", StageControl)