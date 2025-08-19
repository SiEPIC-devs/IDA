import pyvisa
import logging
from time import sleep
from typing import Dict, Any

from LDC.hal.LDC_hal import LdcHAL, LDCEventType

"""
LDC Controller - SRS LDC 502
Cameron Basara, 2025
"""

# Configure logging
logger = logging.getLogger(__name__)

class SrsLdc502(LdcHAL):
    """Driver for SRS LDC500 series using VISA (GPIB) communication."""

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
                baud_rate=9600,
                timeout=5000,
                write_termination='\n',
                read_termination='\n',
            )
            
            # Configure PROLOGIX GPIB-USB controller
            self._inst.write('++mode 1')
            sleep(0.1)
            self._inst.write(f'++addr {2}')
            sleep(0.1)
            self._inst.write('++auto 1')
            sleep(0.1)
            self._inst.write('++eoi 1')
            sleep(0.1)
            self._inst.write('++eos 0')
            sleep(0.1)
            self._inst.write('++read_tmo_ms 3000')
            sleep(0.1)

            # Test connection
            self._inst.write('*IDN?')
            resp = self._inst.read()
            self._log(f"Connected to {resp.strip()}")

            self.connected = True 
            
            # Emit connection event
            self._emit_event(LDCEventType.CONNECTION_CHANGED, {
                'connected': True,
                'device_id': resp.strip()
            })
            
            return True
        
        except Exception as e:
            self._log(f"Connection error: {e}", "error")
            self.connected = False
            self._emit_event(LDCEventType.CONNECTION_CHANGED, {
                'connected': False,
                'error': str(e)
            })
            return False
        
    def disconnect(self) -> bool:
        """Disable TEC and close VISA session."""
        try:
            if self._inst:
                try:
                    # Turn off TEC safely before disconnecting
                    self._inst.write("TEON 0")
                    sleep(0.1)
                    
                    # Emit TEC off event
                    self._emit_event(LDCEventType.TEC_OFF, {
                        'reason': 'disconnect'
                    })
                except Exception:
                    pass
                    
                self._inst.close()
            
            self._rm.close()
            self.connected = False
            
            # Emit disconnect event
            self._emit_event(LDCEventType.CONNECTION_CHANGED, {
                'connected': False,
                'reason': 'user_disconnect'
            })
            
            self._log("Disconnected and TEC powered off")
            return True
            
        except Exception as e:
            self._log(f"Disconnect error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'disconnect',
                'error': str(e)
            })
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
    
    # === TEC Controller ===
    
    def tec_on(self) -> bool:
        """Turn on TEC"""
        try:
            self._inst.write("TEON 1")
            sleep(0.1)
            
            # Verify TEC is on
            if self.tec_status():
                self._log("TEC turned on")
                
                # Emit TEC on event
                self._emit_event(LDCEventType.TEC_ON, {
                    'temperature_setpoint': self._temp_setpoint
                })
                return True
            else:
                self._log("TEC on command failed", "error")
                self._emit_event(LDCEventType.ERROR, {
                    'operation': 'tec_on',
                    'error': 'TEC failed to turn on'
                })
                return False
                
        except Exception as e:
            self._log(f"TEC on error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'tec_on',
                'error': str(e)
            })
            return False

    def tec_off(self) -> bool:
        """Turn off TEC"""
        try:
            self._inst.write("TEON 0")
            sleep(0.1)
            
            # Verify TEC is off
            if not self.tec_status():
                self._log("TEC turned off")
                
                # Emit TEC off event
                self._emit_event(LDCEventType.TEC_OFF, {
                    'reason': 'user_command'
                })
                return True
            else:
                self._log("TEC off command failed", "error")
                self._emit_event(LDCEventType.ERROR, {
                    'operation': 'tec_off',
                    'error': 'TEC failed to turn off'
                })
                return False
                
        except Exception as e:
            self._log(f"TEC off error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'tec_off',
                'error': str(e)
            })
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
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'tec_status',
                'error': str(e)
            })
            return False

    def get_temp(self) -> float:
        """Get current temperature"""
        try:
            self._inst.write("TTRD?")
            sleep(0.1)
            resp = self._inst.read()
            temp = float(resp.strip())
            
            self._log(f"Temperature: {temp}°C")
            
            # Emit temperature reading event
            self._emit_event(LDCEventType.TEMP_CHANGED, {
                'temperature': temp,
                'units': 'celsius'
            })
            
            return temp
            
        except Exception as e:
            self._log(f"Temperature read error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'get_temp',
                'error': str(e)
            })
            return None
   
    def set_temp(self, temperature: float) -> bool:
        """Set desired temperature"""
        try:
            # Check temperature limits
            if temperature > 75.0 or temperature < 15.0:
                raise ValueError("Temperature outside safe limits (15-75°C)")
            
            old_setpoint = self._temp_setpoint
            
            self._inst.write(f"TEMP {temperature}")
            sleep(0.1)
            
            # Update internal setpoint
            self._temp_setpoint = temperature
            
            # Verify by reading back
            current_temp = self.get_temp()
            
            self._log(f"Temperature setpoint changed: {old_setpoint}°C -> {temperature}°C")
            
            # Emit setpoint change event
            self._emit_event(LDCEventType.TEMP_SETPOINT_CHANGED, {
                'old_setpoint': old_setpoint,
                'new_setpoint': temperature,
                'current_temp': current_temp
            })
            
            return True
            
        except Exception as e:
            self._log(f"Set temperature error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'set_temp',
                'target_temp': temperature,
                'error': str(e)
            })
            return False
   
    def set_sensor_type(self, sensor_type: str) -> bool:
        """Configure for sensor models on LDC 50x devices"""
        try:
            old_type = self._sensor_type
            
            self._inst.write(f"TMDN {sensor_type}")
            sleep(0.1)
            
            self._sensor_type = sensor_type
            self._log(f"Sensor type changed: {old_type} -> {sensor_type}")
            
            # Emit configuration change event
            self._emit_event(LDCEventType.CONFIG_CHANGED, {
                'parameter': 'sensor_type',
                'old_value': old_type,
                'new_value': sensor_type
            })
            
            return True
            
        except Exception as e:
            self._log(f"Set sensor type error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'set_sensor_type',
                'sensor_type': sensor_type,
                'error': str(e)
            })
            return False
    
    def configure_sensor_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for whichever sensor model is configured"""
        try:
            if len(coeffs) != 3:
                raise ValueError("Expected 3 coefficients [A, B, C]")
            
            old_coeffs = [self._model_A, self._model_B, self._model_C]
            
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
            
            # Emit configuration change event
            self._emit_event(LDCEventType.CONFIG_CHANGED, {
                'parameter': 'sensor_coeffs',
                'old_value': old_coeffs,
                'new_value': coeffs
            })
            
            return True
            
        except Exception as e:
            self._log(f"Configure sensor coeffs error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'configure_sensor_coeffs',
                'coeffs': coeffs,
                'error': str(e)
            })
            return False

    def configure_PID_coeffs(self, coeffs: list[float]) -> bool:
        """Set the coefficients for PID control"""
        try:
            if len(coeffs) != 3:
                raise ValueError("Expected 3 coefficients [P, I, D]")
            
            old_coeffs = [self._pid_p, self._pid_i, self._pid_d]
            
            # Set PID coefficients
            self._inst.write(f"TPGN {coeffs[0]}")
            sleep(0.2)
            self._inst.write(f"TIGN {coeffs[1]}")
            sleep(0.2)
            self._inst.write(f"TDGN {coeffs[2]}")
            sleep(0.2)
            
            # Update internal values
            self._pid_p, self._pid_i, self._pid_d = coeffs
            
            self._log(f"PID coefficients updated: P={coeffs[0]}, I={coeffs[1]}, D={coeffs[2]}")
            
            # Emit configuration change event
            self._emit_event(LDCEventType.CONFIG_CHANGED, {
                'parameter': 'pid_coeffs',
                'old_value': old_coeffs,
                'new_value': coeffs
            })
            
            return True
            
        except Exception as e:
            self._log(f"Configure PID coeffs error: {e}", "error")
            self._emit_event(LDCEventType.ERROR, {
                'operation': 'configure_pid_coeffs',
                'coeffs': coeffs,
                'error': str(e)
            })
            return False
     
    # === LD Controller (Stubs) ===
    # These are not implemented for the 347 stage but required by the HAL
    
    def ldc_on(self) -> bool:
        """Turn LDC on - Not implemented for 347 stage"""
        self._log("LDC control not implemented for this stage", "error")
        return False
    
    def ldc_off(self) -> bool:
        """Turn LDC off - Not implemented for 347 stage"""
        self._log("LDC control not implemented for this stage", "error")
        return False
    
    def ldc_state(self) -> str:
        """Check state of LDC - Not implemented for 347 stage"""
        return "not_implemented"
    
    def set_voltage_limit(self, limit: float) -> bool:
        """Set voltage limit - Not implemented for 347 stage"""
        return False
    
    def get_voltage_limit(self) -> float:
        """Get voltage limit - Not implemented for 347 stage"""
        return 0.0
    
    def set_current_limit(self, limit: float) -> bool:
        """Set current limit - Not implemented for 347 stage"""
        return False
    
    def get_current_limit(self) -> float:
        """Get current limit - Not implemented for 347 stage"""
        return 0.0
    
    def set_current(self, current: float) -> bool:
        """Configure current setpoints - Not implemented for 347 stage"""
        return False
    
    def get_current(self) -> float:
        """Read current - Not implemented for 347 stage"""
        return 0.0
    
    def get_voltage(self) -> float:
        """Read voltage - Not implemented for 347 stage"""
        return 0.0
    
    def set_current_range(self, toggle: int) -> bool:
        """Set range to be either High or Low - Not implemented for 347 stage"""
        return False

# Register the fixed driver
from LDC.hal.LDC_factory import register_driver
register_driver("srs_ldc_502", SrsLdc502)