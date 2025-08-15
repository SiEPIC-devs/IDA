import logging
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, asdict

from NIR.nir_controller import Agilent8163Controller
from NIR.lambda_sweep import LambdaScanProtocol
from NIR.hal.nir_hal import LaserEvent, LaserEventType
from NIR.config.nir_config import NIRConfiguration  

"""
Cameron Basara, 2025
"""

logger = logging.getLogger(__name__)

class NIRManager:
    def __init__(self, config: NIRConfiguration, use_shared_memory: bool = False, debug: bool = False):
        self.config = config
        self.debug = debug
        self._connected = False
        self._event_callbacks: List[Callable[[LaserEvent], None]] = []
        
        # Initialize controller
        self.controller = Agilent8163Controller(
            com_port=config.com_port,
            laser_slot=config.laser_slot,
            detector_slots=config.detector_slots,
            safety_password=config.safety_password,
            timeout=config.timeout
        )
        
        # # Initialize scan module
        self.scan_module = None
        # self.scan_module = LambdaScanProtocol(
        #     laser=self.controller,
        #     config=self.config,
        #     com_port=config.com_port) 
        
        # Shared memory placeholder
        self.use_shared_memory = use_shared_memory
        if use_shared_memory:
            logger.info("Shared memory support not yet implemented - placeholder")
        
        # Add controller event callback
        self.controller.add_event_callback(self._handle_controller_event)

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if self.debug:
            print(f"[NIR Manager] {message}")
        elif level == "error":
            logger.error(f"[NIR Manager] {message}")

    # === Context Management ===
    
    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()

    def shutdown(self):
        """Shutdown the NIR manager"""
        self.disconnect()
        self._log("NIR manager shutdown complete")

    # === Device Lifecycle ===
    
    def initialize(self) -> bool:
        """Initialize the NIR device"""
        try:
            self._log("Initializing NIR device...")
            
            # Connect to controller
            success = self.connect()
            if success:
                self._log("NIR initialized successfully")
            else:
                self._log("NIR initialization failed", "error")
            return success
            
        except Exception as e:
            self._log(f"NIR initialization error: {e}", "error")
            return False

    def connect(self) -> bool:
        """Connect to the NIR device"""
        try:
            if not self.controller:
                self._log("Controller not initialized", "error")
                return False
                
            success = self.controller.connect()
            if success:
                self._connected = True
                self._log("Connected to NIR device")
                self.scan_module = LambdaScanProtocol(
                    config=self.config, laser=self.controller, com_port=self.config.com_port)
                # Configure device with current settings
                self._configure_device()
            else:
                self._log("Failed to connect to NIR device", "error")
                
            return success
            
        except Exception as e:
            self._log(f"Connection error: {e}", "error")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the NIR device"""
        try:
            if self.controller:
                success = self.controller.disconnect()
                if success:
                    scan = self.scan_module.disconnect()
                    if scan:
                        self._connected = False
                        self._log("Disconnected from NIR device")
                    raise
                return success
            return True
            
        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            return False

    def is_connected(self) -> bool:
        """Check if connected to the NIR device"""
        return self._connected and self.controller.is_connected()

    def _configure_device(self):
        """Configure device with current settings"""
        try:
            if not self.controller or not self._connected:
                return
            
            # Configure units
            self.scan_module.configure_units()
            
            if hasattr(self.config, 'initial_wavelength_nm'):
                self.controller.set_wavelength(self.config.initial_wavelength_nm)
            
            if hasattr(self.config, 'initial_power_dbm'):
                self.controller.set_power(self.config.initial_power_dbm)
            
            self._log("Device configured with current settings")
            
        except Exception as e:
            self._log(f"Device configuration error: {e}", "error")

    # === Laser Control ===
    def set_wavelength(self, wavelength_nm: float) -> bool:
        """Set laser wavelength"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False
                
            success = self.controller.set_wavelength(wavelength_nm)
            if success:
                self._log(f"Wavelength set to {wavelength_nm}nm")
            else:
                self._log(f"Failed to set wavelength to {wavelength_nm}nm", "error")
            return success
            
        except Exception as e:
            self._log(f"Set wavelength error: {e}", "error")
            return False

    def get_wavelength(self) -> float:
        """Get current laser wavelength"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return 0.0
                
            wavelength = self.controller.get_wavelength()
            return wavelength
            
        except Exception as e:
            self._log(f"Get wavelength error: {e}", "error")
            return 0.0

    def set_power(self, power_dbm: float) -> bool:
        """Set laser power"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False
                
            success = self.controller.set_power(power_dbm)
            if success:
                self._log(f"Power set to {power_dbm}dBm")
            else:
                self._log(f"Failed to set power to {power_dbm}dBm", "error")
            return success
            
        except Exception as e:
            self._log(f"Set power error: {e}", "error")
            return False

    def get_power(self) -> float:
        """Get current laser power in dBm"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return -100.0
                
            power, unit = self.controller.get_power()
            return power
            
        except Exception as e:
            self._log(f"Get power error: {e}", "error")
            return -100.0

    def enable_laser(self, enable: bool = True) -> bool:
        """Enable/disable laser output"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False
                
            success = self.controller.enable_output(enable)
            if success:
                state = "enabled" if enable else "disabled"
                self._log(f"Laser {state}")
            else:
                self._log(f"Failed to {'enable' if enable else 'disable'} laser", "error")
            return success
            
        except Exception as e:
            self._log(f"Enable laser error: {e}", "error")
            return False

    def is_laser_on(self) -> bool:
        """Check if laser is enabled"""
        try:
            if not self.controller or not self._connected:
                return False
                
            return self.controller.get_output_state()
            
        except Exception as e:
            self._log(f"Laser status error: {e}", "error")
            return False
    
    # === Scanning Methods ===
    def config_sweep(self):
        try:
            if not self.controller or not self._connected:
                    self._log("Controller not connected", "error")
                    return None
            
            # (wavelengths[nm], channel1[dBm], channel2[dBm])
            results = self.scan_module.sweep()
            if results is not None:
                self._log("Lambda scan completed successfully")
                return results[0], results[1], results[2] 
            else:
                self._log("Lambda scan failed", "error")
                return None, None, None
            
        except Exception as e:
            self._log(f"Lambda scan error: {e}", "error")
            return None, None, None
        
    def sweep(self, start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s=0.02):
        """
        Execute a lambda scan
        """
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return None
            
            # (wavelengths[nm], channel1[dBm], channel2[dBm])
            results = self.scan_module.optical_sweep(
                start_nm, stop_nm, step_nm, laser_power_dbm,
                averaging_time_s=0.02)

            
            if results is not None:
                self._log("Lambda scan completed successfully")
                return results[0], results[1], results[2] 
            else:
                self._log("Lambda scan failed", "error")
                return None, None, None
            
        except Exception as e:
            self._log(f"Lambda scan error: {e}", "error")
            return None, None, None

    # === Power Monitoring ===
    
    def read_power(self, channel: int = 1) -> float:
        """Read power from detector channel"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return -100.0
                
            reading = self.controller.read_power(channel)
            print(reading)
            return reading[0].value, reading[1].value
            
        except Exception as e:
            self._log(f"Read power error: {e}", "error")
            return -100.0

    def check_optical_connections(self) -> Dict[str, Any]:
        """Check optical connections"""
        try:
            if not self.controller or not self._connected:
                return {"error": "Controller not connected"}
                
            return self.controller.check_optical_connections()
            
        except Exception as e:
            self._log(f"Connection check error: {e}", "error")
            return {"error": str(e)}

    # === Configuration ===
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        try:
            config_dict = asdict(self.config)
            if self.controller:
                config_dict.update({
                    "connected": self.is_connected(),
                    "laser_on": self.is_laser_on(),
                    "current_wavelength_nm": self.get_wavelength(),
                    "current_power_dbm": self.get_power()
                })
            return config_dict
        except Exception as e:
            self._log(f"Get config error: {e}", "error")
            return {}

    def update_config(self, new_config: NIRConfiguration) -> bool:
        """Update configuration"""
        try:
            old_config = self.config
            self.config = new_config
            
            # If connected, reconfigure device
            if self._connected:
                self._configure_device()
            
            self._log("Configuration updated")
            return True
            
        except Exception as e:
            self.config = old_config  # Rollback
            self._log(f"Config update error: {e}", "error")
            return False

    # === Event Handling ===
    
    def add_event_callback(self, callback: Callable[[LaserEvent], None]):
        """Register callback for laser events"""
        if callback not in self._event_callbacks:
            self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[LaserEvent], None]):
        """Remove event callback"""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    def _handle_controller_event(self, event: LaserEvent) -> None:
        """Handle events from controller and forward to callbacks"""
        self._log(f"Event: {event.event_type.value} - {event.data}")
        
        # Forward event to all callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self._log(f"Event callback error: {e}", "error")
