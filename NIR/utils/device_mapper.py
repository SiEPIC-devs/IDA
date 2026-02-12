import pyvisa as visa
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

"""
Device mapper to get PWM and TLS slots from VISA address
To be used in nir controllers
Cameron Basara, 2025
"""

@dataclass
class DeviceSlots:
    """Container for TLS and PWM info"""
    visa_addr: str
    model: str
    TLS: List = [] # TLS slot numbs
    PWM: List

    def __repr__(self):
        return (f"{self.model} @ {self.visa_addr}: "
                f"TLS: {self.TLS}, PWM: {self.PWM}")


class DeviceMap():
    # Constants from hp816x driver
    HP816X_UNDEF = 0
    HP816X_SINGLE_SENSOR = 1
    HP816X_DUAL_SENSOR = 2
    HP816X_FIXED_SINGLE_SOURCE = 3
    HP816X_FIXED_DUAL_SOURCE = 4
    HP816X_TUNABLE_SOURCE = 5
    

    def __init__(self, visa_list):
        self.visa_list = visa_list
        self.instruments: Dict[str, DeviceSlots] = {}
        self.rm: Optional[visa.ResourceManager] = None
        
    def enumerate_visa_list(self):
        """
        Enumerate all TLS and PWM slots for all VISA addresses.
        
        Returns:
            Dict[visa_addr: DeviceSlots] containing TLS and PWM lists
        """
        if self.rm is None:
            self.rm = visa.ResourceManager()
        
        self.instruments.clear()

        for visa_addr in self.visa_list:
            try:
                dev = self._enumerate_device(visa_addr)
    
    def _enumerate_device(self, visa_addr):
        """
        Enumerate a single device

        Returns:
            DeviceSlots 
        """
        try:
            # Connect to instr and identify
            inst = self.rm.open_resource(visa_addr)
            idn = self._q(inst, "*IDN?")
            parts = idn.split(',')
            model = parts[1].strip() if len(parts) > 1 else "Unknown"

            # Device type and enumerate
            if "816" in model:
                enumed_device = self._get_816x(inst, model)
            elif "N77" in model:
                enumed_device = self._get_n77(inst, model)
            else:
                print(f'[Device Mapper] Device unknown')
                return None
            return enumed_device
    
    def _get_816x(self, inst, model):
        plugins = {
            "TLS": [  
                "81940A",  # HP816X_TUNABLE_SOURCE = 5
                "81944A",  # 5
                "81949A",  # 5
                "81950A",  # 5
                "81960A",  # 5
                "81980A",  # 5
                "81989A",  # 5
            ],
            "PWM": [   
                "81630B",  # HP816X_SINGLE_SENSOR = 1
                "81632B",  # 1
                "81633B",  # 1
                "81634B",  # 1
                "81635A",  # HP816X_DUAL_SENSOR   = 2
                "81636B",  # 1
                "81637B",  # 1
            ],
        } 
        # Determine num of slots 
        if "8164" in model:
            num_slots = 5
        elif "8163" in model:
            num_slots = 3
        else:
            # Default to 5
            num_slots = 5
        
        tls_list = []
        pwm_list = []

        for slot in range(num_slots):
            try:
                res = self._q(inst, f":SLOT[{slot}]:IDN?")
                idn = res.split(',')[1].strip()
                if idn in plugins["TLS"]:
                    tls_list.append(slot)
                    continue
                if idn in plugins["PWM"]:
                    pwm_list.append(slot)
                    continue
            except:
                # Slot not found, either unknown or disconnected
                continue
        
        obj = DeviceSlots()
        obj.model = model
        obj.TLS = tls_list
        obj.PWM = pwm_list
        obj.visa_addr = inst.resource_name
        return obj

    def _get_N77(self, inst, model):
        plugins = {
            "TLS": [  # Tunable Laser Sources
                ("N7711A", 4),  # Single port 4 source
                ("N7714A", 4),
            ],
            "PWM": [  # Power Meter modules
                ("N7744A", 4),  
                ("N7745A", 8),  
                ("N7747A", 2),  
                ("N7748A", 4),  
            ]
        }


        num_slots = 1

        tls_list, pwm_list, att_list, switch_list = [], [], [], []

        for slot in range(num_slots):
            try:
                res = self._q(inst, f":SLOT[{slot}]:IDN?")
                idn = res.split(',')[1].strip()
                if idn in plugins["TLS"]:
                    tls_list.append(slot)
                    continue
                if idn in plugins["PWM"]:
                    pwm_list.append(slot)
                    continue
                if idn in plugins["ATT"]:
                    att_list.append(slot)
                    continue
                if idn in plugins["SWITCH"]:
                    switch_list.append(slot)
                    continue
            except Exception:
                continue

        obj = DeviceSlots()
        obj.model = model
        obj.TLS = tls_list
        obj.PWM = pwm_list
        obj.ATT = att_list
        obj.SWITCH = switch_list
        obj.visa_addr = inst.resource_name
        return obj

    def _w(self, inst, cmd):
        inst.write(cmd)

    def _q(self, inst, cmd):
        return inst.query(cmd).strip()