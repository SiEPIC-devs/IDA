
import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Any
import json
from pathlib import Path

from NIR.nir_controller_practical import Agilent8163Controller
from NIR.hal.nir_hal import PowerUnit, LaserState, SweepState
from NIR.optical_sweeps_v2 import OpticalSweepManager, StitchedSweepResult

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class SweepTestResults:
    """Track comprehensive test results"""
    def __init__(self):
        self.tests = {}
        self.data_files = []
        self.plots = []
    
    def add_test(self, test_name: str, passed: bool, details: Dict[str, Any] = None):
        self.tests[test_name] = {
            'passed': passed,
            'details': details or {},
            'timestamp': time.time()
        }
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def save_summary(self, filename: str = "sweep_test_results.json"):
        """Save comprehensive test summary"""
        summary = {
            'total_tests': len(self.tests),
            'passed': sum(1 for t in self.tests.values() if t['passed']),
            'failed': sum(1 for t in self.tests.values() if not t['passed']),
            'tests': self.tests,
            'data_files': self.data_files,
            'plots': self.plots
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📊 Test Summary saved to {filename}")
        print(f"Total: {summary['total_tests']}, Passed: {summary['passed']}, Failed: {summary['failed']}")


class OpticalSweepTestSuite:
    """Comprehensive test suite for optical sweeps"""
    
    def __init__(self, controller: Agilent8163Controller):
        self.controller = controller
        self.sweep_manager = OpticalSweepManager(controller, max_points_per_segment=1000)  # Small for testing
        self.results = SweepTestResults()
    
    async def run_all_tests(self, test_level: str = "basic"):
        """
        Run comprehensive test suite
        
        test_level options:
        - "basic": Essential tests (5-10 minutes)
        - "standard": Standard validation (15-30 minutes)  
        - "comprehensive": Full validation (1-2 hours)
        """
        print(f"🚀 Starting {test_level.upper()} Optical Sweep Test Suite")
        print("=" * 60)
        
        try:
            # Connection and initialization
            await self._test_connection()
            
            # Data logging tests (critical)
            await self._test_basic_data_logging()
            await self._test_extended_data_logging()
            
            if test_level in ["standard", "comprehensive"]:
                await self._test_data_logging_edge_cases()
            
            # Basic sweep tests
            await self._test_simple_sweep()
            await self._test_sweep_parameters()
            
            if test_level in ["standard", "comprehensive"]:
                # Advanced sweep tests
                await self._test_stitched_sweep()
                await self._test_large_sweep()
                
                if test_level == "comprehensive":
                    # Stress tests
                    await self._test_sweep_accuracy()
                    await self._test_sweep_repeatability()
                    await self._test_performance_benchmarks()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.results.add_test("Test Suite Execution", False, {"error": str(e)})
        
        finally:
            await self._cleanup()
            self.results.save_summary()
    
    async def _test_connection(self):
        """Test basic connection and setup"""
        print("\n🔌 Testing Connection and Setup")
        print("-" * 40)
        
        try:
            # Test connection
            connected = self.controller.connect()
            self.results.add_test(
                "Controller Connection", 
                connected,
                {"connected": connected}
            )
            
            if not connected:
                raise RuntimeError("Cannot proceed without connection")
            
            # Test basic laser control
            wl_limits = self.controller.get_wavelength_limits()
            power_limits = self.controller.get_power_limits()
            
            self.results.add_test(
                "Instrument Capabilities", 
                True,
                {
                    "wavelength_range": f"{wl_limits[0]:.1f}-{wl_limits[1]:.1f} nm",
                    "power_range": f"{power_limits[0]:.1f}-{power_limits[1]:.1f} dBm"
                }
            )
            
            # Enable output for testing
            enabled = self.controller.enable_output(True)
            time.sleep(0.5)
            
            self.results.add_test(
                "Laser Output Enable",
                enabled,
                {"output_enabled": enabled}
            )
            
        except Exception as e:
            self.results.add_test("Connection Setup", False, {"error": str(e)})
            raise
    
    async def _test_basic_data_logging(self):
        """Test fundamental data logging capabilities"""
        print("\n📝 Testing Basic Data Logging")
        print("-" * 40)
        
        try:
            # Test 1: Start/stop logging
            samples = 10
            averaging_time = 50.0  # ms
            
            start_success = self.controller.start_logging(samples, averaging_time, channel=1)
            time.sleep(1.0)  # Let it collect some data
            stop_success = self.controller.stop_logging(channel=1)
            
            self.results.add_test(
                "Basic Logging Control",
                start_success and stop_success,
                {
                    "start_success": start_success,
                    "stop_success": stop_success,
                    "samples_requested": samples,
                    "averaging_time_ms": averaging_time
                }
            )
            
            # Test 2: Data retrieval
            logged_data = await self.controller.get_logged_data(channel=1)
            
            data_valid = (
                isinstance(logged_data, list) and
                len(logged_data) >= 0 and
                all(hasattr(reading, 'value') and hasattr(reading, 'unit') for reading in logged_data)
            )
            
            self.results.add_test(
                "Data Retrieval Format",
                data_valid,
                {
                    "data_points_retrieved": len(logged_data),
                    "expected_samples": samples,
                    "data_format_valid": data_valid
                }
            )
            
            # Test 3: Data quality
            if logged_data:
                power_values = [r.value for r in logged_data]
                power_range = max(power_values) - min(power_values)
                reasonable_values = all(-100 <= p <= 50 for p in power_values)
                
                self.results.add_test(
                    "Data Quality Check",
                    reasonable_values,
                    {
                        "power_range_db": f"{power_range:.2f}",
                        "min_power": f"{min(power_values):.2f}",
                        "max_power": f"{max(power_values):.2f}",
                        "reasonable_values": reasonable_values
                    }
                )
            
        except Exception as e:
            self.results.add_test("Basic Data Logging", False, {"error": str(e)})
    
    async def _test_extended_data_logging(self):
        """Test data logging with more samples"""
        print("\n📊 Testing Extended Data Logging")
        print("-" * 40)
        
        try:
            # Test larger dataset
            samples = 100
            averaging_time = 20.0  # ms
            
            start_time = time.time()
            
            self.controller.start_logging(samples, averaging_time, channel=1)
            
            # Wait for logging to complete
            expected_time = (samples * averaging_time) / 1000  # Convert to seconds
            await asyncio.sleep(expected_time + 2.0)  # Add buffer
            
            self.controller.stop_logging(channel=1)
            
            logged_data = await self.controller.get_logged_data(channel=1)
            actual_time = time.time() - start_time
            
            data_completeness = len(logged_data) >= samples * 0.8  # Allow 20% loss
            
            self.results.add_test(
                "Extended Logging Test",
                data_completeness,
                {
                    "samples_requested": samples,
                    "samples_retrieved": len(logged_data),
                    "completeness_percent": f"{100 * len(logged_data) / samples:.1f}%",
                    "logging_time_s": f"{actual_time:.2f}",
                    "expected_time_s": f"{expected_time:.2f}"
                }
            )
            
            # Save data for analysis
            if logged_data:
                data_file = f"extended_logging_test_{int(time.time())}.json"
                data_dict = {
                    'timestamp': time.time(),
                    'samples_requested': samples,
                    'samples_retrieved': len(logged_data),
                    'data': [{'value': r.value, 'unit': r.unit.value} for r in logged_data]
                }
                
                with open(data_file, 'w') as f:
                    json.dump(data_dict, f, indent=2)
                
                self.results.data_files.append(data_file)
            
        except Exception as e:
            self.results.add_test("Extended Data Logging", False, {"error": str(e)})
    
    async def _test_data_logging_edge_cases(self):
        """Test edge cases in data logging"""
        print("\n⚠️  Testing Data Logging Edge Cases")
        print("-" * 40)
        
        try:
            # Test 1: Very small dataset
            start_success = self.controller.start_logging(1, 100.0, channel=1)
            time.sleep(0.5)
            stop_success = self.controller.stop_logging(channel=1)
            single_data = await self.controller.get_logged_data(channel=1)
            
            self.results.add_test(
                "Single Sample Logging",
                len(single_data) >= 1,
                {"samples_retrieved": len(single_data)}
            )
            
            # Test 2: Very fast logging
            fast_start = self.controller.start_logging(10, 5.0, channel=1)  # 5ms averaging
            time.sleep(0.2)
            fast_stop = self.controller.stop_logging(channel=1)
            fast_data = await self.controller.get_logged_data(channel=1)
            
            self.results.add_test(
                "Fast Averaging Logging",
                len(fast_data) >= 5,  # At least half the samples
                {
                    "averaging_time_ms": 5.0,
                    "samples_retrieved": len(fast_data)
                }
            )
            
            # Test 3: Stop without start
            try:
                stop_without_start = self.controller.stop_logging(channel=1)
                self.results.add_test(
                    "Stop Without Start",
                    True,  # Should not crash
                    {"handled_gracefully": True}
                )
            except Exception:
                self.results.add_test(
                    "Stop Without Start",
                    False,
                    {"crashed": True}
                )
            
        except Exception as e:
            self.results.add_test("Data Logging Edge Cases", False, {"error": str(e)})
    
    async def _test_simple_sweep(self):
        """Test basic sweep functionality"""
        print("\n🌊 Testing Simple Sweep")
        print("-" * 40)
        
        try:
            # Configure a small sweep
            start_nm = 1550.0
            stop_nm = 1552.0  # 2nm range
            speed = 2.0  # nm/s
            
            # Set sweep parameters
            range_set = self.controller.set_sweep_range(start_nm, stop_nm)
            speed_set = self.controller.set_sweep_speed(speed)
            
            self.results.add_test(
                "Sweep Configuration",
                range_set and speed_set,
                {
                    "range_set": range_set,
                    "speed_set": speed_set,
                    "sweep_range": f"{start_nm}-{stop_nm} nm",
                    "sweep_speed": f"{speed} nm/s"
                }
            )
            
            # Test sweep start/stop
            sweep_started = self.controller.start_sweep()
            time.sleep(0.5)  # Brief sweep
            sweep_stopped = self.controller.stop_sweep()
            
            self.results.add_test(
                "Sweep Control",
                sweep_started and sweep_stopped,
                {
                    "start_success": sweep_started,
                    "stop_success": sweep_stopped
                }
            )
            
            # Test sweep state monitoring
            final_state = self.controller.get_sweep_state()
            
            self.results.add_test(
                "Sweep State Monitoring",
                final_state == SweepState.STOPPED,
                {
                    "final_state": final_state.name,
                    "expected_state": "STOPPED"
                }
            )
            
        except Exception as e:
            self.results.add_test("Simple Sweep", False, {"error": str(e)})
    
    async def _test_sweep_parameters(self):
        """Test sweep parameter validation and limits"""
        print("\n⚙️  Testing Sweep Parameters")
        print("-" * 40)
        
        try:
            wl_min, wl_max = self.controller.get_wavelength_limits()
            
            # Test valid parameters
            valid_range = self.controller.set_sweep_range(wl_min + 1, wl_max - 1)
            valid_speed = self.controller.set_sweep_speed(1.0)
            
            self.results.add_test(
                "Valid Parameter Setting",
                valid_range and valid_speed,
                {
                    "range_valid": valid_range,
                    "speed_valid": valid_speed
                }
            )
            
            # Test edge cases
            edge_cases = []
            
            # Very small range
            small_range = self.controller.set_sweep_range(1550.0, 1550.1)  # 0.1nm
            edge_cases.append(("small_range", small_range))
            
            # Very slow speed
            slow_speed = self.controller.set_sweep_speed(0.1)  # 0.1 nm/s
            edge_cases.append(("slow_speed", slow_speed))
            
            # Very fast speed
            fast_speed = self.controller.set_sweep_speed(10.0)  # 10 nm/s
            edge_cases.append(("fast_speed", fast_speed))
            
            edge_case_results = {name: result for name, result in edge_cases}
            
            self.results.add_test(
                "Sweep Parameter Edge Cases",
                all(result for _, result in edge_cases),
                edge_case_results
            )
            
        except Exception as e:
            self.results.add_test("Sweep Parameters", False, {"error": str(e)})
    
    async def _test_stitched_sweep(self):
        """Test stitched sweep functionality"""
        print("\n🧩 Testing Stitched Sweep")
        print("-" * 40)
        
        try:
            # Configure a sweep that will require stitching
            start_nm = 1548.0
            stop_nm = 1552.0  # 4nm range
            speed = 2.0  # nm/s
            
            start_time = time.time()
            
            result = await self.sweep_manager.stitched_power_sweep(
                start_nm=start_nm,
                stop_nm=stop_nm,
                speed_nm_per_s=speed,
                detector_channel=1,
                averaging_time_ms=50.0,
                overlap_nm=0.2,
                use_internal_triggers=True
            )
            
            actual_time = time.time() - start_time
            
            # Validate stitched result
            sweep_successful = (
                result.num_points > 0 and
                len(result.wavelengths) == result.num_points and
                len(result.powers) == result.num_points
            )
            
            wavelength_range_correct = (
                abs(result.wavelengths[0] - start_nm) < 0.1 and
                abs(result.wavelengths[-1] - stop_nm) < 0.1
            )
            
            self.results.add_test(
                "Stitched Sweep Execution",
                sweep_successful and wavelength_range_correct,
                {
                    "total_points": result.num_points,
                    "segments": result.num_segments,
                    "sweep_time_s": f"{result.sweep_time:.2f}",
                    "actual_time_s": f"{actual_time:.2f}",
                    "wavelength_range_correct": wavelength_range_correct,
                    "power_range_db": f"{np.min(result.powers):.2f} to {np.max(result.powers):.2f}"
                }
            )
            
            # Save stitched sweep data
            if result.num_points > 0:
                sweep_file = f"stitched_sweep_test_{int(time.time())}.npz"
                np.savez(
                    sweep_file,
                    wavelengths=result.wavelengths,
                    powers=result.powers,
                    metadata=result.to_dict()
                )
                self.results.data_files.append(sweep_file)
                
                # Create plot
                plt.figure(figsize=(10, 6))
                plt.plot(result.wavelengths, result.powers, 'b-', linewidth=1)
                plt.xlabel('Wavelength (nm)')
                plt.ylabel('Power (dBm)')
                plt.title(f'Stitched Sweep Test ({result.num_segments} segments)')
                plt.grid(True, alpha=0.3)
                
                # Mark segment boundaries
                for boundary in result.segment_boundaries:
                    plt.axvline(result.wavelengths[boundary], color='r', linestyle='--', alpha=0.5)
                
                plot_file = f"stitched_sweep_plot_{int(time.time())}.png"
                plt.savefig(plot_file, dpi=150, bbox_inches='tight')
                plt.close()
                self.results.plots.append(plot_file)
            
        except Exception as e:
            self.results.add_test("Stitched Sweep", False, {"error": str(e)})
    
    async def _test_large_sweep(self):
        """Test large sweep that definitely requires stitching"""
        print("\n📈 Testing Large Sweep")
        print("-" * 40)
        
        try:
            # Large sweep: 10nm range with fine resolution
            start_nm = 1545.0
            stop_nm = 1555.0  # 10nm range
            speed = 0.5  # nm/s - slow for high resolution
            
            # This should require multiple segments
            start_time = time.time()
            
            result = await self.sweep_manager.stitched_power_sweep(
                start_nm=start_nm,
                stop_nm=stop_nm,
                speed_nm_per_s=speed,
                detector_channel=1,
                averaging_time_ms=25.0,  # 25ms for higher resolution
                overlap_nm=0.3
            )
            
            actual_time = time.time() - start_time
            
            # Validate large sweep
            large_sweep_successful = (
                result.num_points > 1000 and  # Should be large dataset
                result.num_segments > 1 and   # Should require stitching
                len(result.segment_boundaries) > 0
            )
            
            # Check data continuity (no gaps)
            wavelength_diffs = np.diff(result.wavelengths)
            max_gap = np.max(wavelength_diffs)
            avg_spacing = np.mean(wavelength_diffs)
            continuity_good = max_gap < avg_spacing * 3  # No gaps > 3x average
            
            self.results.add_test(
                "Large Sweep with Stitching",
                large_sweep_successful and continuity_good,
                {
                    "total_points": result.num_points,
                    "segments": result.num_segments,
                    "sweep_time_s": f"{result.sweep_time:.2f}",
                    "actual_time_s": f"{actual_time:.2f}",
                    "avg_wavelength_spacing_nm": f"{avg_spacing:.6f}",
                    "max_wavelength_gap_nm": f"{max_gap:.6f}",
                    "continuity_good": continuity_good
                }
            )
            
            # Save large sweep data
            if result.num_points > 0:
                large_sweep_file = f"large_sweep_test_{int(time.time())}.npz"
                np.savez(
                    large_sweep_file,
                    wavelengths=result.wavelengths,
                    powers=result.powers,
                    metadata=result.to_dict()
                )
                self.results.data_files.append(large_sweep_file)
            
        except Exception as e:
            self.results.add_test("Large Sweep", False, {"error": str(e)})
    
    async def _test_sweep_accuracy(self):
        """Test sweep accuracy and precision"""
        print("\n🎯 Testing Sweep Accuracy")
        print("-" * 40)
        
        try:
            # Precision test: Multiple small sweeps at different wavelengths
            test_wavelengths = [1549.0, 1550.0, 1551.0]
            sweep_width = 0.5  # nm
            
            accuracy_results = {}
            
            for center_wl in test_wavelengths:
                start_wl = center_wl - sweep_width/2
                stop_wl = center_wl + sweep_width/2
                
                result = await self.sweep_manager.stitched_power_sweep(
                    start_nm=start_wl,
                    stop_nm=stop_wl,
                    speed_nm_per_s=1.0,
                    detector_channel=1,
                    averaging_time_ms=100.0
                )
                
                if result.num_points > 0:
                    # Check wavelength accuracy
                    wl_start_error = abs(result.wavelengths[0] - start_wl)
                    wl_stop_error = abs(result.wavelengths[-1] - stop_wl)
                    wl_span = result.wavelengths[-1] - result.wavelengths[0]
                    span_error = abs(wl_span - sweep_width)
                    
                    accuracy_results[f"wl_{center_wl}"] = {
                        "start_error_nm": wl_start_error,
                        "stop_error_nm": wl_stop_error,
                        "span_error_nm": span_error,
                        "points": result.num_points
                    }
            
            # Overall accuracy assessment
            all_errors = []
            for wl_data in accuracy_results.values():
                all_errors.extend([wl_data["start_error_nm"], wl_data["stop_error_nm"]])
            
            max_error = max(all_errors) if all_errors else float('inf')
            accuracy_good = max_error < 0.01  # 10pm tolerance
            
            self.results.add_test(
                "Wavelength Accuracy",
                accuracy_good,
                {
                    "max_wavelength_error_nm": f"{max_error:.6f}",
                    "accuracy_good": accuracy_good,
                    "test_results": accuracy_results
                }
            )
            
        except Exception as e:
            self.results.add_test("Sweep Accuracy", False, {"error": str(e)})
    
    async def _test_sweep_repeatability(self):
        """Test sweep repeatability"""
        print("\n🔄 Testing Sweep Repeatability")
        print("-" * 40)
        
        try:
            # Perform identical sweeps multiple times
            start_nm = 1549.5
            stop_nm = 1550.5
            speed = 2.0
            num_repeats = 3
            
            repeat_results = []
            
            for i in range(num_repeats):
                result = await self.sweep_manager.stitched_power_sweep(
                    start_nm=start_nm,
                    stop_nm=stop_nm,
                    speed_nm_per_s=speed,
                    detector_channel=1,
                    averaging_time_ms=50.0
                )
                
                repeat_results.append(result)
                time.sleep(1.0)  # Brief pause between sweeps
            
            # Analyze repeatability
            if len(repeat_results) >= 2:
                # Compare power measurements at similar wavelengths
                ref_wavelengths = repeat_results[0].wavelengths
                ref_powers = repeat_results[0].powers
                
                power_variations = []
                
                for other_result in repeat_results[1:]:
                    # Interpolate other result to same wavelength grid
                    interp_powers = np.interp(ref_wavelengths, other_result.wavelengths, other_result.powers)
                    power_diff = np.abs(ref_powers - interp_powers)
                    power_variations.append(np.mean(power_diff))
                
                avg_variation = np.mean(power_variations)
                max_variation = np.max(power_variations)
                repeatability_good = max_variation < 0.1  # 0.1 dB tolerance
                
                self.results.add_test(
                    "Sweep Repeatability",
                    repeatability_good,
                    {
                        "num_repeats": num_repeats,
                        "avg_power_variation_db": f"{avg_variation:.4f}",
                        "max_power_variation_db": f"{max_variation:.4f}",
                        "repeatability_good": repeatability_good
                    }
                )
            
        except Exception as e:
            self.results.add_test("Sweep Repeatability", False, {"error": str(e)})
    
    async def _test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n⚡ Testing Performance Benchmarks")
        print("-" * 40)
        
        try:
            benchmarks = {}
            
            # Benchmark 1: Speed test
            start_time = time.time()
            speed_result = await self.sweep_manager.stitched_power_sweep(
                start_nm=1549.0,
                stop_nm=1551.0,  # 2nm
                speed_nm_per_s=5.0,   # Fast sweep
                detector_channel=1,
                averaging_time_ms=10.0  # Fast averaging
            )
            speed_test_time = time.time() - start_time
            
            benchmarks["speed_test"] = {
                "sweep_range_nm": 2.0,
                "total_time_s": speed_test_time,
                "points_collected": speed_result.num_points,
                "points_per_second": speed_result.num_points / speed_test_time if speed_test_time > 0 else 0
            }
            
            # Benchmark 2: Resolution test
            start_time = time.time()
            resolution_result = await self.sweep_manager.stitched_power_sweep(
                start_nm=1549.8,
                stop_nm=1550.2,  # 0.4nm
                speed_nm_per_s=0.2,   # Very slow
                detector_channel=1,
                averaging_time_ms=5.0   # Fast averaging for high point density
            )
            resolution_test_time = time.time() - start_time
            
            if resolution_result.num_points > 1:
                avg_spacing = np.mean(np.diff(resolution_result.wavelengths))
                benchmarks["resolution_test"] = {
                    "sweep_range_nm": 0.4,
                    "total_time_s": resolution_test_time,
                    "points_collected": resolution_result.num_points,
                    "avg_wavelength_spacing_pm": avg_spacing * 1000,  # Convert to pm
                    "resolution_pm": avg_spacing * 1000
                }
            
            self.results.add_test(
                "Performance Benchmarks",
                len(benchmarks) > 0,
                benchmarks
            )
            
        except Exception as e:
            self.results.add_test("Performance Benchmarks", False, {"error": str(e)})
    
    async def _cleanup(self):
        """Clean up after tests"""
        try:
            await self.controller.stop_sweep()
            await self.controller.stop_logging(channel=1)
            self.controller.enable_output(False)
            self.controller.disconnect()
            print("\n🧹 Test cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


# Main test execution
async def run_sweep_tests(test_level: str = "basic"):
    """
    Run the complete sweep test suite
    
    Args:
        test_level: "basic", "standard", or "comprehensive"
    """
    controller = Agilent8163Controller(
        com_port=5,  # Adjust for your setup
        laser_slot=0,
        detector_slots=[1],
        safety_password="1234"
    )
    
    test_suite = OpticalSweepTestSuite(controller)
    await test_suite.run_all_tests(test_level)


if __name__ == "__main__":
    import sys
    
    # Get test level from command line or default to basic
    test_level = sys.argv[1] if len(sys.argv) > 1 else "basic"
    
    if test_level not in ["basic", "standard", "comprehensive"]:
        print("Usage: python sweep_test_suite.py [basic|standard|comprehensive]")
        print("  basic: Essential tests (5-10 minutes)")
        print("  standard: Standard validation (15-30 minutes)")
        print("  comprehensive: Full validation (1-2 hours)")
        sys.exit(1)
    
    print(f"Starting {test_level} sweep tests...")
    asyncio.run(run_sweep_tests(test_level))
    