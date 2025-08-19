#!/usr/bin/env python3
"""
Physical Hardware Test Suite for LDC
Cameron Basara, 2025

Simple tests that connect to actual LDC hardware to verify everything works.
Includes automatic restoration of default settings at the end.

REQUIREMENTS:
- LDC must be connected via VISA (GPIB-USB)
- Device must be powered on and responsive
- VISA drivers must be installed

Usage: python LDC/test/test_ldc_hardware.py
"""

import sys
import os
import time
import copy

# # Add parent directories to path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from LDC.ldc_controller import SrsLdc502
from LDC.ldc_manager import LDCManager
from LDC.config.ldc_config import LDCConfiguration
from LDC.hal.LDC_hal import LDCEvent, LDCEventType

class LDCHardwareTest:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
        self.original_config = None
        
    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
        
    def test_result(self, test_name, success, message=""):
        if success:
            self.passed += 1
            status = "✅ PASS"
        else:
            self.failed += 1
            status = "❌ FAIL"
            
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
            
        print(result)
        self.results.append((test_name, success, message))
        return success

    def backup_configuration(self, manager):
        """Backup current configuration for restoration"""
        self.log("📝 Backing up current configuration...")
        self.original_config = {
            'setpoint': manager.config.setpoint,
            'sensor_type': manager.config.sensor_type,
            'model_coeffs': copy.deepcopy(manager.config.model_coeffs),
            'pid_coeffs': copy.deepcopy(manager.config.pid_coeffs),
            'tec_status': manager.get_tec_status() if manager.is_connected() else False
        }
        self.log(f"✅ Configuration backed up: {self.original_config['setpoint']}°C setpoint")

    def restore_configuration(self, manager):
        """Restore original configuration"""
        if not self.original_config:
            self.log("⚠️  No configuration to restore")
            return False
            
        self.log("🔄 Restoring original configuration...")
        
        try:
            # Turn off TEC first for safety
            if manager.get_tec_status():
                manager.tec_off()
                time.sleep(1)
                self.log("✅ TEC turned off")
            
            # Restore temperature setpoint
            success = manager.set_temperature(self.original_config['setpoint'])
            if success:
                self.log(f"✅ Temperature setpoint restored to {self.original_config['setpoint']}°C")
            
            # Restore sensor coefficients
            success = manager.set_sensor_coefficients(self.original_config['model_coeffs'])
            if success:
                self.log("✅ Sensor coefficients restored")
            
            # Restore PID coefficients
            success = manager.set_pid_coefficients(self.original_config['pid_coeffs'])
            if success:
                self.log("✅ PID coefficients restored")
            
            # Restore TEC state if it was originally on
            if self.original_config['tec_status']:
                manager.tec_on()
                self.log("✅ TEC state restored")
            
            self.log("🎉 All settings restored to original values!")
            return True
            
        except Exception as e:
            self.log(f"❌ Error during restoration: {e}")
            return False

    def test_controller_connection(self):
        """Test connecting to LDC controller"""
        self.log("Testing LDC controller connection...")
        
        try:
            controller = SrsLdc502(
                visa_address="ASRL5::INSTR",
                sensor_type="1",
                model_coeffs=[1.204800e-3, 2.417000e-4, 1.482700e-7],
                pid_coeffs=[-1.669519, 0.2317650, 1.078678],
                temp_setpoint=25.0,
                debug=True
            )
            
            success = controller.connect()
            
            if success:
                controller.disconnect()
                return self.test_result("Controller Connection", True, "Connected successfully")
            else:
                return self.test_result("Controller Connection", False, "Failed to connect")
                
        except Exception as e:
            return self.test_result("Controller Connection", False, f"Exception: {e}")

    def test_device_identification(self):
        """Test device identification"""
        self.log("Testing device identification...")
        
        try:
            controller = SrsLdc502(
                visa_address="ASRL5::INSTR",
                sensor_type="1",
                model_coeffs=[1.204800e-3, 2.417000e-4, 1.482700e-7],
                pid_coeffs=[-1.669519, 0.2317650, 1.078678],
                temp_setpoint=25.0,
                debug=True
            )
            
            controller.connect()
            config = controller.get_config()
            controller.disconnect()
            
            if config and 'visa_address' in config:
                return self.test_result("Device Identification", True, f"Device type: {config.get('driver_type', 'unknown')}")
            else:
                return self.test_result("Device Identification", False, "Failed to get device info")
                
        except Exception as e:
            return self.test_result("Device Identification", False, f"Exception: {e}")

    def test_temperature_reading(self):
        """Test reading temperature"""
        self.log("Testing temperature reading...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    temp = manager.get_temperature()
                    
                    if temp is not None and isinstance(temp, float):
                        return self.test_result("Temperature Reading", True, f"Temperature: {temp:.2f}°C")
                    else:
                        return self.test_result("Temperature Reading", False, "Invalid temperature reading")
                else:
                    return self.test_result("Temperature Reading", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Temperature Reading", False, f"Exception: {e}")

    def test_tec_control(self):
        """Test TEC on/off control"""
        self.log("Testing TEC control...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Backup original state
                    original_state = manager.get_tec_status()
                    
                    # Test TEC off
                    success1 = manager.tec_off()
                    time.sleep(1)
                    status_off = manager.get_tec_status()
                    
                    # Test TEC on
                    success2 = manager.tec_on()
                    time.sleep(1)
                    status_on = manager.get_tec_status()
                    
                    # Restore original state
                    if original_state:
                        manager.tec_on()
                    else:
                        manager.tec_off()
                    
                    if success1 and success2 and not status_off and status_on:
                        return self.test_result("TEC Control", True, "TEC on/off working correctly")
                    else:
                        return self.test_result("TEC Control", False, f"TEC control failed: off={status_off}, on={status_on}")
                else:
                    return self.test_result("TEC Control", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("TEC Control", False, f"Exception: {e}")

    def test_temperature_setting(self):
        """Test setting temperature"""
        self.log("Testing temperature setting...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Backup original settings
                    self.backup_configuration(manager)
                    
                    # Test setting temperature
                    test_temp = 30.0
                    success = manager.set_temperature(test_temp)
                    
                    if success:
                        setpoint = manager.get_temperature_setpoint()
                        
                        # Restore original settings
                        self.restore_configuration(manager)
                        
                        if abs(setpoint - test_temp) < 0.1:
                            return self.test_result("Temperature Setting", True, f"Setpoint: {setpoint:.1f}°C")
                        else:
                            return self.test_result("Temperature Setting", False, f"Setpoint mismatch: {setpoint:.1f}°C")
                    else:
                        self.restore_configuration(manager)
                        return self.test_result("Temperature Setting", False, "Failed to set temperature")
                else:
                    return self.test_result("Temperature Setting", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Temperature Setting", False, f"Exception: {e}")

    def test_temperature_limits(self):
        """Test temperature safety limits"""
        self.log("Testing temperature safety limits...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Test high limit (should fail)
                    success_high = manager.set_temperature(80.0)
                    
                    # Test low limit (should fail)
                    success_low = manager.set_temperature(10.0)
                    
                    # Test valid temperature (should succeed)
                    success_valid = manager.set_temperature(25.0)
                    
                    if not success_high and not success_low and success_valid:
                        return self.test_result("Temperature Limits", True, "Safety limits working correctly")
                    else:
                        return self.test_result("Temperature Limits", False, f"Limits failed: high={success_high}, low={success_low}, valid={success_valid}")
                else:
                    return self.test_result("Temperature Limits", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Temperature Limits", False, f"Exception: {e}")

    def test_sensor_coefficients(self):
        """Test sensor coefficient configuration"""
        self.log("Testing sensor coefficient configuration...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Backup original settings
                    self.backup_configuration(manager)
                    
                    # Test setting new coefficients
                    test_coeffs = [2.0e-3, 3.0e-4, 2.0e-7]
                    success = manager.set_sensor_coefficients(test_coeffs)
                    
                    if success:
                        # Verify coefficients were set
                        if manager.config.model_coeffs == test_coeffs:
                            # Restore original settings
                            self.restore_configuration(manager)
                            return self.test_result("Sensor Coefficients", True, "Coefficients set correctly")
                        else:
                            self.restore_configuration(manager)
                            return self.test_result("Sensor Coefficients", False, "Coefficients not saved correctly")
                    else:
                        self.restore_configuration(manager)
                        return self.test_result("Sensor Coefficients", False, "Failed to set coefficients")
                else:
                    return self.test_result("Sensor Coefficients", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Sensor Coefficients", False, f"Exception: {e}")

    def test_pid_coefficients(self):
        """Test PID coefficient configuration"""
        self.log("Testing PID coefficient configuration...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Backup original settings
                    self.backup_configuration(manager)
                    
                    # Test setting new coefficients
                    test_coeffs = [-2.0, 0.5, 1.5]
                    success = manager.set_pid_coefficients(test_coeffs)
                    
                    if success:
                        # Verify coefficients were set
                        if manager.config.pid_coeffs == test_coeffs:
                            # Restore original settings
                            self.restore_configuration(manager)
                            return self.test_result("PID Coefficients", True, "PID coefficients set correctly")
                        else:
                            self.restore_configuration(manager)
                            return self.test_result("PID Coefficients", False, "PID coefficients not saved correctly")
                    else:
                        self.restore_configuration(manager)
                        return self.test_result("PID Coefficients", False, "Failed to set PID coefficients")
                else:
                    return self.test_result("PID Coefficients", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("PID Coefficients", False, f"Exception: {e}")

    def test_event_system(self):
        """Test event system with real hardware"""
        self.log("Testing event system...")
        
        events_received = []
        
        def event_callback(event: LDCEvent):
            events_received.append(event)
            self.log(f"Event: {event.event_type.value}")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                manager.add_event_callback(event_callback)
                
                if manager.initialize():
                    # Backup original settings
                    self.backup_configuration(manager)
                    
                    # Perform operations that should generate events
                    manager.tec_on()
                    time.sleep(0.5)
                    manager.set_temperature(28.0)
                    time.sleep(0.5)
                    manager.tec_off()
                    
                    # Restore original settings
                    self.restore_configuration(manager)
                    
                    # Check events
                    if len(events_received) >= 3:
                        event_types = [e.event_type for e in events_received]
                        return self.test_result("Event System", True, f"Received {len(events_received)} events")
                    else:
                        return self.test_result("Event System", False, f"Only received {len(events_received)} events")
                else:
                    return self.test_result("Event System", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Event System", False, f"Exception: {e}")

    def test_configuration_restoration(self):
        """Test full configuration restoration workflow"""
        self.log("Testing complete configuration restoration...")
        
        try:
            config = LDCConfiguration()
            
            with LDCManager(config, use_shared_memory=False, debug=True) as manager:
                if manager.initialize():
                    # Backup original settings
                    self.backup_configuration(manager)
                    original_setpoint = manager.config.setpoint
                    original_coeffs = copy.deepcopy(manager.config.model_coeffs)
                    
                    # Make multiple changes
                    manager.set_temperature(35.0)
                    manager.set_sensor_coefficients([3.0e-3, 4.0e-4, 3.0e-7])
                    manager.set_pid_coefficients([-3.0, 0.8, 2.0])
                    manager.tec_on()
                    
                    # Verify changes were made
                    if (manager.config.setpoint != original_setpoint and 
                        manager.config.model_coeffs != original_coeffs):
                        
                        # Restore all settings
                        restoration_success = self.restore_configuration(manager)
                        
                        # Verify restoration
                        if (restoration_success and 
                            manager.config.setpoint == original_setpoint and
                            manager.config.model_coeffs == original_coeffs):
                            return self.test_result("Configuration Restoration", True, "Full restoration successful")
                        else:
                            return self.test_result("Configuration Restoration", False, "Restoration verification failed")
                    else:
                        return self.test_result("Configuration Restoration", False, "Changes were not applied")
                else:
                    return self.test_result("Configuration Restoration", False, "Failed to initialize manager")
                    
        except Exception as e:
            return self.test_result("Configuration Restoration", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run all hardware tests"""
        print("🌡️  LDC Hardware Test Suite")
        print("=" * 60)
        print("⚠️  WARNING: This will control real LDC hardware!")
        print("⚠️  Ensure device is properly connected and powered")
        print("=" * 60)
        
        # Ask for confirmation
        try:
            response = input("\n🤔 Continue with hardware tests? (y/N): ")
            if response.lower() != 'y':
                print("❌ Tests cancelled by user")
                return False
        except KeyboardInterrupt:
            print("\n❌ Tests cancelled by user")
            return False
        
        print("\n🚀 Starting LDC hardware tests...\n")
        
        # Run tests in order
        self.test_controller_connection()
        self.test_device_identification()
        self.test_temperature_reading()
        self.test_tec_control()
        self.test_temperature_setting()
        self.test_temperature_limits()
        self.test_sensor_coefficients()
        self.test_pid_coefficients()
        self.test_event_system()
        self.test_configuration_restoration()
        
        # Print summary
        print("\n" + "=" * 60)
        print("LDC HARDWARE TEST RESULTS")
        print("=" * 60)
        
        for test_name, success, message in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if message and not success:
                print(f"     {message}")
        
        print("-" * 60)
        print(f"Total: {len(self.results)} | Passed: {self.passed} | Failed: {self.failed}")
        
        if self.failed == 0:
            print("🎉 All LDC hardware tests passed!")
            print("✅ LDC controller is working correctly")
            print("✅ LDC manager is working correctly")
            print("✅ Event system is working correctly")
            print("✅ Configuration restoration is working correctly")
            print("🔄 All settings have been restored to defaults")
            return True
        else:
            print(f"❌ {self.failed} test(s) failed")
            print("🔍 Check hardware connections and VISA drivers")
            return False

def main():
    """Main test runner"""
    test_suite = LDCHardwareTest()
    
    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())