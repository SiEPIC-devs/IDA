import asyncio
import serial
import threading
import logging
from typing import Optional, Dict, Any, Tuple
import time
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

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

"""
Simple Async Queue Stage Controller
Cameron Basara, 2025
"""

# Configuration 
_GLOBAL_COM_PORT = "COM8"
_GLOBAL_BAUDRATE = 38400
_GLOBAL_TIMEOUT = 0.3

# Shared serial connection 
_serial_lock = threading.Lock()
_global_serial_port = None

def _get_shared_serial():
    """Get or create shared serial connection"""
    global _global_serial_port

    if _global_serial_port is None:
        try:
            _global_serial_port = serial.Serial(
                port=_GLOBAL_COM_PORT,
                baudrate=_GLOBAL_BAUDRATE,
                timeout=_GLOBAL_TIMEOUT
            )
        except Exception as e:
            raise
    else:
        # print(f"=== Using existing serial connection ===")
        pass
    return _global_serial_port

# Simple async queue for commands
_command_queue = None
_queue_worker_task = None

def _get_command_queue():
    """Get or create the command queue"""
    global _command_queue
    if _command_queue is None:
        _command_queue = asyncio.Queue()
    return _command_queue

async def _process_command_queue():
    """Process commands from queue"""
    command_queue = _get_command_queue()
    while True:
        try:
            command_func, future = await command_queue.get()
            try:
                result = command_func()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            command_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Queue worker error: {e}")

async def _ensure_queue_worker():
    """Ensure queue worker is running"""
    global _queue_worker_task
    if _queue_worker_task is None or _queue_worker_task.done():
        _queue_worker_task = asyncio.create_task(_process_command_queue())
    else:
        logger.debug("Queue worker already running")

async def _queue_command(command_func):
    """Queue a command for execution"""
    await _ensure_queue_worker()
    future = asyncio.Future()
    command_queue = _get_command_queue()
    await command_queue.put((command_func, future))
    result = await future
    return result

class StageController(MotorHAL):
    """
    Simple async stage controller using queue over modern_stage.py pattern
    """
    
    # Same axis mapping as modern_stage.py
    AXIS_MAP = {
        AxisType.X: 1,
        AxisType.Y: 2,
        AxisType.Z: 3,
        AxisType.ROTATION_FIBER: 4,
        AxisType.ROTATION_CHIP: 5,
    }

    def __init__(
        self,
        axis: AxisType,
        velocity: float = 2000.0,
        acceleration: float = 5000.0,
        position_limits: Tuple[float, float] = (0.0, 50000.0),
        debug: bool = False
    ):
        super().__init__(axis)
        
        # Configuration
        self.debug = debug
        self._velocity = velocity
        self._acceleration = acceleration
        self._position_limits = position_limits
        
        # State tracking
        self._is_connected = False
        self._axis_num = self.AXIS_MAP[axis]
        self._last_position = 0.0
        
        # Serial connection (shared)
        self._serial_lock = _serial_lock
        self._serial_port = None
        
        # Event callbacks
        self._callbacks = []

    def add_callback(self, callback):
        """Add event callback"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def _emit_event(self, event_type: MotorEventType, data: Dict[str, Any] = None):
        """Emit event to callbacks"""
        event = MotorEvent(
            axis=self.axis,
            event_type=event_type,
            data=data or {},
            timestamp=monotonic()
        )
        
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                if self.debug:
                    logger.error(f"Callback error: {e}")

    def _send_command_sync(self, cmd: str) -> str:
        """Send command synchronously - same as modern_stage.py"""
        with self._serial_lock:
            if not self._serial_port:
                self._serial_port = _get_shared_serial()
            
            if not self._serial_port.is_open:
                raise ConnectionError("Serial port not connected")

            if self.debug:
                logger.debug(f"Sending: {cmd}")
            
            self._serial_port.write((cmd + "\r").encode('ascii'))
            import time
            time.sleep(0.05)
            
            response = ""
            if self._serial_port.in_waiting > 0:
                response = self._serial_port.read_until(b'\r\n').decode('ascii').strip()
                if self.debug:
                    logger.debug(f"Response: {response}")
                    
            return response

    def _query_command_sync(self, cmd: str) -> str:
        """Query command synchronously - same as modern_stage.py"""
        with self._serial_lock:
            if not self._serial_port:
                self._serial_port = _get_shared_serial()
            
            if not self._serial_port.is_open:
                raise ConnectionError("Serial port not connected")
            
            # Clear buffers
            self._serial_port.reset_input_buffer()
            self._serial_port.reset_output_buffer()

            if self.debug:
                logger.debug(f"Querying: {cmd}")
            
            self._serial_port.write((cmd + "\r").encode('ascii'))   
            import time
            time.sleep(0.05)
            self._serial_port.flush()          
            time.sleep(0.05)

            if "STA?" in cmd:
                raw = self._serial_port.read_until(b"\n\r")
                text = raw.decode('ascii').strip()
                
                if len(text) == 0:
                    return "0"
                
                status_number = int(text.strip('#'))
                status_bit = (status_number >> 3) & 1
                return str(status_bit)

            elif "POS?" in cmd:
                raw = self._serial_port.read_until(b"\n\r")
                text = raw.decode('ascii').strip()
                
                if len(text) == 0:
                    raise Exception("No position data received")
                
                clean_text = text.strip('#')
                values = clean_text.split(',')
                return values
            
            response = self._serial_port.read_until(b"\n\r").decode('ascii').strip()
            if self.debug:
                logger.debug(f"Query response: {response}")
            return response

    async def connect(self) -> bool:
        """Connect this axis"""
        def _connect():
            try:
                # Always get the shared serial port
                self._serial_port = _get_shared_serial()
                
                if not self._serial_port.is_open:
                    self._serial_port.open()
                else:
                    pass

                # Initialize axis - same as modern_stage.py
                self._send_command_sync(f"{self._axis_num}FBK3")
                
                
                time.sleep(0.1)
                
                # Set velocity
                vel_mm_s = self._velocity * 0.001
                self._send_command_sync(f"{self._axis_num}VEL{vel_mm_s:.6f}")
                time.sleep(0.1)

                self._is_connected = True
                return True
                
            except Exception as e:
                logger.error(f"CONNECTION FAILED for axis {self._axis_num}: {e}")
                return False
        
        result = await _queue_command(_connect)
        return result

    async def disconnect(self) -> bool:
        """Disconnect this axis"""
        def _disconnect():
            try:
                if self._serial_port and self._serial_port.is_open:
                    self._serial_port.close()
                self._is_connected = False
                if self.debug:
                    logger.debug(f"Axis {self._axis_num} disconnected")
                return True
            except Exception as e:
                if self.debug:
                    logger.error(f"Disconnect error: {e}")
                return False
        
        return await _queue_command(_disconnect)

    async def get_position(self) -> Position:
        """Get current position"""
        def _get_position():
            try:
                print("Start get position")
                response = self._query_command_sync(f"{self._axis_num}POS?")
                print("get it")
                
                theoretical_mm = float(response[0])
                actual_mm = float(response[1])
                
                theoretical_um = theoretical_mm * 1000
                actual_um = actual_mm * 1000
                
                self._last_position = actual_um
                
                return Position(
                    theoretical=theoretical_um,
                    actual=actual_um,
                    units="um",
                    timestamp=monotonic()
                )
                
            except Exception as e:
                if self.debug:
                    logger.error(f"Position error: {e}")
                return Position(0.0, 0.0, "um", monotonic())

        return await _queue_command(_get_position)

    async def get_state(self) -> MotorState:
        """Get current motor state"""
        def _get_state():
            try:
                response = self._query_command_sync(f"{self._axis_num}STA?")
                status_int = int(response)
                
                if status_int == 1:
                    return MotorState.IDLE
                else:
                    return MotorState.MOVING
                    
            except Exception as e:
                if self.debug:
                    logger.error(f"State error: {e}")
                return MotorState.ERROR
        
        return await _queue_command(_get_state)

    async def is_moving(self) -> bool:
        """Check if axis is moving"""
        state = await self.get_state()
        return state == MotorState.MOVING

    async def move_absolute(
        self,
        position: float,
        velocity: Optional[float] = None,
        wait_for_completion: bool = True,
        timeout: float = 30.0
    ) -> bool:
        """Move to absolute position"""
        def _move_absolute():
            try:
                if not (self._position_limits[0] <= position <= self._position_limits[1]):
                    raise ValueError(f"Position {position} outside limits {self._position_limits}")
                
                if velocity:
                    vel_mm_s = velocity * 0.001
                    self._send_command_sync(f"{self._axis_num}VEL{vel_mm_s:.6f}")
                
                self._emit_event(MotorEventType.MOVE_STARTED, {
                    'target_position': position,
                    'operation': 'move_absolute'
                })
                
                # Handle rotation scaling
                if self.axis == AxisType.ROTATION_FIBER:
                    limit_range = self._position_limits[1]
                    scaled_distance = (45 - position) * (limit_range / 45)
                    position_mm = scaled_distance * 0.001
                else:
                    position_mm = position * 0.001
                
                self._send_command_sync(f"{self._axis_num}MVA{position_mm:.6f}")
                
                if wait_for_completion:
                    import time
                    start_time = time.time()
                    while True:
                        response = self._query_command_sync(f"{self._axis_num}STA?")
                        status = int(response)
                        if status == 1:
                            break
                        
                        if time.time() - start_time > timeout:
                            return False
                        
                        time.sleep(0.1)
                
                self._last_position = position
                self._emit_event(MotorEventType.MOVE_COMPLETE, {
                    'position': position,
                    'operation': 'move_absolute'
                })
                
                return True
                
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {
                    'error': str(e),
                    'operation': 'move_absolute'
                })
                if self.debug:
                    logger.error(f"Move error: {e}")
                return False
        
        return await _queue_command(_move_absolute)

    async def move_relative(
        self,
        distance: float,
        velocity: Optional[float] = None,
        wait_for_completion: bool = True,
        timeout: float = 30.0
    ) -> bool:
        """Move relative distance"""
        def _move_relative():
            try:
                target_pos = self._last_position + distance
                
                if not (self._position_limits[0] <= target_pos <= self._position_limits[1]):
                    raise ValueError(f"Target position {target_pos} outside limits {self._position_limits}")
                
                if velocity:
                    vel_mm_s = velocity * 0.001
                    self._send_command_sync(f"{self._axis_num}VEL{vel_mm_s:.6f}")
                
                self._emit_event(MotorEventType.MOVE_STARTED, {
                    'target_position': target_pos,
                    'distance': distance,
                    'operation': 'move_relative'
                })
                
                distance_mm = distance * 0.001
                self._send_command_sync(f"{self._axis_num}MVR{distance_mm:.6f}")
                
                if wait_for_completion:
                    import time
                    start_time = time.time()
                    while True:
                        response = self._query_command_sync(f"{self._axis_num}STA?")
                        status = int(response)
                        if status == 1:
                            break
                        
                        if time.time() - start_time > timeout:
                            return False
                        
                        time.sleep(0.1)
                
                self._last_position = target_pos
                self._emit_event(MotorEventType.MOVE_COMPLETE, {
                    'distance': distance,
                    'operation': 'move_relative'
                })
                
                return True
                
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {
                    'error': str(e),
                    'operation': 'move_relative'
                })
                if self.debug:
                    logger.error(f"Move error: {e}")
                return False
        
        return await _queue_command(_move_relative)

    async def stop(self) -> bool:
        """Stop motor"""
        def _stop():
            try:
                self._send_command_sync(f"{self._axis_num}STP")
                
                pos_response = self._query_command_sync(f"{self._axis_num}POS?")
                actual_mm = float(pos_response[1])
                actual_um = actual_mm * 1000
                
                self._emit_event(MotorEventType.MOVE_STOPPED, {
                    'position': actual_um,
                    'operation': 'stop'
                })
                
                return True
                
            except Exception as e:
                if self.debug:
                    logger.error(f"Stop error: {e}")
                return False
        
        return await _queue_command(_stop)

    async def emergency_stop(self) -> bool:
        """Emergency stop"""
        def _emergency_stop():
            try:
                self._send_command_sync(f"{self._axis_num}EST")
                
                pos_response = self._query_command_sync(f"{self._axis_num}POS?")
                actual_mm = float(pos_response[1])
                actual_um = actual_mm * 1000
                
                self._emit_event(MotorEventType.MOVE_STOPPED, {
                    'position': actual_um,
                    'operation': 'emergency_stop'
                })
                
                return True
                
            except Exception as e:
                if self.debug:
                    logger.error(f"Emergency stop error: {e}")
                return False
        
        return await _queue_command(_emergency_stop)

    async def set_velocity(self, velocity: float) -> bool:
        """Set velocity"""
        def _set_velocity():
            try:
                vel_mm_s = velocity * 0.001
                self._send_command_sync(f"{self._axis_num}VEL{vel_mm_s:.6f}")
                self._velocity = velocity
                return True
            except Exception as e:
                if self.debug:
                    logger.error(f"Set velocity error: {e}")
                return False
        
        return await _queue_command(_set_velocity)

    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration"""
        def _set_acceleration():
            try:
                acc_mm_s2 = acceleration * 0.001
                self._send_command_sync(f"{self._axis_num}ACC{acc_mm_s2:.6f}")
                self._acceleration = acceleration
                return True
            except Exception as e:
                if self.debug:
                    logger.error(f"Set acceleration error: {e}")
                return False
        
        return await _queue_command(_set_acceleration)

    async def get_config(self) -> MotorConfig:
        """Get motor configuration"""
        units = "degrees" if self.axis in [AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP] else "um"
        return MotorConfig(
            max_velocity=self._velocity,
            max_acceleration=self._acceleration,
            position_limits=self._position_limits,
            units=units
        )

    async def home(self, direction: int = 0) -> bool:
        """Home the axis"""
        def _home():
            try:
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing'})
                
                home_cmd = f"{self._axis_num}MLN" if direction == 0 else f"{self._axis_num}MLP"
                self._send_command_sync(home_cmd)
                
                import time
                start_time = time.time()
                while True:
                    response = self._query_command_sync(f"{self._axis_num}STA?")
                    status = int(response)
                    if status == 1:
                        break
                    
                    if time.time() - start_time > 30.0:
                        return False
                    
                    time.sleep(0.3)
                
                if direction == 0:
                    self._send_command_sync(f"{self._axis_num}ZRO")
                    self._last_position = 0.0
                else:
                    pos_response = self._query_command_sync(f"{self._axis_num}POS?")
                    pos_mm = float(pos_response[0])
                    pos_um = pos_mm * 1000
                    self._last_position = pos_um
                    self._position_limits = (self._position_limits[0], pos_um)
                
                self._emit_event(MotorEventType.HOMED, {'direction': direction})
                return True
                
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                if self.debug:
                    logger.error(f"Homing error: {e}")
                return False
        
        return await _queue_command(_home)

    async def home_limits(self) -> Tuple[bool, Optional[Tuple[float, float]]]:
        """Home both limits"""
        def _home_limits():
            try:
                self._emit_event(MotorEventType.MOVE_STARTED, {'operation': 'homing_limits'})
                
                # Move to negative limit
                self._send_command_sync(f"{self._axis_num}MLN")
                
                import time
                while True:
                    response = self._query_command_sync(f"{self._axis_num}STA?")
                    status = int(response)
                    if status == 1:
                        break
                    time.sleep(0.1)
                
                # Set zero
                self._send_command_sync(f"{self._axis_num}ZRO")
                bottom_limit = 0.0
                
                # Move to positive limit
                self._send_command_sync(f"{self._axis_num}MLP")
                
                while True:
                    response = self._query_command_sync(f"{self._axis_num}STA?")
                    status = int(response)
                    if status == 1:
                        break
                    time.sleep(0.1)
                
                # Get top position
                pos_response = self._query_command_sync(f"{self._axis_num}POS?")
                top_mm = float(pos_response[0])
                top_limit = top_mm * 1000
                
                # Set limits
                self._position_limits = (bottom_limit, top_limit)
                
                # Move to middle
                mid_point = top_limit / 2
                mid_point_mm = mid_point * 0.001
                self._send_command_sync(f"{self._axis_num}MVA{mid_point_mm:.6f}")
                
                while True:
                    response = self._query_command_sync(f"{self._axis_num}STA?")
                    status = int(response)
                    if status == 1:
                        break
                    time.sleep(0.1)
                
                self._emit_event(MotorEventType.HOMED, {'limits': self._position_limits})
                
                return True, self._position_limits
                
            except Exception as e:
                self._emit_event(MotorEventType.ERROR_OCCURRED, {'error': str(e)})
                if self.debug:
                    logger.error(f"Home limits error: {e}")
                return False, None
        
        return await _queue_command(_home_limits)

    async def set_zero(self) -> bool:
        """Set current position as zero"""
        def _set_zero():
            try:
                self._send_command_sync(f"{self._axis_num}ZRO")
                self._last_position = 0.0
                return True
            except Exception as e:
                if self.debug:
                    logger.error(f"Set zero error: {e}")
                return False
        
        return await _queue_command(_set_zero)

    async def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """Wait for move completion"""
        def _wait_for_completion():
            import time
            start_time = time.time()
            while True:
                try:
                    response = self._query_command_sync(f"{self._axis_num}STA?")
                    status = int(response)
                    if status == 1:
                        return True
                    
                    if time.time() - start_time > timeout:
                        return False
                    
                    time.sleep(0.1)
                    
                except Exception:
                    return False
        
        return await _queue_command(_wait_for_completion)

# Register the queue-based driver
register_driver("347_stage_control", StageController)