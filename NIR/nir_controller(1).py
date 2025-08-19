import pyvisa
import time
import math
import struct
import asyncio
from typing import Optional, Tuple, List, Dict, Any

from NIR.hal.nir_hal import LaserHAL, LaserState, SweepState, PowerUnit, WavelengthRange, PowerReading, LaserEventType
from NIR.hal.nir_factory import register_driver
from NIR.drivers.agilent_8163a import agilent_8163a_mainframe

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

"""
Agilent 8163A Hardware Abstraction Layer Implementation 

Cameron Basara, 2025
"""

class Agilent8164Controller(LaserHAL):
    def __init__(self, 
                com_port: int = 5,
                laser_slot: int = 0,
                detector_slots: List[int] = None,
                gpib_addr: int = 20,
                safety_password: str = "1234",
                instrument_id: str = None,
                timeout: int = 5000):
        """
        Initialize Agilent 8164B with GPIB communication via Prologix GPIB-USB
        
        Args:
            com_port: COM port number for Prologix GPIB-USB converter
            laser_slot: Slot number containing tunable laser
            detector_slots: List of slots containing power detectors
            safety_password: 4-digit laser safety pwk
            instrument_id: Optional instrument identifier, absolute path
            timeout: Communication timeout in ms
        """
        super().__init__(instrument_id or f"ASRL{com_port}::INSTR")
        
        self.com_port = com_port
        self.gpib_addr = gpib_addr
        self.laser_slot = laser_slot
        self.detector_slots = detector_slots or ["1"] # 347 specific
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
    def connect(self) -> bool:
        """Connect to agilent mainframe via GPIB using Prologix GPIB-USB converter"""
        try:
            # Initialize PyVISA resource manager
            self.resource_manager = pyvisa.ResourceManager()
            
            # Use COM port for Prologix GPIB-USB converter
            visa_address = f"ASRL{self.com_port}::INSTR"
            
            # Open instrument connection with serial parameters for Prologix
            self.instrument = self.resource_manager.open_resource(
                visa_address,
                baud_rate=115200,
                timeout=self.timeout,
                write_termination='\n',
                read_termination=None
            )
            
            # Clear buffer
            self.instrument.clear()
            time.sleep(0.2)

            # Configure Prologix 
            self.instrument.write('++mode 1') # Controller mode
            time.sleep(0.1)
            self.instrument.write(f'++addr {self.gpib_addr}') # Set gpib addr
            time.sleep(0.1)
            self.instrument.write('++auto 0') # Manual reads; use ++read eoi
            time.sleep(0.1)
            self.instrument.write('++eos 2') # Append LF termination
            time.sleep(0.1)
            self.instrument.write('++eoi 1') # Assert EOI at end of device writes
            time.sleep(0.1)
            resp = self._send_command(self.cmd.identity()).strip() # *IDN?

            # Max binary block size that can be read from 1 block
            self.instrument.chunk_size = 204050 * 2 + 8 # Represents 100k data points + header, EOF

            if "8164" in resp or "8163" in resp:
                self._is_connected = True
                logger.info(f"Connected to {resp.strip()}")

                # Clear status after successful connection
                self._send_command(self.cmd.clear_status(), expect_response=False)

                # Check and unlock laser if needed
                self._send_command(self.cmd.lock_laser("0", self.safety_password), expect_response=False)
                if not self._verify_slots():
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

    def disconnect(self) -> bool:
        """Disconnect GPIB connection"""
        try:
            if self._is_connected and self.instrument:
                # Safe shutdown sequence
                self.enable_output(False)
                self.stop_sweep()
                
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
    def _send_command(self, command: str, expect_response: bool = True) -> str:
        """Send SCPI cmds via GPIB"""
        if not self.instrument:
            logger.error("[SEND_CMD] No GPIB connection available")
            raise RuntimeError("Not connected to instrument")
        
        try:
            if expect_response:
                self.instrument.write(command)
                time.sleep(0.05)  # small delay
                self.instrument.write('++read eoi')  # Prologix read trigger
                return self.instrument.read().strip()
            else:
                self.instrument.write(command)
                return ""
                
        except Exception as e:
            logger.error(f"GPIB command failed: {command}, Error: {e}")
            raise
    
    def _verify_slots(self) -> bool:
        """Verify that expected modules are installed"""
        try:
            options_resp = self._send_command(self.cmd.options())
            logger.info(f"Installed modules: {options_resp}")
            return True
            
        except Exception as e:
            logger.error(f"Slot verification failed: {e}")
            return False
    
    ############## LASER SOURCE METHODS ##############
    def set_wavelength(self, wavelength: float) -> bool:
        """Set laser wavelength, in nm"""
        try:
            self._send_command(self.cmd.clear_status(), expect_response=False)
            
            cmd = self.cmd.set_laser_current_wavelength(self.laser_slot, wavelength)
            self._send_command(cmd, expect_response=False)
            
            self._current_wavelength = wavelength
            self._emit_event(LaserEventType.WAVELENGTH_CHANGED, {"wavelength": wavelength})
            return True
            
        except Exception as e:
            logger.error(f"Set wavelength failed: {e}")
            return False
    
    def get_wavelength(self) -> float:
        """Get current wavelength with proper unit handling"""
        try:
            cmd = self.cmd.read_laser_wavelength(self.laser_slot)
            resp = self._send_command(cmd).strip()
            
            # Check for unit indicators in response
            if "nm" in resp.lower():
                # Response includes nm unit
                wavelength_str = resp.replace("nm", "").replace("NM", "").strip()
                wavelength = float(wavelength_str)
            elif "m" in resp.lower() and "nm" not in resp.lower():
                # Response in meters, convert to nm
                wavelength_str = resp.replace("m", "").replace("M", "").strip()
                wavelength = float(wavelength_str) * 1e9
            else:
                # No unit, detect by magnitude
                wavelength_raw = float(resp)
                if wavelength_raw < 1e-3:  # Less than 0.001, probably meters
                    wavelength = wavelength_raw * 1e9
                else:
                    wavelength = wavelength_raw
            
            self._current_wavelength = wavelength
            return wavelength
            
        except Exception as e:
            logger.error(f"Get wavelength failed: {e}")
            return self._current_wavelength
    
    def set_power(self, power: float, unit: PowerUnit = PowerUnit.DBM) -> bool:
        """Set laser power"""
        try:
            self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Set power unit, then power level 
            unit_value = "0" if unit == PowerUnit.DBM else "1"
            unit_cmd = self.cmd.laser_power_units(self.laser_slot, unit_value)
            self._send_command(unit_cmd, expect_response=False)
            
            power_str = f"{power}dbm" if unit == PowerUnit.DBM else f"{power}W"
            power_cmd = self.cmd.set_laser_current_power(self.laser_slot, power_str)
            self._send_command(power_cmd, expect_response=False)
            
            self._current_power = power
            self._emit_event(LaserEventType.POWER_CHANGED, {"power": power, "unit": unit.value})
            return True
            
        except Exception as e:
            logger.error(f"Set power failed: {e}")
            return False
        
    def get_power(self) -> Tuple[float, PowerUnit]:
        """Get current power with proper unit handling"""
        try:
            cmd = self.cmd.read_laser_power(self.laser_slot)
            response = self._send_command(cmd).strip()
            power = float(response)
            unit = PowerUnit.DBM
            self._current_power = power
            return power, unit
            
        except Exception as e:
            logger.error(f"Get power failed: {e}")
            return self._current_power, PowerUnit.DBM
    
    def enable_output(self, enable: bool = True) -> bool:
        """Enable/disable laser output"""
        try:
            self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Legacy uses both laser_current and set_laser_power_state
            current_cmd = self.cmd.laser_current(self.laser_slot, "1" if enable else "0")
            self._send_command(current_cmd, expect_response=False)
            
            power_cmd = self.cmd.set_laser_power_state(self.laser_slot, "1" if enable else "0")
            self._send_command(power_cmd, expect_response=False)
            
            self._output_enabled = enable
            event_type = LaserEventType.OUTPUT_ENABLED if enable else LaserEventType.OUTPUT_DISABLED
            self._emit_event(event_type, {"enabled": enable})
            return True
            
        except Exception as e:
            logger.error(f"Enable output failed: {e}")
            return False
    
    def get_output_state(self) -> bool:
        """Get output state"""
        try:
            cmd = self.cmd.read_laser_current(self.laser_slot)
            response = self._send_command(cmd)
            
            self._output_enabled = "1" in response
            return self._output_enabled
            
        except Exception as e:
            logger.error(f"Get output state failed: {e}")
            return self._output_enabled

    ############## SWEEP UTILITY METHODS ##############
    def set_sweep_range(self, start_nm: float, stop_nm: float) -> bool:
        """Set sweep range"""
        try:
            # Set start wavelength
            start_cmd = self.cmd.set_sweep_wavelength(self.laser_slot, "STAR", f"{start_nm}nm")
            self._send_command(start_cmd, expect_response=False)
            
            # Set stop wavelength  
            stop_cmd = self.cmd.set_sweep_wavelength(self.laser_slot, "STOP", f"{stop_nm}nm")
            self._send_command(stop_cmd, expect_response=False)
            
            self._sweep_range = WavelengthRange(start_nm, stop_nm)
            return True
            
        except Exception as e:
            logger.error(f"Set sweep range failed: {e}")
            return False
    
    def get_sweep_range(self) -> WavelengthRange:
        """Get sweep range"""
        return self._sweep_range
    
    def set_sweep_speed(self, speed: float) -> bool:
        """Set sweep speed"""
        try:
            cmd = self.cmd.set_continuous_sweep_speed(self.laser_slot, f"{speed}nm/s")
            self._send_command(cmd, expect_response=False)
            
            self._sweep_speed = speed
            return True
            
        except Exception as e:
            logger.error(f"Set sweep speed failed: {e}")
            return False
    
    def get_sweep_speed(self) -> float:
        """Get sweep speed with proper unit handling"""
        try:
            cmd = self.cmd.read_continuous_sweep_speed(self.laser_slot)
            response = self._send_command(cmd).strip()
            
            # Parse based on unit indicators
            if "nm/s" in response.lower():
                speed_str = response.replace("nm/s", "").replace("NM/S", "").strip()
                speed = float(speed_str)
            elif "m/s" in response.lower():
                speed_str = response.replace("m/s", "").replace("M/S", "").strip()
                speed_ms = float(speed_str)
                speed = speed_ms * 1e9  # Convert m/s to nm/s
            else:
                # No clear unit, detect by magnitude
                speed_raw = float(response)
                if speed_raw < 1e-6:  # Very small, probably m/s
                    speed = speed_raw * 1e9
                else:
                    speed = speed_raw  # Assume nm/s
            
            self._sweep_speed = speed
            return speed
        
        except Exception as e:
            logger.error(f"Get sweep speed failed: {e}")
            return self._sweep_speed

    # Sweep control - because sweeps take time
    def set_sweep_state(self, enable: bool) -> bool:
        """Enable/disable sweep state"""
        if enable:
            return self.start_sweep()
        else:
            return self.stop_sweep()

    def start_sweep(self) -> bool:
        """Start wavelength sweep - because it takes time"""
        try:
            # Configure sweep parameters first
            self.set_sweep_range(self._sweep_range.start, self._sweep_range.stop)
            self.set_sweep_speed(self._sweep_speed)
            
            # Set sweep mode and parameters 
            self._send_command(
                self.cmd.set_laser_sweep_mode(self.laser_slot, "CONT"), 
                expect_response=False
            )
            self._send_command(
                self.cmd.set_laser_sweep_cycles(self.laser_slot, "1"), 
                expect_response=False
            )
            self._send_command(
                self.cmd.set_laser_sweep_directionality(self.laser_slot, "ONEWay"), 
                expect_response=False
            )
            
            # Arm and start sweep
            self._send_command(
                self.cmd.arm_laser_sweep(self.laser_slot), 
                expect_response=False
            )
            
            # Start sweep
            cmd = self.cmd.set_laser_sweep_state(self.laser_slot, "1", "STAR")
            self._send_command(cmd, expect_response=False)
            
            self._sweep_active = True
            self._emit_event(LaserEventType.SWEEP_STARTED, {"enabled": True})
            return True
            
        except Exception as e:
            logger.error(f"Start sweep failed: {e}")
            return False

    def stop_sweep(self) -> bool:
        """Stop sweep"""
        try:
            cmd = self.cmd.set_laser_sweep_state(self.laser_slot, "1", "STOP")
            self._send_command(cmd, expect_response=False)
            
            self._sweep_active = False
            self._emit_event(LaserEventType.SWEEP_STOPPED, {"enabled": False})
            return True
            
        except Exception as e:
            logger.error(f"Stop sweep failed: {e}")
            return False
        
    def get_sweep_state(self) -> SweepState:
        """Get sweep state"""
        try:
            cmd = self.cmd.read_laser_sweep_state(self.laser_slot, "1")
            response = self._send_command(cmd)
            
            if "1" in response:
                return SweepState.RUNNING
            else:
                return SweepState.STOPPED
                
        except Exception as e:
            logger.error(f"Get sweep state failed: {e}")
            return SweepState.STOPPED if not self._sweep_active else SweepState.RUNNING

    ############## DETECTOR METHODS ##############
    def read_power(self, channel: int = 1):
        """Read power from detector"""
        # detector_slot = self._get_detector_slot(channel)
        # for now do it manually, read both slots
        master_slot = 1
        slave_slot = 2
        
        try:
            self._send_command(self.cmd.clear_status(), expect_response=False)
            
            # Small delay for averaging
            time.sleep(0.1)
            
            cmd_master = self.cmd.read_power(master_slot, channel) 
            cmd_slave = self.cmd.read_power(slave_slot, channel)
            response_master = self._send_command(cmd_master)
            time.sleep(0.1)
            response_slave = self._send_command(cmd_slave)
            
            # Parse power value
            power_value_master = float(response_master.strip())
            power_value_slave = float(response_slave.strip())
            
            wavelength = self.get_wavelength()
            
            return PowerReading(
                value=power_value_master,
                unit=PowerUnit.DBM,
                wavelength=wavelength
            ), PowerReading(
                value=power_value_slave,
                unit=PowerUnit.DBM,
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
    
    def set_power_unit(self, unit: PowerUnit, channel: int = 1) -> bool:
        """Set power unit"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            unit_str = "0" if unit == PowerUnit.DBM else "1"
            cmd = self.cmd.power_sensor_unit(detector_slot, channel, unit_str)
            self._send_command(cmd, expect_response=False)
            return True
            
        except Exception as e:
            logger.error(f"Set power unit failed: {e}")
            return False

    def get_power_unit(self, channel: int = 1) -> PowerUnit:
        """Get power unit"""
        # For now return default 
        return PowerUnit.DBM
    
    def get_power_range(self, channel: int = 1) -> float:
        """Get power range with proper unit handling"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.read_power_sensor_range(detector_slot, channel)
            response = self._send_command(cmd).strip()
            
            # Parse power range based on units
            if "dbm" in response.lower():
                range_value = float(response.replace("DBM", "").replace("dbm", "").strip())
            elif "w" in response.lower() and "mw" not in response.lower():
                range_watts = float(response.replace("W", "").replace("w", "").strip())
                range_value = 10 * math.log10(range_watts) + 30 if range_watts > 0 else -100.0
            elif "mw" in response.lower():
                range_mw = float(response.replace("MW", "").replace("mw", "").replace("mW", "").strip())
                range_value = 10 * math.log10(range_mw) if range_mw > 0 else -100.0
            else:
                range_raw = float(response)
                if range_raw < 1e-3:
                    range_value = 10 * math.log10(range_raw) + 30 if range_raw > 0 else -100.0
                else:
                    range_value = range_raw
            
            return range_value
        
        except Exception as e:
            logger.error(f"Get power range failed: {e}")
            return 0.0
    
    def enable_autorange(self, enable: bool = True, channel: int = 1) -> bool:
        """Enable/disable autorange """
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.power_sensor_autorange(detector_slot, "1" if enable else "0")
            self._send_command(cmd, expect_response=False)
            return True
            
        except Exception as e:
            logger.error(f"Enable autorange failed: {e}")
            return False

    def set_power_range(self, range_dbm: float, channel: int = 1) -> bool:
        """Set power range """
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Disable autorange first 
            auto_cmd = self.cmd.power_sensor_autorange(detector_slot, "0")
            self._send_command(auto_cmd, expect_response=False)
            
            # Set range
            range_cmd = self.cmd.set_power_sensor_range(detector_slot, channel, f"{range_dbm}dbm")
            self._send_command(range_cmd, expect_response=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Set power range failed: {e}")
            return False

    ############## DATA LOGGING ##############
    def start_logging(self, samples: int, averaging_time: float, channel: int = 1) -> bool:
        """Start logging"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Configure logging
            config_cmd = self.cmd.set_detector_sensor_logging(
                detector_slot, samples, f"{averaging_time}ms"
            )
            self._send_command(config_cmd, expect_response=False)
            
            # Start logging
            start_cmd = self.cmd.set_detector_data_acquisition(detector_slot, "LOGG", "STAR")
            self._send_command(start_cmd, expect_response=False)
            
            self._logging_active[channel] = True
            return True
            
        except Exception as e:
            logger.error(f"Start logging failed: {e}")
            return False
    
    def stop_logging(self, channel: int = 1) -> bool:
        """Stop logging"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            cmd = self.cmd.set_detector_data_acquisition(detector_slot, "LOGG", "STOP")
            self._send_command(cmd, expect_response=False)
            
            self._logging_active[channel] = False
            return True
            
        except Exception as e:
            logger.error(f"Stop logging failed: {e}")
            return False
        def _read_binblock_f32(self, cmd: str):
            """Send a command that returns an IEEE-488.2 definite-length binary block of float32 (little-endian)."""
            self.instrument.write(cmd)
            time.sleep(0.1)
            self.instrument.write('++read eoi')
            # Read header #<N><len>
            h = self.instrument.read_bytes(2)
            if h[:1] != b'#':
                raise ValueError('Bad block header')
            nd = int(h[1:2].decode())
            nbytes = int(self.instrument.read_bytes(nd).decode())
            # Read payload
            buf = b''
            remaining = nbytes
            while remaining > 0:
                chunk = self.instrument.read_bytes(min(4096, remaining))
                if not chunk:
                    break
                buf += chunk
                remaining -= len(chunk)
            # consume trailing newline if present
            try:
                self.instrument.read()
            except Exception:
                pass
            import struct
            if len(buf) % 4 != 0:
                raise ValueError('Payload not multiple of 4 bytes')
            return list(struct.unpack('<' + 'f'*(len(buf)//4), buf))

    
    async def get_logged_data(self, channel: int = 1) -> List[PowerReading]:
        """Get logged data"""
        detector_slot = self._get_detector_slot(channel)
        
        try:
            # Get data using binary format via GPIB
            cmd = self.cmd.read_data(detector_slot, channel)
            
            # For binary data over GPIB, we need special handling
            loop = asyncio.get_event_loop()
            # Use manual binblock reader through Prologix
            # Avoid query_binary_values which assumes GPIB backend

            response = await loop.run_in_executor(
                None,
                lambda: self._read_binblock_f32(cmd)
            )
            
            # Convert to PowerReading objects
            readings = []
            current_wavelength = self.get_wavelength()
            
            for power_value in response:
                # Filter out obvious bad values 
                if -100.0 <= power_value <= 0.0:  
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

    ############## STATUS METHODS ##############
    def get_laser_state(self) -> LaserState:
        """Get laser state"""
        try:
            if not self._is_connected:
                return LaserState.ERROR
            
            output_state = self.get_output_state()
            if not output_state:
                return LaserState.IDLE
                
            sweep_state = self.get_sweep_state()
            if sweep_state == SweepState.RUNNING:
                return LaserState.SWEEPING
                
            return LaserState.READY
            
        except Exception as e:
            logger.error(f"Get laser state failed: {e}")
            return LaserState.ERROR
    
    def get_wavelength_limits(self) -> Tuple[float, float]:
        """Get wavelength limits with proper unit handling"""
        try:
            min_cmd = self.cmd.read_laser_wavelength(self.laser_slot, "MIN")
            max_cmd = self.cmd.read_laser_wavelength(self.laser_slot, "MAX")
            
            min_response = self._send_command(min_cmd).strip()
            max_response = self._send_command(max_cmd).strip()
            
            # Handle min wavelength
            if "nm" in min_response.lower():
                min_wl = float(min_response.replace("nm", "").replace("NM", "").strip())
            elif "m" in min_response.lower():
                min_wl_m = float(min_response.replace("m", "").replace("M", "").strip())
                min_wl = min_wl_m * 1e9  # Convert m to nm
            else:
                min_wl_raw = float(min_response)
                min_wl = min_wl_raw * 1e9 if min_wl_raw < 1e-3 else min_wl_raw
            
            # Handle max wavelength
            if "nm" in max_response.lower():
                max_wl = float(max_response.replace("nm", "").replace("NM", "").strip())
            elif "m" in max_response.lower():
                max_wl_m = float(max_response.replace("m", "").replace("M", "").strip())
                max_wl = max_wl_m * 1e9  # Convert m to nm
            else:
                max_wl_raw = float(max_response)
                max_wl = max_wl_raw * 1e9 if max_wl_raw < 1e-3 else max_wl_raw
            
            return min_wl, max_wl
            
        except Exception as e:
            logger.error(f"Get wavelength limits failed: {e}")
            return 1460.0, 1580.0 # defailt from leg code
    
    def get_power_limits(self) -> Tuple[float, float]:
        """Get power limits with proper unit handling"""
        try:
            min_cmd = self.cmd.read_laser_power(self.laser_slot, "MIN")
            max_cmd = self.cmd.read_laser_power(self.laser_slot, "MAX")
            
            min_response = self._send_command(min_cmd).strip()
            max_response = self._send_command(max_cmd).strip()
            
            # Handle min power
            if "dbm" in min_response.lower():
                min_power = float(min_response.replace("DBM", "").replace("dbm", "").strip())
            elif "w" in min_response.lower() and "mw" not in min_response.lower():
                min_watts = float(min_response.replace("W", "").replace("w", "").strip())
                min_power = 10 * math.log10(min_watts) + 30 if min_watts > 0 else -100.0
            elif "mw" in min_response.lower():
                min_mw = float(min_response.replace("MW", "").replace("mw", "").replace("mW", "").strip())
                min_power = 10 * math.log10(min_mw) if min_mw > 0 else -100.0
            else:
                min_raw = float(min_response)
                if min_raw < 1e-3:
                    min_power = 10 * math.log10(min_raw) + 30 if min_raw > 0 else -100.0
                else:
                    min_power = min_raw
            
            # Handle max power
            if "dbm" in max_response.lower():
                max_power = float(max_response.replace("DBM", "").replace("dbm", "").strip())
            elif "w" in max_response.lower() and "mw" not in max_response.lower():
                max_watts = float(max_response.replace("W", "").replace("w", "").strip())
                max_power = 10 * math.log10(max_watts) + 30 if max_watts > 0 else -100.0
            elif "mw" in max_response.lower():
                max_mw = float(max_response.replace("MW", "").replace("mw", "").replace("mW", "").strip())
                max_power = 10 * math.log10(max_mw) if max_mw > 0 else -100.0
            else:
                max_raw = float(max_response)
                if max_raw < 1e-3:
                    max_power = 10 * math.log10(max_raw) + 30 if max_raw > 0 else -100.0
                else:
                    max_power = max_raw
            
            return min_power, max_power
            
        except Exception as e:
            logger.error(f"Get power limits failed: {e}")
            return -40.0, 10.0

# Register driver
register_driver("347_NIR", Agilent8164Controller)

def main_idn():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--com", type=int, required=True, help="COM port number (e.g., 7)")
    p.add_argument("--addr", type=int, default=20, help="GPIB address")
    args = p.parse_args()
    c = Agilent8164Controller(com_port=args.com, gpib_addr=args.addr)
    if not c.connect():
        print("Connect failed")
        return 2
    try:
        print(c._send_command("*IDN?"))
    finally:
        c.disconnect()
    return 0
