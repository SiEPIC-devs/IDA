import ctypes
import numpy as np
import pyvisa
import time
import struct
import logging
from typing import Optional, Tuple, List
from ctypes import c_int32, byref, create_string_buffer

from NIR.hal.nir_hal import LaserHAL 
from NIR.sweep import HP816xLambdaSweep

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

"""
Nir implementation for optical sweeps. Functionality for laser, detector configuration and methods
as well as taking lambda sweeps.
Cameron Basara, 2025
"""

######################################################################
# Helpers / Connection
######################################################################

class NIR8164(LaserHAL):
    def __init__(self, gpib_addr: int = 20, laser_slot: int = 1, 
                 detector_slots: List[int] = [1], safety_password: str = "1234", 
                 timeout_ms: int = 30000):

        self.gpib_addr = gpib_addr
        self.timeout_ms = timeout_ms
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.inst: Optional[pyvisa.Resource] = None
        self._is_connected = False
        self.addr = f'GPIB0::{gpib_addr}::INSTR'

        # DLL connection for lambda sweeps
        self.lib = None
        self.dll_session = None
        self._dll_connected = False
        
        # Sweep module
        self.sweep = HP816xLambdaSweep()
        
    def connect(self) -> bool:
        try:
            # Setup SCPI VISA connection
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(
                self.addr,
                timeout=self.timeout_ms
            )
            
            # Test SCPI connection
            idn = self.inst.query('*IDN?').strip()
            if not idn:
                raise RuntimeError("No response to *IDN?")
                
            # Setup DLL connection for lambda sweeps
            self._setup_dll_connection()
            
            self._is_connected = True
            self.configure_units()
            return True
        except Exception as e:
            raise ConnectionError(f"{e}")
    
    def _setup_dll_connection(self) -> None:
        """Setup HP816x DLL connection for lambda sweeps"""
        try:
            self.lib = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")
            self._setup_dll_prototypes()
            
            session = c_int32()
            result = self.lib.hp816x_init(
                self.addr.encode(), 1, 0, byref(session)
            )
            
            if result == 0:
                self.dll_session = session.value
                self.lib.hp816x_errorQueryDetect(self.dll_session, 1)
                self.lib.hp816x_registerMainframe(self.dll_session)
                self._dll_connected = True
                
                # Connect sweep module to DLL
                self.sweep.set_session(self.lib, self.dll_session)
            else:
                logging.warning(f"DLL connection failed: {result}")
                self._dll_connected = False
        except Exception as e:
            logging.warning(f"DLL setup failed: {e}")
            self._dll_connected = False
    
    def _setup_dll_prototypes(self):
        """Setup DLL function prototypes"""
        from ctypes import c_double, c_uint32, c_char_p, POINTER
        
        # hp816x_init
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32
        
        # Error functions
        self.lib.hp816x_error_message.argtypes = [c_int32, c_int32, POINTER(ctypes.c_char)]
        self.lib.hp816x_error_message.restype = c_int32
        self.lib.hp816x_error_query.argtypes = [c_int32, POINTER(c_int32), POINTER(ctypes.c_char)]
        self.lib.hp816x_error_query.restype = c_int32
        self.lib.hp816x_errorQueryDetect.argtypes = [c_int32, c_int32]
        self.lib.hp816x_errorQueryDetect.restype = c_int32
        self.lib.hp816x_registerMainframe.argtypes = [c_int32]
        self.lib.hp816x_registerMainframe.restype = c_int32
        
        # Lambda scan functions
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32, c_int32, c_double, c_int32, c_int32, c_int32,
            c_double, c_double, c_double, POINTER(c_uint32), POINTER(c_uint32)
        ]
        self.lib.hp816x_prepareMfLambdaScan.restype = c_int32
        
        self.lib.hp816x_executeMfLambdaScan.argtypes = [c_int32, POINTER(c_double)]
        self.lib.hp816x_executeMfLambdaScan.restype = c_int32
        
        self.lib.hp816x_getLambdaScanResult.argtypes = [
            c_int32, c_int32, c_int32, c_double, POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_getLambdaScanResult.restype = c_int32
        
        self.lib.hp816x_close.argtypes = [c_int32]
        self.lib.hp816x_close.restype = c_int32

    def disconnect(self) -> bool:
        try:
            self.cleanup_scan()
        except Exception:
            return False
            
        # Disconnect SCPI
        try:
            if self.inst:
                self.inst.close()
        finally:
            self.inst = None
            
        if self.rm:
            try:
                self.rm.close()
            finally:
                self.rm = None
                
        # Disconnect DLL
        if self.dll_session and self.lib and self._dll_connected:
            try:
                self.lib.hp816x_close(self.dll_session)
            except Exception:
                pass
            finally:
                self.dll_session = None
                self._dll_connected = False
                
        return True

    def write(self, scpi: str) -> None:
        self.inst.write(scpi)

    def query(self, scpi: str, sleep_s: float = 0.02, retries: int = 1) -> str:
        for attempt in range(retries + 1):
            resp = self.inst.query(scpi).strip()
            if resp or attempt == retries:
                return resp
            time.sleep(0.03)

    ######################################################################
    # Laser functions
    ######################################################################

    def configure_units(self) -> None:
        """Configured nir to dBm"""
        self.write("SOUR0:POW:UNIT 0")
        self.write("SENS1:CHAN1:POW:UNIT 0")
        self.write("SENS1:CHAN2:POW:UNIT 0")
        _ = self.query("SOUR0:POW:UNIT?")
        _ = self.query("SENS1:CHAN1:POW:UNIT?")
        _ = self.query("SENS1:CHAN2:POW:UNIT?")

    def set_wavelength(self, nm: float) -> None:
        """Set wl in nm"""
        self.write(f"SOUR0:WAV {nm*1e-9}")

    def get_wavelength(self) -> float:
        """Get wl in nm"""
        v = self.query("SOUR0:WAV?")
        x = float(v)
        return x*1e9 if x < 1e-3 else x

    def set_power(self, dbm: float) -> None:
        """Set power in dBm"""
        self.write("SOUR0:POW:UNIT 0")
        self.write(f"SOUR0:POW {dbm}")

    def get_power(self) -> float:
        """Get power in dBm"""
        self.write("SOUR0:POW:UNIT 0")
        v = self.query("SOUR0:POW?")
        return float(v)

    def enable_output(self, on: bool) -> None:
        """Turn laser on and off"""
        self.write(f"SOUR0:POW:STAT {'ON' if on else 'OFF'}")

    def get_output_state(self):
        state = self.query("SOUR0:POW:STAT?")
        state = "1" in state
        return state

    ######################################################################
    # Detector functions
    ######################################################################

    def set_detector_units(self, units: int = 0) -> None:
        """
        Set Detector units
            unit[int]: 0 dBm, 1 W
        """
        self.write(f"SENS1:CHAN1:POW:UNIT {units}")
        self.write(f"SENS1:CHAN2:POW:UNIT {units}")

    def get_detector_units(self) -> None:
        """Set Detector units"""
        _ = self.query("SENS1:CHAN1:POW:UNIT?")
        _ = self.query("SENS1:CHAN2:POW:UNIT?")

    def read_power(self) -> Tuple[float, float]:
        """
        Read power from each chan with unit configured
        """
        p1 = self.query("FETC1:CHAN1:POW?")
        p2 = self.query("FETC1:CHAN2:POW?")
        return float(p1), float(p2)

    def enable_autorange(self, enable: bool = True, channel: int = 1) -> bool:
        """Enable/disable autorange """
        try:
            self.write(f"SENSe{channel}:POWer:RANGe:AUTO {1 if enable else 0}")
            return True
        except Exception as e:
            return False

    def set_power_range(self, range_dbm: float, channel: int = 1) -> bool:
        """Set power range for both slots"""
        try:
            # Disable autorange first 
            self.write(f"SENSe{channel}:POWer:RANGe:AUTO 0")
            # Set range
            self.write("SENS1:CHAN1:POW:RANG " + str(range_dbm))
            time.sleep(0.05)
            self.write("SENS1:CHAN2:POW:RANG " + str(range_dbm))
            return True
        except Exception as e:
            return False

    def get_power_range(self) -> bool:
        """Get power range for both slots"""
        try:
            # Set range
            _ = self.query("SENS1:CHAN1:POW:RANG?")
            _ = self.query("SENS1:CHAN2:POW:RANG?") # don't know if you need to query the slave
            return True
        except Exception as e:
            return False

    ######################################################################
    # Sweep functions
    ######################################################################

    def set_sweep_range_nm(self, start_nm: float, stop_nm: float) -> None:
        self.write(f"SOUR0:WAV:SWE:STAR {start_nm*1e-9}")
        self.write(f"SOUR0:WAV:SWE:STOP {stop_nm*1e-9}")

    def set_sweep_step_nm(self, step_nm: float) -> None:
        self.write(f"SOUR0:WAV:SWE:STEP {step_nm}NM")

    def arm_sweep_cont_oneway(self) -> None:
        self.write("SOUR0:WAV:SWE:MODE CONT")
        self.write("SOUR0:WAV:SWE:REP ONEW")
        self.write("SOUR0:WAV:SWE:CYCL 1")

    def start_sweep(self) -> None:
        self.write("SOUR0:WAV:SWE:STAT START")

    def stop_sweep(self) -> None:
        self.write("SOUR0:WAV:SWE:STAT STOP")

    def get_sweep_state(self) -> str:
        return self.query("SOUR0:WAV:SWE:STAT?")

    ######################################################################
    # Lambda scan functions
    ######################################################################
    
    def optical_sweep(
            self, start_nm: float, stop_nm: float, step_pm: float,
            laser_power_dbm: float, num_scans: int = 0, channel: int = 1
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Args:
            start_nm (float): Start wavelength in nm (1660 max)
            stop_nm (float): Stop wavelength in nm (1660 max)
            step_pm (float): Step size in picometers (0.1 pm min)
            laser_power_dbm (float): Laser output power in dBm
            num_scans (int): Number of scans (0 for single)
            channel (int): Detector channel to read (1 or 2)
            
        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: (wavelengths, ch1_powers, ch2_powers)
        """
        if not self._dll_connected:
            raise RuntimeError("DLL connection not available for lambda sweeps")
            
        # Execute sweep using sweep module
        result = self.sweep.lambda_scan(
            start_nm=start_nm,
            stop_nm=stop_nm, 
            step_pm=step_pm,
            power_dbm=laser_power_dbm,
            num_scans=num_scans,
            channel=channel
        )
        
        # Convert to expected format (wavelengths, ch1, ch2)
        wavelengths = result['wavelengths_nm']
        if channel == 1:
            ch1_powers = result['powers_dbm']
            ch2_powers = np.full_like(ch1_powers, np.nan)  # Placeholder
        else:
            ch1_powers = np.full_like(result['powers_dbm'], np.nan)  # Placeholder  
            ch2_powers = result['powers_dbm']
            
        return wavelengths, ch1_powers, ch2_powers

    def cleanup_scan(self) -> None:
        try:
            self.write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
        except Exception:
            pass
        try:
            self.write("SOUR0:WAV:SWE:STAT STOP")
        except Exception:
            pass
        try:
            self.write("SOUR0:POW:STAT OFF")
        except Exception:
            pass
        try:
            self.drain()
        except Exception:
            pass

# Register driver
from NIR.hal.nir_factory import register_driver
register_driver("347_NIR", NIR8164)