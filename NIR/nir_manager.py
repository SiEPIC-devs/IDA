import logging
from typing import Dict, Any, Callable, List, Optional, Tuple
from dataclasses import dataclass, asdict

# from NIR.nir_controller import NIR8164
from NIR.hal.nir_hal import LaserEvent
from NIR.hal.nir_factory import create_driver
from NIR.config.nir_config import NIRConfiguration
from utils.logging_helper import setup_logger

"""
Cameron Basara, 2025
"""

# logger = logging.getLogger(__name__)


class NIRManager:
    def __init__(self, config: NIRConfiguration, use_shared_memory: bool = False, debug: bool = False):
        self.config = config
        self.debug = debug
        self._connected = False
        self._event_callbacks: List[Callable[[LaserEvent], None]] = []

        # Setup logger
        self.logger = setup_logger("NIRManager", "NIR", debug_mode=debug)

        # Initialize controller
        cfg = self.config.to_dict()
        driver_key = cfg.get('driver_types')
        self.controller = create_driver(driver_key, **cfg)
                
        # Slot info helper
        self.slot_info = None

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)

    ######################################################################
    # Context manager
    ######################################################################

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

    ######################################################################
    # Device lifecycle
    ######################################################################
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
                self._log("Connected to NIR device")
                self._connected = True
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
                    self._connected = False
                    self._log("Disconnected from NIR device")
                return success
            return True
        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            return False

    def is_connected(self) -> bool:
        """Check if connected to the NIR device"""
        return self._connected and self.controller._is_connected()

    def _configure_device(self):
        """Configure device with current settings"""
        try:
            if not self.controller or not self._connected:
                return

            # Configure units
            ok = self.controller.configure_units()
            if ok:
                pass
            else:
                raise
            if hasattr(self.config, 'initial_wavelength_nm'):
                aok = self.controller.set_wavelength(self.config.initial_wavelength_nm)
                if aok:
                    pass
                else:
                    raise
            if hasattr(self.config, 'initial_power_dbm'):
                bok = self.controller.set_power(self.config.initial_power_dbm)
                if bok:
                    pass
                else:
                    raise
            self._log("Device configured with current settings")
        except Exception as e:
            self._log(f"Device configuration error: {e}", "error")

    def get_mainframe_slot_info(self):
        """ 
        Get slot information for a 816x mainframe

        Specify return data as follows:

        [(MF,slot,head), ...] 
        """
        try:
            if not self.controller or not self._connected:
                return

            if hasattr(self.controller, "get_mainframe_slot_info"):
                self.slot_info = self.controller.get_mainframe_slot_info()
            else:
                return [(0,1,0),(0,1,1)]  # Default to 1 slot
            return self.slot_info
        
        except Exception as e:
            self._log(f"Mainframe slot info: {e}", "error")
            return None

    ######################################################################
    # Laser control
    ######################################################################
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
            if wavelength is None:
                raise
            return wavelength

        except Exception as e:
            self._log(f"Get wavelength error: {e}", "error")
            return 0.0

    def set_power(self, power_dbm: float) -> bool:
        """Set laser power in dBm"""
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
                return 0.0

            power = self.controller.get_power()
            return power

        except Exception as e:
            self._log(f"Get power error: {e}", "error")
            return 0.0

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
        """ Check if laser is enabled """
        try:
            if not self.controller or not self._connected:
                return False

            return self.controller.get_output_state()

        except Exception as e:
            self._log(f"Laser status error: {e}", "error")
            return False

    ######################################################################
    # Detector methods
    ######################################################################
    def read_power(self, slot: int = 1, head: int = 0, mf: int = 0) -> tuple[float, float]:
        """Read power from detector channel"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return -80.0

            reading = self.controller.read_power(slot, head, mf)
            if reading > 0.0:
                reading = -80.0
            return reading

        except Exception as e:
            self._log(f"Read power error: {e}", "error")
            return -80.0

    def set_detector_units(self, slot, units: int = 0, mf: int = 0) -> bool:
        """Set Detector units"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False

            self.controller.set_detector_units(slot, units=units, mf=mf)
            return True

        except Exception as e:
            self._log(f"Set detector units error: {e}", "error")
            return False

    def get_detector_units(self, slot) -> bool:
        """Get Detector units"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False
            self.controller.get_detector_units(slot)
            return True
        except Exception as e:
            self._log(f"Get detector units error: {e}", "error")
            return False

    def set_power_range(self, range_dbm: float, slot: int = 1, mf: int = 0) -> bool:
        """Set power range"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False

            ok = self.controller.set_power_range(range_dbm, slot, mf)
            if ok:
                self._log(f"Power range set to {range_dbm}dBm for slot {slot}", "info")
                return True
            else:
                self._log(f"Failed to set power range for slot {slot}", "error")
                return False
        except Exception as e:
            self._log(f"Set detector range error: {e}", "error")
            return False

    def set_power_range_auto(self, slot: int = 1, mf: int = 0):
        """Set the devices power ranging to auto"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False

            ok = self.controller.set_power_range_auto(slot, mf)
            if ok:
                self._log(f"[NIR Manager] Set power range auto: {slot}")
                return True
            self._log(f"Failed to set power range auto: {slot}dBm", "error")
            return False
        except Exception as e:
            self._log(f"Set power range error: {e}", "info")
            return False

    def get_power_range(self, slot) -> Optional[Tuple]:
        """Get power range"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False
            ok = self.controller.get_power_range(slot)
            if not ok:
                self._log(f"Failed to get power range: {ok}dBm", "error")
                return False
            self._log(f"Power range set to {ok}dBm", "info")
            return ok
        except Exception as e:
            self._log(f"Get detector range error: {e}", "error")
            return False

    def set_power_reference(self, ref_dbm: float, slot: int = 1, mf: int = 0) -> bool:
        """Set power reference (noise floor)"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False

            success = self.controller.set_power_reference(ref_dbm, slot, mf)
            if success:
                self._log(f"Power reference set to {ref_dbm}dBm for slot {slot}", "info")
            else:
                self._log(f"Failed to set power reference to {ref_dbm}dBm for slot {slot}", "error")
            return success

        except Exception as e:
            self._log(f"Set power reference error: {e}", "error")
            return False

    def get_power_reference(self, slot: int = 1) -> Optional[Tuple]:
        """Get current power reference (noise floor)"""
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return False

            ok = self.controller.get_power_reference(slot)
            if not ok:
                self._log(f"Failed to get power reference: {ok}dBm", "error")
                return False
            self._log(f"Power reference set to {ok}dBm for slot {slot}", "info")
            return ok

        except Exception as e:
            self._log(f"Get power reference error: {e}", "error")
            return False

    ######################################################################
    # Sweep methods
    ######################################################################
    def sweep(self, start_nm, stop_nm,
              step_nm, laser_power_dbm,
              num_scans=0, args=[]):
        """
        Execute a lambda scan, auto stitches longer measurements (>20,001 points)
        params:
            start_nm[nm]: start of sweep in nm
            stop_nm[nm]: end of sweep in nm
            step_nm[nm]: step size of sweep in nm
            laser_power_dbm[dbm]: laser power in dBm
            num_scans[int]: num scans zero indexes up to 3,
            :param args: input arguments for changing the reference and ranging before
                      a sweep has been taken. Use these parameter naming convention,
                      should be taken from shared memory config. Group args into a 
                      list of 3 tuples like the following:
                      lambda_scan(..., [(slot1=1, ref1=-10, range1=-80),
                                  (slot2=2, ref2=-20, range2=None)])
                                  but w/o var names: [(1,-30.0, -20.0)] 
                      :param slot[int]: master/slave channel slot
                      :param ref[float]: reference value in dBm (PWM relative internal)
                      :param range[float]: range value in dBm, if None, then autorange
        """
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return None, None

            # (wavelengths[nm], channels[ch1[dBm], ch2[dBm], ..., chn[dBm]])
            results = self.controller.optical_sweep(
                start_nm, stop_nm, step_nm, laser_power_dbm,
                num_scans, args)
            self.controller.cleanup_scan()
            self.controller.set_wavelength(self.config.initial_wavelength_nm)
            self.controller.configure_units()
            
            if results is not None:
                self._log("Lambda scan completed successfully")
                # results is (wavelengths, channels_list)
                # Return wavelengths and channels directly
                return results[0], results[1]
            else:
                self._log("Lambda scan failed", "error")
                return None, None

        except Exception as e:
            self._log(f"Lambda scan error: {e}", "error")
            return None, None

    def cancel_sweep(self):
        try:
            if not self.controller or not self._connected:
                self._log("Controller not connected", "error")
                return None

            # (wavelengths[nm], channel1[dBm], channel2[dBm])
            results = self.controller.sweep_cancel()
            self.controller.cleanup_scan()

            if results is not None:
                self._log("Lambda scan Interrupted")
                return True
            else:
                self._log("Lambda scan interrupt failed", "error")
                return False

        except Exception as e:
            self._log(f"Lambda scan error: {e}", "error")
            return False

    ######################################################################
    # Configuration
    ######################################################################

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

    ######################################################################
    # Event handling
    ######################################################################

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