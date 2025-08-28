import ctypes
import numpy as np
from ctypes import c_double, c_int32, c_uint32, c_char, c_char_p, POINTER, byref, create_string_buffer
from tqdm import tqdm

"""
Cameron Basara, 2025
"""

class HP816xLambdaSweep:
    def __init__(self, lib=None, session=None):
        self.lib = lib
        self.session = session
        
    def set_session(self, lib, session):
        """Set DLL library and session from controller"""
        self.lib = lib
        self.session = session
        
    def _err_msg(self, status):
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

    def lambda_scan(self, start_nm: float=1490, stop_nm: float=1600, step_pm: float=0.5,
                    power_dbm: float=3.0, num_scans: int=0, channels: list=[1,2]):
        if not self.session:
            raise RuntimeError("No DLL session provided by controller")
            
        # Constrain values to limits if out of range
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm 
        
        # Build uniform grid
        step_nm = step_pm / 1000.0
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Stitching params
        max_points_per_scan = 20001
        guard_pre_pm  = 90.0
        guard_post_pm = 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too large for guard-banded segmentation (eff_points_budget < 2).")

        pts_est = n_target
        segments = int(np.ceil(pts_est / float(eff_points_budget)))
        if segments < 1:
            segments = 1

        # Preallocate outputs
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}

        # Segment loop
        bottom = float(start_nm)
        for seg in tqdm(range(segments), desc="Lambda Scan Stitching", unit="seg"):
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r    = top

            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            result = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                0,                  # dBm
                power_dbm,
                0,                  # High power
                num_scans,
                len(channels),      # expose all requested arrays
                bottom_r * 1e-9,
                top_r    * 1e-9,
                step_pm  * 1e-12,
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            if result != 0:
                raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")

            points_seg = int(num_points_seg.value)
            wavelengths_seg = (c_double * points_seg)()

            result = self.lib.hp816x_executeMfLambdaScan(self.session, wavelengths_seg)
            if result != 0:
                raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")

            # Wavelengths (nm), guard trim, grid index map
            wl_seg_nm_full = np.ctypeslib.as_array(wavelengths_seg, shape=(points_seg,)).astype(np.float64) * 1e9
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue
            wl_seg_nm = wl_seg_nm_full[mask]
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]

            # Per-array fetch into preallocated grid
            for ch in channels:
                buf = (c_double * points_seg)()
                res = self.lib.hp816x_getLambdaScanResult(self.session, 1, int(ch), -90.0, buf, wavelengths_seg)
                if res != 0:
                    continue
                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).astype(np.float64)
                pwr_seg = pwr_full[mask][valid]
                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m <= 0:
                        continue
                    out_by_ch[ch][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[ch][idx] = pwr_seg

            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm

        # Guarantee last sample is filled
        for ch in channels:
            if n_target >= 2 and np.isnan(out_by_ch[ch][-1]):
                nz = np.where(~np.isnan(out_by_ch[ch]))[0]
                if nz.size:
                    out_by_ch[ch][-1] = out_by_ch[ch][nz[-1]]

        channels_dbm = [out_by_ch[ch] for ch in channels]
        return {
            'wavelengths_nm': wl_target,
            'channels': channels,
            'channels_dbm': channels_dbm,
            'num_points': int(n_target)
        }