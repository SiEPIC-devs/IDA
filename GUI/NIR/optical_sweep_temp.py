import logging
import pyvisa
import time
import numpy as np
import struct
from typing import Tuple, Optional, List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

class LambdaScanProtocol:
    def __init__(self, com_port=5):
        self.com_port = com_port
        self.rm = None
        self.instrument = None
        
        # Lambda scan parameters
        self.start_wavelength = None
        self.stop_wavelength = None
        self.step_size = None
        self.num_points = None
        self.laser_power = None
        self.averaging_time = None
        
    def connect(self):
        """Connect using proven working method."""
        try:
            self.rm = pyvisa.ResourceManager()
            visa_address = f"ASRL{self.com_port}::INSTR"
            
            self.instrument = self.rm.open_resource(
                visa_address,
                baud_rate=9600,
                timeout=10000,
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
            
            # Read the raw bytes
            raw_data = self.instrument.read_raw()
            return raw_data
            
        except Exception as e:
            logging.error(f"Binary query failed: {command}, Error: {e}")
            raise
    
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
    
    def check_optical_connections(self):
        """Check if laser and detectors are properly connected and working."""
        try:
            logging.info("Checking optical connections...")
            
            # Set a known wavelength
            test_wavelength = 1550e-9
            self._write(f"SOUR0:WAV {test_wavelength}")
            self._write(f"SENS1:CHAN1:POW:WAV {test_wavelength}")
            self._write(f"SENS1:CHAN2:POW:WAV {test_wavelength}")
            time.sleep(0.5)
            
            # Check laser status
            laser_state = self._query("SOUR0:POW:STAT?")
            laser_power_setting = self._query("SOUR0:POW?")
            laser_wavelength = float(self._query("SOUR0:WAV?")) * 1e9
            
            logging.info(f"Laser state: {laser_state}, Power setting: {laser_power_setting}dBm, Wavelength: {laser_wavelength:.1f}nm")
            
            if laser_state.strip() != "1":
                logging.warning("Laser is not turned on!")
                return False
            
            # Take measurements from both channels
            try:
                power1 = float(self._query("READ1:CHAN1:POW?"))
                power2 = float(self._query("READ1:CHAN2:POW?"))
                
                logging.info(f"Current readings - Ch1: {power1:.2f}dBm, Ch2: {power2:.2f}dBm")
                
                # Check for reasonable power levels (not exactly 0 or error values)
                if abs(power1) < 0.01:  # Very close to 0
                    logging.warning("Channel 1 reading very low power - check optical connection")
                
                if power2 > 1e10:  # Error value
                    logging.warning("Channel 2 showing error value - check optical connection")
                    return False
                
                if abs(power2) < 0.01:  # Very close to 0
                    logging.warning("Channel 2 reading very low power - check optical connection")
                
                return True
                
            except Exception as e:
                logging.error(f"Failed to read power: {e}")
                return False
            
        except Exception as e:
            logging.error(f"Connection check failed: {e}")
            return False
    
    def parse_binary_block(self, raw_data):
        """
        Parse SCPI binary block format: #<H><Len><Block>
        where H = number of digits, Len = number of bytes, Block = data
        """
        try:
            if not raw_data.startswith(b'#'):
                raise ValueError("Not a valid binary block")
            
            # Get number of digits in length field
            num_digits = int(chr(raw_data[1]))
            
            # Get length of data block
            length_str = raw_data[2:2+num_digits].decode('ascii')
            data_length = int(length_str)
            
            # Extract the actual data
            data_start = 2 + num_digits
            binary_data = raw_data[data_start:data_start + data_length]
            
            # Parse as 4-byte floats (Intel byte order = little endian)
            num_floats = data_length // 4
            float_data = struct.unpack(f'<{num_floats}f', binary_data)
            
            return np.array(float_data)
            
        except Exception as e:
            logging.error(f"Binary block parsing failed: {e}")
            return None
    
    def setup_lambda_scan(self, start_nm=1530, stop_nm=1570, step_nm=0.1, 
                         laser_power_dbm=-10, averaging_time_s=0.01):
        """
        Setup lambda scan parameters with enhanced diagnostics.
        """
        try:
            # Convert to meters for SCPI commands
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength = stop_nm * 1e-9
            self.step_size = step_nm * 1e-9
            self.laser_power = laser_power_dbm
            self.averaging_time = averaging_time_s
            
            # Calculate number of points
            self.num_points = int((self.stop_wavelength - self.start_wavelength) / self.step_size) + 1
            
            logging.info(f"Lambda scan setup: {start_nm}-{stop_nm}nm, {step_nm}nm steps, {self.num_points} points")
            
            # Clear any existing errors
            self._write("*CLS")
            
            # 1. Configure laser
            self._write(f"SOUR0:POW {self.laser_power}")
            self._write("SOUR0:POW:STAT ON")
            time.sleep(1.0)  # Allow more time for laser to settle
            
            # 2. Set initial wavelength and check
            self._write(f"SOUR0:WAV {self.start_wavelength}")
            time.sleep(0.5)
            
            # Verify laser is actually on and at correct settings
            actual_power = self._query("SOUR0:POW?")
            actual_wavelength = float(self._query("SOUR0:WAV?")) * 1e9
            laser_state = self._query("SOUR0:POW:STAT?")
            
            logging.info(f"Laser verification - State: {laser_state}, Power: {actual_power}dBm, Wavelength: {actual_wavelength:.1f}nm")
            
            # 3. Configure power meters
            self._write(f"SENS1:CHAN1:POW:WAV {self.start_wavelength}")
            self._write(f"SENS1:CHAN2:POW:WAV {self.start_wavelength}")
            
            # Enable auto-ranging and set averaging time
            self._write("SENS1:CHAN1:POW:RANG:AUTO ON")
            self._write(f"SENS1:CHAN1:POW:ATIM {self.averaging_time}")
            
            # 4. Check optical connections
            if not self.check_optical_connections():
                logging.warning("Optical connection check failed - continuing anyway")
            
            # 5. Configure sweep parameters
            self._write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            self._write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            self._write(f"SOUR0:WAV:SWE:STEP {self.step_size}")
            self._write("SOUR0:WAV:SWE:MODE STEP")
            self._write("SOUR0:WAV:SWE:REP ONEW")
            self._write("SOUR0:WAV:SWE:CYCL 1")
            
            # 6. Configure logging function
            self._write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
            self._write(f"SENS1:CHAN1:FUNC:PAR:LOGG {self.num_points},{self.averaging_time}")
            
            logging.info("Lambda scan setup complete")
            return True
            
        except Exception as e:
            logging.error(f"Lambda scan setup failed: {e}")
            error = self._query("SYST:ERR?")
            logging.error(f"System error: {error}")
            return False
    
    def configure_internal_triggering(self):
        """
        Configure internal triggering for coordinated sweep.
        Based on manual page 157-158 trigger configuration.
        """
        try:
            # Configure trigger system for default coordination
            self._write("TRIG:CONF DEF")  # Default trigger configuration
            
            # Configure laser to generate trigger on step finished
            self._write("TRIG0:OUTP STF")  # Step finished trigger output
            
            # Configure power meter to respond to triggers (master channel only)
            self._write("TRIG1:CHAN1:INP SME")      # Single measurement on trigger
            self._write("TRIG1:CHAN1:INP:REAR ON")  # Enable re-arming
            
            # Configure power meter to generate trigger when measurement complete
            self._write("TRIG1:CHAN1:OUTP AVG")     # Trigger when averaging complete
            self._write("TRIG1:CHAN1:OUTP:REAR ON") # Enable output re-arming
            
            logging.info("Internal triggering configured")
            return True
            
        except Exception as e:
            logging.error(f"Trigger configuration failed: {e}")
            error = self._query("SYST:ERR?")
            logging.error(f"System error: {error}")
            return False
    
    def execute_lambda_scan(self):
        """
        Execute the complete lambda scan with data logging.
        """
        try:
            logging.info("Starting lambda scan execution...")
            
            # Start logging function on master channel
            self._write("SENS1:CHAN1:FUNC:STAT LOGG,START")
            time.sleep(0.2)
            
            # Start the sweep
            self._write("SOUR0:WAV:SWE:STAT START")
            
            # Monitor sweep progress
            sweep_complete = False
            scan_start_time = time.time()
            timeout = 300  # 5 minute timeout
            
            while not sweep_complete and (time.time() - scan_start_time) < timeout:
                # Check sweep status
                sweep_status = self._query("SOUR0:WAV:SWE:STAT?").strip()
                
                # Check logging function status
                func_status = self._query("SENS1:CHAN1:FUNC:STAT?").strip()
                
                logging.info(f"Sweep status: {sweep_status}, Function status: {func_status}")
                
                if "0" in sweep_status:  # Sweep stopped
                    sweep_complete = True
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
    
    def retrieve_scan_data_logged(self):
        """
        Try to retrieve logged data using binary block parsing with error handling.
        """
        try:
            logging.info("Attempting to retrieve logged binary data...")
            
            # Check if logging function completed successfully
            func_status = self._query("SENS1:CHAN1:FUNC:STAT?")
            logging.info(f"Function status before data retrieval: {func_status}")
            
            # Try to get the logged data
            raw_data = self._query_binary("SENS1:CHAN1:FUNC:RES?")
            
            # Parse the binary block
            power_data = self.parse_binary_block(raw_data)
            
            if power_data is not None and len(power_data) > 0:
                # Calculate corresponding wavelengths
                wavelengths_nm = np.linspace(
                    self.start_wavelength * 1e9,
                    self.stop_wavelength * 1e9,
                    len(power_data)
                )
                
                logging.info(f"Retrieved {len(power_data)} logged data points")
                logging.info(f"Power data range: {np.min(power_data):.2f} to {np.max(power_data):.2f} dBm")
                
                return wavelengths_nm, power_data, None
            else:
                logging.error("No valid power data retrieved from logging")
                return None, None, None
                
        except Exception as e:
            logging.error(f"Logged data retrieval failed: {e}")
            return None, None, None
    
    def retrieve_scan_data_alternative(self):
        """
        Alternative data retrieval method - step through sweep manually.
        This is more reliable for the initial test.
        """
        try:
            logging.info("Retrieving scan data using manual sweep method...")
            
            # Calculate wavelength array
            wavelengths_nm = np.linspace(
                self.start_wavelength * 1e9,
                self.stop_wavelength * 1e9,
                self.num_points
            )
            
            power_ch1 = []
            power_ch2 = []
            
            # Set to start wavelength
            self._write(f"SOUR0:WAV {self.start_wavelength}")
            time.sleep(0.5)  # Allow settling
            
            # Step through each wavelength
            for i, wavelength_nm in enumerate(wavelengths_nm):
                wavelength_m = wavelength_nm * 1e-9
                
                # Set wavelength
                self._write(f"SOUR0:WAV {wavelength_m}")
                time.sleep(0.2)  # Allow settling
                
                # Update detector wavelengths to match
                self._write(f"SENS1:CHAN1:POW:WAV {wavelength_m}")
                self._write(f"SENS1:CHAN2:POW:WAV {wavelength_m}")
                time.sleep(0.1)
                
                # Take measurements
                try:
                    p1 = float(self._query("READ1:CHAN1:POW?"))
                    p2 = float(self._query("READ1:CHAN2:POW?"))
                    
                    power_ch1.append(p1)
                    power_ch2.append(p2)
                    
                    if i % 2 == 0:  # Progress update every 2 points
                        logging.info(f"Point {i+1}/{self.num_points}: {wavelength_nm:.1f}nm, Ch1: {p1:.2f}dBm, Ch2: {p2:.2f}dBm")
                        
                except Exception as e:
                    logging.warning(f"Measurement failed at {wavelength_nm:.1f}nm: {e}")
                    power_ch1.append(np.nan)
                    power_ch2.append(np.nan)
            
            logging.info(f"Retrieved {len(power_ch1)} data points using manual method")
            return wavelengths_nm, np.array(power_ch1), np.array(power_ch2)
            
        except Exception as e:
            logging.error(f"Alternative data retrieval failed: {e}")
            return None, None, None
    
    def retrieve_scan_data(self):
        """
        Retrieve measurement data with improved error handling.
        """
        logging.info("Retrieving scan data...")
        
        # First try to get the logged data
        wavelengths, power_ch1, power_ch2 = self.retrieve_scan_data_logged()
        
        if wavelengths is not None:
            logging.info("Successfully retrieved logged data from master channel")
            
            # Get slave channel data more carefully
            try:
                logging.info("Getting slave channel data...")
                power_ch2 = []
                
                for i, wavelength_nm in enumerate(wavelengths):
                    wavelength_m = wavelength_nm * 1e-9
                    
                    # Set laser wavelength
                    self._write(f"SOUR0:WAV {wavelength_m}")
                    
                    # Set detector wavelength
                    self._write(f"SENS1:CHAN2:POW:WAV {wavelength_m}")
                    time.sleep(0.1)
                    
                    try:
                        # Use READ instead of FETCH to ensure fresh measurement
                        p2_str = self._query("READ1:CHAN2:POW?")
                        p2 = float(p2_str)
                        
                        # Check for error values
                        if abs(p2) > 1e10:  # Likely an error value
                            logging.warning(f"Error value detected at {wavelength_nm:.1f}nm: {p2}")
                            p2 = np.nan
                            
                        power_ch2.append(p2)
                        
                        if i % 3 == 0:  # Progress every 3 points
                            logging.info(f"Ch2 point {i+1}/{len(wavelengths)}: {wavelength_nm:.1f}nm = {p2:.2f}dBm")
                            
                    except Exception as e:
                        logging.warning(f"Failed to read Ch2 at {wavelength_nm:.1f}nm: {e}")
                        power_ch2.append(np.nan)
                
                power_ch2 = np.array(power_ch2)
                logging.info(f"Slave channel data range: {np.nanmin(power_ch2):.2f} to {np.nanmax(power_ch2):.2f} dBm")
                
            except Exception as e:
                logging.error(f"Failed to get slave channel data: {e}")
                power_ch2 = np.full_like(power_ch1, np.nan)
                
            return wavelengths, power_ch1, power_ch2
        else:
            logging.info("Logged data failed, using manual sweep method")
            return self.retrieve_scan_data_alternative()
    
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


# def test_lambda_scan_with_diagnostics():
#     """Test the lambda scan with enhanced diagnostics"""
#     print("=" * 60)
#     print("LAMBDA SCAN WITH DIAGNOSTICS")
#     print("=" * 60)
    
#     scanner = LambdaScanProtocol(com_port=5)  # Adjust your COM port
    
#     try:
#         # Connect
#         print("Step 1: Connecting...")
#         if not scanner.connect():
#             print("❌ Connection failed")
#             return False
#         print("✅ Connected")
        
#         # Setup with smaller range for testing
#         print("\nStep 2: Setup (with diagnostics)...")
#         if scanner.setup_lambda_scan(
#             start_nm=1530, 
#             stop_nm=1535,
#             step_nm=1.0,  # Even larger steps for testing
#             laser_power_dbm=-5,  # Higher power for better signal
#             averaging_time_s=0.02
#         ):
#             print("✅ Setup complete")
#         else:
#             print("❌ Setup failed")
#             return False
        
#         # Configure triggering
#         print("\nStep 3: Configure triggering...")
#         if scanner.configure_internal_triggering():
#             print("✅ Triggering configured")
#         else:
#             print("❌ Triggering failed")
#             return False
        
#         # Execute scan
#         print("\nStep 4: Execute scan...")
#         if scanner.execute_lambda_scan():
#             print("✅ Scan executed")
#         else:
#             print("❌ Scan failed")
#             return False
        
#         # Retrieve data
#         print("\nStep 5: Retrieve data...")
#         wavelengths, power_ch1, power_ch2 = scanner.retrieve_scan_data()
        
#         if wavelengths is not None:
#             print("✅ Data retrieved")
#             print(f"   Points: {len(wavelengths)}")
#             print(f"   Wavelengths: {wavelengths[0]:.1f} - {wavelengths[-1]:.1f} nm")
            
#             # Check for valid data
#             valid_ch1 = ~np.isnan(power_ch1) & (np.abs(power_ch1) < 1e10)
#             valid_ch2 = ~np.isnan(power_ch2) & (np.abs(power_ch2) < 1e10)
            
#             if np.any(valid_ch1):
#                 print(f"   Ch1 range: {np.min(power_ch1[valid_ch1]):.2f} - {np.max(power_ch1[valid_ch1]):.2f} dBm")
#             else:
#                 print("   Ch1: No valid data")
                
#             if np.any(valid_ch2):
#                 print(f"   Ch2 range: {np.min(power_ch2[valid_ch2]):.2f} - {np.max(power_ch2[valid_ch2]):.2f} dBm")
#             else:
#                 print("   Ch2: No valid data")
            
#             print("\nSample points:")
#             for i in range(0, len(wavelengths), max(1, len(wavelengths)//3)):
#                 ch1_val = f"{power_ch1[i]:.2f}" if valid_ch1[i] else "INVALID"
#                 ch2_val = f"{power_ch2[i]:.2f}" if valid_ch2[i] else "INVALID"
#                 print(f"   {wavelengths[i]:.1f}nm: Ch1={ch1_val}dBm, Ch2={ch2_val}dBm")
                
#         else:
#             print("❌ Data retrieval failed")
#             return False
        
#         print("\n✅ LAMBDA SCAN TEST COMPLETED!")
#         return True
        
#     except Exception as e:
#         print(f"❌ Test failed: {e}")
#         return False
#     finally:
#         scanner.disconnect()


# if __name__ == "__main__":
#     test_lambda_scan_with_diagnostics()