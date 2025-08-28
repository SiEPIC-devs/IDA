import time
import struct
import numpy as np
import pyvisa
from typing import Optional, Tuple, List

from NIR.hal.nir_hal import LaserHAL 

"""
Nir implementation for optical sweeps. Functionality for laser, detector configuration and methods
as well as taking lambda sweeps.
Cameron Basara, 2025
"""

######################################################################
# Helpers / Connection
######################################################################

class NIR8164(LaserHAL):
    def __init__(self, com_port: int = 3, gpib_addr: int = 20,
                 laser_slot: int = 1, detector_slots: List[int] = [1,2], 
                 safety_password: str ="1234", timeout_ms: int = 30000):

        self.com_port = com_port
        self.detector_slots = detector_slots
        self.timeout_ms = timeout_ms
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.inst: Optional[pyvisa.Resource] = None
        self._is_connected = False
        self.addr = f'GPIB0::{gpib_addr}::INSTR'
        
        # lambda-scan state
        self.start_wavelength = None
        self.stop_wavelength = None
        self.step_size = None
        self.num_points = None
        self.laser_power = None

    def connect(self) -> bool:
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(
                self.addr,
                timeout=self.timeout_ms,
            )
            try:
                self.inst.clear()
            except Exception:
                pass

            idn = self.query('*IDN?')
            if not idn:
                return False

            self._is_connected = True
            self.configure_units()
            return True
        except Exception as e:
            raise ConnectionError(f"{e}")

    def disconnect(self) -> bool:
        try:
            self.cleanup_scan()
        except Exception:
            return False
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

    def configure_units(self) -> bool:
        """Configured nir to dBm""" 
        try:
            self.write("SOUR0:POW:UNIT 0")
            self.write("SENS1:CHAN1:POW:UNIT 0")
            self.write("SENS1:CHAN2:POW:UNIT 0")
            _ = self.query("SOUR0:POW:UNIT?")
            _ = self.query("SENS1:CHAN1:POW:UNIT?")
            _ = self.query("SENS1:CHAN2:POW:UNIT?")
            return True
        except Exception as e:
            return False
    def set_wavelength(self, nm: float) -> bool:
        """Set wl in nm"""
        try:
            self.write(f"SOUR0:WAV {nm*1e-9}")
            return True
        except Exception as e:
            return False
    def get_wavelength(self) -> Optional[float]:
        """Get wl in nm"""
        try:
            v = self.query("SOUR0:WAV?")
            x = float(v)
            return x*1e9 if x < 1e-3 else x
        except:
            return None
        
    def set_power(self, dbm: float) -> bool:
        """Set power in dBm"""
        try:
            self.write("SOUR0:POW:UNIT 0")
            self.write(f"SOUR0:POW {dbm}")
            return True
        except:
            return False
    def get_power(self) -> Optional[float]:
        """Get power in dBm"""
        try:
            self.write("SOUR0:POW:UNIT 0")
            v = self.query("SOUR0:POW?")
            return float(v)
        except:
            return False
        
    def enable_output(self, on: bool) -> bool:
        """Turn laser on and off"""
        try:
            self.write(f"SOUR0:POW:STAT {'ON' if on else 'OFF'}")
            return True
        except:
            return False
    def get_output_state(self) -> bool:
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
        try:
            self.write(f"SENS1:CHAN1:POW:UNIT {units}")
            self.write(f"SENS1:CHAN2:POW:UNIT {units}")
            return True
        except:
            return False
    def get_detector_units(self) -> Optional[Tuple]:
        """Set Detector units"""
        try:
            ch1 = self.query("SENS1:CHAN1:POW:UNIT?")
            ch2 = self.query("SENS1:CHAN2:POW:UNIT?")
            return ch1, ch2
        except:
            return False
    def read_power(self) -> Optional[Tuple[float, float]]:
        """
        Read power from each chan with unit configured
        """
        try:
            p1 = self.query("FETC1:CHAN1:POW?")
            p2 = self.query("FETC1:CHAN2:POW?")
            return float(p1), float(p2)
        except:
            return False
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

    def stop_sweep(self) -> bool:
        try:
            self.write("SOUR0:WAV:SWE:STAT STOP")
            return True
        except:
            return False
        
    def get_sweep_state(self) -> str:
        return self.query("SOUR0:WAV:SWE:STAT?")

    ######################################################################
    # Lambda scan functions
    ######################################################################
    def optical_sweep(
        self, start_nm: float, stop_nm: float, step_nm: float,
        laser_power_dbm: float, num_scans: int = 0
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        from NIR.sweep import HP816xLambdaScan
        
        step_pm = float(step_nm) * 1000.0
        try:
            self._preflight_cleanup()
        except Exception:
            pass

        hp = HP816xLambdaScan()
        try:
            ok = hp.connect()
            if not ok:
                raise RuntimeError("HP816xLambdaScan.connect() failed")

            res = hp.lambda_scan(
                start_nm=float(start_nm),
                stop_nm=float(stop_nm),
                step_pm=step_pm,
                power_dbm=float(laser_power_dbm),
                num_scans=0,
                channels=self.detector_slots
            )
        finally:
            try:
                hp.disconnect()
            except Exception:
                pass

        wl = np.asarray(res.get('wavelengths_nm', []), dtype=np.float64)
        chs = res.get('channels_dbm', [])
        ch1 = np.asarray(chs[0], dtype=np.float64) if len(chs) >= 1 else np.full_like(wl, np.nan)
        ch2 = np.asarray(chs[1], dtype=np.float64) if len(chs) >= 2 else np.full_like(wl, np.nan)

        return wl, ch1, ch2
   
    def _preflight_cleanup(self) -> None:
        try: 
            self.write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
        except: 
            pass
        try: 
            self.write("SOUR0:WAV:SWE:STAT STOP")
        except: 
            pass
        try: 
            self.write("*CLS")
        except: 
            pass

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
    def get_power_unit(self, channel = 1):
        pass
    def set_power_unit(self, unit, channel = 1):
        pass
    
# Register driver
from NIR.hal.nir_factory import register_driver
register_driver("347_NIR", NIR8164)