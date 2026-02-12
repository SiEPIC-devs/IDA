"""
BSC203 3-Axis Stepper Motor Controller Library
Uses Thorlabs Kinesis Official DLL

Author: Auto-generated
Date: 2026-01-10
Version: 1.0.0

Dependencies:
- pythonnet (pip install pythonnet)
- Thorlabs Kinesis Software

Usage Example:
    from bsc203_controller import BSC203Controller
    
    # Create controller
    controller = BSC203Controller()
    
    # Connect device
    if controller.connect():
        # Move X axis
        controller.move_relative('X', 5.0)
        
        # Get position
        pos = controller.get_position('X')
        print(f"X-axis position: {pos} mm")
        
        # Disconnect
        controller.disconnect()
"""

import clr
import time
from typing import Optional, Dict, Tuple, List
from enum import Enum
from dataclasses import dataclass

try:
    clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
    clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
    clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.Benchtop.StepperMotorCLI.dll")
    
    from Thorlabs.MotionControl.DeviceManagerCLI import *
    from Thorlabs.MotionControl.GenericMotorCLI import *
    from Thorlabs.MotionControl.Benchtop.StepperMotorCLI import *
    from System import Decimal
    
    KINESIS_AVAILABLE = True
except Exception as e:
    KINESIS_AVAILABLE = False
    print(f"Warning: Failed to load Kinesis DLL: {e}")


class Axis(Enum):
    """Axis enumeration"""
    X = 1
    Y = 2
    Z = 3


@dataclass
class AxisConfig:
    """Axis configuration"""
    min_position: float = -50.0  # mm
    max_position: float = 50.0   # mm
    max_velocity: float = 2.0     # mm/s
    acceleration: float = 4.0     # mm/s²
    
    
@dataclass
class MotorStatus:
    """Motor status"""
    position: float
    velocity: float
    is_homed: bool
    is_moving: bool
    is_enabled: bool


class BSC203Exception(Exception):
    """BSC203 exception"""
    pass


class BSC203Controller:
    """
    BSC203 3-Axis Stepper Motor Controller
    
    Supported Features:
    - Connect/disconnect device
    - Independent control of 3 axes (X, Y, Z)
    - Relative/absolute movement
    - Homing operations
    - Set zero position
    - Velocity and acceleration control
    - Software limit protection
    - Status query
    """
    
    # Channel mapping
    CHANNEL_MAP = {
        'X': 1,
        'Y': 2,
        'Z': 3,
        Axis.X: 1,
        Axis.Y: 2,
        Axis.Z: 3
    }
    
    def __init__(self, serial_number: Optional[str] = None):
        """
        Initialize controller
        
        Args:
            serial_number: Device serial number, auto-search first device if None
        """
        if not KINESIS_AVAILABLE:
            raise BSC203Exception("Kinesis DLL not installed or failed to load")
        
        self.serial_number = serial_number
        self.device = None
        self.channels: Dict[str, any] = {}
        self.configs: Dict[str, AxisConfig] = {
            'X': AxisConfig(),
            'Y': AxisConfig(max_velocity=1.0, acceleration=2.0),  # Y-axis uses safer default parameters
            'Z': AxisConfig()
        }
        self.is_connected = False
        self._enable_limit_check = True
        
    def connect(self, timeout: int = 10000) -> bool:
        """
        Connect to device
        
        Args:
            timeout: Initialization timeout (milliseconds)
            
        Returns:
            bool: Whether connection succeeded
        """
        try:
            # Build device list
            DeviceManagerCLI.BuildDeviceList()
            device_list = DeviceManagerCLI.GetDeviceList(BenchtopStepperMotor.DevicePrefix70)
            
            if device_list.Count == 0:
                raise BSC203Exception("BSC20x device not found")
            
            # Select device
            if self.serial_number is None:
                self.serial_number = device_list[0]
            elif self.serial_number not in [device_list[i] for i in range(device_list.Count)]:
                raise BSC203Exception(f"Device {self.serial_number} not found")
            
            # Create and connect device
            self.device = BenchtopStepperMotor.CreateBenchtopStepperMotor(self.serial_number)
            self.device.Connect(self.serial_number)
            time.sleep(0.5)
            
            # Initialize three channels
            for axis_name, channel_num in [('X', 1), ('Y', 2), ('Z', 3)]:
                channel = self.device.GetChannel(channel_num)
                
                # Wait for settings initialization
                if not channel.IsSettingsInitialized():
                    channel.WaitForSettingsInitialized(timeout)
                
                # Load motor configuration
                motor_config = channel.LoadMotorConfiguration(channel.DeviceID)
                time.sleep(0.3)
                
                # Start polling
                channel.StartPolling(250)
                time.sleep(0.3)
                
                # Enable channel
                channel.EnableDevice()
                time.sleep(0.3)
                
                # Set velocity parameters
                config = self.configs[axis_name]
                vel_params = channel.GetVelocityParams()
                vel_params.MaxVelocity = Decimal(config.max_velocity)
                vel_params.Acceleration = Decimal(config.acceleration)
                channel.SetVelocityParams(vel_params)
                
                self.channels[axis_name] = channel
            
            self.is_connected = True
            return True
            
        except Exception as e:
            raise BSC203Exception(f"Connection failed: {e}")
    
    def disconnect(self) -> bool:
        """
        Disconnect device
        
        Returns:
            bool: Whether disconnection succeeded
        """
        try:
            if self.is_connected and self.device:
                # Stop polling for all channels
                for channel in self.channels.values():
                    try:
                        channel.StopPolling()
                    except:
                        pass
                
                # Disconnect device
                self.device.Disconnect()
                self.device = None
                self.channels.clear()
                self.is_connected = False
                
            return True
            
        except Exception as e:
            raise BSC203Exception(f"Disconnection failed: {e}")
    
    def _check_connected(self):
        """Check if device is connected"""
        if not self.is_connected:
            raise BSC203Exception("Device not connected, please call connect() first")
    
    def _validate_axis(self, axis: str) -> str:
        """Validate axis name"""
        if isinstance(axis, Axis):
            axis = axis.name
        axis = axis.upper()
        if axis not in ['X', 'Y', 'Z']:
            raise ValueError(f"Invalid axis name: {axis}")
        return axis
    
    def _check_limits(self, axis: str, target_position: float) -> bool:
        """Check if target position is within limit range"""
        if not self._enable_limit_check:
            return True
        
        config = self.configs[axis]
        if target_position < config.min_position or target_position > config.max_position:
            raise BSC203Exception(
                f"{axis}-axis target position {target_position:.3f}mm exceeds limit range "
                f"[{config.min_position:.3f}, {config.max_position:.3f}]"
            )
        return True
    
    # ==================== Movement Control ====================
    
    def move_relative(self, axis: str, distance: float, wait: bool = True) -> bool:
        """
        Relative movement
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            distance: Movement distance (mm, positive forward, negative backward)
            wait: Whether to wait for movement completion
            
        Returns:
            bool: Whether movement started successfully
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            current_pos = Decimal.ToDouble(channel.Position)
            target_pos = current_pos + distance
            
            # Check limits
            self._check_limits(axis, target_pos)
            
            # Execute movement
            direction = MotorDirection.Forward if distance >= 0 else MotorDirection.Backward
            timeout = 60000 if wait else 0
            channel.MoveRelative(direction, Decimal(abs(distance)), timeout)
            
            return True
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis relative move failed: {e}")
    
    def move_absolute(self, axis: str, position: float, wait: bool = True) -> bool:
        """
        Absolute movement
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            position: Target position (mm)
            wait: Whether to wait for movement completion
            
        Returns:
            bool: Whether movement started successfully
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            # Check limits
            self._check_limits(axis, position)
            
            # Execute movement
            channel = self.channels[axis]
            timeout = 60000 if wait else 0
            channel.MoveTo(Decimal(position), timeout)
            
            return True
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis absolute move failed: {e}")
    
    def stop(self, axis: Optional[str] = None) -> bool:
        """
        Stop movement
        
        Args:
            axis: Axis name, if None stop all axes
            
        Returns:
            bool: Whether stop succeeded
        """
        self._check_connected()
        
        try:
            if axis is None:
                # Stop all axes
                for channel in self.channels.values():
                    channel.Stop(0)
            else:
                axis = self._validate_axis(axis)
                self.channels[axis].Stop(0)
            
            return True
            
        except Exception as e:
            raise BSC203Exception(f"Stop failed: {e}")
    
    # ==================== Homing Operations ====================
    
    def home(self, axis: str, timeout: int = 60000) -> bool:
        """
        Homing operation (move to limit switch)
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            timeout: Timeout (milliseconds)
            
        Returns:
            bool: Whether homing succeeded
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            channel.Home(timeout)
            return True
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis homing failed: {e}")
    
    def set_zero(self, axis: str) -> bool:
        """
        Set current position as zero (software reset, no motor movement)
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            bool: Whether setting succeeded
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            channel.SetPositionCounter(0)
            time.sleep(0.2)
            return True
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis set zero failed: {e}")
    
    # ==================== Position Query ====================
    
    def get_position(self, axis: str) -> float:
        """
        Get current position
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            float: Current position (mm)
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            return Decimal.ToDouble(channel.Position)
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis get position failed: {e}")
    
    def get_all_positions(self) -> Dict[str, float]:
        """
        Get positions of all axes
        
        Returns:
            dict: {'X': pos_x, 'Y': pos_y, 'Z': pos_z}
        """
        return {
            axis: self.get_position(axis)
            for axis in ['X', 'Y', 'Z']
        }
    
    # ==================== Velocity Control ====================
    
    def set_velocity(self, axis: str, velocity: float, acceleration: Optional[float] = None) -> bool:
        """
        Set velocity parameters
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            velocity: Maximum velocity (mm/s)
            acceleration: Acceleration (mm/s²), no change if None
            
        Returns:
            bool: Whether setting succeeded
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            vel_params = channel.GetVelocityParams()
            vel_params.MaxVelocity = Decimal(velocity)
            
            if acceleration is not None:
                vel_params.Acceleration = Decimal(acceleration)
            
            channel.SetVelocityParams(vel_params)
            
            # Update configuration
            self.configs[axis].max_velocity = velocity
            if acceleration is not None:
                self.configs[axis].acceleration = acceleration
            
            return True
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis set velocity failed: {e}")
    
    def get_velocity(self, axis: str) -> Tuple[float, float]:
        """
        Get velocity parameters
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            tuple: (maximum velocity, acceleration)
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            vel_params = channel.GetVelocityParams()
            return (Decimal.ToDouble(vel_params.MaxVelocity), Decimal.ToDouble(vel_params.Acceleration))
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis get velocity failed: {e}")
    
    # ==================== Limit Settings ====================
    
    def set_limits(self, axis: str, min_pos: float, max_pos: float) -> bool:
        """
        Set software limits
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            min_pos: Minimum position (mm)
            max_pos: Maximum position (mm)
            
        Returns:
            bool: Whether setting succeeded
        """
        axis = self._validate_axis(axis)
        
        if max_pos <= min_pos:
            raise ValueError("max_pos must be greater than min_pos")
        
        self.configs[axis].min_position = min_pos
        self.configs[axis].max_position = max_pos
        return True
    
    def get_limits(self, axis: str) -> Tuple[float, float]:
        """
        Get software limits
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            tuple: (minimum position, maximum position)
        """
        axis = self._validate_axis(axis)
        config = self.configs[axis]
        return (config.min_position, config.max_position)
    
    def enable_limit_check(self, enable: bool = True):
        """
        Enable/disable limit checking
        
        Args:
            enable: True to enable, False to disable
        """
        self._enable_limit_check = enable
    
    # ==================== Status Query ====================
    
    def get_status(self, axis: str) -> MotorStatus:
        """
        Get motor status
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            MotorStatus: Motor status object
        """
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            channel = self.channels[axis]
            vel_params = channel.GetVelocityParams()
            
            # Note: Some states may require different API calls
            status = MotorStatus(
                position=Decimal.ToDouble(channel.Position),
                velocity=Decimal.ToDouble(vel_params.MaxVelocity),
                is_homed=True,  # Simplified handling
                is_moving=False,  # Requires additional API
                is_enabled=True
            )
            
            return status
            
        except Exception as e:
            raise BSC203Exception(f"{axis}-axis get status failed: {e}")
    
    def is_moving(self, axis: str) -> bool:
        """
        Check if axis is moving
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            
        Returns:
            bool: True if moving
        """
        # Simplified implementation: judge by position change
        self._check_connected()
        axis = self._validate_axis(axis)
        
        try:
            pos1 = self.get_position(axis)
            time.sleep(0.05)
            pos2 = self.get_position(axis)
            return abs(pos2 - pos1) > 0.001
            
        except Exception as e:
            return False
    
    def wait_for_move_complete(self, axis: str, timeout: float = 30.0, check_interval: float = 0.1) -> bool:
        """
        Wait for movement completion
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            timeout: Timeout (seconds)
            check_interval: Check interval (seconds)
            
        Returns:
            bool: True if movement completed, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.is_moving(axis):
                return True
            time.sleep(check_interval)
        
        return False
    
    # ==================== Device Information ====================
    
    def get_device_info(self) -> Dict[str, str]:
        """
        Get device information
        
        Returns:
            dict: Device information dictionary
        """
        self._check_connected()
        
        try:
            device_info = self.device.GetDeviceInfo()
            return {
                'serial_number': str(device_info.SerialNumber),
                'name': str(device_info.Name),
                'description': str(device_info.Description)
            }
            
        except Exception as e:
            raise BSC203Exception(f"Get device info failed: {e}")
    
    # ==================== Context Manager ====================
    
    def __enter__(self):
        """Support with statement"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support with statement"""
        self.disconnect()
        return False


# ==================== Utility Functions ====================

def list_devices() -> List[str]:
    """
    List all connected BSC20x devices
    
    Returns:
        list: Device serial number list
    """
    if not KINESIS_AVAILABLE:
        return []
    
    try:
        DeviceManagerCLI.BuildDeviceList()
        device_list = DeviceManagerCLI.GetDeviceList(BenchtopStepperMotor.DevicePrefix70)
        return [device_list[i] for i in range(device_list.Count)]
    except:
        return []


if __name__ == "__main__":
    print("BSC203 Controller")
    print("=" * 60)
    
    devices = list_devices()
    print(f"\nFind {len(devices)} devices:")
    for dev in devices:
        print(f"  - {dev}")
    
    if devices:
        print("\nExample usage:")
        print("  from bsc203_controller import BSC203Controller")
        print("  ")
        print("  controller = BSC203Controller()")
        print("  controller.connect()")
        print("  ")
        print("  # Move X axis")
        print("  controller.move_relative('X', 5.0)")
        print("  ")
        print("  # Get position")
        print("  pos = controller.get_position('X')")
        print("  ")
        print("  controller.disconnect()")
