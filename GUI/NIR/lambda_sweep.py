import logging
import pyvisa
import time
import numpy as np
import struct
from typing import Tuple, Optional, List

logging.basicConfig(level=logging.DEBUG, format='%(funcName)s - %(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

class LambdaScanProtocol:
    def __init__(self, config = None, laser=None, com_port=5):
        self.laser = laser
        self.com_port = com_port
        self.rm = None
        self.instrument = None

        # If laser is provided and already connected, use its instrument
        if self.laser and hasattr(self.laser, 'instrument') and self.laser.instrument:
            self.instrument = self.laser.instrument
        
        # Lambda scan parameters
        self.start_wavelength = None if not config else config.start_nm 
        self.stop_wavelength = None if not config else config.stop_nm
        self.step_size = None if not config else config.step_nm
        self.num_points = None
        self.laser_power = None if not config else config.laser_power_dbm
        self.averaging_time = None
        
    def connect(self):
        """Connect using proven working method."""
        try:
            if self.laser:
                self.instrument = self.laser.instrument
            else:
                self.rm = pyvisa.ResourceManager()
                visa_address = f"ASRL{self.com_port}::INSTR"
                
                self.instrument = self.rm.open_resource(
                    visa_address,
                    baud_rate=115200,
                    timeout=30000, # high to read lots of binary data
                    write_termination='\n',
                    read_termination=None
                )
                
                # Clear and configure Prologix
                self.instrument.clear()
                time.sleep(0.2)
                self.instrument.write('++mode 1')
                time.sleep(0.1)
                self.instrument.write('++addr 20')
                time.sleep(0.1)
                self.instrument.write('++auto 1')
                time.sleep(0.1)
                self.instrument.write('++eos 2')
                time.sleep(0.1)
                
                # Max binary block size that can be read from 1 block
                self.instrument.chunk_size = 204050 * 2 + 8 # Represents 100k data points + header, EOF
            
            # Test connection
            resp = self._send_command("*IDN?").strip()
            logging.info(f"Connected to: {resp}")
            self.configure_units()
            return resp
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    def _send_command(self, command, expect_response=True):
        """Send command using proven working method."""
        if not self.instrument:
            raise RuntimeError("Not connected")
        
        try:
            self.instrument.write('++addr 20')
            
            if expect_response:
                self.instrument.write(command)
                time.sleep(0.05)
                self.instrument.write('++read eoi')
                return self.instrument.read().strip()
            else:
                self.instrument.write(command)
                return ""
                
        except Exception as e:
            logging.error(f"Command failed: {command}, Error: {e}")
            raise
    
    def _write(self, command):
        """Write command without expecting response."""
        return self._send_command(command, expect_response=False)
    
    def _query(self, command):
        """Query command expecting response."""
        return self._send_command(command, expect_response=True)
    
    def _query_binary(self, command):
        """Query command expecting binary response."""
        if not self.instrument:
            raise RuntimeError("Not connected")
        
        try:
            self.instrument.write('++addr 20')
            self.instrument.write(command)
            time.sleep(0.1)
            self.instrument.write('++read eoi')
            raw_data = self.instrument.read_raw()
            return raw_data
        
        except Exception as e:
            logging.error(f"Binary query failed: {command}, Error: {e}")
            raise

    def _query_binary_and_parse(self, command):
        if not self.instrument:
            raise RuntimeError("Not connected")
        self.instrument.write('++addr 20')
        self.instrument.write(command)
        time.sleep(0.5)
        self.instrument.write('++read eoi')

        # Read header first
        header = self.instrument.read_bytes(2)  
        if header[0:1] != b"#":
            raise ValueError("Invalid SCPI block header")

        num_digits = int(header[1:2].decode())
        len_field = self.instrument.read_bytes(num_digits)
        data_len = int(len_field.decode())

        # Read binary data in chunks until complete
        data_block = b""
        remaining = data_len
        while remaining > 0:
            chunk = self.instrument.read_bytes(min(remaining, 4096))
            data_block += chunk
            remaining -= len(chunk)

        # Flush leftovers 
        try:
            self.instrument.read()  # Read trailing \n
        except Exception:
            pass

        data = struct.unpack("<" + "f" * (len(data_block)//4), data_block)
        data = np.array(data)

        if data[0] > 0:
            # W
            data = 10*np.log10(data) + 30 
        return data
    
    def sweep(self):
        return self.optical_sweep(self.start_wavelength, self.stop_wavelength, self.step_size, self.laser_power)
    
    def optical_sweep(self, start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s=0.02):
        """Call full optical sweep procedure"""
        try:
            # Pass params, execute scan, retrieve data, cleanup
            self.configure_and_start_lambda_sweep(start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s)   
            self.execute_lambda_scan()
            wavelengths, power_ch1, power_ch2 = self.retrieve_scan_data()
            power_ch1 = np.where(power_ch1 > 0, np.nan, power_ch1)
            power_ch2 = np.where(power_ch2 > 0, np.nan, power_ch2)
            self.cleanup_scan()
            return wavelengths, power_ch1, power_ch2
        except Exception as e:
            logging.error(f"Found error in optical sweep: {e}")
            return None, None, None
        
    def configure_units(self):
        """Configure all channels to use consistent units."""
        # Set laser source to dBm
        self._write("SOUR0:POW:UNIT 0")  # 0 = dBm
        
        # Set all detector channels to dBm
        self._write("SENS1:CHAN1:POW:UNIT 0")  # 0 = dBm
        self._write("SENS1:CHAN2:POW:UNIT 0")  # 0 = dBm
        
        # Verify settings
        source_unit = self._query("SOUR0:POW:UNIT?")
        det1_unit = self._query("SENS1:CHAN1:POW:UNIT?")
        det2_unit = self._query("SENS1:CHAN2:POW:UNIT?")
        
        logging.info(f"Units configured - Source: {source_unit}, Det1: {det1_unit}, Det2: {det2_unit}")
    
    def parse_binary_block(self, raw_data):
        """
        Parse SCPI binary block format: #<H><Len><Block>
        where H = number of digits, Len = number of bytes, Block = data
        """
        try:
            if not raw_data.startswith(b'#'):
                raise ValueError("Not a valid binary block")
            logging.debug(f"raw dogging: {raw_data} \nis it the same?")
            # Get number of digits in length field
            num_digits = int(raw_data[1:2].decode())
            
            # Get length of data block, extract
            data_len = int(raw_data[2:2+num_digits].decode())
            binary_data = raw_data[2+num_digits:2+num_digits+data_len] # everything after header
            
            # Parse as 4-byte floats little endian
            float_data = struct.unpack(
                "<" + "f"*(len(binary_data)//4), binary_data 
            )
            float_data = np.array(float_data) 
            
            if float_data[0] > 0:
                # data is in watts
                float_data = 10*np.log10(float_data) + 30 
            return float_data
            
        except Exception as e:
            logging.error(f"Binary block parsing failed: {e}")
            return None
    
    
    def configure_and_start_lambda_sweep(self, start_nm, stop_nm, step_nm,
                                         laser_power_dbm=-10, avg_time_s=0.01):
        try:
            # Convert to meters for SCPI commands
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength = stop_nm * 1e-9
            self.step_size = str(step_nm) + "NM" 
            self.laser_power = laser_power_dbm
            self.averaging_time = avg_time_s

            # Calculate number of points
            self.num_points = int((stop_nm - start_nm) / step_nm) + 1
            self.step_width_nm = step_nm 

            # 1. Clear system and set power
            self._write("*CLS")
            self._write(f"SOUR0:POW {laser_power_dbm}")
            self._write("SOUR0:POW:STAT ON")
            
            # 2. Initial wavelength
            self._write(f"SOUR0:WAV {self.start_wavelength}")
            
            # 3. Configure sweep
            self._write("SOUR0:WAV:SWE:MODE CONT")
            self._write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            self._write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            self._write(f"SOUR0:WAV:SWE:STEP {self.step_width_nm}NM")
            self._write("SOUR0:WAV:SWE:REP ONEW")
            self._write("SOUR0:WAV:SWE:CYCL 1")
            
            # 4. Configure logging
            self._write("SENS1:FUNC 'POWer'")
            self._write(f"SENS1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")
            self._write("SENS1:FUNC:STAT LOGG,START")
            
            # 5. Start sweep
            self._write("SOUR0:WAV:SWE:STAT START")
            logging.info("Lambda sweep started.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to configure and start lambda sweep: {e}")
            err = self._query("SYST:ERR?")
            logging.error(f"Instrument error: {err}")
            return False
    
    
    def execute_lambda_scan(self):
        """
        Execute the complete lambda scan with data logging.
        """
        try: 
            # Monitor sweep progress
            sweep_complete = False
            flag = True
            scan_start_time = time.time()
            timeout = 300  # 5 minute timeout
            
            while not sweep_complete and (time.time() - scan_start_time) < timeout:
                # Check sweep status
                sweep_status = self._query("SOUR0:WAV:SWE:STAT?").strip()
                
                # Check logging function status
                func_status = self._query("SENS1:CHAN1:FUNC:STAT?").strip()
                
                if "0" in sweep_status:  # Sweep stopped
                    sweep_complete_in = True
                    if sweep_complete_in and flag:
                        flag = False
                        timeout = 300
                elif "COMPLETE" in func_status:
                    sweep_complete = True
                
                time.sleep(1.0)  # Check every second
            
            if time.time() - scan_start_time >= timeout:
                logging.error("Lambda scan timed out")
                return False
            
            logging.info("Lambda scan completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Lambda scan execution failed: {e}")
            error = self._query("SYST:ERR?")
            logging.error(f"System error: {error}")
            return False
    
    def retrieve_scan_data(self):
        """
        Retrieve logged data from a measurement, without stitching
        """
        try:
            logging.info("[NEW] Attempting to retrieve logged binary data...")
            time.sleep(1) # give some time to stop the logging

            # Try to get the logged data
            raw_data = self._query_binary_and_parse("SENS1:CHAN1:FUNC:RES?") # CORRECT DATAAAAAAAAAAAAAAAAAAAAA
            time.sleep(0.4) 
            rd2 = self._query_binary_and_parse("SENS1:CHAN2:FUNC:RES?")
            logging.debug(f"rawdata: {raw_data}\n s2: {rd2}")
            # time.sleep(0.4)

            # Parse the binary block
            power_data = raw_data # self.parse_binary_block(raw_data)
            pow_data = rd2  # self.parse_binary_block(rd2)

            if power_data is not None and len(power_data) > 0:
                # Calculate corresponding wavelengths
                wavelengths_nm = np.linspace(
                    self.start_wavelength * 1e9,
                    self.stop_wavelength * 1e9,
                    len(power_data)
                )
                return wavelengths_nm, power_data, pow_data
            else:
                logging.error("No valid power data retrieved from logging")
                return None, None, None
                
        except Exception as e:
            logging.error(f"Logged data retrieval failed: {e}")
            return None, None, None
        
    def cleanup_scan(self):
        """Clean up after scan - stop functions and turn off laser."""
        try:
            # Stop logging function
            self._write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
            
            # Stop sweep
            self._write("SOUR0:WAV:SWE:STAT STOP")
            
            # Turn off laser
            self._write("SOUR0:POW:STAT OFF")
            
            logging.info("Scan cleanup complete")
            
        except Exception as e:
            logging.error(f"Cleanup failed: {e}")
    
    def disconnect(self):
        """Safely disconnect from instrument."""
        try:
            if self.instrument:
                self.cleanup_scan()
                self.instrument.close()
                self.instrument = None
            if self.rm:
                self.rm.close()
                self.rm = None
            logging.info("Disconnected successfully")
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")

############# ZOMBIES##################
    #  def optical_sweep2(self, start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s=0.02):
    #     """Full sweep procedure"""
    #     # Pass lambda scan params
    #     self.configure_and_start_lambda_sweep(start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s)
        
    #     self.execute_lambda_scan()

    #     # Retrieve data
    #     # wavelengths, power_ch1, power_ch2 = self.retrieve_scan_data()
    #     wavelengths, power_ch1, power_ch2 = self.retrieve_scan_data_logged()
        
    #     # if wavelengths is not None:
    #     #     logging.debug("Data retrieved")
    #     #     logging.debug(f"   Points: {len(wavelengths)}")
    #     #     logging.debug(f"   Wavelengths: {wavelengths[0]:.1f} - {wavelengths[-1]:.1f} nm")
            
    #     #     # Check for valid data
    #     #     valid_ch1 = ~np.isnan(power_ch1) & (np.abs(power_ch1) < 1e10)
    #     #     valid_ch2 = ~np.isnan(power_ch2) & (np.abs(power_ch2) < 1e10)
            
    #     #     if np.any(valid_ch1):
    #     #         logging.debug(f"   Ch1 range: {np.min(power_ch1[valid_ch1]):.2f} - {np.max(power_ch1[valid_ch1]):.2f} dBm")
    #     #     else:
    #     #         logging.debug("   Ch1: No valid data")
                
    #     #     if np.any(valid_ch2):
    #     #         logging.debug(f"   Ch2 range: {np.min(power_ch2[valid_ch2]):.2f} - {np.max(power_ch2[valid_ch2]):.2f} dBm")
    #     #     else:
    #     #         logging.debug("   Ch2: No valid data")
            
    #     #     logging.debug("\nSample points:")
    #     #     for i in range(0, len(wavelengths), max(1, len(wavelengths)//3)):
    #     #         ch1_val = f"{power_ch1[i]:.2f}" if valid_ch1[i] else "INVALID"
    #     #         ch2_val = f"{power_ch2[i]:.2f}" if valid_ch2[i] else "INVALID"
    #     #         logging.debug(f"   {wavelengths[i]:.1f}nm: Ch1={ch1_val}dBm, Ch2={ch2_val}dBm")
                
    #     # else:
    #     #     logging.debug("Data retrieval failed")
    #     #     return None, None, None
        
    #     return wavelengths, power_ch1, power_ch2

    # def retrieve_scan_data_logged(self):
    #     """
    #     Try to retrieve logged data using binary block parsing with error handling.
    #     """
    #     try:
    #         logging.info("Attempting to retrieve logged binary data...")
            
    #         # Check if logging function completed successfully
    #         func_status = self._query("SENS1:CHAN1:FUNC:STAT?")
    #         logging.info(f"Function status before data retrieval: {func_status}")
    #         # logging.debug("Stopping logging...")
    #         # self._write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
    #         time.sleep(1) # give some time to stop the logging
    #         # Try to get the logged data
    #         raw_data = self._query_binary("SENS1:CHAN1:FUNC:RES?") # CORRECT DATAAAAAAAAAAAAAAAAAAAAA
    #         time.sleep(0.4) 
    #         rd2 = self._query_binary("SENS1:CHAN2:FUNC:RES?")
    #         logging.debug(f"rawdata: {raw_data}\n s2: {rd2}")
    #         time.sleep(0.4)

    #         # logging.debug("Stopping logging...")
    #         # self._write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
    #         # time.sleep(1) # give some time to stop the logging

    #         get_pt = self._query("SENSe1:CHANnel1:FUNCtion:PARameter:LOGGing?")
    #         pts = get_pt.split("+")[1].replace(",","")
    #         # logging.debug(f"PTS: {pts}")

    #         # Check if logging function completed successfully
    #         # func_status = self._query("SENS1:CHAN1:FUNC:STAT?")
    #         # logging.info(f"Function status before data retrieval: {func_status}")

    #         # get_block_ch1 = self._query_binary(f"SENS1:CHAN1:FUNC:RES:BLOCk? 0,{pts}")
            
    #         # get_block = self._query_binary("SENS1:CHAN1:FUNC:RES:MAXBlocksize?") # b'+204050\n' or 51,012 data points (floor(bytes/4))
    #         # logging.debug(f"\nblockdataraw : {get_block}")
    #         time.sleep(0.5)
    #         # get_block_ch2 =  self._query_binary(f"SENS1:CHAN2:FUNC:RES:BLOCk? 0,{pts}")
    #         # get_pt = self._query(":SENSe1:CHANnel1:FUNCtion:PARameter:LOGGing?")
    #         # pts = float(get_pt.split("+")[1].replace(",",""))
    #         # logging.debug(f"PTS: {pts}")

    #         # Parse the binary block
    #         power_data = self.parse_binary_block(raw_data)
    #         pow_data = self.parse_binary_block(rd2)

    #         logging.debug(f"pow1: {power_data}\n pow2: {pow_data}\n")
            
    #         if power_data is not None and len(power_data) > 0:
    #             # Calculate corresponding wavelengths
    #             wavelengths_nm = np.linspace(
    #                 self.start_wavelength * 1e9,
    #                 self.stop_wavelength * 1e9,
    #                 len(power_data)
    #             )
                
    #             logging.info(f"Retrieved {len(power_data)} logged data points")
    #             logging.info(f"Power data range: {np.min(power_data):.2f} to {np.max(power_data):.2f} dBm")
                
    #             return wavelengths_nm, power_data, pow_data
    #         else:
    #             logging.error("No valid power data retrieved from logging")
    #             return None, None, None
                
    #     except Exception as e:
    #         logging.error(f"Logged data retrieval failed: {e}")
    #         return None, None, None