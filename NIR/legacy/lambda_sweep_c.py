import ctypes
import numpy as np
import pyvisa
import pandas as pd
from ctypes import c_double, c_int32, c_uint32, c_char, c_char_p, POINTER, byref, create_string_buffer  # <<< added c_char, create_string_buffer
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

    def _setup_function_prototypes(self):
        # Convenience typedefs (match NI/Keysight: 32-bit status/session on Win64)
        ViSession = c_int32  # <<< added
        ViStatus  = c_int32  # <<< added

        # hp816x_init
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32

        # --- Error/utility functions (so we can actually read human messages) ---  # <<< added
        self.lib.hp816x_error_message.argtypes = [ViSession, ViStatus, POINTER(c_char)]
        self.lib.hp816x_error_message.restype  = ViStatus

        self.lib.hp816x_error_query.argtypes   = [ViSession, POINTER(c_int32), POINTER(c_char)]
        self.lib.hp816x_error_query.restype    = ViStatus

        self.lib.hp816x_errorQueryDetect.argtypes = [ViSession, c_int32]  # VI_TRUE/VI_FALSE
        self.lib.hp816x_errorQueryDetect.restype  = ViStatus

        self.lib.hp816x_dcl.argtypes = [ViSession]
        self.lib.hp816x_dcl.restype  = ViStatus

        self.lib.hp816x_reset.argtypes = [ViSession]
        self.lib.hp816x_reset.restype  = ViStatus

        if hasattr(self.lib, "hp816x_registerMainframe"):
            self.lib.hp816x_registerMainframe.argtypes = [ViSession]
            self.lib.hp816x_registerMainframe.restype  = ViStatus

        # hp816x_prepareMfLambdaScan
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32,    # session ViSession
            c_int32,    # unit ViInt32
            c_double,   # power ViReal64
            c_int32,    # optical output ViInt32
            c_int32,    # number of scans ViInt32
            c_int32,    # PWM channels ViInt32
            c_double,   # start wavelength ViReal64
            c_double,   # stop wavelength ViReal64
            c_double,   # step size ViReal64
            POINTER(c_uint32),  # number of datapoints ViUInt32
            POINTER(c_uint32)   # number of value arrays ViUInt32
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

        # NOTE: Your call to hp816x_getLambdaScanParameters_Q() below lacked a prototype.
        # It’s safer to guard it and only call if present.  # <<< added
        if hasattr(self.lib, "hp816x_getLambdaScanParameters_Q"):
            # Many driver variants expose a _Q that returns by reference; signature varies.
            # Without the exact header, avoid setting argtypes (call is optional).  # <<< added
            pass

    # Helper: fetch readable driver+instrument error text  # <<< added
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

    def connect(self):
        try:
            session = c_int32()
            self.rm = pyvisa.ResourceManager()
            visa_address = "GPIB0::20::INSTR" 
    
            # Set up Prologix instrument
            self.instrument = self.rm.open_resource(visa_address)
            # self.instrument.write('++mode 1')
            # self.instrument.write('++addr 20')  # Set GPIB address
            # self.instrument.write('++auto 0')
            # self.instrument.write('++eos 2')
            time.sleep(0.3) 
            self.instrument.close()  

            queryID = 1
            result = self.lib.hp816x_init(
                visa_address.encode(), queryID, 0, byref(session)
            )
            error_msg = create_string_buffer(256)  # 256 byte buffer
            # NOTE: print the *message buffer*, not the return code of error_message  # <<< added
            self.lib.hp816x_error_message(session.value, result, error_msg)  # <<< added
            logging.debug(f"result: {result}, error: {error_msg.value.decode('utf-8')}")  # <<< added

            if result == 0:
                self.session = session.value
                # Enable automatic instrument error checking following each function call.  # <<< added
                self.lib.hp816x_errorQueryDetect(self.session, 1)  # VI_TRUE  # <<< added
                self.lib.hp816x_registerMainframe(self.session) 
                self.connected = True
                return True
            else:
                # Provide clear message on init failure.  # <<< added
                raise RuntimeError(f"hp816x_init failed ({result}): {self._err_msg(result)}")  # <<< added

        except Exception as e:
            logging.error(f"[LSC] Connection error: {e}")
            return False

    def lambda_scan(self, start_nm=1490, stop_nm=1570, step_pm=0.5,
                    power_dbm=3.0, num_scans=0, channel=1):
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        # Convert to meters
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_size = step_pm * 1e-12

        # Prepare scan
        num_points = c_uint32()
        num_arrays = c_uint32()
        
        ##########################################################
        # hp816x_prepareLambdaScan(
        #     ViSession ihandle, ViInt32 powerUnit, 
        #     ViReal64 power, ViInt32 opticalOutput, 
        #     ViInt32 numberofScans, ViInt32 PWMChannels, 
        #     ViReal64 startWavelength, ViReal64 stopWavelength, 
        #     ViReal64 stepSize, ViUInt32 numberofDatapoints, 
        #     ViUInt32 numberofChannels);
        ##########################################################
        # 81635A:
        #   Power range: +10 to -80dBm
        #   Wavelength range 800 nm – 1650 nm
        result = self.lib.hp816x_prepareMfLambdaScan(
            self.session, 
            0,  # 0 hp816x_PU_DBM 1 hp816x_PU_WATT
            power_dbm, # Set power output to a val in dBm
            0, # 0: High power, 1: Low SSE, 2: BHR Both high power 3: BLR Both Low SSE (0 WORKS)
            num_scans, # 0 index to 3 scans
            2,  # PWM channels, how many to use
            start_wl, # in m
            stop_wl, # in m
            step_size, # in m
            byref(num_points), # number of wavelength steps llscan produce
            byref(num_arrays) # number of PW Chn (allocate num of power value arrays for ll scan func)
        )
        if result != 0:
            # Human-readable diagnostics (driver + instrument FIFO)  # <<< added
            raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")  # <<< added

        # Get the values for sanity
        if hasattr(self.lib, "hp816x_getLambdaScanParameters_Q"):  # <<< added guard
            try:
                paramsq = self.lib.hp816x_getLambdaScanParameters_Q()  # signature varies by driver
                if paramsq != 0:
                    raise RuntimeError(
                        f"ParamsQ failed ({paramsq}) :: {self._err_msg(paramsq)}"  # <<< added
                    )
                else:
                    print(paramsq)
            except Exception as e:
                logging.debug(f"hp816x_getLambdaScanParameters_Q not usable: {e}")  # <<< added

        # Allocate arrays
        points = num_points.value
        wavelengths = (c_double * points)()
        powers = (c_double * points)()

        # Execute scan
        result = self.lib.hp816x_executeMfLambdaScan(self.session, wavelengths)
        if result != 0:
            raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")  # <<< added

        # Get results
        result = self.lib.hp816x_getLambdaScanResult(
            self.session, channel, 1, -50, powers, wavelengths
        )
        if result != 0:
            raise RuntimeError(f"Get results failed: {result} :: {self._err_msg(result)}")  # <<< added

        # Convert to numpy arrays
        wl_array = np.array([wavelengths[i] for i in range(points)])
        pow_array = np.array([powers[i] for i in range(points)])

        return {
            'wavelengths_nm': wl_array * 1e9,
            'powers_dbm': pow_array,
            'num_points': points
        }

    def save_csv(self, data, filename):
        df = pd.DataFrame({
            'Wavelength_nm': data['wavelengths_nm'],
            'Power_dBm': data['powers_dbm']
        })
        df.to_csv(filename, index=False)

    def disconnect(self):
        if self.session:
            try:
                self.lib.hp816x_close(self.session)
            except Exception as e:
                logging.debug(f"hp816x_close: {e}")
            try:
                self.instrument.close()
            except Exception as e:
                logging.debug(f"instrument.close: {e}")
            self.connected = None

def main():
    """Tester"""
    inst = HP816xLambdaScan()
    ok = inst.connect()
    if ok:
        print("success")
    else:
        inst.disconnect()
        return 

    d = inst.lambda_scan()

    print(d)
    inst.disconnect()


if __name__ == "__main__":
    main()
