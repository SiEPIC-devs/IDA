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
    # Class-level: keep INTFC session alive to hold REN deasserted
    _ren_intf = None
    _ren_rm = None

    def __init__(self,
                 laser_slot: str = 'GPIB0::20::INSTR',
                 detector_slots: list = [],
                 safety_password: str = "1234", timeout_ms: int = 30000):
        """
        Controller instance for single / mf 816x machines
        
        :param laser_slot: primary and laser mf slot
                           if single, then this will 
                           handle everything
        :type laser_slot: str
        :param detector_slots: Additional detector 
                               mainframe detectors
        :type detector_slots: Optional[list]
        :param safety_password: pwk
        :type safety_password: str
        :param timeout_ms: visa timeout
        :type timeout_ms: int
        """

        self.timeout_ms = timeout_ms

        # Connection
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.laser_inst: Optional[pyvisa.Resource] = None
        self.detector_insts: list[pyvisa.Resource] = []
        self.detector_slots = detector_slots
        self.laser_slot = laser_slot
        self.slot_info = []
        self._is_connected = False
        self.is_mf = True if (len(detector_slots) > 0 and isinstance(detector_slots[0], str)) else False

        # lambda-scan state
        self.start_wavelength = None
        self.stop_wavelength = None
        self.step_size = None
        self.num_points = None
        self.laser_power = None
        self.sweep_module = False

    @classmethod
    def _release_ren_hold(cls):
        """Release the INTFC session that holds REN deasserted."""
        if cls._ren_intf is not None:
            try:
                cls._ren_intf.close()
            except Exception:
                pass
            cls._ren_intf = None
        if cls._ren_rm is not None:
            try:
                cls._ren_rm.close()
            except Exception:
                pass
            cls._ren_rm = None

    def connect(self) -> bool:
        try:
            # Check for existing resources and clean them up
            if self.rm is not None or self.laser_inst is not None or self.detector_insts:
                print("[NIR] Found existing resources, cleaning up first...")
                self.disconnect()
                import time
                time.sleep(0.3)  # Brief pause
            
            print(f"[NIR] Connecting to {self.laser_slot}...")
            
            if not self.is_mf:
                # Connect as usual
                self.rm = pyvisa.ResourceManager()
                self.laser_inst = self.rm.open_resource(
                    self.laser_slot,
                    timeout=self.timeout_ms,
                )
                try:
                    self.laser_inst.clear()
                except Exception:
                    pass

                idn = self.query('*IDN?')
                if not idn:
                    return False

                self._is_connected = True
                self.get_mainframe_slot_info()
                self.configure_units()
                return True
            else:
                # Now, open a ressource for each detector
                self.rm = pyvisa.ResourceManager()
                self.laser_inst = self.rm.open_resource(
                    self.laser_slot,
                    timeout=self.timeout_ms,
                )
                try:
                    self.laser_inst.clear()
                except Exception:
                    pass

                idn = self.query('*IDN?')
                if not idn:
                    return False
                
                for gpib in self.detector_slots:
                    print(gpib)
                    temp_inst = self.rm.open_resource(
                            gpib,
                            timeout=self.timeout_ms,
                        )
                    self.detector_insts.append(temp_inst)
                    try:
                        temp_inst.clear()
                    except Exception:
                        pass
                    # Do not query IDN
                self._is_connected = True
                self.get_mainframe_slot_info()
                self.configure_units()
                return True     
        except Exception as e:
            raise ConnectionError(f"{e}")

    def disconnect(self) -> bool:
        print("[NIR] === DISCONNECT START ===", flush=True)

        # 1. Stop any running sweep / logging
        try:
            self.cleanup_scan()
        except Exception as e:
            print(f"[NIR] cleanup_scan warning: {e}", flush=True)

        # 2. Close every instrument session
        try:
            if self.laser_inst:
                self.laser_inst.close()
                print("[NIR] Closed laser session", flush=True)
        except Exception as e:
            print(f"[NIR] Error closing laser: {e}", flush=True)

        for i, inst in enumerate(self.detector_insts):
            try:
                inst.close()
                print(f"[NIR] Closed detector {i}", flush=True)
            except Exception as e:
                print(f"[NIR] Error closing detector {i}: {e}", flush=True)

        # 3. Clear references — do NOT call self.rm.close() because NI-VISA
        #    shares the default RM handle across the entire process.  Closing
        #    it would invalidate every other VISA session (e.g. CorvusController).
        self.laser_inst = None
        self.detector_insts = []
        self.rm = None
        self._is_connected = False

        # 4. Deassert REN — but ONLY if no other GPIB device is still connected.
        #    REN deassert affects the entire GPIB0 bus, which would kick SMU/TEC
        #    out of remote mode and cause VI_ERROR_TMO on their next command.
        other_gpib_active = False
        try:
            import json, os
            sm_path = os.path.join(os.path.dirname(__file__), "..", "GUI",
                                   "database", "shared_memory.json")
            sm_path = os.path.normpath(sm_path)
            with open(sm_path, "r", encoding="utf-8") as f:
                sm = json.load(f)
            cfg = sm.get("Configuration", {})
            # Check if SMU or TEC (also on GPIB0) are still connected
            for key in ("smu", "tec"):
                if cfg.get(key, "") != "":
                    other_gpib_active = True
                    break
        except Exception:
            # If we can't read shared memory, be safe and skip deassert
            other_gpib_active = True

        if not other_gpib_active:
            try:
                import subprocess, sys
                proc = subprocess.Popen(
                    [sys.executable, "-c",
                     "import pyvisa,pyvisa.constants as vc;"
                     "rm=pyvisa.ResourceManager();"
                     "i=rm.open_resource('GPIB0::INTFC');"
                     "i.control_ren(vc.VI_GPIB_REN_DEASSERT);"
                     "i.close();rm.close();"
                     "print('[NIR-GTL] REN deasserted (subprocess)',flush=True)"],
                    stdout=None, stderr=None
                )
                proc.wait(timeout=5)
                print("[NIR] REN-deassert subprocess completed", flush=True)
            except Exception as e:
                print(f"[NIR-GTL] Subprocess launch/wait failed: {e}", flush=True)
        else:
            print("[NIR] Skipping REN deassert — other GPIB devices still active", flush=True)

        print("[NIR] === DISCONNECT COMPLETE ===", flush=True)
        return True

    def write(self, scpi: str) -> None:
        self.laser_inst.write(scpi)

    def write_detector(self, scpi: str, idx: int) -> None:
        self.detector_insts[idx].write(scpi)

    def query(self, scpi: str, sleep_s: float = 0.02, retries: int = 1) -> str:
        for attempt in range(retries + 1):
            resp = self.laser_inst.query(scpi).strip()
            if resp or attempt == retries:
                return resp
            time.sleep(0.03)
    
    def query_detector(self, scpi: str, idx: int) -> str:
        for attempt in range(2):
            resp = self.detector_insts[idx].query(scpi).strip()
            if resp or attempt == 1:
                return resp
            time.sleep(0.03)

    def get_mainframe_slot_info(self):
        """
        Call mainframe to get a list of tuples containing

        [(MF,slot,head), ...]        
        
        Where SCPI calls will use Slot, Head
        """

        from NIR.sweep import HP816xLambdaScan
        hp = HP816xLambdaScan(
            self.laser_slot,
            self.detector_slots
        )
        try:
            if self.is_mf:
                ok = hp.connect_mf()
            else:
                ok = hp.connect()
            if not ok:
                raise RuntimeError("HP816xLambdaScan.connect() failed")
            # [(PWMCh, MF, Slot, Head), ...,])
            self.slot_info = []
            mapping = hp.enumarate_slots()
            for _, mf, slot, head in mapping:
                self.slot_info.append((mf, slot, head))
        finally:
            try:
                hp.disconnect()
                self.sweep_module = False
                self.configure_units()
            except Exception:
                pass
            self.slot_info = sorted(self.slot_info)
            return self.slot_info

    ######################################################################
    # Laser functions
    ######################################################################

    def configure_units(self) -> bool:
        """Configured nir to dBm"""
        try:
            # Write laser source unit
            self.write(f"SOUR0:POW:UNIT 0")

            # PWM config
            for mf, slot, head in self.slot_info:
                if mf > 0:
                    self.write_detector(
                        f"SENS{slot}:CHAN{head+1}:POW:UNIT 0",
                        mf-1  # MF will be +1 due to laser
                    )
                    continue
                self.write(f"SENS{slot}:CHAN{head+1}:POW:UNIT 0")
            
            return True
        except Exception as e:
            return False

    # Rest of the laser functions only pertain to main laser module
    # So behaviour is same as usual
    def set_wavelength(self, nm: float) -> bool:
        """Set wl in nm"""
        try:
            self.write(f"SOUR0:WAV {nm * 1e-9}")
            return True
        except Exception as e:
            return False

    def get_wavelength(self) -> Optional[float]:
        """Get wl in nm"""
        try:
            v = self.query("SOUR0:WAV?")
            x = float(v)
            return x * 1e9 if x < 1e-3 else x
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
    # Behaviour now has to be seperated by detectors vs. Laser
    # Some were skipped because they are not really used
    # Or only for development, niche or debugging
    ######################################################################

    def set_detector_units(self, slot, units: int = 0, mf: int = 0) -> None:
        """
        Set Detector units
            unit[int]: 0 dBm, 1 W
        """
        try:
            if mf == 0:
                self.write(f"SENS{slot}:CHAN1:POW:UNIT {units}")
                self.write(f"SENS{slot}:CHAN2:POW:UNIT {units}")
            else:
                self.write_detector(
                    f"SENS{slot}:CHAN1:POW:UNIT {units}",
                    mf-1
                )
                try:
                    self.write_detector(
                        f"SENS{slot}:CHAN2:POW:UNIT {units}",
                        mf-1
                    )
                except:
                    # Some detectors will no have this functionality
                    pass
            return True
        except:
            return False

    def get_detector_units(self, slot) -> Optional[Tuple]:
        """Set Detector units"""
        try:
            ch1 = self.query(f"SENS{slot}:CHAN1:POW:UNIT?")
            ch2 = self.query(f"SENS{slot}:CHAN2:POW:UNIT?")
            return ch1, ch2
        except:
            return False

    def read_power(self, slot, head, mf: int = 0) -> Optional[Tuple[float]]:
        """
        Read power from detector channel.
        Note: head is 0-based from slot_info, but SCPI CHAN is 1-based.
        READ triggers a new measurement and waits for completion.
        """
        chan = head + 1  # Convert 0-based head to 1-based SCPI CHAN
        try:
            if mf == 0:
                p = self.query(f"READ{slot}:CHAN{chan}:POW?")
                return float(p)
            else:
                p = self.query_detector(
                    f"READ{slot}:CHAN{chan}:POW?",
                    mf-1
                )
                return float(p)
        except:
            return -80.0

    def enable_autorange(self, enable: bool = True, slot: int = 1, mf: int = 0) -> bool:
        """Enable/disable autorange """
        try:
            if mf == 0:
                self.write(f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO {1 if enable else 0}")
                return True
            else:
                self.write_detector(
                    f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO {1 if enable else 0}",
                    mf-1
                )
                return True
        except Exception as e:
            return False

    def set_power_range(self, range_dbm: float, slot: int = 1, mf: int = 0) -> bool:
        """Set power range for both slots"""
        try:
            if mf == 0:
                # Disable autorange first
                self.write(f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO 0")
                # Set range
                self.write(f"SENS{slot}:CHAN1:POW:RANG " + str(range_dbm))
                time.sleep(0.05)
                self.write(f"SENS{slot}:CHAN2:POW:RANG " + str(range_dbm))
                return True
            else:
                # Disable autorange first
                self.write_detector(f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO 0",
                                    mf-1)
                # Set range
                self.write_detector(f"SENS{slot}:CHAN1:POW:RANG " + str(range_dbm),
                                    mf-1)
                time.sleep(0.05)
                self.write_detector(f"SENS{slot}:CHAN2:POW:RANG " + str(range_dbm),
                                    mf-1)
                return True
        except Exception as e:
            return False

    def set_power_range_auto(self, slot: int = 1, mf: int = 0) -> bool:
        """Set power range to auto for both channels of detector slot"""
        try:
            if mf == 0:
                # Enable auto ranging for both channels
                self.write(f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO 1")
                time.sleep(0.05)
                self.write(f"SENSe{slot}:CHAN2:POWer:RANGe:AUTO 1")
                return True
            else:
                # Enable auto ranging for both channels
                self.write_detector(f"SENSe{slot}:CHAN1:POWer:RANGe:AUTO 1",
                                    mf-1)
                time.sleep(0.05)
                self.write_detector(f"SENSe{slot}:CHAN2:POWer:RANGe:AUTO 1",
                                    mf-1)
                return True
        except Exception as e:
            return False

    def get_power_range(self, slot: int = 1) -> Optional[Tuple]:
        """Get power range for both slots"""
        try:
            # Set range
            a = self.query(f"SENS{slot}:CHAN1:POW:RANG?")
            b = self.query(f"SENS{slot}:CHAN2:POW:RANG?")
            return a, b
        except Exception as e:
            return False

    def set_power_reference(self, ref_dbm: float, slot: int = 1, mf: int = 0) -> bool:
        """Set power reference (noise floor) for detector slot"""
        try:
            if mf == 0:
                # Set reference level for the specified slot
                self.write(f"SENS{slot}:CHAN1:POW:REF TOREF,{ref_dbm}DBM")
                self.write(f"SENS{slot}:CHAN2:POW:REF TOREF,{ref_dbm}DBM")
                time.sleep(0.05)
                return True
            else:
                # Set reference level for the specified slot
                self.write_detector(f"SENS{slot}:CHAN1:POW:REF TOREF,{ref_dbm}DBM",
                                    mf-1)
                self.write_detector(f"SENS{slot}:CHAN2:POW:REF TOREF,{ref_dbm}DBM",
                                    mf-1)
                time.sleep(0.05)
                return True
 
        except Exception as e:
            return False

    def get_power_reference(self, slot: int = 1) -> Optional[Tuple[float, float]]:
        """Get current power reference (noise floor) for detector slot"""
        try:
            # Query reference level for the specified slot
            response = self.query(f"SENS{slot}:CHAN1:POW:REF? TOREF")
            response2 = self.query(f"SENS{slot}:CHAN2:POW:REF? TOREF")
            return float(response), float(response2)
        except Exception as e:
            return False

    ######################################################################
    # Sweep functions
    # For mf purposes, this was a bit of a legacy adaptation 
    # And isn't really used. Consider refactoring this out
    ######################################################################

    def set_sweep_range_nm(self, start_nm: float, stop_nm: float) -> None:
        self.write(f"SOUR0:WAV:SWE:STAR {start_nm * 1e-9}")
        self.write(f"SOUR0:WAV:SWE:STOP {stop_nm * 1e-9}")

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
            laser_power_dbm: float, num_scans: int = 0,
            args: list = []
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        from NIR.sweep import HP816xLambdaScan
        
        # Round to avoid floating point precision issues
        start_nm = round(float(start_nm), 9)
        stop_nm = round(float(stop_nm), 9)
        step_nm = round(float(step_nm), 9)
        
        step_pm = float(step_nm) * 1000.0
        try:
            self._preflight_cleanup()
        except Exception:
            pass
        hp = HP816xLambdaScan(
            self.laser_slot,
            self.detector_slots
        )
        self.sweep_module = hp
        res = None  # Initialize res in case lambda_scan fails
        try:
            if not self.is_mf:
                ok = hp.connect()
            else:
                ok = hp.connect_mf()
            if not ok:
                raise RuntimeError("HP816xLambdaScan.connect() failed")
            res = hp.lambda_scan(
                start_nm=float(start_nm),
                stop_nm=float(stop_nm),
                step_pm=step_pm,
                power_dbm=float(laser_power_dbm),
                num_scans=0,
                args=args
            )
        finally:
            try:
                hp.disconnect()
                self.sweep_module = False
                self.configure_units()
            except Exception:
                pass
        
        # If sweep failed, res will be None
        if res is None:
            return np.array([]), []
        
        wl = np.asarray(res.get('wavelengths_nm', []), dtype=np.float64)
        power_dict = res.get('power_dbm_by_detector')
        
        # Check if power_dict is valid
        if power_dict is None or not isinstance(power_dict, dict):
            return wl, []
        
        chs = []
        for mf, slot, head in self.slot_info:
            # Only include channels that have data in power_dict
            key = (mf, slot, head)
            if key in power_dict:
                chs.append(power_dict[key])
        
        return wl, chs

    def sweep_cancel(self):
        try:
            if not self.sweep_module:
                raise RuntimeError("HP816xLambdaScan not connected")
            else:
                self.sweep_module.cancel()
                return True
        except:
            return False

    def _preflight_cleanup(self) -> None:
        try:
            for mf, slot, _ in self.slot_info:
                if mf > 0:
                    self.write_detector(f"SENS{slot}:CHAN1:FUNC:STAT LOGG,STOP", mf-1)
                else:
                    self.write(f"SENS{slot}:CHAN1:FUNC:STAT LOGG,STOP")
        except:
            pass
        try:
            self.write("SOUR0:WAV:SWE:STAT STOP")
        except:
            pass
        try:
            self.configure_units()
            self.enable_output(True)
            pass
        except:
            pass

    def cleanup_scan(self) -> None:
        try:
            for _, slot, _ in self.slot_info:
                self.write(f"SENS{slot}:CHAN1:FUNC:STAT LOGG,STOP")
        except Exception:
            pass
        try:
            self.write("SOUR0:WAV:SWE:STAT STOP")
        except Exception:
            pass
        try:
            self.drain()
        except Exception:
            pass

    def get_power_unit(self, channel=1):
        pass

    def set_power_unit(self, unit, channel=1):
        pass


# Register driver
from NIR.hal.nir_factory import register_driver

register_driver("8164B_NIR", NIR8164)