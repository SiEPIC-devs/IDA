import ctypes
import numpy as np
import pyvisa
import pandas as pd
from ctypes import c_double, c_int32, c_uint32, c_char_p, POINTER, byref
import time

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
# pyvisa_logger = logging.getLogger('pyvisa')
# pyvisa_logger.setLevel(logging.WARNING)

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
        # hp816x_init
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32

        # hp816x_prepareMfLambdaScan
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32,    # session
            c_int32,    # unit
            c_double,   # power
            c_int32,    # optical output
            c_int32,    # number of scans
            c_int32,    # PWM channels
            c_double,   # start wavelength
            c_double,   # stop wavelength
            c_double,   # step size
            POINTER(c_uint32),  # number of datapoints
            POINTER(c_uint32)   # number of value arrays
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

    def connect(self):
        try:
            session = c_int32()
            self.rm = pyvisa.ResourceManager()
            visa_address = "ASRL5::INSTR" 
    
            # Set up Prologix instrument
            self.instrument = self.rm.open_resource(visa_address, baud_rate=9600)
            self.instrument.write('++mode 1')
            self.instrument.write('++addr 20')  # Set GPIB address
            self.instrument.write('++auto 0')
            self.instrument.write('++eos 2')
            time.sleep(0.3) 
            self.instrument.close()  

            queryID = 1
            result = self.lib.hp816x_init(
                visa_address.encode(), queryID, 0, byref(session)
            )
            error_msg = ctypes.create_string_buffer(256)  # 256 byte buffer
            errorcode = self.lib.hp816x_error_message(
                session, result, error_msg
            )
            logging.debug(f"result: {result}, error: {error_msg.value.decode('utf-8')}")
            if result == 0:
                self.session = session.value
                self.lib.hp816x_registerMainframe(self.session)
                self.connected = True
                return True
        except Exception as e:
            logging.error(f"[LSC] Connection error: {e}")
            return False

    def lambda_scan(self, start_nm=1550, stop_nm=1555, step_pm=5,
                    power_dbm=-3.0, num_scans=1, channel=1):
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        # Convert to meters
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_size = step_pm * 1e-12

        # Prepare scan
        num_points = c_uint32()
        num_arrays = c_uint32()

        result = self.lib.hp816x_prepareMfLambdaScan(
            self.session,
            0,  # hp816x_PU_DBM
            power_dbm,
            1,  # hp816x_HIGHPOW
            num_scans,
            1,  # PWM channels
            start_wl,
            stop_wl,
            step_size,
            byref(num_points),
            byref(num_arrays)
        )

        if result != 0:
            raise RuntimeError(f"Prepare scan failed: {result}")

        # Allocate arrays
        points = num_points.value
        wavelengths = (c_double * points)()
        powers = (c_double * points)()

        # Execute scan
        result = self.lib.hp816x_executeMfLambdaScan(self.session, wavelengths)
        if result != 0:
            raise RuntimeError(f"Execute scan failed: {result}")

        # Get results
        result = self.lib.hp816x_getLambdaScanResult(
            self.session, channel, 1, -50, powers, wavelengths
        )
        if result != 0:
            raise RuntimeError(f"Get results failed: {result}")

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
            self.lib.hp816x_close(self.session)
            self.instrument.close()
            self.connected = None