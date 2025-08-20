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
                 laser_slot: int = 1, detector_slots: List[int] = [1], # not yet implemented
                 safety_password: str ="1234", timeout_ms: int = 30000):

        self.com_port = com_port
        self.gpib_addr = gpib_addr
        self.timeout_ms = timeout_ms
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.inst: Optional[pyvisa.Resource] = None
        self._is_connected = False

        # lambda-scan state
        self.start_wavelength = None
        self.stop_wavelength = None
        self.step_size = None
        self.num_points = None
        self.laser_power = None
        self.averaging_time = None
        self.stitching = False

    def get_power_unit(self):
        # TODO: 实际逻辑
        return "dBm"

    def set_power_unit(self, unit):
        # TODO: 实际逻辑
        pass

    def get_sweep_range(self):
        return (1520, 1570)

    def set_sweep_range(self, start, stop):
        pass

    def get_sweep_speed(self):
        return 100  # nm/s

    def set_sweep_speed(self, speed):
        pass

    def set_sweep_state(self, state):
        pass

    def connect(self) -> bool:
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(
                f'ASRL{self.com_port}::INSTR',
                baud_rate=115200,
                timeout=self.timeout_ms,
                write_termination='\n',
                read_termination=None
            )
            try:
                self.inst.clear()
            except Exception:
                pass

            self.inst.write('++mode 1')
            self.inst.write('++auto 0')
            self.inst.write('++eos 2')
            self.inst.write('++eoi 1')
            self.inst.write('++ifc')
            time.sleep(0.05)
            self.inst.write(f'++addr {self.gpib_addr}')
            self.inst.write('++clr')
            time.sleep(0.05)

            idn = self.query('*IDN?')
            if not idn:
                return False

            # large binary transfers
            try:
                self.inst.chunk_size = 204050 * 2 + 8
            except Exception:
                pass

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
            self.inst.write(scpi)
            time.sleep(sleep_s)
            self.inst.write('++read eoi')
            resp = self.inst.read().strip()
            if resp or attempt == retries:
                return resp
            time.sleep(0.03)
            self.drain()

    def _query_binary_and_parse(self, command: str) -> np.ndarray:
        if not self.inst:
            raise RuntimeError("Not connected")
        self.drain()
        self.inst.write(command)
        time.sleep(0.5)
        self.inst.write('++read eoi')

        header = self.inst.read_bytes(2)
        if header[0:1] != b"#":
            raise ValueError("Invalid SCPI block header")

        num_digits = int(header[1:2].decode())
        len_field = self.inst.read_bytes(num_digits)
        data_len = int(len_field.decode())

        data_block = b""
        remaining = data_len
        while remaining > 0:
            chunk = self.inst.read_bytes(min(remaining, 4096))
            data_block += chunk
            remaining -= len(chunk)
        try:
            self.inst.read()  # trailing LF if present

        except Exception:
            pass


        data = struct.unpack("<" + "f" * (len(data_block) // 4), data_block)
        arr = np.array(data, dtype=np.float32)

        # Unit conversion
        if arr.size and arr[0] > 0:
            arr = 10 * np.log10(arr) + 30  # W -> dBm
        return arr

    def drain(self) -> None:
        old = self.inst.timeout
        try:
            self.inst.timeout = 100
            while True:
                try:
                    b = self.inst.read_raw()
                except Exception:
                    b = b''
                if not b:
                    break
        finally:
            self.inst.timeout = old

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

    def configure_and_start_lambda_sweep(
        self, start_nm: float, stop_nm: float, step_nm: float,
        laser_power_dbm: float = -10, avg_time_s: float = 0.01
        ) -> bool:
        try:
            self._preflight_cleanup()
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength  = stop_nm  * 1e-9
            self.step_size = f"{step_nm}NM"
            self.laser_power = laser_power_dbm
            self.averaging_time = avg_time_s
            self.num_points = int((stop_nm - start_nm) / step_nm) + 1
            sweep_speed = step_nm / avg_time_s  # NM/S

            # Laser config
            self.write("*CLS")
            self.write(f"SOUR0:POW {laser_power_dbm}")
            self.write("SOUR0:POW:STAT ON")
            self.write(f"SOUR0:WAV {self.start_wavelength}")

            # Sweep config
            self.write("SOUR0:WAV:SWE:MODE CONT")
            self.write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STEP {self.step_size}")
            self.write(f"SOUR0:WAV:SWE:SPEed {sweep_speed}NM/S")   
            self.write("SOUR0:WAV:SWE:REP ONEW")
            self.write("SOUR0:WAV:SWE:CYCL 1")
            self.write("SOUR0:AM:STATe OFF")

            # Lambda config
            self.write("TRIG0:OUTP STFinished")                     
            self.write("SOUR0:WAV:SWE:LLOG 1")                      

            ok = self.query("SOUR0:WAV:SWE:CHECkparams?")  # sanity check 
            if "OK" not in ok.strip().upper():
                raise RuntimeError(f"Sweep Params are inconsistent: {ok}")

            # Detector logging: select function, then set LOGG 
            self.write("SENS1:FUNC 'POWer'")                       
            self.write(f"SENS1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")      
            self.write(f"SENS1:CHAN1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")
            self.write(f"SENS1:CHAN2:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")

            self.write("SENS1:FUNC:STAT LOGG,START")
            time.sleep(0.3)  # breathe

            return True
        except Exception:
            _ = self.query("SYST:ERR?")
            return False

    def execute_lambda_scan(self, timeout_s: float = 300) -> bool:
        self.write("SOUR0:WAV:SWE:STAT START")
        t0 = time.time()
        flag = True
        while (time.time() - t0) < timeout_s:
            swe = self.query("SOUR0:WAV:SWE:STAT?").strip()
            fun = self.query("SENS1:CHAN1:FUNC:STAT?").strip()
            print(swe, fun)
            if "0" in swe:
                sweep_complete_in = True
                if sweep_complete_in and flag:
                    flag = False
                    timeout_s = 300
            if "COMPLETE" in fun:
                return True
            time.sleep(1.0)
        return False

    def retrieve_scan_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        time.sleep(0.5)
        ch1 = self._query_binary_and_parse("SENS1:CHAN1:FUNC:RES?")
        # time.sleep(0.4)
        ch2 = self._query_binary_and_parse("SENS1:CHAN2:FUNC:RES?")

        wl = np.linspace(self.start_wavelength * 1e9,
                         self.stop_wavelength * 1e9,
                         len(ch1))
        ch1 = np.where(ch1 > 0, np.nan, ch1)
        ch2 = np.where(ch2 > 0, np.nan, ch2)
        return wl, ch1, ch2

    def optical_sweep(
            self, start_nm: float, stop_nm: float, step_nm: float,
            laser_power_dbm: float, averaging_time_s: float = 0.02
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        pts = int(((float(stop_nm) - float(start_nm)) / float(step_nm)) + 1.0000001)
        self.stitching = pts > 20001
        if self.stitching:
            print("i am stitching")
            segments = int(np.ceil(pts/20001.0))
            seg_span = int(np.ceil((stop_nm - start_nm)/segments))
            bottom = int(start_nm)
            flag = False
            while bottom <= stop_nm:
                top = min(bottom + seg_span, stop_nm)
                self.configure_and_start_lambda_sweep(bottom, top, step_nm, laser_power_dbm, averaging_time_s)
                self.execute_lambda_scan()
                wls, c1, c2 = self.retrieve_scan_data()
                if not flag:
                    wl, ch1, ch2 = wls, c1, c2
                    flag = True
                else:
                    ch1 = np.concatenate([ch1, c1])
                    ch2 = np.concatenate([ch2, c2])
                    wl = np.concatenate([wl, wls])
                bottom = top + step_nm
            return wl, ch1, ch2
        else:
            aok = self.configure_and_start_lambda_sweep(start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s)
            if aok:
                pass
            else:
                print("grrr")
            bok = self.execute_lambda_scan()
            if bok:
                pass
            else:
                print("brrrr")
            return self.retrieve_scan_data()

    def prepare_llog_sweep(
            self,
            start_nm: float,
            stop_nm: float,
            step_nm: float,
            laser_power_dbm: float = -10.0,
            avg_time_s: float = 0.01,
            speed_nm_s: float = 0.05,  # sweep speed in nm/s
    ) -> bool:
        """
        Prepare a continuous sweep with Lambda Logging (LLOG) and internal triggers.
        Does NOT start logging or the sweep. Call execute_llog_sweep() after this.
        """
        try:
            self._preflight_cleanup()

            # Save state
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength = stop_nm * 1e-9
            self.step_size = f"{step_nm}NM"
            self.laser_power = laser_power_dbm
            self.averaging_time = avg_time_s
            self.num_points = int((stop_nm - start_nm) / step_nm) + 1

            # Laser basic setup
            self.write("*CLS")
            self.write("SOUR0:POW:UNIT 0")
            self.write(f"SOUR0:POW {laser_power_dbm}")
            self.write("SOUR0:POW:STAT ON")
            self.write(f"SOUR0:WAV {self.start_wavelength}")

            # Sweep config (continuous mode, one way, 1 cycle)
            self.write("SOUR0:WAV:SWE:MODE CONT")
            self.write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STEP {self.step_size}")
            # Sweep speed is specified in meters/second; convert nm/s -> m/s
            self.write(f"SOUR0:WAV:SWE:SPE {speed_nm_s * 1e-9}")
            self.write("SOUR0:WAV:SWE:REP ONEW")
            self.write("SOUR0:WAV:SWE:CYCL 1")

            # Enable lambda logging on the laser
            self.write("SOUR0:WAV:SWE:LLOG 1")  # 1=enable, 0=disable

            # Internal trigger: route Step-Finished from the laser to Node A
            # Use your laser slot index if needed; TRIG1 means slot 1 in the mainframe.
            # We stick to laser_slot to be explicit.
            self.write(f"TRIG0:OUTP STF")

            # Power meter logging function
            self.write("SENS1:FUNC 'POWer'")
            # Points + averaging time (seconds)
            self.write(f"SENS1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")

            # Do NOT start logging here; that happens in execute_llog_sweep()
            return True
        except Exception:
            _ = self.query("SYST:ERR?")
            return False

    def execute_llog_sweep(self, timeout_s: float = 300) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Execute previously prepared LLOG sweep.
        Returns (wl_nm, ch1_dbm, ch2_dbm).
        """
        import numpy as _np
        t0 = time.time()

        # Start logging first so we don't miss the first trigger
        self.write("SENS1:FUNC:STAT LOGG,START")
        # Then start the sweep
        self.write("SOUR0:WAV:SWE:STAT START")

        # Wait for completion (either the logger completes, or sweep stops)
        while (time.time() - t0) < timeout_s:
            swe = self.query("SOUR0:WAV:SWE:STAT?").strip()
            fun = self.query("SENS1:CHAN1:FUNC:STAT?").strip()
            if "COMPLETE" in fun:
                break
            if "0" in swe:  # sweep stopped
                break
            time.sleep(0.5)

        # Read power results (4-byte floats in W unless you've set dBm units; you set dBm)
        ch1 = self._query_binary_block("SENS1:CHAN1:FUNC:RES?", dtype="<f4")
        time.sleep(0.2)
        ch2 = self._query_binary_block("SENS1:CHAN2:FUNC:RES?", dtype="<f4")

        # Read actual wavelengths from the laser LLOG buffer (8-byte doubles, in meters)
        # [:SOUR0]:READout:DATA? LLOG returns the sample positions for the last sweep.
        try:
            wl_m = self._query_binary_block("SOUR0:READ:DATA? LLOG", dtype="<f8")
            wl_nm = wl_m * 1e9
        except Exception:
            # Fallback: reconstruct if LLOG buffer isn’t available for some reason
            wl_nm = _np.linspace(self.start_wavelength * 1e9, self.stop_wavelength * 1e9, len(ch1))

        # Sanity-align lengths (trim to the shortest)
        n = min(len(wl_nm), len(ch1), len(ch2))
        wl_nm = wl_nm[:n]
        ch1 = ch1[:n]
        ch2 = ch2[:n]

        # Your code keeps values in dBm already; leave as-is
        return wl_nm, ch1, ch2

    def _query_binary_block(self, command: str, dtype: str = "<f4") -> np.ndarray:
        """
        Generic IEEE 488.2 definite-length block reader.
        dtype: '<f4' for 4-byte float (logger power results), '<f8' for 8-byte double (LLOG wavelengths).
        """
        if not self.inst:
            raise RuntimeError("Not connected")
        self.drain()
        self.inst.write(command)
        time.sleep(0.5)
        self.inst.write('++read eoi')

        header = self.inst.read_bytes(2)  # b"#" + digit count
        if header[0:1] != b"#":
            raise ValueError("Invalid SCPI block header")
        num_digits = int(header[1:2].decode())
        data_len = int(self.inst.read_bytes(num_digits).decode())

        # Read the data payload
        data_block = b""
        remaining = data_len
        while remaining > 0:
            chunk = self.inst.read_bytes(min(remaining, 8192))
            data_block += chunk
            remaining -= len(chunk)

        # Consume possible trailing LF
        try:
            self.inst.read()
        except Exception:
            pass

        item_size = 8 if dtype.endswith("f8") else 4
        if len(data_block) % item_size != 0:
            raise ValueError("Binary data length not aligned with dtype")

        arr = np.frombuffer(data_block, dtype=dtype, count=len(data_block) // item_size)
        return arr.copy()  # ensure not a view into the bytes buffer

    def prepare_step_sweep(
            self,
            start_nm: float,
            stop_nm: float,
            step_nm: float,
            laser_power_dbm: float = -10.0,
            avg_time_s: float = 0.01,
    ) -> bool:
        """
        Prepare a true STEP sweep (no LLOG). The laser moves point-to-point,
        and Step-Finished triggers clock the power meter logger.
        """
        try:
            self._preflight_cleanup()

            # Save state
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength = stop_nm * 1e-9
            self.step_size = f"{step_nm}NM"
            self.laser_power = laser_power_dbm
            self.averaging_time = avg_time_s
            self.num_points = int((stop_nm - start_nm) / step_nm) + 1

            # Laser setup
            self.write("*CLS")
            self.write("SOUR0:POW:UNIT 0")
            self.write(f"SOUR0:POW {laser_power_dbm}")
            self.write("SOUR0:POW:STAT ON")
            self.write(f"SOUR0:WAV {self.start_wavelength}")

            # STEP mode config
            self.write("SOUR0:WAV:SWE:MODE STEP")
            self.write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            self.write(f"SOUR0:WAV:SWE:STEP {self.step_size}")
            self.write("SOUR0:WAV:SWE:REP ONEW")
            self.write("SOUR0:WAV:SWE:CYCL 1")
            self.write("SOUR0:WAV:SWE:LLOG 0")  # not used in STEP mode

            # Internal triggering: Step-Finished out
            self.write(f"TRIG0:OUTP STF")

            # Power meter logging params
            self.write("SENS1:FUNC 'POWer'")
            self.write(f"SENS1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")

            return True
        except Exception:
            _ = self.query("SYST:ERR?")
            return False

    def execute_step_sweep(self, timeout_s: float = 300) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Execute previously prepared STEP sweep (no LLOG).
        Returns (wl_nm, ch1_dbm, ch2_dbm).
        """
        import numpy as _np
        t0 = time.time()

        self.write("SENS1:FUNC:STAT LOGG,START")
        self.write("SOUR0:WAV:SWE:STAT START")

        while (time.time() - t0) < timeout_s:
            swe = self.query("SOUR0:WAV:SWE:STAT?").strip()
            fun = self.query("SENS1:CHAN1:FUNC:STAT?").strip()
            if "COMPLETE" in fun:
                break
            if "0" in swe:
                break
            time.sleep(0.5)

        ch1 = self._query_binary_block("SENS1:CHAN1:FUNC:RES?", dtype="<f4")
        time.sleep(0.2)
        ch2 = self._query_binary_block("SENS1:CHAN2:FUNC:RES?", dtype="<f4")

        # Build wavelength vector from start/stop/step and the actual number of samples returned
        wl_nm = _np.linspace(self.start_wavelength * 1e9, self.stop_wavelength * 1e9, len(ch1))

        # Align lengths and return
        n = min(len(wl_nm), len(ch1), len(ch2))
        return wl_nm[:n], ch1[:n], ch2[:n]

    def _preflight_cleanup(self) -> None:
        try: self.write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
        except: pass
        try: self.write("SOUR0:WAV:SWE:STAT STOP")
        except: pass
        try: self.write("*CLS")
        except: pass

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