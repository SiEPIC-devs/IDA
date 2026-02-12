from typing import Dict, List, Any, Optional
import pyvisa
import struct
from SMU.hal.smu_hal import SMUHal, SMUEventType  

# --- Helpers ---
_CHMAP = {"A": "smua", "B": "smub"}

def _chname(channel: str) -> str:
    c = channel.upper()
    if c not in _CHMAP: raise ValueError(f"channel must be 'A' or 'B', got {channel}")
    return _CHMAP[c]

class Keithley2600BController(SMUHal):
    def __init__(self, visa_address: str, nplc: float = 0.1, off_mode: str = "NORMAL"):
        super().__init__()
        self.addr = visa_address
        self.nplc = nplc
        self.off_mode = off_mode.upper()  # NORMAL | ZERO | HI-Z
        self.rm = None
        self.inst = None

    # --- lifecycle ---
    def connect(self) -> bool:
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(self.addr)
            self.inst.write_termination = "\n"
            self.inst.read_termination = "\n"
            
            # Do a light reset of per-channel state (no *RST).
            for ch in ("A", "B"):
                c = _chname(ch)
                self.inst.write(f"{c}.reset() {c}.nvbuffer1.clear()")
                # OFF mode configuration (predictable output-off behavior)
                if self.off_mode == "HI-Z":
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_HIGH_Z")
                elif self.off_mode == "ZERO":
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_ZERO")
                else:
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_NORMAL; {c}.source.offfunc = {c}.OUTPUT_DCVOLTS")
            self.connected = True
            self._emit_event(SMUEventType.CONFIG_CHANGED, {"idn": self.idn()})
            return True
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"connect", "error": str(e)})
            return False

    def disconnect(self) -> bool:
        try:
            for ch in ("A", "B"):
                c = _chname(ch)
                self.inst.write(f"{c}.source.output = {c}.OUTPUT_OFF")
            if self.inst: self.inst.close()
            if self.rm: self.rm.close()
            self.connected = False
            self._emit_event(SMUEventType.SMU_OFF, {"all": True})
            return True
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"disconnect", "error": str(e)})
            return False
    
    def idn(self) -> str:
        # keep as-is; useful for logging
        return self.inst.query("*IDN?").strip()

    def get_and_clear_errors(self) -> list[dict]:
        try:
            errs = self.get_errors()
            self.clear_errors()
            return errs
        except Exception as e:
            self._emit_event(
                SMUEventType.ERROR,
                {"where":"get_and_clear_errors", "error": str(e)}
                )
            return []

    def clear_errors(self) -> None:
        try:
            self.inst.write("errorqueue.clear()")
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"clear_errors", "error": str(e)})

    def get_errors(self) -> list[dict]:
        try:
            n = int(float(self.inst.query("print(errorqueue.count)")))
            errs = []
            for _ in range(n):
                code, msg, sev, node = self.inst.query("print(errorqueue.next())").strip().split("\t")
                errs.append({"code": int(code), "message": msg, "severity": int(sev), "node": int(node)})
            return errs
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"get_errors", "error": str(e)})
            return []
        
    def get_config(self) -> Dict:
        return {"address": self.addr, "nplc": self.nplc, "off_mode": self.off_mode}

    # --- getters (both channels) ---
    def get_current(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.i())")) for ch in ("A","B")}  # SI A

    def get_current_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limiti)")) for ch in ("A","B")}  # SI A

    def get_voltage(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.v())")) for ch in ("A","B")}  # SI V

    def get_voltage_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limitv)")) for ch in ("A","B")}  # SI V

    def get_resistance(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.r())")) for ch in ("A","B")}  # SI ohms

    def get_power_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limitp)")) for ch in ("A","B")}  # SI W

    def get_state(self) -> Dict:
        return {
            "connected": self.connected,
            "idn": self.idn(),
            "limits": {
                "V": self.get_voltage_limits(),
                "I": self.get_current_limits(),
                "P": self.get_power_limits(),
            },
            "output": {ch: bool(int(float(self.inst.query(f"print({_chname(ch)}.source.output)") or "0"))) for ch in ("A","B")},
        }

    # --- setters (per-channel) ---
    def set_source_mode(self, mode: str, channel: str) -> bool:
        c = _chname(channel)
        if mode.upper() == "V" or mode.upper().startswith("VOLT"):
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCVOLTS")
        else:
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCAMPS")
        return True

    def set_current(self, val: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.leveli = {val}")
        return True

    def set_current_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limiti = {lim}")
        return True

    def set_voltage(self, val: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.levelv = {val}")
        return True

    def set_voltage_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limitv = {lim}")
        return True

    def set_power_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limitp = {lim}")
        return True  # 2600B supports limitp (true power compliance)

    # --- output & level ) ---
    def output_on(self, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.output = {c}.OUTPUT_ON")
        self._emit_event(SMUEventType.SMU_ON, {"ch": channel})
        return True

    def output_off(self, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.output = {c}.OUTPUT_OFF")
        self._emit_event(SMUEventType.SMU_OFF, {"ch": channel})
        return True

    def output_level(self, output: float, channel: str) -> bool:
        # Set setpoint respecting current source mode
        c = _chname(channel)
        func = self.inst.query(f"print({c}.source.func)").strip()
        if "DCVOLTS" in func:
            self.inst.write(f"{c}.source.levelv = {output}")
        else:
            self.inst.write(f"{c}.source.leveli = {output}")
        return True
    
    # --- Ranging ---
    def source_range(self, range_val: float, 
                     channel: list, var_type: str) -> bool:
        channels = []
        for i in range(len(channel)):
            ch = channel[i]
            c = _chname(ch)
            channels.append(c)
        kind = var_type.lower()
        if kind not in ("voltage", "current", "v", "i"):
            raise ValueError("type must be 'voltage' or 'current'")
        else:
            kind = kind[0] if kind[0] != "c" else "i" 

        for ch in channels:
            self.inst.write(f'{ch}.source.autorange{kind} = {ch}.AUTORANGE_OFF')
            self.inst.write(f'{ch}.source.range{kind} = {range_val}')

        self._emit_event(SMUEventType.CONFIG_CHANGED, {"range": range_val, "var": var_type})
        return True
    
    def source_autorange(self, lowest_range: Optional[float],
                         channel: list, var_type: str) -> bool:
        channels = []
        for i in range(len(channel)):
            ch = channel[i]
            c = _chname(ch)
            channels.append(c)
        kind = var_type.lower()
        if kind not in ("voltage", "current", "v", "i"):
            raise ValueError("type must be 'voltage' or 'current'")
        else:
            kind = kind[0] if kind[0] != "c" else "i" 

        if lowest_range is None:
            if kind == "i":
                lowest_range = 100e-9  # 100 nA
            else: 
                lowest_range = 0.1     # 100 mV 

        for ch in channels:
            self.inst.write(f'{ch}.source.lowrange{kind} = {lowest_range}')
            self.inst.write(f'{ch}.source.autorange{kind} = {ch}.AUTORANGE_ON')

        self._emit_event(SMUEventType.CONFIG_CHANGED, {"range": "auto_range", "var": var_type})
        return True

    # --- IV sweep ---
    def iv_sweep(self,
                 start: float,
                 stop: float,
                 step: float,
                 channel: List[str],
                 sweep_type: str,  # "voltage" or "current"
                 scale: str = "LIN" # or LOG
                 ) -> Dict[str, Any]:
        channels = []
        for i in range(len(channel)):
            ch = channel[i]
            c = _chname(ch)
            channels.append(c)
        kind = sweep_type.lower()
        if kind not in ("voltage", "current", "v", "i"):
            raise ValueError("type must be 'voltage' or 'current'")

        # step = (stopi - starti) / (points - 1)
        npts = int(round((stop - start) / step)) + 1
        if npts <= 1: raise ValueError("sweep requires at least 2 points")

        # Return data
        out = {ch: None for ch in channels}

        for ch in channels:
            # Configure measure speed and buffers
            w = self.inst.write
            q = self.inst.query
            w(f'{ch}.nvbuffer1.clear()')
            w(f'{ch}.nvbuffer1.appendmode=1')
            w(f'{ch}.nvbuffer1.collectsourcevalues=1')
            w(f'{ch}.nvbuffer1.collecttimestamps=1')

            # Select source mode
            if kind == "voltage" or kind == "v":
                if scale == 'LIN':
                    w(f'SweepVLinMeasureI({ch}, {start}, {stop}, 0.01, {npts})')
                    w('waitcomplete()')

                    # Get points from buffer and retrieve
                    i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
                    v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
                    t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')
                
                else:
                    # LOG scale
                    w(f'SweepVLogMeasureI({ch}, {start}, {stop}, 0.01, {npts})')
                    w('waitcomplete()')

                    # Get points from buffer and retrieve
                    i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
                    v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
                    t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')

            else:
                # Current sweep
                if scale == 'LIN':
                    w(f'SweepILinMeasureV({ch}, {start}, {stop}, 0.01, {npts})')
                    w('waitcomplete()')

                    # Get points from buffer and retrieve, flipped
                    v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
                    i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
                    t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')
                
                else:
                    # LOG scale
                    w(f'SweepILogMeasureV({ch}, {start}, {stop}, 0.01, {npts})')
                    w('waitcomplete()')

                    # Get points from buffer and retrieve, flipped
                    v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
                    i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
                    t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')
                
            I = [float(x) for x in i_csv.strip().split(',') if x]
            V = [float(x) for x in v_csv.strip().split(',') if x]
            t = [float(x) for x in t_csv.strip().split(',') if x]
            out[f'{ch}'] = {'I': I, 'V': V, 't': t}
        
        self._emit_event(SMUEventType.IV_SWEEP, {"channels": channel, "npts": npts})
        return out

    # def iv_sweep_list(
    #         self,
    #         sweep_list: list,
    #         channel: list,
    #         sweep_type: str # Voltage or Current
    # ) -> dict[str, Any]:
    #     channels = []
    #     for i in range(len(channel)):
    #         ch = channel[i]
    #         c = _chname(ch)
    #         channels.append(c)
    #     kind = sweep_type.lower()
    #     if kind not in ("voltage", "current", "v", "i"):
    #         raise ValueError("type must be 'voltage' or 'current'")

    #     # step = (stopi - starti) / (points - 1)
    #     npts = len(sweep_list) 
    #     if npts <= 1: raise ValueError("sweep requires at least 2 points")

    #     # Return data
    #     out = {ch: None for ch in channels}

    #     for ch in channels:
    #         # Configure measure speed and buffers
    #         w = self.inst.write
    #         q = self.inst.query
    #         w(f'{ch}.nvbuffer1.clear()')
    #         w(f'{ch}.nvbuffer1.appendmode=1')
    #         w(f'{ch}.nvbuffer1.collectsourcevalues=1')
    #         w(f'{ch}.nvbuffer1.collecttimestamps=1')

    #         # Select source mode
    #         if kind == "voltage" or kind == "v":
    #             w(f'SweepVListMeasureI({ch}, {sweep_list}, 0.01, {npts})')
    #             w('waitcomplete()')

    #             # Get points from buffer and retrieve
    #             n = int(float(q(f'print({ch}.nvbuffer.n)')))
    #             i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
    #             v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
    #             t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')
    #         else:
    #             # Current sweep
    #             w(f'SweepIListMeasureV({ch}, {sweep_list}, 0.01, {npts})')
    #             w('waitcomplete()')

    #             # Get points from buffer and retrieve, flipped
    #             v_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.readings)')
    #             i_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.sourcevalues)')
    #             t_csv = q(f'printbuffer(1, {ch}.nvbuffer1.n, {ch}.nvbuffer1.timestamps)')
                
    #         I = [float(x) for x in i_csv.strip().split(',') if x]
    #         V = [float(x) for x in v_csv.strip().split(',') if x]
    #         t = [float(x) for x in t_csv.strip().split(',') if x]
    #         out[f'{ch}'] = {'I': I, 'V': V, 't': t}

    #     self._emit_event(SMUEventType.IV_SWEEP, {"channels": channel, "npts": npts})
    #     return out

# Register the fixed driver
from SMU.hal.smu_factory import register_driver
register_driver("keithley2600B_smu", Keithley2600BController)