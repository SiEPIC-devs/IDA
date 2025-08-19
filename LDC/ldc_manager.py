import logging
from typing import Dict, Any, Callable, List
from LDC.ldc_controller import SrsLdc502
from LDC.hal.LDC_hal import LDCEvent, LDCEventType
from LDC.hal.LDC_factory import create_driver
from LDC.config.ldc_config import LDCConfiguration
from LDC.utils.shared_memory import *

"""
LDC Manager - Simplified Implementation
Cameron Basara, 2025
"""

logger = logging.getLogger(__name__)

class LDCManager:
    def __init__(self, config: LDCConfiguration, use_shared_memory: bool = True, debug: bool = False):
        self.config = config
        self.debug = debug
        self._connected = False
        self._event_callbacks: List[Callable[[LDCEvent], None]] = []
        self.ldc = None
        
        # Shared memory setup
        self.use_shared_memory = use_shared_memory
        if use_shared_memory:
            try:
                self.shm_config = create_shared_ldc_config()
                write_shared_ldc_config(self.shm_config, config)
                logger.info("LDC shared memory initialized")
            except Exception as e:
                logger.warning(f"LDC shared memory initialization failed: {e}")
                self.use_shared_memory = False

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if self.debug:
            print(f"[LDC Manager] {message}")
        elif level == "error":
            logger.error(f"[LDC Manager] {message}")

    # === Context Management ===
    
    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()

    def shutdown(self):
        """Shutdown the LDC manager"""
        self.disconnect()
        
        # Clean up shared memory
        if self.use_shared_memory:
            try:
                if hasattr(self, 'shm_config'):
                    self.shm_config.close()
                    self.shm_config.unlink()
            except Exception as e:
                logger.debug(f"LDC shared memory cleanup: {e}")
        
        self._log("LDC manager shutdown complete")

    # === Device Lifecycle ===
    
    def initialize(self) -> bool:
        """Initialize the LDC device"""
        try:
            # Read config from shared memory if available
            if self.use_shared_memory:
                try:
                    self.config = read_shared_ldc_config(self.shm_config)
                except Exception as e:
                    self._log(f"Could not read config from shared memory, using default: {e}")
            
            # Create driver instance
            params = {
                'visa_address': self.config.visa_address,
                'sensor_type': self.config.sensor_type,
                'model_coeffs': self.config.model_coeffs,
                'pid_coeffs': self.config.pid_coeffs,
                'temp_setpoint': self.config.setpoint,
                'debug': self.debug
            }
            
            self.ldc = create_driver("srs_ldc_502", **params)
            
            # Add event callback to forward events
            self.ldc.add_event_callback(self._handle_ldc_event)
            
            # Connect to device
            success = self.connect()
            if success:
                self._log("LDC initialized successfully")
            else:
                self._log("LDC initialization failed", "error")
            
            return success
            
        except Exception as e:
            self._log(f"LDC initialization error: {e}", "error")
            return False

    def connect(self) -> bool:
        """Connect to the LDC device"""
        try:
            if not self.ldc:
                self._log("LDC not initialized. Call initialize() first.", "error")
                return False
                
            success = self.ldc.connect()
            if success:
                self._connected = True
                self._log("Connected to LDC device")
                
                # Configure device with current settings
                self._configure_device()
            else:
                self._log("Failed to connect to LDC device", "error")
                
            return success
            
        except Exception as e:
            self._log(f"Connection error: {e}", "error")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the LDC device"""
        try:
            if self.ldc:
                success = self.ldc.disconnect()
                if success:
                    self._connected = False
                    self._log("Disconnected from LDC device")
                return success
            return True
            
        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            return False

    def is_connected(self) -> bool:
        """Check if connected to the LDC device"""
        return self._connected

    def _configure_device(self):
        """Configure device with current settings"""
        try:
            if not self.ldc or not self._connected:
                return
            
            # Set sensor type
            self.ldc.set_sensor_type(self.config.sensor_type)
            
            # Configure sensor coefficients
            self.ldc.configure_sensor_coeffs(self.config.model_coeffs)
            
            # Configure PID coefficients
            self.ldc.configure_PID_coeffs(self.config.pid_coeffs)
            
            # Set temperature setpoint
            self.ldc.set_temp(self.config.setpoint)
            
            self._log("Device configured with current settings")
            
        except Exception as e:
            self._log(f"Device configuration error: {e}", "error")

    # === Temperature Control ===
    
    def tec_on(self) -> bool:
        """Turn on the TEC"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            success = self.ldc.tec_on()
            if success:
                self._log("TEC turned on")
            else:
                self._log("Failed to turn on TEC", "error")
            return success
            
        except Exception as e:
            self._log(f"TEC on error: {e}", "error")
            return False

    def tec_off(self) -> bool:
        """Turn off the TEC"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            success = self.ldc.tec_off()
            if success:
                self._log("TEC turned off")
            else:
                self._log("Failed to turn off TEC", "error")
            return success
            
        except Exception as e:
            self._log(f"TEC off error: {e}", "error")
            return False

    def get_tec_status(self) -> bool:
        """Get TEC status - True if on, False if off"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            status = self.ldc.tec_status()
            return status
            
        except Exception as e:
            self._log(f"TEC status error: {e}", "error")
            return False

    def get_temperature(self) -> float:
        """Get current temperature reading"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return None
                
            temp = self.ldc.get_temp()
            return temp
            
        except Exception as e:
            self._log(f"Temperature read error: {e}", "error")
            return None

    def set_temperature(self, temperature: float) -> bool:
        """Set target temperature"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            success = self.ldc.set_temp(temperature)
            if success:
                self.config.setpoint = temperature
                self._log(f"Temperature setpoint set to {temperature}°C")
                
                # Update shared memory config
                if self.use_shared_memory:
                    try:
                        write_shared_ldc_config(self.shm_config, self.config)
                    except Exception as e:
                        self._log(f"Failed to update shared memory: {e}")
            else:
                self._log(f"Failed to set temperature to {temperature}°C", "error")
                
            return success
            
        except Exception as e:
            self._log(f"Set temperature error: {e}", "error")
            return False

    def get_temperature_setpoint(self) -> float:
        """Get current temperature setpoint"""
        return self.config.setpoint

    # === Configuration ===
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        try:
            if self.ldc:
                return self.ldc.get_config()
            else:
                return self.config.to_dict()
        except Exception as e:
            self._log(f"Get config error: {e}", "error")
            return {}

    def update_config(self, new_config: LDCConfiguration) -> bool:
        """Update configuration"""
        try:
            old_config = self.config
            self.config = new_config
            
            # Update shared memory
            if self.use_shared_memory:
                write_shared_ldc_config(self.shm_config, new_config)
            
            # If connected, reconfigure device
            if self._connected:
                self._configure_device()
            
            self._log("Configuration updated")
            return True
            
        except Exception as e:
            self.config = old_config  # Rollback
            self._log(f"Config update error: {e}", "error")
            return False

    def set_sensor_coefficients(self, coeffs: List[float]) -> bool:
        """Set sensor model coefficients"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            if len(coeffs) != 3:
                self._log("Sensor coefficients must be a list of 3 floats [A, B, C]", "error")
                return False
                
            success = self.ldc.configure_sensor_coeffs(coeffs)
            if success:
                self.config.model_coeffs = coeffs
                self._log(f"Sensor coefficients updated: {coeffs}")
            else:
                self._log("Failed to configure sensor coefficients", "error")
                
            return success
            
        except Exception as e:
            self._log(f"Set sensor coefficients error: {e}", "error")
            return False

    def set_pid_coefficients(self, coeffs: List[float]) -> bool:
        """Set PID control coefficients"""
        try:
            if not self.ldc or not self._connected:
                self._log("LDC not connected", "error")
                return False
                
            if len(coeffs) != 3:
                self._log("PID coefficients must be a list of 3 floats [P, I, D]", "error")
                return False
                
            success = self.ldc.configure_PID_coeffs(coeffs)
            if success:
                self.config.pid_coeffs = coeffs
                self._log(f"PID coefficients updated: {coeffs}")
            else:
                self._log("Failed to configure PID coefficients", "error")
                
            return success
            
        except Exception as e:
            self._log(f"Set PID coefficients error: {e}", "error")
            return False

    # === Event Handling ===
    
    def add_event_callback(self, callback: Callable[[LDCEvent], None]):
        """Register callback for LDC events."""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[LDCEvent], None]):
        """Remove event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def _handle_ldc_event(self, event: LDCEvent) -> None:
        """Handle events from LDC controller and forward to callbacks"""
        self._log(f"Event: {event.event_type.value} - {event.data}")
        
        # Forward event to all callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self._log(f"Event callback error: {e}", "error")

    # === Status and Monitoring ===
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device information and status"""
        try:
            return {
                "connected": self._connected,
                "tec_status": self.get_tec_status() if self._connected else False,
                "current_temp": self.get_temperature() if self._connected else None,
                "temp_setpoint": self.get_temperature_setpoint(),
                "visa_address": self.config.visa_address,
                "sensor_type": self.config.sensor_type,
                "model_coeffs": self.config.model_coeffs,
                "pid_coeffs": self.config.pid_coeffs,
                "use_shared_memory": self.use_shared_memory
            }
            
        except Exception as e:
            self._log(f"Get device info error: {e}", "error")
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        return self.get_device_info()