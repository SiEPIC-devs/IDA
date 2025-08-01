import asyncio
import time
from NIR.nir_controller_practical import Agilent8163Controller
from NIR.hal.nir_hal import PowerUnit, LaserState, SweepState, WavelengthRange

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, test_name):
        self.passed += 1
        print(f"✅ {test_name}")
    
    def fail_test(self, test_name, error=None):
        self.failed += 1
        error_msg = f" - {error}" if error else ""
        print(f"❌ {test_name}{error_msg}")
        if error:
            self.errors.append(f"{test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.errors:
            print(f"\nErrors encountered:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")

async def test_connection(controller, results):
    """Test connection and disconnection"""
    print("\n🔌 Testing Connection Management")
    print("-" * 40)
    
    try:
        # Test connection
        conn_success = controller.connect()
        if conn_success and controller._is_connected:
            results.pass_test("Connection establishment")
        else:
            results.fail_test("Connection establishment", "Failed to connect")
            return False
        
        # Test disconnection
        disconn_success = controller.disconnect()
        if disconn_success and not controller._is_connected:
            results.pass_test("Disconnection")
        else:
            results.fail_test("Disconnection", "Failed to disconnect properly")
        
        # Reconnect for other tests
        if controller.connect():
            results.pass_test("Reconnection for testing")
            return True
        else:
            results.fail_test("Reconnection for testing")
            return False
            
    except Exception as e:
        results.fail_test("Connection management", str(e))
        return False

async def test_wavelength_operations(controller, results):
    """Test wavelength-related operations"""
    print("\n📡 Testing Wavelength Operations")
    print("-" * 40)
    
    try:
        # Test wavelength limits
        try:
            min_wl, max_wl = controller.get_wavelength_limits()
            if isinstance(min_wl, float) and isinstance(max_wl, float) and min_wl < max_wl:
                results.pass_test(f"Get wavelength limits: {min_wl}nm - {max_wl}nm")
            else:
                results.fail_test("Get wavelength limits", "Invalid range returned")
        except Exception as e:
            results.fail_test("Get wavelength limits", str(e))
        
        # Test current wavelength reading
        try:
            current_wl = controller.get_wavelength()
            if isinstance(current_wl, float) and 1400 <= current_wl <= 1700:
                results.pass_test(f"Get current wavelength: {current_wl}nm")
            else:
                results.fail_test("Get current wavelength", f"Unexpected value: {current_wl}")
        except Exception as e:
            results.fail_test("Get current wavelength", str(e))
        
        # Test wavelength setting
        test_wavelengths = [1550.0, 1530.0, 1570.0]
        for wl in test_wavelengths:
            try:
                if controller.set_wavelength(wl):
                    time.sleep(0.5)  # Allow time for setting
                    actual_wl = controller.get_wavelength()
                    if abs(actual_wl - wl) < 0.1:  # Allow small tolerance
                        results.pass_test(f"Set wavelength to {wl}nm")
                    else:
                        results.fail_test(f"Set wavelength to {wl}nm", 
                                        f"Set {wl}nm but read {actual_wl}nm")
                else:
                    results.fail_test(f"Set wavelength to {wl}nm", "Method returned False")
            except Exception as e:
                results.fail_test(f"Set wavelength to {wl}nm", str(e))
                
    except Exception as e:
        results.fail_test("Wavelength operations", str(e))

async def test_power_operations(controller, results):
    """Test power-related operations"""
    print("\n⚡ Testing Power Operations")
    print("-" * 40)
    
    try:
        # Test power limits
        try:
            min_power, max_power = controller.get_power_limits()
            if isinstance(min_power, float) and isinstance(max_power, float) and min_power < max_power:
                results.pass_test(f"Get power limits: {min_power}dBm - {max_power}dBm")
            else:
                results.fail_test("Get power limits", "Invalid range returned")
        except Exception as e:
            results.fail_test("Get power limits", str(e))
        
        # Test current power reading
        try:
            current_power, unit = controller.get_power()
            if isinstance(current_power, float) and isinstance(unit, PowerUnit):
                results.pass_test(f"Get current power: {current_power} {unit.value}")
            else:
                results.fail_test("Get current power", "Invalid response format")
        except Exception as e:
            results.fail_test("Get current power", str(e))
        
        # Test power setting with different units
        test_powers = [
            (-10.0, PowerUnit.DBM),
            (-15.0, PowerUnit.DBM),
            (-5.0, PowerUnit.DBM)
        ]
        
        for power, unit in test_powers:
            try:
                if controller.set_power(power, unit):
                    time.sleep(0.5)  # Allow time for setting
                    actual_power, actual_unit = controller.get_power()
                    if abs(actual_power - power) < 0.5 and actual_unit == unit:
                        results.pass_test(f"Set power to {power} {unit.value}")
                    else:
                        results.fail_test(f"Set power to {power} {unit.value}", 
                                        f"Set {power} but read {actual_power}")
                else:
                    results.fail_test(f"Set power to {power} {unit.value}", "Method returned False")
            except Exception as e:
                results.fail_test(f"Set power to {power} {unit.value}", str(e))
                
    except Exception as e:
        results.fail_test("Power operations", str(e))

async def test_output_control(controller, results):
    """Test output enable/disable"""
    print("\n🔦 Testing Output Control")
    print("-" * 40)
    
    try:
        # Test output disable
        try:
            if controller.enable_output(False):
                time.sleep(0.5)
                state = controller.get_output_state()
                if not state:
                    results.pass_test("Disable laser output")
                else:
                    results.fail_test("Disable laser output", "Output still enabled")
            else:
                results.fail_test("Disable laser output", "Method returned False")
        except Exception as e:
            results.fail_test("Disable laser output", str(e))
        
        # Test output enable
        try:
            if controller.enable_output(True):
                time.sleep(0.5)
                state = controller.get_output_state()
                if state:
                    results.pass_test("Enable laser output")
                else:
                    results.fail_test("Enable laser output", "Output still disabled")
            else:
                results.fail_test("Enable laser output", "Method returned False")
        except Exception as e:
            results.fail_test("Enable laser output", str(e))
            
    except Exception as e:
        results.fail_test("Output control", str(e))

async def test_sweep_operations(controller, results):
    """Test sweep functionality"""
    print("\n🌊 Testing Sweep Operations")
    print("-" * 40)
    
    try:
        # Test sweep range setting
        try:
            start_wl, stop_wl = 1530.0, 1560.0
            if controller.set_sweep_range(start_wl, stop_wl):
                sweep_range = controller.get_sweep_range()
                if abs(sweep_range.start - start_wl) < 0.1 and abs(sweep_range.stop - stop_wl) < 0.1:
                    results.pass_test(f"Set sweep range: {start_wl}-{stop_wl}nm")
                else:
                    results.fail_test("Set sweep range", "Range not set correctly")
            else:
                results.fail_test("Set sweep range", "Method returned False")
        except Exception as e:
            results.fail_test("Set sweep range", str(e))
        
        # Test sweep speed
        try:
            test_speed = 2.0
            if controller.set_sweep_speed(test_speed):
                actual_speed = controller.get_sweep_speed()
                if abs(actual_speed - test_speed) < 0.1:
                    results.pass_test(f"Set sweep speed: {test_speed}nm/s")
                else:
                    results.fail_test("Set sweep speed", f"Set {test_speed} but read {actual_speed}")
            else:
                results.fail_test("Set sweep speed", "Method returned False")
        except Exception as e:
            results.fail_test("Set sweep speed", str(e))
        
        # Test sweep state operations
        try:
            # Start sweep
            if controller.start_sweep():
                time.sleep(1.0)  # Allow sweep to start
                sweep_state = controller.get_sweep_state()
                if sweep_state == SweepState.RUNNING:
                    results.pass_test("Start sweep")
                else:
                    results.fail_test("Start sweep", f"State is {sweep_state}")
            else:
                results.fail_test("Start sweep", "Method returned False")
            
            # Stop sweep
            if controller.stop_sweep():
                time.sleep(0.5)
                sweep_state = controller.get_sweep_state()
                if sweep_state == SweepState.STOPPED:
                    results.pass_test("Stop sweep")
                else:
                    results.fail_test("Stop sweep", f"State is {sweep_state}")
            else:
                results.fail_test("Stop sweep", "Method returned False")
                
        except Exception as e:
            results.fail_test("Sweep state control", str(e))
            
    except Exception as e:
        results.fail_test("Sweep operations", str(e))

async def test_detector_operations(controller, results):
    """Test detector/power measurement operations"""
    print("\n📊 Testing Detector Operations")
    print("-" * 40)
    
    try:
        # Test power reading
        try:
            power_reading = controller.read_power(channel=1)
            if hasattr(power_reading, 'value') and hasattr(power_reading, 'unit'):
                if isinstance(power_reading.value, float) and isinstance(power_reading.unit, PowerUnit):
                    results.pass_test(f"Read power: {power_reading.value} {power_reading.unit.value}")
                else:
                    results.fail_test("Read power", "Invalid power reading format")
            else:
                results.fail_test("Read power", "Invalid PowerReading object")
        except Exception as e:
            results.fail_test("Read power", str(e))
        
        # Test power unit setting
        try:
            if controller.set_power_unit(PowerUnit.DBM, channel=1):
                unit = controller.get_power_unit(channel=1)
                if unit == PowerUnit.DBM:
                    results.pass_test("Set power unit to dBm")
                else:
                    results.fail_test("Set power unit to dBm", f"Unit is {unit}")
            else:
                results.fail_test("Set power unit to dBm", "Method returned False")
        except Exception as e:
            results.fail_test("Set power unit", str(e))
        
        # Test autorange
        try:
            if controller.enable_autorange(True, channel=1):
                results.pass_test("Enable autorange")
            else:
                results.fail_test("Enable autorange", "Method returned False")
        except Exception as e:
            results.fail_test("Enable autorange", str(e))
        
        # Test power range operations
        try:
            range_dbm = controller.get_power_range(channel=1)
            if isinstance(range_dbm, float):
                results.pass_test(f"Get power range: {range_dbm} dBm")
            else:
                results.fail_test("Get power range", "Invalid range value")
        except Exception as e:
            results.fail_test("Get power range", str(e))
            
    except Exception as e:
        results.fail_test("Detector operations", str(e))

async def test_logging_operations(controller, results):
    """Test data logging functionality"""
    print("\n📝 Testing Data Logging")
    print("-" * 40)
    
    try:
        # Test start logging
        try:
            samples = 10
            averaging_time = 100.0  # ms
            if controller.start_logging(samples, averaging_time, channel=1):
                results.pass_test("Start logging")
                
                # Let it collect some data
                await asyncio.sleep(2.0)
                
                # Test stop logging
                if controller.stop_logging(channel=1):
                    results.pass_test("Stop logging")
                else:
                    results.fail_test("Stop logging", "Method returned False")
                    
            else:
                results.fail_test("Start logging", "Method returned False")
        except Exception as e:
            results.fail_test("Logging control", str(e))
        
        # Test get logged data
        try:
            logged_data = await controller.get_logged_data(channel=1)
            if isinstance(logged_data, list):
                results.pass_test(f"Get logged data: {len(logged_data)} samples")
                
                # Check data format if we have samples
                if logged_data:
                    sample = logged_data[0]
                    if hasattr(sample, 'value') and hasattr(sample, 'unit'):
                        results.pass_test("Logged data format validation")
                    else:
                        results.fail_test("Logged data format validation", "Invalid sample format")
            else:
                results.fail_test("Get logged data", "Invalid return type")
        except Exception as e:
            results.fail_test("Get logged data", str(e))
            
    except Exception as e:
        results.fail_test("Logging operations", str(e))

async def test_status_methods(controller, results):
    """Test status and state methods"""
    print("\n📋 Testing Status Methods")
    print("-" * 40)
    
    try:
        # Test laser state
        try:
            laser_state = controller.get_laser_state()
            if isinstance(laser_state, LaserState):
                results.pass_test(f"Get laser state: {laser_state.name}")
            else:
                results.fail_test("Get laser state", "Invalid state type")
        except Exception as e:
            results.fail_test("Get laser state", str(e))
        
        # We already tested wavelength and power limits in their respective sections
        
    except Exception as e:
        results.fail_test("Status methods", str(e))

async def test_edge_cases(controller, results):
    """Test edge cases and error conditions"""
    print("\n⚠️  Testing Edge Cases")
    print("-" * 40)
    
    try:
        # Test invalid wavelength
        try:
            # Try setting wavelength outside expected range
            if not controller.set_wavelength(2000.0):  # Way outside range
                results.pass_test("Reject invalid wavelength (2000nm)")
            else:
                results.fail_test("Reject invalid wavelength (2000nm)", "Accepted invalid value")
        except Exception as e:
            results.pass_test(f"Reject invalid wavelength (exception): {str(e)[:50]}")
        
        # Test invalid power
        try:
            if not controller.set_power(50.0, PowerUnit.DBM):  # Way too high
                results.pass_test("Reject invalid power (50dBm)")
            else:
                results.fail_test("Reject invalid power (50dBm)", "Accepted invalid value")
        except Exception as e:
            results.pass_test(f"Reject invalid power (exception): {str(e)[:50]}")
        
        # Test operations while disconnected
        controller.disconnect()
        try:
            wl = controller.get_wavelength()
            # Should return cached value, not fail
            results.pass_test("Handle get_wavelength while disconnected")
        except Exception as e:
            results.fail_test("Handle get_wavelength while disconnected", str(e))
        
        # Reconnect for cleanup
        controller.connect()
        
    except Exception as e:
        results.fail_test("Edge cases", str(e))

async def run_comprehensive_tests():
    """Run all test suites"""
    print("🚀 Starting Comprehensive Agilent8163Controller Test Suite")
    print("=" * 60)
    
    results = TestResults()
    controller = Agilent8163Controller(
        com_port=5,
        laser_slot=0,
        detector_slots=[1],
        safety_password="1234"
    )
    
    try:
        # Test connection first - if this fails, we can't do other tests
        if not await test_connection(controller, results):
            print("❌ Connection failed - stopping tests")
            return
        
        # Run all test suites
        await test_wavelength_operations(controller, results)
        await test_power_operations(controller, results)
        await test_output_control(controller, results)
        await test_sweep_operations(controller, results)
        await test_detector_operations(controller, results)
        await test_logging_operations(controller, results)
        await test_status_methods(controller, results)
        await test_edge_cases(controller, results)
        
    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        results.fail_test("Test suite execution", str(e))
        
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        try:
            if controller._is_connected:
                controller.enable_output(False)
                controller.stop_sweep()
                controller.disconnect()
            print("✓ Cleanup complete")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
        
        # Show results
        results.summary()

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())