import time
import ctypes
from ctypes import (c_int32,
                    c_uint16,
                    c_uint32,
                    c_double,
                    c_char,
                    c_char_p,
                    byref,
                    POINTER,
                    create_string_buffer)

import numpy as np
from typing import Optional, Tuple, List, Dict
import logging
from tqdm import tqdm

from NIR.hal.nir_hal import LaserHAL

"""
Multi-Fram NIR Controller module for multiple Laser(s)
/ Detector(s) for Keysight 816x and N77xx devices
Compatible on Windows OS.

Autodetects all NIR devices and enumerates resp. slots

Cameron Basara, 2025
"""


class MF_NIR_controller(LaserHAL):
    """
    Multi-Frame NIR Controller for Laser / Detectors using
    Keysight 816x and N77xx setups

    
    """
    # Module type constants from hp816x driver
    MODULE_EMPTY = 0
    MODULE_SINGLE_SENSOR = 1
    MODULE_DUAL_SENSOR = 2
    MODULE_FIXED_SINGLE_SOURCE = 3
    MODULE_FIXED_DUAL_SOURCE = 4
    MODULE_TUNABLE_SOURCE = 5
    MODULE_RETURN_LOSS = 6
    MODULE_RETURN_LOSS_COMBO = 7
    
    MODULE_TYPE_NAMES = {
        0: 'EMPTY',
        1: 'SINGLE_SENSOR',
        2: 'DUAL_SENSOR',
        3: 'FIXED_SINGLE_SOURCE',
        4: 'FIXED_DUAL_SOURCE',
        5: 'TUNABLE_SOURCE',
        6: 'RETURN_LOSS',
        7: 'RETURN_LOSS_COMBO',
    }
    
    # Mainframe slot counts
    MAINFRAME_SLOTS = {
        '8163': 3,   # 8163A/B
        '8164': 5,   # 8164A/B
        '8166': 18,  # 8166A/B
    }
    
    def __init__(self, visa_addresses: List[str]):
        # Load DLL
        self.lib = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")
        self.visa_addresses = visa_addresses
        self.sessions = []
        self._is_connected = False
        self._cancel = False
        
        # Setup function prototypes
        self._setup_function_prototypes()
        
        # Enumeration results
        self.discovered_modules = {'lasers': [], 'detectors': []}
        self.num_slots = 0
        
        # Active configuration
        self.laser_slot = None      # Will be auto-selected
        self.detector_slots = None  # Will be auto-selected
        self.laser_channels = []
        self.detector_channels = []
        
        # Lambda-scan state
        self.start_wavelength = None
        self.stop_wavelength = None
        self.step_size = None
        self.num_points = None
        self.laser_power = None

    def _setup_function_prototypes(self):
        """Define all DLL function signatures"""
        
        # Initialization
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32
        
        self.lib.hp816x_close.argtypes = [c_int32]
        self.lib.hp816x_close.restype = c_int32
        
        self.lib.hp816x_registerMainframe.argtypes = [c_int32]
        self.lib.hp816x_registerMainframe.restype = c_int32
        
        self.lib.hp816x_errorQueryDetect.argtypes = [c_int32, c_int32]
        self.lib.hp816x_errorQueryDetect.restype = c_int32
        
        # Error handling
        self.lib.hp816x_error_message.argtypes = [c_int32, c_int32, c_char_p]
        self.lib.hp816x_error_message.restype = c_int32
        
        self.lib.hp816x_error_query.argtypes = [c_int32, POINTER(c_int32), POINTER(c_char)]
        self.lib.hp816x_error_query.restype = c_int32
        
        # Enumeration
        self.lib.hp816x_getInstrumentId_Q.argtypes = [
            c_char_p, c_char
        ]
        self.lib.hp816x_getInstrumentId_Q.restype = c_int32
        self.lib.hp816x_getSlotInformation_Q.argtypes = [
            c_int32, c_int32, POINTER(c_int32)
        ]
        self.lib.hp816x_getSlotInformation_Q.restype = c_int32
        
        self.lib.hp816x_PWM_slaveChannelCheck.argtypes = [c_int32, c_int32, c_int32]
        self.lib.hp816x_PWM_slaveChannelCheck.restype = c_int32
        
        # TLS (Laser) Functions
        self.lib.hp816x_set_TLS_parameters.argtypes = [
            c_int32, c_int32, c_int32, c_int32, c_double
        ]
        self.lib.hp816x_set_TLS_parameters.restype = c_int32
        
        self.lib.hp816x_set_TLS_wavelength.argtypes = [
            c_int32, c_int32, c_int32, c_double
        ]
        self.lib.hp816x_set_TLS_wavelength.restype = c_int32
        
        self.lib.hp816x_get_TLS_wavelength_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_double)
        ]
        self.lib.hp816x_get_TLS_wavelength_Q.restype = c_int32
        
        self.lib.hp816x_get_TLS_parameters_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_int32), POINTER(c_double)
        ]
        self.lib.hp816x_get_TLS_parameters_Q.restype = c_int32
        
        self.lib.hp816x_set_TLS_laserState.argtypes = [
            c_int32, c_int32, c_int32, c_uint16
        ]
        self.lib.hp816x_set_TLS_laserState.restype = c_int32
        
        self.lib.hp816x_get_TLS_laserState_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_uint16)
        ]
        self.lib.hp816x_get_TLS_laserState_Q.restype = c_int32
        
        # PWM (Power Meter) Functions
        self.lib.hp816x_set_PWM_powerUnit.argtypes = [
            c_int32, c_int32, c_int32, c_int32
        ]
        self.lib.hp816x_set_PWM_powerUnit.restype = c_int32
        
        self.lib.hp816x_get_PWM_powerUnit_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_int32)
        ]
        self.lib.hp816x_get_PWM_powerUnit_Q.restype = c_int32
        
        self.lib.hp816x_readValue.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_double)
        ]
        self.lib.hp816x_readValue.restype = c_int32
        
        self.lib.hp816x_set_PWM_powerRange.argtypes = [
            c_int32, c_int32, c_int32, c_uint16, c_double
        ]
        self.lib.hp816x_set_PWM_powerRange.restype = c_int32
        
        self.lib.hp816x_get_PWM_powerRange_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_uint16), POINTER(c_double)
        ]
        self.lib.hp816x_get_PWM_powerRange_Q.restype = c_int32
        
        self.lib.hp816x_set_PWM_referenceSource.argtypes = [
            c_int32, c_int32, c_int32, c_int32, c_int32, c_int32, c_int32
        ]
        self.lib.hp816x_set_PWM_referenceSource.restype = c_int32
        
        self.lib.hp816x_set_PWM_referenceValue.argtypes = [
            c_int32, c_int32, c_int32, c_double, c_double
        ]
        self.lib.hp816x_set_PWM_referenceValue.restype = c_int32
        
        self.lib.hp816x_get_PWM_referenceValue_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_get_PWM_referenceValue_Q.restype = c_int32  
        
        # Lambda Scan Functions - Multi-Frame
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32,   # session
            c_int32,   # powerUnit (0=dBm, 1=W)
            c_double,  # power
            c_int32,   # opticalOutput
            c_int32,   # numberOfScans
            c_int32,   # PWMChannels
            c_double,  # startWavelength (m)
            c_double,  # stopWavelength (m)
            c_double,  # stepSize (m)
            POINTER(c_uint32),  # numberOfDatapoints
            POINTER(c_uint32)   # numberOfArrays
        ]
        self.lib.hp816x_prepareMfLambdaScan.restype = c_int32
        
        self.lib.hp816x_executeMfLambdaScan.argtypes = [c_int32, POINTER(c_double)]
        self.lib.hp816x_executeMfLambdaScan.restype = c_int32
        
        self.lib.hp816x_getLambdaScanResult.argtypes = [
            c_int32, c_int32, c_int32, c_double, POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_getLambdaScanResult.restype = c_int32

    def _check_error(self, status: int, context: str = "") -> None:
        """Check DLL return status and raise exception on error"""
        if status != 0:
            error_msg = create_string_buffer(256)
            self.lib.hp816x_error_message(self.session, status, error_msg)
            msg = error_msg.value.decode('utf-8')
            
            # Try to get instrument error too
            inst_code = c_int32(0)
            inst_buf = create_string_buffer(512)
            if self.lib.hp816x_error_query(self.session, byref(inst_code), inst_buf) == 0:
                if inst_code.value != 0:
                    msg += f" | Instrument Error {inst_code.value}: {inst_buf.value.decode('utf-8', errors='replace')}"
            
            raise RuntimeError(f"{context} failed: {msg} (status={status})")

    def _err_msg(self, status: int) -> str:
        """Get error message for status code"""
        if not self.session:
            return f"(no session) status={status}"
        buf = create_string_buffer(512)
        self.lib.hp816x_error_message(self.session, status, buf)
        msg = buf.value.decode(errors="replace")
        
        inst_code = c_int32(0)
        buf2 = create_string_buffer(512)
        if self.lib.hp816x_error_query(self.session, byref(inst_code), buf2) == 0 and inst_code.value != 0:
            msg += f" | Instrument Error {inst_code.value}: {buf2.value.decode(errors='replace')}"
        return msg

    ######################################################################
    # Connection & Enumeration
    ######################################################################

    def connect(self) -> bool:
        """Connect to instrument and auto-enumerate all modules"""
        try:
            # Register all mainframes
            sessions = []
            results = []
            
            for addr in self.visa_addresses:
                ss = c_int32()
                result = self.lib.hp816x_init(
                    addr.encode(),
                    c_int32(1),
                    c_int32(0),
                    byref(ss)
                )
                sessions.append(ss)
                results.append(result)
            
            # Check all connections succeeded
            for i, result in enumerate(results):
                if result != 0:
                    error_msg = create_string_buffer(256)
                    self.lib.hp816x_error_message(sessions[i].value, result, error_msg)
                    logging.error(f"Connection failed for {self.visa_addresses[i]}: {error_msg.value.decode('utf-8')}")
                    return False
            
            # Store sessions and enable error checking
            for s in sessions:
                self.sessions.append(s.value)
                self.lib.hp816x_errorQueryDetect(s.value, 1)
            
            # Register each mainframe
            for s in self.sessions:
                reg_result = self.lib.hp816x_registerMainframe(s)
                if reg_result != 0:
                    logging.warning(f"registerMainframe returned {reg_result}")
            
            # Enumerate all modules
            self._enumerate_modules()
            
            # Auto-select laser
            self._auto_select_laser()
            
            # Auto-select detectors
            self._auto_select_detectors()
            
            # Build detector channel map
            self._build_detector_channel_map()
            
            # Configure all units to dBm
            self._is_connected = True
            self.configure_units()
            
            # Log results
            logging.info(f"Total slots: {self.num_slots}")
            logging.info(f"Found {len(self.discovered_modules['lasers'])} laser(s)")
            logging.info(f"Found {len(self.discovered_modules['detectors'])} detector(s)")
            logging.info(f"Active laser slot: {self.laser_slot}")
            logging.info(f"Active detector channels: {self.detector_channels}")
            
            return True
                
        except Exception as e:
            logging.error(f"Connection error: {e}")
            return False
    
    def _enumerate_modules(self) -> None:
        """Enumerate all modules in the mainframe"""
        # Enumerate all "mainframes" to determine the slots, channels
        # And types of devices (ie lasers/detectors)
        self.discovered_modules = {'lasers': [], 'detectors': []}
        self.num_slots = 0
        
        for i, addr in enumerate(self.visa_addresses):
            # Get device IDN string
            idn_buf = create_string_buffer(256)
            result = self.lib.hp816x_getInstrumentId_Q(
                addr.encode(),
                idn_buf,
                create_string_buffer(256)
            )
            
            idn_str = idn_buf.value.decode() if result == 0 else ""
            
            if "8164" in idn_str:
                num_slots = 5
            elif "8163" in idn_str:
                num_slots = 3
            elif "8166" in idn_str:
                num_slots = 18
            elif "N7744" in idn_str:
                num_slots = 4
            elif "N7745" in idn_str:
                num_slots = 8
            else:
                logging.warning(f"Instrument {addr} not recognized: {idn_str}")
                continue
            
            self.num_slots += num_slots
            
            # Allocate array for slot information
            slot_info_array = (c_int32 * num_slots)()
            
            result = self.lib.hp816x_getSlotInformation_Q(
                self.sessions[i],
                c_int32(num_slots),
                slot_info_array
            )
            
            if result != 0:
                logging.warning(f"getSlotInformation_Q failed with status {result}")
                continue
            
            # Parse slot information
            for slot_idx in range(num_slots):
                module_type = slot_info_array[slot_idx]
                
                if module_type == self.MODULE_EMPTY:
                    continue
                
                type_name = self.MODULE_TYPE_NAMES.get(module_type, f'UNKNOWN_{module_type}')
                
                # Categorize module
                if module_type in [self.MODULE_TUNABLE_SOURCE,
                                self.MODULE_FIXED_SINGLE_SOURCE,
                                self.MODULE_FIXED_DUAL_SOURCE]:
                    self.discovered_modules['lasers'].append({
                        'mainframe': i,
                        'session': self.sessions[i],
                        'slot': slot_idx,
                        'type': module_type,
                        'type_name': type_name
                    })
                    logging.info(f"Slot {slot_idx}: Laser ({type_name})")
                    
                elif module_type in [self.MODULE_SINGLE_SENSOR, self.MODULE_DUAL_SENSOR]:
                    channels = 2 if module_type == self.MODULE_DUAL_SENSOR else 1
                    self.discovered_modules['detectors'].append({
                        'mainframe': i,
                        'session': self.sessions[i],
                        'slot': slot_idx,
                        'type': module_type,
                        'type_name': type_name,
                        'channels': channels
                    })
                    logging.info(f"Slot {slot_idx}: Detector ({type_name}, {channels} channel(s))")
                    
                    # Disable slave channel check for dual sensors
                    if module_type == self.MODULE_DUAL_SENSOR:
                        self.lib.hp816x_PWM_slaveChannelCheck(
                            self.sessions[i],
                            c_int32(slot_idx),
                            c_int32(0)
                        )

    def _auto_select_laser(self) -> None:
        """Auto-select first available tunable laser"""
        if not self.discovered_modules['lasers']:
            logging.warning("No lasers found during enumeration")
            self.laser_slot = 0  # Default fallback
            return
        
        # Prefer tunable lasers
        for laser in self.discovered_modules['lasers']:
            if laser['type'] == self.MODULE_TUNABLE_SOURCE:
                self.laser_slot = laser['slot']
                logging.info(f"Auto-selected tunable laser in slot {self.laser_slot}")
                return
        
        # Otherwise use first laser found
        self.laser_slot = self.discovered_modules['lasers'][0]['slot']
        logging.info(f"Auto-selected laser in slot {self.laser_slot}")
    
    def _auto_select_detectors(self) -> None:
        """Auto-select all available detectors"""
        if not self.discovered_modules['detectors']:
            logging.warning("No detectors found during enumeration")
            self.detector_slots = []
            return
        
        self.detector_slots = [det['slot'] for det in self.discovered_modules['detectors']]
        logging.info(f"Auto-selected {len(self.detector_slots)} detector slot(s): {self.detector_slots}")
    
    def _build_detector_channel_map(self) -> None:
        """
        Build flat list of (slot, channel, session) tuples for all active detector channels.
        For dual sensors: includes both master (0) and slave (1).
        For single sensors: includes only channel 0.
        """
        self.detector_channels = []
        
        for slot in self.detector_slots:
            # Find detector info
            detector_info = None
            for det in self.discovered_modules['detectors']:
                if det['slot'] == slot:
                    detector_info = det
                    break
            
            if detector_info is None:
                logging.warning(f"Detector slot {slot} not found in enumeration, assuming single channel")
                self.detector_channels.append((slot, 0))
            else:
                # Add all channels for this detector
                for ch in range(detector_info['channels']):
                    self.detector_channels.append((slot, ch, detector_info['session']))
        
        logging.info(f"Built detector channel map: {self.detector_channels}")
    
    def get_enumeration_info(self) -> Dict:
        """Return enumeration results for inspection"""
        return {
            'num_slots': self.num_slots,
            'discovered_modules': self.discovered_modules,
            'active_laser_slot': self.laser_slot,
            'active_detector_slots': self.detector_slots,
            'detector_channels': self.detector_channels
        }

    def disconnect(self) -> bool:
        """Disconnect from instrument"""
        try:
            for session in self.sessions:
                if session:
                    self.cleanup_scan()
                    self.lib.hp816x_close(session)
                    self.session = None
                    self._is_connected = False
            return True
        except Exception as e:
            logging.error(f"Disconnect error: {e}")
            return False

    ######################################################################
    # Laser functions
    ######################################################################

    def configure_units(self) -> bool:
        """Configure all units to dBm"""
        if not self._is_connected or self.laser_slot is None:
            return False
        
        try:
            for 
            # Set laser power unit to dBm
            power = c_double()
            unit = c_int32()
            self.lib.hp816x_get_TLS_parameters_Q(
                self.session,
                c_int32(self.laser_slot),
                c_int32(0),
                byref(unit),
                byref(power)
            )
            
            self._check_error(
                self.lib.hp816x_set_TLS_parameters(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    c_int32(0),  # unit: 0=dBm
                    power
                ),
                "Set laser unit to dBm"
            )
            
            # Set detector units to dBm for all active detector channels
            for slot, ch, session in self.detector_channels:
                self._check_error(
                    self.lib.hp816x_set_PWM_powerUnit(
                        session,
                        c_int32(slot),
                        c_int32(ch),
                        c_int32(0)  # unit: 0=dBm
                    ),
                    f"Set detector slot {slot} ch {ch} unit to dBm"
                )
            
            return True
        except Exception as e:
            logging.error(f"configure_units error: {e}")
            return False

    def set_wavelength(self, nm: float) -> bool:
        """Set wavelength in nm"""
        try:
            self._check_error(
                self.lib.hp816x_set_TLS_wavelength(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    c_double(nm * 1e-9)
                ),
                "Set wavelength"
            )
            return True
        except Exception as e:
            logging.error(f"set_wavelength error: {e}")
            return False

    def get_wavelength(self) -> Optional[float]:
        """Get wavelength in nm"""
        try:
            wavelength_m = c_double()
            self._check_error(
                self.lib.hp816x_get_TLS_wavelength(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    byref(wavelength_m)
                ),
                "Get wavelength"
            )
            return wavelength_m.value * 1e9
        except Exception as e:
            logging.error(f"get_wavelength error: {e}")
            return None

    def set_power(self, dbm: float) -> bool:
        """Set power in dBm"""
        try:
            self._check_error(
                self.lib.hp816x_set_TLS_parameters(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    c_int32(0),
                    c_double(dbm)
                ),
                "Set power"
            )
            return True
        except Exception as e:
            logging.error(f"set_power error: {e}")
            return False

    def get_power(self) -> Optional[float]:
        """Get power in dBm"""
        try:
            power = c_double()
            unit = c_int32()
            self._check_error(
                self.lib.hp816x_get_TLS_parameters(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    byref(unit),
                    byref(power)
                ),
                "Get power"
            )
            return power.value
        except Exception as e:
            logging.error(f"get_power error: {e}")
            return None

    def enable_output(self, on: bool) -> bool:
        """Turn laser on/off"""
        try:
            self._check_error(
                self.lib.hp816x_set_TLS_state(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    c_uint16(1 if on else 0)
                ),
                "Set laser output state"
            )
            return True
        except Exception as e:
            logging.error(f"enable_output error: {e}")
            return False

    def get_output_state(self) -> bool:
        """Get laser output state"""
        try:
            state = c_uint16()
            self._check_error(
                self.lib.hp816x_get_TLS_state(
                    self.session,
                    c_int32(self.laser_slot),
                    c_int32(0),
                    byref(state)
                ),
                "Get laser output state"
            )
            return bool(state.value)
        except Exception as e:
            logging.error(f"get_output_state error: {e}")
            return False

    ######################################################################
    # Detector functions (work with all discovered channels)
    ######################################################################

    def set_detector_units(self, units: int = 0) -> bool:
        """Set detector units for all channels (0=dBm, 1=W)"""
        try:
            for slot, ch in self.detector_channels:
                self._check_error(
                    self.lib.hp816x_set_PWM_powerUnit(
                        self.session,
                        c_int32(slot),
                        c_int32(ch),
                        c_int32(units)
                    ),
                    f"Set detector slot {slot} ch {ch} unit"
                )
            return True
        except Exception as e:
            logging.error(f"set_detector_units error: {e}")
            return False

    def get_detector_units(self) -> Optional[List[int]]:
        """Get detector units for all channels"""
        try:
            units = []
            for slot, ch in self.detector_channels:
                unit = c_int32()
                self._check_error(
                    self.lib.hp816x_get_PWM_powerUnit(
                        self.session,
                        c_int32(slot),
                        c_int32(ch),
                        byref(unit)
                    ),
                    f"Get detector unit slot {slot} ch {ch}"
                )
                units.append(unit.value)
            return units
        except Exception as e:
            logging.error(f"get_detector_units error: {e}")
            return None

    def read_power(self) -> Optional[List[float]]:
        """Read power from all detector channels, returns list matching detector_channels order"""
        try:
            powers = []
            for slot, ch in self.detector_channels:
                power = c_double()
                self._check_error(
                    self.lib.hp816x_readValue(
                        self.session,
                        c_int32(slot),
                        c_int32(ch),
                        byref(power)
                    ),
                    f"Read power slot {slot} ch {ch}"
                )
                powers.append(power.value)
            return powers
        except Exception as e:
            logging.error(f"read_power error: {e}")
            return None

    def enable_autorange(self, enable: bool = True, slot: Optional[int] = None, 
                         channel: Optional[int] = None) -> bool:
        """
        Enable/disable autorange for detectors.
        If slot/channel not specified, applies to all detector channels.
        """
        try:
            if slot is not None and channel is not None:
                targets = [(slot, channel)]
            else:
                targets = self.detector_channels
            
            for s, c in targets:
                self._check_error(
                    self.lib.hp816x_set_PWM_powerRange(
                        self.session,
                        c_int32(s),
                        c_int32(c),
                        c_uint16(1 if enable else 0),
                        c_double(0.0)
                    ),
                    f"Set autorange slot {s} ch {c}"
                )
            return True
        except Exception as e:
            logging.error(f"enable_autorange error: {e}")
            return False

    def set_power_range(self, range_dbm: float, slot: Optional[int] = None,
                       channel: Optional[int] = None) -> bool:
        """
        Set manual power range in dBm.
        If slot/channel not specified, applies to all detector channels.
        """
        try:
            if slot is not None and channel is not None:
                targets = [(slot, channel)]
            else:
                targets = self.detector_channels
            
            for s, c in targets:
                self._check_error(
                    self.lib.hp816x_set_PWM_powerRange(
                        self.session,
                        c_int32(s),
                        c_int32(c),
                        c_uint16(0),  # MANUAL
                        c_double(range_dbm)
                    ),
                    f"Set power range slot {s} ch {c}"
                )
            return True
        except Exception as e:
            logging.error(f"set_power_range error: {e}")
            return False

    def set_power_range_auto(self, slot: Optional[int] = None, 
                            channel: Optional[int] = None) -> bool:
        """Enable auto ranging (convenience method)"""
        return self.enable_autorange(True, slot, channel)

    def get_power_range(self) -> Optional[List[Tuple[int, float]]]:
        """Get power range for all channels, returns list of (mode, range_dbm)"""
        try:
            ranges = []
            for slot, ch in self.detector_channels:
                mode = c_uint16()
                range_val = c_double()
                self._check_error(
                    self.lib.hp816x_get_PWM_powerRange_Q(
                        self.session,
                        c_int32(slot),
                        c_int32(ch),
                        byref(mode),
                        byref(range_val)
                    ),
                    f"Get power range slot {slot} ch {ch}"
                )
                ranges.append((mode.value, range_val.value))
            return ranges
        except Exception as e:
            logging.error(f"get_power_range error: {e}")
            return None

    def set_power_reference(self, ref_dbm: float, slot: Optional[int] = None,
                           channel: Optional[int] = None) -> bool:
        """
        Set power reference for relative measurements.
        If slot/channel not specified, applies to all detector channels.
        """
        try:
            if slot is not None and channel is not None:
                targets = [(slot, channel)]
            else:
                targets = self.detector_channels
            
            for s, c in targets:
                # Set to RELATIVE mode with INTERNAL reference
                self._check_error(
                    self.lib.hp816x_set_PWM_referenceSource(
                        self.session,
                        c_int32(s),
                        c_int32(c),
                        c_int32(1),  # RELATIVE
                        c_int32(0),  # INTERNAL
                        c_int32(0),
                        c_int32(0)
                    ),
                    f"Set reference mode slot {s} ch {c}"
                )
                
                # Set reference value
                self._check_error(
                    self.lib.hp816x_set_PWM_referenceValue(
                        self.session,
                        c_int32(s),
                        c_int32(c),
                        c_double(ref_dbm),
                        c_double(0.0)
                    ),
                    f"Set reference value slot {s} ch {c}"
                )
            return True
        except Exception as e:
            logging.error(f"set_power_reference error: {e}")
            return False

    def get_power_reference(self) -> Optional[List[float]]:
        """Get power reference value for all channels"""
        try:
            refs = []
            for slot, ch in self.detector_channels:
                ref_val = c_double()
                wl_offset = c_double()
                self._check_error(
                    self.lib.hp816x_get_PWM_referenceValue_Q(
                        self.session,
                        c_int32(slot),
                        c_int32(ch),
                        byref(ref_val),
                        byref(wl_offset)
                    ),
                    f"Get reference value slot {slot} ch {ch}"
                )
                refs.append(ref_val.value)
            return refs
        except Exception as e:
            logging.error(f"get_power_reference error: {e}")
            return None

    ######################################################################
    # Lambda Scan Functions (Integrated from sweep.py)
    ######################################################################

    @staticmethod
    def _round_to_pm_grid(value_nm: float, step_pm: float) -> float:
        """Round wavelength to PM grid"""
        pm = step_pm
        return round((value_nm * 1000.0) / pm) * (pm / 1000.0)

    def optical_sweep(
            self, 
            start_nm: float, 
            stop_nm: float, 
            step_nm: float,
            laser_power_dbm: float, 
            num_scans: int = 0,
            args: Optional[list] = None,
            max_points_per_segment: int = 1000000  # 1M for mainframes, set to 100000 for N77xx
    ) -> Tuple[np.ndarray, ...]:
        """
        Perform multi-frame lambda scan.

        - Supports 1M+ points for mainframes, 100k for N77xx
        
        Args:
            start_nm: Start wavelength in nm
            stop_nm: Stop wavelength in nm
            step_nm: Step size in nm  (min 0.1 pm)
            laser_power_dbm: Laser power in dBm
            num_scans: Number of scans (0 = single scan)
            args: List of (slot, ref_dbm, range_dbm_or_None) for each detector channel
                  If None, uses auto configuration
            max_points_per_segment: Maximum points per segment (1M for mainframes, 100k for N77xx)
        
        Returns:
            Tuple of (wavelengths, ch0_power, ch1_power, ...) - one array per detector channel
        """
        if not self.session:
            raise RuntimeError("Not connected to instrument")
        
        # Convert step to pm
        step_pm = float(step_nm) * 1000.0
        
        # Clamp to safe limits (81635A spec: 1490-1640 nm, step >= 0.1 pm)
        start_nm = max(1490.0, float(start_nm))
        stop_nm = min(1640.0, float(stop_nm))
        if stop_nm <= start_nm:
            raise ValueError("stop_nm must be > start_nm")
        step_pm = max(0.1, float(step_pm))
        step_nm = step_pm / 1000.0
        
        # Clamp laser power
        power_dbm = float(laser_power_dbm)
        power_dbm = max(-20.0, min(13.0, power_dbm))
        
        # Build uniform target grid for stitching
        n_target = int(round((stop_nm - start_nm) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm
        
        # Segmentation with guard bands (CRITICAL FOR STITCHING)
        guard_pre_pm = 90.0
        guard_post_pm = 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_segment - guard_points
        
        if eff_points_budget < 2:
            raise RuntimeError("Step too small for guard-banded segmentation")
        
        segments = int(np.ceil(n_target / float(eff_points_budget)))
        if segments < 1:
            segments = 1
        
        logging.info(f"Lambda scan: {start_nm:.3f}-{stop_nm:.3f} nm, step={step_pm:.2f} pm")
        logging.info(f"Total points: {n_target}, segments: {segments}, points/segment: ~{eff_points_budget}")
        
        # Preallocate output arrays for each detector channel
        num_channels = len(self.detector_channels)
        out_by_ch = [np.full(n_target, np.nan, dtype=np.float64) for _ in range(num_channels)]
        
        # Build args if not provided
        if args is None:
            args = []
            for slot, ch in self.detector_channels:
                args.extend([slot, -80.0, None])  # Default: ref=-80dBm, auto range
        
        # Helper for error checking
        def _ok(status, ctx):
            if status != 0:
                raise RuntimeError(f"{ctx} failed: {self._err_msg(status)}")
        
        # Helper to re-apply PM settings AFTER prepare (CRITICAL!)
        def _apply_pm_config():
            """Re-apply power meter configuration after prepareMfLambdaScan"""
            if args and len(args) >= 3:
                for i in range(0, len(args), 3):
                    slot = int(args[i])
                    ref_dbm = float(args[i + 1])
                    range_dbm = args[i + 2]
                    
                    for chn in (0, 1):  # Apply to both master and slave
                        # Set unit to dBm
                        _ok(self.lib.hp816x_set_PWM_powerUnit(
                            self.session, c_int32(slot), c_int32(chn), c_int32(0)),
                            f"set unit dBm s{slot} ch{chn}")
                        
                        # Set range (auto or manual)
                        if range_dbm is None:
                            _ok(self.lib.hp816x_set_PWM_powerRange(
                                self.session, c_int32(slot), c_int32(chn),
                                c_uint16(1), c_double(0.0)),
                                f"set AUTO range s{slot} ch{chn}")
                        else:
                            _ok(self.lib.hp816x_set_PWM_powerRange(
                                self.session, c_int32(slot), c_int32(chn),
                                c_uint16(0), c_double(float(range_dbm))),
                                f"set MAN range s{slot} ch{chn}={range_dbm} dBm")
                        
                        # Set reference (RELATIVE mode with INTERNAL source)
                        _ok(self.lib.hp816x_set_PWM_referenceSource(
                            self.session, c_int32(slot), c_int32(chn),
                            c_int32(1), c_int32(0), c_int32(0), c_int32(0)),
                            f"set REF REL/INT s{slot} ch{chn}")
                        
                        if ref_dbm is not None:
                            _ok(self.lib.hp816x_set_PWM_referenceValue(
                                self.session, c_int32(slot), c_int32(chn),
                                c_double(float(ref_dbm)), c_double(0.0)),
                                f"set REF value s{slot} ch{chn}={ref_dbm} dBm")
        
        # Segment loop with progress bar
        bottom = float(start_nm)
        for seg_idx in tqdm(range(segments), desc="Lambda Scan", unit="seg"):
            if self._cancel:
                logging.info("Scan cancelled by user")
                break
            
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))
            
            # Requested sub-span (mainframe handles guard bands internally)
            bottom_r = bottom
            top_r = top
            
            # PREPARE (Multi-Frame)
            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            st = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                c_int32(0),                 # powerUnit: 0=dBm
                c_double(power_dbm),        # TLS power
                c_int32(0),                 # opticalOutput: 0=HIGHPOW
                c_int32(int(num_scans)),    # numberOfScans
                c_int32(num_channels),      # PWMChannels count
                c_double(bottom_r * 1e-9),  # start (m)
                c_double(top_r * 1e-9),     # stop (m)
                c_double(step_pm * 1e-12),  # step (m)
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            _ok(st, "prepareMfLambdaScan")
            
            points_seg = int(num_points_seg.value)
            C = int(num_arrays_seg.value)
            
            if C < 1 or points_seg < 2:
                bottom = top + step_nm
                continue
            
            # RE-APPLY PM CONFIG AFTER PREPARE (CRITICAL!)
            _apply_pm_config()
            
            # EXECUTE (Multi-Frame - returns wavelengths only)
            wl_buf = (c_double * points_seg)()
            st = self.lib.hp816x_executeMfLambdaScan(self.session, wl_buf)
            _ok(st, "executeMfLambdaScan")
            
            # Convert wavelengths and trim guard bands
            wl_seg_nm_full = np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
            
            # Keep only points within [bottom_r, top_r] (removes ~90 pm guards)
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue
            
            wl_seg_nm = wl_seg_nm_full[mask]
            
            # Map to global target grid indices (CRITICAL FOR STITCHING)
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]
            
            if idx.size == 0:
                bottom = top + step_nm
                continue
            
            # Fetch per-channel power arrays and stitch into output
            for ch_idx in range(num_channels):
                buf = (c_double * points_seg)()
                st = self.lib.hp816x_getLambdaScanResult(
                    self.session,
                    c_int32(ch_idx + 1),  # Array index (1-based)
                    c_int32(1),           # interpolate=1
                    c_double(-90.0),      # floor
                    buf,
                    wl_buf
                )
                _ok(st, f"getLambdaScanResult ch{ch_idx}")
                
                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).copy()
                pwr_seg = pwr_full[mask][valid]
                
                # Stitch into output array
                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m > 0:
                        out_by_ch[ch_idx][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[ch_idx][idx] = pwr_seg
            
            # Next segment
            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm
        
        # Post-processing: fill last sample if needed
        for ch_idx in range(num_channels):
            arr = out_by_ch[ch_idx]
            if np.isnan(arr[-1]) and n_target >= 2:
                arr[-1] = arr[-2]
        
        # Return as tuple: (wavelengths, ch0, ch1, ...)
        result = [wl_target] + out_by_ch
        return tuple(result)

    def sweep_cancel(self):
        """Cancel ongoing sweep"""
        self._cancel = True

    ######################################################################
    #  HAL Required Methods
    ######################################################################

    def set_sweep_range_nm(self, start_nm: float, stop_nm: float) -> None:
        self.start_wavelength = start_nm
        self.stop_wavelength = stop_nm

    def set_sweep_step_nm(self, step_nm: float) -> None:
        self.step_size = step_nm

    def arm_sweep_cont_oneway(self) -> None:
        pass

    def start_sweep(self) -> None:
        pass

    def stop_sweep(self) -> bool:
        return True

    def get_sweep_state(self) -> str:
        return "IDLE"

    def cleanup_scan(self) -> None:
        """Cleanup after scan"""
        try:
            self.enable_output(False)
        except Exception:
            pass

    def get_power_unit(self, channel=1):
        """Compatibility - returns first channel unit"""
        units = self.get_detector_units()
        return units[0] if units else None

    def set_power_unit(self, unit, channel=1):
        """Compatibility - sets all channels"""
        return self.set_detector_units(unit)


# Register driver
from NIR.hal.nir_factory import register_driver
register_driver("MF_NIR_controller", MF_NIR_controller)