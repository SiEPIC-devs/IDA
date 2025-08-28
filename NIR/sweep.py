import ctypes
import numpy as np
import pyvisa
import pandas as pd
from ctypes import c_double, c_int32, c_uint32, c_char, c_char_p, POINTER, byref, create_string_buffer
from tqdm import tqdm
import time

import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)


class HP816xLambdaScan:
    def __init__(self):
        # Load the HP 816x library
        self.lib = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  # or .lib path
        self.visa_lib = ctypes.WinDLL("visa32.dll")
        self.session = None
        self.connected = False
        self._setup_function_prototypes()
        self.instrument = None
        self._cancel = False

    def _setup_function_prototypes(self):
        # hp816x_init
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32

        # Error/utility functions (so we can actually read human messages)
        ViSession = c_int32
        ViStatus = c_int32
        self.lib.hp816x_error_message.argtypes = [ViSession, ViStatus, POINTER(c_char)]
        self.lib.hp816x_error_message.restype = ViStatus
        self.lib.hp816x_error_query.argtypes = [ViSession, POINTER(c_int32), POINTER(c_char)]
        self.lib.hp816x_error_query.restype = ViStatus
        self.lib.hp816x_errorQueryDetect.argtypes = [ViSession, c_int32]  # VI_TRUE/VI_FALSE
        self.lib.hp816x_errorQueryDetect.restype = ViStatus
        self.lib.hp816x_dcl.argtypes = [ViSession]
        self.lib.hp816x_dcl.restype = ViStatus
        self.lib.hp816x_reset.argtypes = [ViSession]
        self.lib.hp816x_reset.restype = ViStatus
        self.lib.hp816x_registerMainframe.argtypes = [ViSession]
        self.lib.hp816x_registerMainframe.restype = ViStatus

        # hp816x_prepareMfLambdaScan
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32,  # session ViSession
            c_int32,  # unit ViInt32
            c_double,  # power ViReal64
            c_int32,  # optical output ViInt32
            c_int32,  # number of scans ViInt32
            c_int32,  # PWM channels ViInt32
            c_double,  # start wavelength ViReal64
            c_double,  # stop wavelength ViReal64
            c_double,  # step size ViReal64
            POINTER(c_uint32),  # number of datapoints ViUInt32
            POINTER(c_uint32)  # number of value arrays ViUInt32
        ]
        self.lib.hp816x_prepareMfLambdaScan.restype = c_int32

        # hp816x_executeMfLambdaScan
        self.lib.hp816x_executeMfLambdaScan.argtypes = [c_int32, POINTER(c_double)]
        self.lib.hp816x_executeMfLambdaScan.restype = c_int32

        # hp816x_getLambdaScanResult
        self.lib.hp816x_getLambdaScanResult.argtypes = [
            c_int32, c_int32, c_int32, c_double, POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_getLambdaScanResult.restype = c_int32

    def _err_msg(self, status):
        if not self.session:
            return f"(no session) status={status}"
        buf = create_string_buffer(512)
        # Driver/VISA message
        self.lib.hp816x_error_message(self.session, status, buf)
        msg = buf.value.decode(errors="replace")
        # Try instrument FIFO too (if any)
        inst_code = c_int32(0)
        buf2 = create_string_buffer(512)
        if self.lib.hp816x_error_query(self.session, byref(inst_code), buf2) == 0 and inst_code.value != 0:
            msg += f" | Instrument Error {inst_code.value}: {buf2.value.decode(errors='replace')}"
        return msg

    @staticmethod
    def _round_to_pm_grid(value_nm: float, step_pm: float) -> float:
        pm = step_pm
        return round((value_nm * 1000.0) / pm) * (pm / 1000.0)

    def connect(self):
        try:
            session = c_int32()
            # self.rm = pyvisa.ResourceManager()
            visa_address = "GPIB0::20::INSTR"

            queryID = 1
            result = self.lib.hp816x_init(
                visa_address.encode(), queryID, 0, byref(session)
            )
            error_msg = create_string_buffer(256)  # 256 byte buffer
            self.lib.hp816x_error_message(session.value, result, error_msg)
            logging.debug(f"result: {result}, error: {error_msg.value.decode('utf-8')}")

            if result == 0:
                self.session = session.value
                self.lib.hp816x_errorQueryDetect(self.session, 1)  # VI_TRUE
                self.lib.hp816x_registerMainframe(self.session)
                self.connected = True
                return True
        except Exception as e:
            logging.error(f"[LSC] Connection error: {e}")
            return False

    def lambda_scan_mf(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                       power_dbm: float = 3.0, num_scans: int = 0, channels: list = [0, 1]):
        if not self.session:
            raise RuntimeError("Not connected to instrument")
        ##############################################################
        # Addendum
        # To obtain a higher precision, the Tunable Laser Source
        # is set 1 nm before the Start Wavelength, this means,
        # you have to choose a Start Wavelength 1 nm greater than
        # the minimum possible wavelength. Also, the wavelength
        # sweep is actually started 90 pm befo re the Start Wavelength
        #  and ends 90 pm after the Stop Wavelength, this means, you
        # have to choose a Stop Wavelength 90 pm less than
        # the maximum possible wavelength.
        ###############################################################
        # hp816x_prepareLambdaScan(
        #     ViSession ihandle, ViInt32 powerUnit,
        #     ViReal64 power, ViInt32 opticalOutput,
        #     ViInt32 numberofScans, ViInt32 PWMChannels,
        #     ViReal64 startWavelength, ViReal64 stopWavelength,
        #     ViReal64 stepSize, ViUInt32 numberofDatapoints,
        #     ViUInt32 numberofChannels);
        ###############################################################
        # 81635A:
        #   Power range: +10 to -80dBm
        #   Wavelength range 800 nm – 1650 nm
        ###############################################################
        # Constain values to limits if out of range
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm

        # Convert to meters
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_size = step_pm * 1e-12

        # Build uniform grid
        step_nm = step_pm / 1000.0
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Stitching params
        max_points_per_scan = 20001
        guard_pre_pm = 90.0
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
            if self._cancel: break
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r = top

            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            result = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                0,  # dBm
                power_dbm,
                0,  # High power
                num_scans,
                len(channels),  # expose all requested arrays
                bottom_r * 1e-9,
                top_r * 1e-9,
                step_pm * 1e-12,
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
                res = self.lib.hp816x_getLambdaScanResult(self.session, int(ch), 1, -90.0, buf, wavelengths_seg)
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

    def lambda_scan(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                    power_dbm: float = 3.0, num_scans: int = 0, channels: list = [1, 2]):
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        # Constrain to instrument limits
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm
        # 2.06279e-007 to 13.5241;
        if power_dbm < 3e-7: power_dbm = 3e-7
        elif power_dbm > 13.5: power_dbm = 13.5

        # Convert to meters for DLL
        step_nm = step_pm / 1000.0
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_m = step_pm * 1e-12

        # Uniform output grid
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Segmentation (accounting for 90 pm guard)
        max_points_per_scan = 20001
        guard_pre_pm, guard_post_pm = 90.0, 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too large for guard-banded segmentation (eff_points_budget < 2).")

        pts_est = n_target
        segments = max(1, int(np.ceil(pts_est / float(eff_points_budget))))

        # Preallocate outputs
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}

        bottom = float(start_nm)
        for seg in tqdm(range(segments), desc="Lambda Scan Stitching", unit="seg"):
            if self._cancel:
                print("SHOULD BE CANCELLLL !!!!!!!!!!!!!")
                raise RuntimeError("Cancelling Lambda Scan Stitching")
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r = top

            # -------- SINGLE-FRAME PREP --------
            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            result = self.lib.hp816x_prepareLambdaScan(
                self.session,
                0,  # powerUnit: 0=dBm
                c_double(power_dbm),  # TLS setpoint
                0,  # opticalOutput: 0=HIGHPOW (change if LOWSSE/BHR/BLR)
                c_int32(num_scans),  # 0->1 scan, 1->2 scans, etc.
                c_int32(len(channels)),  # PWMChannels = COUNT (NOT a mask)
                c_double(bottom_r * 1e-9),
                c_double(top_r * 1e-9),
                c_double(step_pm * 1e-12),
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            if result != 0:
                raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")

            points_seg = int(num_points_seg.value)
            C = int(num_arrays_seg.value)
            if C < 1:
                # Nothing enabled; skip this segment
                bottom = top + step_nm
                continue
            if C != len(channels):
                pass

            # -------- ALLOCATE BUFFERS FOR EXECUTE --------
            wl_buf = (c_double * points_seg)()

            # Prepare up to 8 power array pointers; fill first C, NULL the rest
            power_slots = [None] * 8
            power_arrays = {}
            for i in range(C):  # i: 0..C-1 maps to powerArray1..C
                arr = (c_double * points_seg)()
                power_slots[i] = arr
                power_arrays[i + 1] = arr  # keep by slot index (1-based)

            # Helper: NULL pointer for unused arrays
            from ctypes import POINTER
            def ptr_or_null(arr):
                return arr if arr is not None else POINTER(c_double)()

            # -------- SINGLE-FRAME EXECUTE (returns wl + all channels at once) --------
            result = self.lib.hp816x_executeLambdaScan(
                self.session,
                wl_buf,
                ptr_or_null(power_slots[0]),
                ptr_or_null(power_slots[1]),
                ptr_or_null(power_slots[2]),
                ptr_or_null(power_slots[3]),
                ptr_or_null(power_slots[4]),
                ptr_or_null(power_slots[5]),
                ptr_or_null(power_slots[6]),
                ptr_or_null(power_slots[7]),
            )
            if result != 0:
                raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")

            # -------- Convert wl + guard-trim + index into global grid --------
            wl_seg_nm_full = np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
            # Keep only [bottom_r, top_r] (drop 90 pm guards)
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue

            wl_seg_nm = wl_seg_nm_full[mask]
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]

            # -------- Map slot order (1..C) to 'channels' labels --------
            # Example: if channels=[2,4], powerArray1->ch=2, powerArray2->ch=4
            for slot_i, ch_label in enumerate(channels, start=1):
                if slot_i > C:
                    break
                arr = power_arrays[slot_i]
                pwr_full = np.ctypeslib.as_array(arr, shape=(points_seg,)).copy()  # copy: decouple
                pwr_seg = pwr_full[mask][valid]

                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m > 0:
                        out_by_ch[ch_label][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[ch_label][idx] = pwr_seg

            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm

        # Fill last sample if instrument left it NaN after stitching
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

    def cancel(self):
        print("AJHHHHHHHHHHHHHHHHHHHHHH CANCEL")
        self._cancel = True
        self.disconnect()
    def disconnect(self):
        if self.session:
            self.lib.hp816x_close(self.session)
            self.connected = None

# def main():
#     """Tester"""
#     inst = HP816xLambdaScan()
#     ok = inst.connect()
#     if ok:
#         print("success")
#     else:
#         inst.disconnect()
#         return

#     dict = inst.lambda_scan(start_nm=1400,stop_nm=1800,step_pm=4)

#     print(dict)
#     inst.disconnect()

# if __name__ == "__main__":
#      main()