import asyncio
import time
import pyvisa
import struct
from typing import Optional, Tuple, List, Dict, Any

from NIR.hal.nir_hal import LaserHAL, LaserState, SweepState, PowerUnit, WavelengthRange, PowerReading, LaserEventType
from NIR.hal.nir_factory import register_driver
from NIR.drivers.agilent_8163a import agilent_8163a_mainframe

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

"""
Cameron Basara, 2025
"""

class Agilent8163Controller(LaserHAL):
    """
    HAL implementation for Agilent 8163A Multi-slot Optical System via GPIB
    
    This instrument can contain multiple modules:
        - Tunable laser sources (TLS)
        - Power meter detector heads
    """

    def __init__(self, 
                com_port: int,
                laser_slot: int = 0,
                detector_slots: List[int] = None,
                safety_password: str = "1234",
                instrument_id: str = None,
                timeout: int = 5000):
        """
        Initialize Agilent 8163A with GPIB communication
        
        Args:
            gpib_address: GPIB address of the instrument (typically 1-30)
            gpib_board: GPIB board number (usually 0)
            laser_slot: Slot number containing tunable laser
            detector_slots: List of slots containing power detectors
            safety_password: 4-digit laser safety password
            instrument_id: Optional instrument identifier
            timeout: Communication timeout in milliseconds
        """
        super().__init__(instrument_id or f"GPIB{gpib_board}::{gpib_address}::INSTR")
        
        self.gpib_address = gpib_address
        self.gpib_board = gpib_board
        self.laser_slot = laser_slot
        self.detector_slots = detector_slots or [2] # 347 specific
        self.safety_password = safety_password
        self.timeout = timeout

        # GPIB connection via PyVISA
        self.resource_manager: Optional[pyvisa.ResourceManager] = None
        self.instrument: Optional[pyvisa.Resource] = None
        
        # Command generator 
        self.cmd = agilent_8163a_mainframe()
        
        # State tracking 
        self._current_wavelength = 1550.0  # nm
        self._current_power = -10.0  # dBm
        self._output_enabled = False
        self._sweep_active = False
        self._sweep_range = WavelengthRange(1520.0, 1570.0)
        self._sweep_speed = 1.0  # nm/s
        
        # Logging state per channel
        self._logging_active = {}
        self._logged_data = {}

    # Connection management
    async def connect(self) -> bool:
        """Connect to agilent mainframe via GPIB using Prologix GPIB-USB converter"""
        try:
            # Initialize PyVISA resource manager
            self.resource_manager = pyvisa.ResourceManager()
            
            # Use COM port for Prologix GPIB-USB converter (LDC pattern)
            # Construct visa address - typically COM3, COM4, etc.
            visa_address = f"ASRL{self.gpib_address}::INSTR"  # Reuse gpib_address as COM port number
            
            # Open instrument connection with serial parameters for Prologix
            self.instrument = self.resource_manager.open_resource(
                visa_address,
                baud_rate=9600,
                timeout=self.timeout,
                write_termination='\n',
                read_termination='\n'
            )
            
            # Configure Prologix GPIB-USB controller (matching LDC pattern)
            await asyncio.sleep(0.1)
            loop = asyncio.get_event_loop()
            
            # Set controller mode
            await loop.run_in_executor(None, lambda: self.instrument.write('++mode 1'))
            await asyncio.sleep(0.1)
            
            # Set GPIB address for the Agilent 8163A (typically address 20)
            await loop.run_in_executor(None, lambda: self.instrument.write(f'++addr 20'))
            await asyncio.sleep(0.1)
            
            # Enable auto mode
            await loop.run_in_executor(None, lambda: self.instrument.write('++auto 1'))
            await asyncio.sleep(0.1)
            
            # Enable EOI assertion
            await loop.run_in_executor(None, lambda: self.instrument.write('++eoi 1'))
            await asyncio.sleep(0.1)
            
            # Set EOS mode
            await loop.run_in_executor(None, lambda: self.instrument.write('++eos 0'))
            await asyncio.sleep(0.1)
            
            # Set read timeout
            await loop.run_in_executor(None, lambda: self.instrument.write('++read_tmo_ms 3000'))
            await asyncio.sleep(0.1)
            
            # Test connection with identity query
            resp = await self._send_command(self.cmd.identity())

            if "8163" in resp:
                self._is_connected = True
                logger.info(f"Connected to {resp.strip()}")

                # Clear status after successful connection
                await self._send_command(self.cmd.clear_status(), expect_response=False)

                # Check and unlock laser if needed
                await self._send_command(self.cmd.lock_laser("0", self.safety_password), expect_response=False)
                if not await self._verify_slots():
                    logger.warning("Some expected modules not found")
                
                self._emit_event(LaserEventType.OUTPUT_ENABLED, {"connected": True})
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"[CONNECT] GPIB Connection error: {e}")
            if self.instrument:
                try:
                    self.instrument.close()
                except:
                    pass
                self.instrument = None
            if self.resource_manager:
                try:
                    self.resource_manager.close()
                except:
                    pass
                self.resource_manager = None
            return False

    async def disconnect(self,) -> bool:
        """Disconnect GPIB connection"""
        try:
            if self._is_connected and self.instrument:
                # Safe shutdown sequence
                await self.enable_output(False)
                await self.stop_sweep()
                
                self.instrument.close()
                self.instrument = None
                
                if self.resource_manager:
                    self.resource_manager.close()
                    self.resource_manager = None
                    
                self._is_connected = False
            return True
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False
        
    # Communication protocols
    async def _send_command(self, command: str, expect_response: bool = True, timeout: float = 5.0) -> str:
        """
        Send command via GPIB using PyVISA with proper async handling
        """
        if not self.instrument:
            logger.error("[SEND_CMD] No GPIB connection available")
            raise RuntimeError("Not connected to instrument")
        
        try:
            # PyVISA operations are inherently blocking, so we run them in executor
            # to maintain async compatibility
            loop = asyncio.get_event_loop()
            
            if expect_response:
                # Use query for commands that expect a response
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.instrument.query(command)
                )
                response = response.strip()
                
                # Handle error checking
                await self._check_and_clear_errors()
                
                return response
            else:
                # Use write for commands that don't expect a response
                await loop.run_in_executor(
                    None,
                    lambda: self.instrument.write(command)
                )
                
                # Just check for errors
                await self._check_and_clear_errors()
                return ""
                
        except Exception as e:
            logger.error(f"GPIB command failed: {command}, Error: {e}")
            raise
    
    async def _check_and_clear_errors(self):
        """Error checking pattern adapted for GPIB (cleaned up from legacy)"""
        try:
            loop = asyncio.get_event_loop()
            error_response = await loop.run_in_executor(
                None,
                lambda: self.instrument.query(self.cmd.check_error())
            )
            
            # Ignore the specific "Query UNTERMINATED" error that legacy code ignores
            if '-420,"Query UNTERMINATED"' in error_response or '420,"Query UNTERMINATED"' in error_response:
                await loop.run_in_executor(
                    None,
                    lambda: self.instrument.write(self.cmd.clear_status())
                )
                return
            
            # Log other errors but don't raise 
            if error_response and "No error" not in error_response:
                logger.error(f"Instrument error: {error_response}")
            
            # Always clear status 
            await loop.run_in_executor(
                None,
                lambda: self.instrument.write(self.cmd.clear_status())
            )
            
        except Exception as e:
            logger.error(f"Error checking failed: {e}")
    
    async def _verify_slots(self) -> bool:
        """Verify that expected modules are installed"""
        try:
            options_resp = await self._send_command(self.cmd.options())
            logger.info(f"Installed modules: {options_resp}")
            
            # Check for laser slot (legacy uses model name lookup)
            # For now, just assume slot is correct if we get a response
            return True
            
        except Exception as e:
            logger.error(f"Slot verification failed: {e}")
            return False
    
    ############## LASER SOURCE METHODS ##############
    async def set_wavelength(self, wavelength: float) -> bool:
        """Set laser wavelength, in nm"""
        try:
            await self._send_command(self.cmd.clear_status(), expect_response=False)
            
            cmd = self.cmd.set_laser_current_wavelength(self.laser_slot, wavelength)
            await self._send_command(cmd, expect_response=False)
            
            self._current_wavelength = wavelength
            self._emit_event(LaserEventType.WAVELENGTH_CHANGED, {"wavelength": wavelength})
            return True
            
        except Exception as e:
            logger.error(f"Set wavelength failed: {e}")
            return False
    
    async def get_wavelength(self) -> float:
        """Get current wavelength """
        try:
            cmd = self.cmd.read_laser_wavelength(self.laser_slot)
            resp = await self._send_command(cmd)
            
            # Parse response 
            wavelength_str = resp.replace("nm", "").replace("NM", "").strip() # legacy
            wavelength = float(wavelength_str)
            
            self._current_wavelength = wavelength
            return wavelength
            
        except Exception as e:
            logger.error(f"Get wavelength failed: {e}")
            return self._current_wavelength
    
    async def set_power(self, power: float, unit: PowerUnit = PowerUnit.DBM) -> bool:
        """Set laser power"""
        try:
            await self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Set power unit, then power level 
            unit_value = "0" if unit == PowerUnit.DBM else "1"
            unit_cmd = self.cmd.laser_power_units(self.laser_slot, unit_value)
            await self._send_command(unit_cmd, expect_response=False)
            
            power_str = f"{power}dbm" if unit == PowerUnit.DBM else f"{power}W"
            power_cmd = self.cmd.set_laser_current_power(self.laser_slot, power_str)
            await self._send_command(power_cmd, expect_response=False)
            
            self._current_power = power
            self._emit_event(LaserEventType.POWER_CHANGED, {"power": power, "unit": unit.value})
            return True
            
        except Exception as e:
            logger.error(f"Set power failed: {e}")
            return False
        
    async def get_power(self) -> Tuple[float, PowerUnit]:
        """Get current power"""
        try:
            cmd = self.cmd.read_laser_power(self.laser_slot)
            response = await self._send_command(cmd)
            
            # Parse power and unit from response
            if "DBM" in response.upper() or "dbm" in response:
                power_str = response.replace("DBM", "").replace("dbm", "").strip()
                power = float(power_str)
                unit = PowerUnit.DBM
            else:
                power_str = response.replace("W", "").strip() # won't
                power = float(power_str)
                unit = PowerUnit.WATTS
            
            self._current_power = power
            return power, unit
            
        except Exception as e:
            logger.error(f"Get power failed: {e}")
            return self._current_power, PowerUnit.DBM
    
    async def enable_output(self, enable: bool = True) -> bool:
        """Enable/disable laser output"""
        try:
            await self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Legacy uses both laser_current and set_laser_power_state
            current_cmd = self.cmd.laser_current(self.laser_slot, "1" if enable else "0")
            await self._send_command(current_cmd, expect_response=False)
            
            power_cmd = self.cmd.set_laser_power_state(self.laser_slot, "1" if enable else "0")
            await self._send_command(power_cmd, expect_response=False)
            
            self._output_enabled = enable
            event_type = LaserEventType.OUTPUT_ENABLED if enable else LaserEventType.OUTPUT_DISABLED
            self._emit_event(event_type, {"enabled": enable})
            return True
            
        except Exception as e:
            logger.error(f"Enable output failed: {e}")
            return False
    
    async def get_output_state(self) -> bool:
        """Get output state"""
        try:
            cmd = self.cmd.read_laser_current(self.laser_slot)
            response = await self._send_command(cmd)
            
            self._output_enabled = "1" in response
            return self._output_enabled
            
        except Exception as e:
            logger.error(f"Get output state failed: {e}")
            return self._output_enabled

    ############## SWEEP UTILITY METHODS ##############
    async def set_sweep_state(self, enable: bool) -> bool:
        """Enable/disable sweep """
        try:
            if enable:
                # Legacy sweep setup sequence
                await self._send_command(self.cmd.clear_status(), expect_response=False)
                
                # Configure sweep parameters first
                await self.set_sweep_range(self._sweep_range.start, self._sweep_range.stop)
                await self.set_sweep_speed(self._sweep_speed)
                
                # Set sweep mode and parameters 
                await self._send_command(
                    self.cmd.set_laser_sweep_mode(self.laser_slot, "CONT"), 
                    expect_response=False
                )
                await self._send_command(
                    self.cmd.set_laser_sweep_cycles(self.laser_slot, "1"), 
                    expect_response=False
                )
                await self._send_command(
                    self.cmd.set_laser_sweep_directionality(self.laser_slot, "ONEWay"), 
                    expect_response=False
                )
                
                # Arm and start sweep
                await self._send_command(
                    self.cmd.arm_laser_sweep(self.laser_slot), 
                    expect_response=False
                )
                
                # Start sweep
                cmd = self.cmd.set_laser_sweep_state(self.laser_slot, "1", "STAR")
                await self._send_command(cmd, expect_response=False)
            else:
                # Stop sweep
                cmd = self.cmd.set_laser_sweep_state(self.laser_slot, "1", "STOP")
                await self._send_command(cmd, expect_response=False)
            
            self._sweep_active = enable
            event_type = LaserEventType.SWEEP_STARTED if enable else LaserEventType.SWEEP_STOPPED
            self._emit_event(event_type, {"enabled": enable})
            return True
            
        except Exception as e:
            logger.error(f"Set sweep state failed: {e}")
            return False
        
    async def get_sweep_state(self) -> SweepState:
        """Get sweep state"""
        try:
            cmd = self.cmd.read_laser_sweep_state(self.laser_slot, "1")
            response = await self._send_command(cmd)
            
            if "1" in response:
                return SweepState.RUNNING
            else:
                return SweepState.STOPPED
                
        except Exception as e:
            logger.error(f"Get sweep state failed: {e}")
            return SweepState.STOPPED if not self._sweep_active else SweepState.RUNNING
    
    async def set_sweep_range(self, start_nm: float, stop_nm: float) -> bool:
        """Set sweep range"""
        try:
            # Set start wavelength
            start_cmd = self.cmd.set_sweep_wavelength(self.laser_slot, "STAR", f"{start_nm}nm")
            await self._send_command(start_cmd, expect_response=False)
            
            # Set stop wavelength  
            stop_cmd = self.cmd.set_sweep_wavelength(self.laser_slot, "STOP", f"{stop_nm}nm")
            await self._send_command(stop_cmd, expect_response=False)
            
            self._sweep_range = WavelengthRange(start_nm, stop_nm)
            return True
            
        except Exception as e:
            logger.error(f"Set sweep range failed: {e}")
            return False
    
    async def get_sweep_range(self) -> WavelengthRange:
        """Get sweep range"""
        return self._sweep_range
    
    async def set_sweep_speed(self, speed: float) -> bool:
        """Set sweep speed, continous"""
        try:
            cmd = self.cmd.set_continuous_sweep_speed(self.laser_slot, f"{speed}nm/s")
            await self._send_command(cmd, expect_response=False)
            
            self._sweep_speed = speed
            return True
            
        except Exception as e:
            logger.error(f"Set sweep speed failed: {e}")
            return False
    
    async def get_sweep_speed(self) -> float:
        """Get sweep speed"""
        try:
            cmd = self.cmd.read_continuous_sweep_speed(self.laser_slot)
            response = await self._send_command(cmd)
            
            speed_str = response.replace("nm/s", "").replace("NM/S", "").strip()
            speed = float(speed_str)
            
            self._sweep_speed = speed
            return speed
            
        except Exception as e:
            logger.error(f"Get sweep speed failed: {e}")
            return self._sweep_speed
    
    ############## HARDWARE TRIGGER METHODS ##############
    async def configure_hardware_triggers(
        self, 
        trigger_mode: str = "DEF",  # DIS, DEF, PASS, LOOP
        laser_output_trigger: str = "SWS",  # When laser generates trigger: SWS=sweep start
        detector_input_trigger: str = "SME",  # How detector responds: SME=single measurement
        configure_detector_outputs: bool = True  # Configure detector output triggers
    ) -> bool:
        """
        Configure hardware triggering for precise laser/detector synchronization.
        
        Configures triggers for the actual detector slots in use (self.detector_slots).
        This way it works regardless of stage configuration differences.
        """
        try:
            logger.info(f"Configuring hardware triggers: mode={trigger_mode}")
            logger.info(f"Laser slot: {self.laser_slot}, Detector slots: {self.detector_slots}")
            
            # Set global trigger configuration
            await self._send_command(
                self.cmd.set_hardware_trigger_config(trigger_mode),
                expect_response=False
            )
            
            # Configure laser output trigger timing (when laser generates triggers)
            await self._send_command(
                self.cmd.set_laser_output_trigger_timing(self.laser_slot, laser_output_trigger),
                expect_response=False  
            )
            
            # Configure each detector slot that's actually in use
            for detector_slot in self.detector_slots:
                # Set how detector responds to input triggers
                await self._send_command(
                    self.cmd.set_incoming_trigger_response(detector_slot, detector_input_trigger),
                    expect_response=False
                )
                
                # Configure detector output triggers (for chaining/advanced use)
                if configure_detector_outputs:
                    # Configure standard channels (1 and 2) for this detector slot
                    for channel in [1, 2]:
                        try:
                            await self._send_command(
                                self.cmd.set_detector_output_trigger_timing(detector_slot, channel, "AVG"),
                                expect_response=False
                            )
                        except Exception as e:
                            # Some slots may not have all channels - that's ok
                            logger.debug(f"Channel {channel} not available on slot {detector_slot}: {e}")
            
            logger.info("Hardware triggering configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Hardware trigger configuration failed: {e}")
            return False
    
    async def enable_internal_triggering(self) -> bool:
        """
        Enable internal triggering - laser automatically triggers detectors.
        
        Perfect for this stage: microsecond precision, no external hardware needed.
        """
        return await self.configure_hardware_triggers(
            trigger_mode="DEF",           # Enable trigger connectors
            laser_output_trigger="SWS",   # Trigger when sweep point is stable  
            detector_input_trigger="SME"  # Take single measurement per trigger
        )
    
    async def disable_triggering(self) -> bool:
        """Disable hardware triggering (fallback to software timing)"""
        return await self.configure_hardware_triggers(trigger_mode="DIS")

    ############## DETECTOR METHODS, IMPLEMENTING DETECTOR FUCNTIONALITY ##############

    async def read_power(self, channel: int = 1) -> PowerReading:
        """Read power from detector"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Legacy pattern includes averaging time delay
            await self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Small delay for averaging (from legacy code)
            await asyncio.sleep(0.1)
            
            cmd = self.cmd.read_power(detector_slot, channel)
            response = await self._send_command(cmd)
            
            # Parse power value (legacy returns float directly)
            power_value = float(response.strip())
            
            # Legacy code converts W to dBm: 10 * log10(W) + 30
            # Assume response is already in correct units based on previous settings for now
            
            wavelength = await self.get_wavelength()
            
            return PowerReading(
                value=power_value,
                unit=PowerUnit.DBM,  # dBm for now
                wavelength=wavelength
            )
            
        except Exception as e:
            logger.error(f"Read power failed: {e}")
            return PowerReading(value=-100.0, unit=PowerUnit.DBM)
    
    def _get_detector_slot(self, channel: int) -> int:
        """Get detector slot for logical channel"""
        if channel <= len(self.detector_slots):
            return self.detector_slots[channel - 1]
        return self.detector_slots[0]
    
    async def set_power_unit(self, unit: PowerUnit, channel: int = 1) -> bool:
        """Set power unit"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            unit_str = "0" if unit == PowerUnit.DBM else "1"
            cmd = self.cmd.power_sensor_unit(detector_slot, channel, unit_str)
            await self._send_command(cmd, expect_response=False)
            return True
            
        except Exception as e:
            logger.error(f"Set power unit failed: {e}")
            return False
    
    async def get_power_unit(self, channel: int = 1) -> PowerUnit:
        """Get power unit"""
        # For now return default
        return PowerUnit.DBM
    
    async def set_power_range(self, range_dbm: float, channel: int = 1) -> bool:
        """Set power range """
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Disable autorange first 
            auto_cmd = self.cmd.power_sensor_autorange(detector_slot, "0")
            await self._send_command(auto_cmd, expect_response=False)
            
            # Set range
            range_cmd = self.cmd.set_power_sensor_range(detector_slot, channel, f"{range_dbm}dbm")
            await self._send_command(range_cmd, expect_response=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Set power range failed: {e}")
            return False

    async def get_power_range(self, channel: int = 1) -> float:
        """Get power range"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.read_power_sensor_range(detector_slot, channel)
            response = await self._send_command(cmd)
            
            range_str = response.replace("DBM", "").replace("dbm", "").strip()
            return float(range_str)
            
        except Exception as e:
            logger.error(f"Get power range failed: {e}")
            return 0.0
    
    async def enable_autorange(self, enable: bool = True, channel: int = 1) -> bool:
        """Enable/disable autorange """
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.power_sensor_autorange(detector_slot, "1" if enable else "0")
            await self._send_command(cmd, expect_response=False)
            return True
            
        except Exception as e:
            logger.error(f"Enable autorange failed: {e}")
            return False
    
    ############## DATA LOGGING ##############
    async def start_logging(self, samples: int, averaging_time: float, channel: int = 1) -> bool:
        """Start logging"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Configure logging
            config_cmd = self.cmd.set_detector_sensor_logging(
                detector_slot, samples, f"{averaging_time}ms"
            )
            await self._send_command(config_cmd, expect_response=False)
            
            # Start logging
            start_cmd = self.cmd.set_detector_data_acquisition(detector_slot, "LOGG", "STAR")
            await self._send_command(start_cmd, expect_response=False)
            
            self._logging_active[channel] = True
            return True
            
        except Exception as e:
            logger.error(f"Start logging failed: {e}")
            return False
    
    async def stop_logging(self, channel: int = 1) -> bool:
        """Stop logging"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.set_detector_data_acquisition(detector_slot, "LOGG", "STOP")
            await self._send_command(cmd, expect_response=False)
            
            self._logging_active[channel] = False
            return True
            
        except Exception as e:
            logger.error(f"Stop logging failed: {e}")
            return False
    
    async def get_logged_data(self, channel: int = 1) -> List[PowerReading]:
        """Get logged data - clean IEEE 488.2 binary parsing (adapted for GPIB)"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Get data using clean IEEE 488.2 binary format via GPIB
            cmd = self.cmd.read_data(detector_slot, channel)
            
            # For binary data over GPIB, we need special handling
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.instrument.query_binary_values(
                    cmd, 
                    datatype='f',  # 32-bit float
                    is_big_endian=False  # Little-endian
                )
            )
            
            # Convert to PowerReading objects
            readings = []
            current_wavelength = await self.get_wavelength()
            
            for power_value in response:
                # Filter out obvious bad values 
                if -100.0 <= power_value <= 50.0:  # Reasonable power range
                    readings.append(PowerReading(
                        value=power_value,
                        unit=PowerUnit.DBM,
                        wavelength=current_wavelength
                    ))
                else:
                    logger.warning(f"Filtered bad power reading: {power_value}")
            
            logger.info(f"Retrieved {len(readings)} power readings from channel {channel}")
            return readings
            
        except Exception as e:
            logger.error(f"Get logged data failed: {e}")
            return []

    ############## STATUS METHODS FOR LASER + DETECTOR ##############
    async def get_laser_state(self) -> LaserState:
        """Get laser state"""
        try:
            if not self._is_connected:
                return LaserState.ERROR
            
            output_state = await self.get_output_state()
            if not output_state:
                return LaserState.IDLE
                
            sweep_state = await self.get_sweep_state()
            if sweep_state == SweepState.RUNNING:
                return LaserState.SWEEPING
                
            return LaserState.READY
            
        except Exception as e:
            logger.error(f"Get laser state failed: {e}")
            return LaserState.ERROR
    
    async def get_wavelength_limits(self) -> Tuple[float, float]:
        """Get wavelength limits"""
        try:
            min_cmd = self.cmd.read_laser_wavelength(self.laser_slot, "MIN")
            max_cmd = self.cmd.read_laser_wavelength(self.laser_slot, "MAX")
            
            min_response = await self._send_command(min_cmd)
            max_response = await self._send_command(max_cmd)
            
            min_wl = float(min_response.replace("nm", "").strip())
            max_wl = float(max_response.replace("nm", "").strip())
            
            return min_wl, max_wl
            
        except Exception as e:
            logger.error(f"Get wavelength limits failed: {e}")
            return 1460.0, 1580.0  # Default from legacy code
    
    async def get_power_limits(self) -> Tuple[float, float]:
        """Get power limits"""
        try:
            min_cmd = self.cmd.read_laser_power(self.laser_slot, "MIN")
            max_cmd = self.cmd.read_laser_power(self.laser_slot, "MAX")
            
            min_response = await self._send_command(min_cmd)
            max_response = await self._send_command(max_cmd)
            
            min_power = float(min_response.replace("DBM", "").replace("dbm", "").strip())
            max_power = float(max_response.replace("DBM", "").replace("dbm", "").strip())
            
            return min_power, max_power
            
        except Exception as e:
            logger.error(f"Get power limits failed: {e}")
            return -40.0, 10.0  # Default range

# Register driver with new identifier
register_driver("347_NIR", Agilent8163Controller)