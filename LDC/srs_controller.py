import pyvisa
import logging
from time import sleep
from typing import Dict, Any

from LDC.hal.LDC_hal import LdcHAL, LDCEventType

"""
LDC Controller - SRS LDC 501

This module is refactored ldc_controller to work with
pure GPIB connections instead of Prologix

Cameron Basara, 2025
"""

# Configure logging
logger = logging.getLogger(__name__)

class SrsLdc501(LdcHAL):
    """Driver for SRS LDC500 series using GPIB communication."""

    def __init__(
        self,
        visa_address: str,
        sensor_type: str,
        model_coeffs: list[float],
        pid_coeffs: list[float],
        temp_setpoint: float,
        debug: bool = False
    ):
        super().__init__()
        self._visa_addr = visa_address
        self._sensor_type = sensor_type
        self._pid_p, self._pid_i, self._pid_d = pid_coeffs
        self._model_A, self._model_B, self._model_C = model_coeffs
        self._temp_setpoint = temp_setpoint
        self._debug = debug
        self._rm = pyvisa.ResourceManager() 
        self._inst = None

        # From sheri, lets use hard set vals
        self._pid_p, self._pid_i, self._pid_d = [-1.71, 0.058, 4.29]
        # w e also dont care about ABC params, apply hard set vals for now
        self._sensor_type = '0'

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if self._debug:
            print(f"[LDC] {message}")
        elif level == "error":
            logger.error(f"[LDC] {message}")

    def connect(self) -> bool:
        """Open VISA session and basic instrument init."""
        try:
            self._inst = self._rm.open_resource(
                self._visa_addr,
                timeout=5000,
                write_termination='\n',
                read_termination='\n',
            )
            
            # Test connection
            self._inst.write('*IDN?')
            resp = self._inst.read()
            self._log(f"Connected to {resp.strip()}")
            
            self.connected = True 

            return True
        
        except Exception as e:
            self._log(f"Connection error: {e}", "error")
            self.connected = False
            return False
        
    def disconnect(self) -> bool:
        """Disable TEC and close VISA session."""
        try:
            # Mark as disconnected FIRST to prevent any concurrent access
            self.connected = False
            
            if self._inst:
                try:
                    self._inst.write("TEON 0")
                    sleep(0.2)
                except Exception:
                    pass
                pass
            # Do NOT call self._rm.close() — NI-VISA shares the default
            # ResourceManager handle across the entire process.  Closing it
            # would invalidate every other VISA session (SMU, NIR, etc.).
            if self._inst:
                try:
                    self._inst.close()
                except Exception:
                    pass
            
            self._inst = None
            self._rm = None
            self._log("Disconnected and TEC powered off")
            return True
            
        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            return False

    def get_config(self) -> Dict[str, Any]:
        """Get configuration parameters"""
        try:
            return {
                'visa_address': self._visa_addr,
                'sensor_type': self._sensor_type,
                'pid_coeffs': [self._pid_p, self._pid_i, self._pid_d],
                'model_coeffs': [self._model_A, self._model_B, self._model_C],
                'setpoint': self._temp_setpoint,
                'connected': getattr(self, 'connected', False),
                'driver_type': 'srs_ldc_502_fixed'
            }
        except Exception as e:
            self._log(f"Get config error: {e}", "error")
            return {}
    
    # --- TEC Controller ---
    
    def tec_on(self) -> bool:
        """Turn on TEC"""
        try:
            self._inst.write("TEON 1")
            sleep(0.1)
            
            # Verify TEC is on
            if self.tec_status():
                self._log("TEC turned on")
                
                return True
            else:
                self._log("TEC on command failed", "error")
                return False
                
        except Exception as e:
            self._log(f"TEC on error: {e}", "error")
            return False

    def tec_off(self) -> bool:
        """Turn off TEC"""
        try:
            self._inst.write("TEON 0")
            sleep(0.1)
            
            # Verify TEC is off
            if not self.tec_status():
                self._log("TEC turned off")
                
                return True
            else:
                self._log("TEC off command failed", "error")
                return False
                
        except Exception as e:
            self._log(f"TEC off error: {e}", "error")
            return False

    def tec_status(self) -> bool:
        """Return TEC status, True if on False if off"""
        try:
            self._inst.write("TEON?")
            sleep(0.1)
            resp = self._inst.read()
            
            status = resp.strip() == "1"
            self._log(f"TEC status: {'ON' if status else 'OFF'}")
            return status
            
        except Exception as e:
            self._log(f"TEC status error: {e}", "error")
            return False

    def get_temp(self) -> float:
        """Get current temperature"""
        try:
            self._inst.write("TTRD?")
            sleep(0.1)
            resp = self._inst.read()
            temp = float(resp.strip())
            
            self._log(f"Temperature: {temp}C")
            
            return temp
            
        except Exception as e:
            self._log(f"Temperature read error: {e}", "error")
            return None
   
    def set_temp(self, temperature: float) -> bool:
        """Set desired temperature"""
        try:
            # Check temperature limits
            if temperature > 75.0 or temperature < 15.0:
                raise ValueError("Temperature outside safe limits (15-75C)")
            
            old_setpoint = self._temp_setpoint
            
            self._inst.write(f"TEMP {temperature}")
            sleep(0.1)
            
            # Update internal setpoint
            self._temp_setpoint = temperature
            
            self._log(f"Temperature setpoint changed: {old_setpoint}C -> {temperature}C")
            return True
            
        except Exception as e:
            self._log(f"Set temperature error: {e}", "error")
            return False
   
    def set_sensor_type(self, sensor_type: str) -> bool:
        """Configure for sensor models on LDC 50x devices"""
        try:
            old_type = self._sensor_type
            
            if sensor_type == '1':
                self._inst.write(f"TMDN {sensor_type}")
                sleep(0.1)
                
                self._sensor_type = sensor_type
                self._log(f"Sensor type changed: {old_type} -> {sensor_type}")
            
            elif sensor_type == '0':
                print('is this wiorking')
                self._inst.write(f"TMDR ALPHA")
                sleep(0.1)

            return True
            
        except Exception as e:
            self._log(f"Set sensor type error: {e}", "error")
            return False
    
    def configure_sensor_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for whichever sensor model is configured"""
        try:
            if self._sensor_type == '0':
                self.configure_linear_model(
                    [0.1, 0.00334]  # R0, alpha
                )
                return True
            if len(coeffs) != 3:
                raise ValueError("Expected 3 coefficients [A, B, C]")
            
            # Set coefficients
            self._inst.write(f"TSHA {coeffs[0]}")
            sleep(0.2)
            self._inst.write(f"TSHB {coeffs[1]}")
            sleep(0.2)
            self._inst.write(f"TSHC {coeffs[2]}")
            sleep(0.2)
            
            # Update internal values
            self._model_A, self._model_B, self._model_C = coeffs
            
            self._log(f"Sensor coefficients updated: A={coeffs[0]}, B={coeffs[1]}, C={coeffs[2]}")
            return True
            
        except Exception as e:
            self._log(f"Configure sensor coeffs error: {e}", "error")
            return False

    def configure_PID_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for PID control"""
        try:
            if len(coeffs) != 3:
                raise ValueError("Expected 3 coefficients [P, I, D]")
            
            self._inst.write(f"TPGN {self._pid_p}")
            sleep(0.2)
            self._inst.write(f"TIGN {self._pid_i}")
            sleep(0.2)
            self._inst.write(f"TDGN {self._pid_d}")
            sleep(0.2)
            print(self._inst.query(f"TDGN?"))
            
            # Update internal values
            self._pid_p, self._pid_i, self._pid_d = coeffs
            
            self._log(f"PID coefficients updated: P={coeffs[0]}, I={coeffs[1]}, D={coeffs[2]}")
            return True
            
        except Exception as e:
            self._log(f"Configure PID coeffs error: {e}", "error")
            return False
    
    def configure_linear_model(self, coeffs: list[float]) -> bool:
        # Set model, then params
        self._inst.write(f"TRTR {coeffs[0]}")
        sleep(0.1)
        self._inst.write(f"TRTA {coeffs[1]}")
        return True
    
    # --- LD Controller ---
    def ldc_on(self) -> None:
        """Enable LD output (forces current to 0 first)."""
        if not self._inst:
            raise RuntimeError("Instrument not connected")

        self._inst.write("SILD 0")
        sleep(0.1)
        self._inst.write("LDON 1")
        sleep(0.2)

    def ldc_off(self) -> None:
        """Disable LD output (forces current to 0 first)."""
        if not self._inst:
            raise RuntimeError("Instrument not connected")

        self._inst.write("SILD 0")
        sleep(0.1)
        self._inst.write("LDON 0")
        sleep(0.2)

    def ldc_state(self) -> str:
        """Return 'on' or 'off'."""
        self._inst.write("LDON?")
        sleep(0.05)
        return "on" if self._inst.read().strip() == "1" else "off"

    # --- Limits ---

    def set_voltage_limit(self, v_lim: float) -> None:
        self._inst.write(f"SVLM {v_lim}")
        sleep(0.05)

    def get_voltage_limit(self) -> float:
        self._inst.write("SVLM?")
        sleep(0.05)
        return float(self._inst.read())

    def set_current_limit(self, i_lim: float) -> None:
        self._inst.write(f"SILM {i_lim}")
        sleep(0.05)

    def get_current_limit(self) -> float:
        self._inst.write("SILM?")
        sleep(0.05)
        return float(self._inst.read())

    # --- Set / Read ---

    def set_current(self, i_set: float) -> None:
        """Set LD current setpoint (mA)."""
        self._inst.write(f"SILD {i_set}")
        sleep(0.05)

    def get_current(self) -> float:
        self._inst.write("RILD?")
        sleep(0.05)
        return float(self._inst.read())

    def get_voltage(self) -> float:
        self._inst.write("RVLD?")
        sleep(0.05)
        return float(self._inst.read())

    def set_current_range(self, high: bool) -> None:
        self._inst.write("RNGE HIGH" if high else "RNGE LOW")
        sleep(0.05)

    # --- Current Sweep ---

    def current_sweep(
        self,
        start_ma: float,
        stop_ma: float,
        step_ma: float,
        dwell_ms: int,
        trigger_delay_ms: int = 0,
    ) -> None:
        """
        Hardware current sweep using SRS SCAN command.

        Notes:
        - start_ma must NOT be 0 (SRS quirk).
        - Sweep blocks until complete.
        """

        if not self._inst:
            raise RuntimeError("Instrument not connected")

        # Enable LD (SRS takes several seconds internally)
        self.ldc_on()
        sleep(4.5)

        steps = int((stop_ma - start_ma) / step_ma) + 1

        # Trigger delay (applies to all steps)
        self._inst.write(f"SYND {trigger_delay_ms}")
        sleep(0.1)

        # Set initial current one step below start
        self._inst.write(f"SILD {start_ma - step_ma}")
        sleep(0.1)

        # SCAN <step>, <count>, <dwell>
        self._inst.write(f"SCAN {step_ma},{steps},{dwell_ms}")
        sleep(0.1)

        # Wait until sweep completes
        while True:
            self._inst.write("SCAN?")
            sleep(0.1)
            if int(self._inst.read()) == 0:
                break
        
        # Retrieve
        scan_data = []
        for i in range(steps):
            self._inst.write(f"RDAT? {i}")
            sleep(0.05)
            resp = self._inst.read().strip()

            # Parse I,V 
            i_str, v_str = resp.split(',')
            current_ma = float(i_str) if type(i_str) == str else None
            voltage_ma = float(v_str) if type(v_str) == str else None
            scan_data.append((current_ma, voltage_ma))

        self.ldc_off()
        return scan_data


# Register the fixed driver
from LDC.hal.LDC_factory import register_driver
register_driver("srs_ldc_501", SrsLdc501)