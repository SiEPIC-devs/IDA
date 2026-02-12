import logging
import asyncio
import threading
import time
from typing import Dict, Any, Callable, List, Optional
from SMU.keithley2600_controller import Keithley2600BController
from SMU.hal.smu_hal import SMUEvent, SMUEventType
from SMU.hal.smu_factory import create_driver
from SMU.config.smu_config import SMUConfiguration
from utils.logging_helper import setup_logger


class Keithley2600Manager:
    """
    Manager for Keithley 2600 Series SMU - Simplified Implementation
    Following the design patterns of existing managers in the codebase.

    Cameron Basara, 2025
    """

    def __init__(self, config: SMUConfiguration, use_shared_memory: bool = False, debug: bool = False):
        self.config = config
        self.debug = debug or config.debug
        self._connected = False
        self._event_callbacks: List[Callable[[SMUEvent], None]] = []
        self.smu = None

        # Polling and monitoring
        self._is_polling = False
        self._polling_thread: Optional[threading.Thread] = None
        self._last_measurements: Dict[str, Any] = {}
        self._measurement_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Setup logger
        self.logger = setup_logger("Keithley2600Manager", "SMU", debug_mode=self.debug)

        # Validate configuration
        if not self.config.validate():
            self.logger.error("Invalid SMU configuration")
            raise ValueError("Invalid SMU configuration")

        # Shared memory setup (placeholder for future implementation)
        self.use_shared_memory = use_shared_memory or config.use_shared_memory
        if self.use_shared_memory:
            self.logger.warning("Shared memory not yet implemented for SMU")
            self.use_shared_memory = False

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)

    # === Context Management ===

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()

    def shutdown(self):
        """Shutdown the SMU manager"""
        self.stop_polling()
        self.disconnect()
        self._log("Keithley 2600 manager shutdown complete")

    # === Device Lifecycle ===

    def initialize(self) -> bool:
        """Initialize the SMU device"""
        try:
            # Create controller instance using config
            self.smu = Keithley2600BController(
                visa_address=self.config.visa_address,
                nplc=self.config.nplc,
                off_mode=self.config.off_mode
            )

            # Add event callback to forward events
            self.smu.add_event_callback(self._handle_smu_event)

            # Connect to device
            success = self.connect()
            if success:
                self._log("Keithley 2600 initialized successfully")
            else:
                self._log("Keithley 2600 initialization failed", "error")

            return success

        except Exception as e:
            self._log(f"SMU initialization error: {e}", "error")
            return False

    def connect(self) -> bool:
        """Connect to the SMU device"""
        try:
            if not self.smu:
                self._log("SMU not initialized. Call initialize() first.", "error")
                return False

            success = self.smu.connect()
            if success:
                self._connected = True
                self._log("Connected to Keithley 2600 device")
            else:
                self._log("Failed to connect to Keithley 2600 device", "error")

            return success

        except Exception as e:
            self._log(f"Connection error: {e}", "error")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the SMU device"""
        try:
            if self.smu:
                success = self.smu.disconnect()
                if success:
                    self._connected = False
                    self._log("Disconnected from Keithley 2600 device")
                return success
            return True

        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            return False

    def is_connected(self) -> bool:
        """Check if connected to the SMU device"""
        return self._connected

    # === Device Control ===

    def output_on(self, channel: str) -> bool:
        """Turn on output for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.output_on(channel)
            if success:
                self._log(f"Channel {channel} output turned on")
            else:
                self._log(f"Failed to turn on channel {channel} output", "error")
            return success

        except Exception as e:
            self._log(f"Output on error: {e}", "error")
            return False

    def output_off(self, channel: str) -> bool:
        """Turn off output for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.output_off(channel)
            if success:
                self._log(f"Channel {channel} output turned off")
            else:
                self._log(f"Failed to turn off channel {channel} output", "error")
            return success

        except Exception as e:
            self._log(f"Output off error: {e}", "error")
            return False

    def set_source_mode(self, mode: str, channel: str) -> bool:
        """Set source mode (voltage or current) for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_source_mode(mode, channel)
            if success:
                self._log(f"Channel {channel} source mode set to {mode}")
            else:
                self._log(f"Failed to set channel {channel} source mode to {mode}", "error")
            return success

        except Exception as e:
            self._log(f"Set source mode error: {e}", "error")
            return False

    def set_voltage(self, voltage: float, channel: str) -> bool:
        """Set voltage for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_voltage(voltage, channel)
            if success:
                self._log(f"Channel {channel} voltage set to {voltage}V")
            else:
                self._log(f"Failed to set channel {channel} voltage to {voltage}V", "error")
            return success

        except Exception as e:
            self._log(f"Set voltage error: {e}", "error")
            return False

    def set_current(self, current: float, channel: str) -> bool:
        """Set current for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_current(current, channel)
            if success:
                self._log(f"Channel {channel} current set to {current}A")
            else:
                self._log(f"Failed to set channel {channel} current to {current}A", "error")
            return success

        except Exception as e:
            self._log(f"Set current error: {e}", "error")
            return False

    def set_voltage_limit(self, limit: float, channel: str) -> bool:
        """Set voltage limit for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_voltage_limit(limit, channel)
            if success:
                self._log(f"Channel {channel} voltage limit set to {limit}V")
            else:
                self._log(f"Failed to set channel {channel} voltage limit to {limit}V", "error")
            return success

        except Exception as e:
            self._log(f"Set voltage limit error: {e}", "error")
            return False

    def set_current_limit(self, limit: float, channel: str) -> bool:
        """Set current limit for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_current_limit(limit, channel)
            if success:
                self._log(f"Channel {channel} current limit set to {limit}A")
            else:
                self._log(f"Failed to set channel {channel} current limit to {limit}A", "error")
            return success

        except Exception as e:
            self._log(f"Set current limit error: {e}", "error")
            return False

    def set_power_limit(self, limit: float, channel: str) -> bool:
        """Set power limit for specified channel"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.set_power_limit(limit, channel)
            if success:
                self._log(f"Channel {channel} power limit set to {limit}W")
            else:
                self._log(f"Failed to set channel {channel} power limit to {limit}W", "error")
            return success

        except Exception as e:
            self._log(f"Set power limit error: {e}", "error")
            return False

    # === Measurements ===

    def get_voltage(self) -> Optional[Dict[str, float]]:
        """Get voltage measurements from all channels"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return None

            voltages = self.smu.get_voltage()
            return voltages

        except Exception as e:
            self._log(f"Get voltage error: {e}", "error")
            return None

    def get_current(self) -> Optional[Dict[str, float]]:
        """Get current measurements from all channels"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return None

            currents = self.smu.get_current()
            return currents

        except Exception as e:
            self._log(f"Get current error: {e}", "error")
            return None

    def get_resistance(self) -> Optional[Dict[str, float]]:
        """Get resistance measurements from all channels"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return None

            resistances = self.smu.get_resistance()
            return resistances

        except Exception as e:
            self._log(f"Get resistance error: {e}", "error")
            return None

    # === Ranging ===

    def source_range(self, range_val: float, channels: List[str], var_type: str) -> bool:
        """Set source range for specified channels"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.source_range(range_val, channels, var_type)
            if success:
                self._log(f"Source range set to {range_val} for {var_type} on channels {channels}")
            else:
                self._log(f"Failed to set source range", "error")
            return success

        except Exception as e:
            self._log(f"Source range error: {e}", "error")
            return False

    def source_autorange(self, lowest_range: Optional[float], channels: List[str], var_type: str) -> bool:
        """Enable autorange for specified channels"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            success = self.smu.source_autorange(lowest_range, channels, var_type)
            if success:
                self._log(f"Autorange enabled for {var_type} on channels {channels}")
            else:
                self._log(f"Failed to enable autorange", "error")
            return success

        except Exception as e:
            self._log(f"Source autorange error: {e}", "error")
            return False

    # === IV Sweeps ===

    def iv_sweep(self, start: float, stop: float, step: float,
                 channels: List[str], sweep_type: str, scale: str = "LIN") -> Optional[Dict[str, Any]]:
        """Perform IV sweep"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return None

            results = self.smu.iv_sweep(start, stop, step, channels, sweep_type, scale)
            self._log(f"IV sweep completed for channels {channels}")
            return results

        except Exception as e:
            self._log(f"IV sweep error: {e}", "error")
            return None

    def iv_sweep_list(self, sweep_list: List[float], channels: List[str],
                      sweep_type: str) -> Optional[Dict[str, Any]]:
        """Perform IV sweep using list of values"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return None

            results = self.smu.iv_sweep_list(sweep_list, channels, sweep_type)
            self._log(f"IV sweep list completed for channels {channels}")
            return results

        except Exception as e:
            self._log(f"IV sweep list error: {e}", "error")
            return None

    # === Configuration ===

    def update_config(self, new_config: SMUConfiguration) -> bool:
        """Update configuration"""
        try:
            if not new_config.validate():
                self._log("Invalid configuration provided", "error")
                return False

            old_config = self.config
            self.config = new_config

            # If connected, may need to reinitialize with new settings
            if self._connected:
                self._log("Configuration updated - device may need reinitialization")

            self._log("Configuration updated successfully")
            return True

        except Exception as e:
            self.config = old_config  # Rollback
            self._log(f"Config update error: {e}", "error")
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        try:
            if self.smu:
                device_config = self.smu.get_config()
                # Merge with manager config
                full_config = self.config.to_dict()
                full_config.update(device_config)
                return full_config
            else:
                return self.config.to_dict()
        except Exception as e:
            self._log(f"Get config error: {e}", "error")
            return {}

    def get_state(self) -> Optional[Dict[str, Any]]:
        """Get device state"""
        try:
            if not self.smu or not self._connected:
                return {"connected": False}

            state = self.smu.get_state()
            return state

        except Exception as e:
            self._log(f"Get state error: {e}", "error")
            return None

    def get_errors(self) -> List[Dict[str, Any]]:
        """Get device errors"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return []

            errors = self.smu.get_errors()
            return errors

        except Exception as e:
            self._log(f"Get errors error: {e}", "error")
            return []

    def clear_errors(self) -> bool:
        """Clear device errors"""
        try:
            if not self.smu or not self._connected:
                self._log("SMU not connected", "error")
                return False

            self.smu.clear_errors()
            self._log("Device errors cleared")
            return True

        except Exception as e:
            self._log(f"Clear errors error: {e}", "error")
            return False

    # === Polling and Monitoring ===

    def start_polling(self) -> bool:
        """Start background polling of SMU measurements"""
        try:
            if self._is_polling:
                self._log("Polling already running")
                return True

            if not self._connected:
                self._log("Cannot start polling - SMU not connected", "error")
                return False

            self._is_polling = True
            self._polling_thread = threading.Thread(
                target=self._polling_loop,
                daemon=True,
                name="Keithley2600_Polling"
            )
            self._polling_thread.start()
            self._log(f"Started polling at {self.config.polling_interval}s intervals")
            return True

        except Exception as e:
            self._log(f"Start polling error: {e}", "error")
            return False

    def stop_polling(self) -> bool:
        """Stop background polling"""
        try:
            if not self._is_polling:
                return True

            self._is_polling = False
            if self._polling_thread and self._polling_thread.is_alive():
                self._polling_thread.join(timeout=2.0)

            self._log("Polling stopped")
            return True

        except Exception as e:
            self._log(f"Stop polling error: {e}", "error")
            return False

    def is_polling(self) -> bool:
        """Check if polling is active"""
        return self._is_polling

    def set_polling_interval(self, interval: float) -> bool:
        """Set polling interval in seconds"""
        try:
            if interval <= 0:
                self._log("Polling interval must be positive", "error")
                return False

            self.config.polling_interval = interval
            self._log(f"Polling interval set to {interval}s")
            return True

        except Exception as e:
            self._log(f"Set polling interval error: {e}", "error")
            return False

    def _polling_loop(self):
        """Background polling loop - runs in separate thread"""
        self._log("Polling loop started")

        while self._is_polling:
            try:
                if not self._connected or not self.smu:
                    time.sleep(1.0)
                    continue

                # Get current measurements
                measurements = self._get_all_measurements()

                if measurements:
                    # Update last measurements
                    self._last_measurements.update(measurements)

                    # Notify measurement callbacks
                    self._notify_measurement_callbacks(measurements)

                    # Update shared memory if enabled (placeholder)
                    if self.use_shared_memory:
                        self._update_shared_memory(measurements)

                time.sleep(self.config.polling_interval)

            except Exception as e:
                self._log(f"Polling loop error: {e}", "error")
                time.sleep(1.0)

        self._log("Polling loop stopped")

    def _get_all_measurements(self) -> Optional[Dict[str, Any]]:
        """Get all current measurements from SMU"""
        try:
            measurements = {
                'timestamp': time.time(),
                'voltage': self.smu.get_voltage(),
                'current': self.smu.get_current(),
                'resistance': self.smu.get_resistance(),
                'voltage_limits': self.smu.get_voltage_limits(),
                'current_limits': self.smu.get_current_limits(),
                'power_limits': self.smu.get_power_limits(),
                'state': self.smu.get_state()
            }
            return measurements

        except Exception as e:
            self._log(f"Get all measurements error: {e}", "error")
            return None

    def _update_shared_memory(self, measurements: Dict[str, Any]):
        """Update shared memory with measurements (placeholder)"""
        # TODO: Implement shared memory updates when shared memory is available
        pass

    def get_last_measurements(self) -> Dict[str, Any]:
        """Get the last polled measurements"""
        return self._last_measurements.copy()

    def add_measurement_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for measurement updates"""
        try:
            if callback not in self._measurement_callbacks:
                self._measurement_callbacks.append(callback)
                self._log("Measurement callback added")
        except Exception as e:
            self._log(f"Add measurement callback error: {e}", "error")

    def remove_measurement_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove measurement callback"""
        try:
            if callback in self._measurement_callbacks:
                self._measurement_callbacks.remove(callback)
                self._log("Measurement callback removed")
        except Exception as e:
            self._log(f"Remove measurement callback error: {e}", "error")

    def _notify_measurement_callbacks(self, measurements: Dict[str, Any]):
        """Notify all measurement callbacks"""
        for callback in self._measurement_callbacks:
            try:
                callback(measurements)
            except Exception as e:
                self._log(f"Measurement callback error: {e}", "error")

    # === Event Handling ===

    def add_event_callback(self, callback: Callable[[SMUEvent], None]):
        """Register callback for SMU events."""
        try:
            if callback not in self._event_callbacks:
                self._event_callbacks.append(callback)
        except Exception as e:
            self.logger.error(f"Failed to add event callback: {e}")

    def remove_event_callback(self, callback: Callable[[SMUEvent], None]):
        """Remove event callback."""
        try:
            if callback in self._event_callbacks:
                self._event_callbacks.remove(callback)
        except Exception as e:
            self.logger.error(f"Failed to remove event callback: {e}")

    def _handle_smu_event(self, event: SMUEvent) -> None:
        """Handle events from SMU controller and forward to callbacks"""
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
            device_info = {
                "connected": self._connected,
                "visa_address": self.config.visa_address,
                "nplc": self.config.nplc,
                "off_mode": self.config.off_mode,
                "use_shared_memory": self.use_shared_memory,
                "polling_active": self._is_polling,
                "polling_interval": self.config.polling_interval,
                "last_measurements": self._last_measurements
            }

            if self._connected and self.smu:
                try:
                    device_info["idn"] = self.smu.idn()
                    device_info["state"] = self.smu.get_state()
                except Exception as e:
                    self._log(f"Error getting device details: {e}", "error")

            return device_info

        except Exception as e:
            self._log(f"Get device info error: {e}", "error")
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get manager status"""
        return self.get_device_info()