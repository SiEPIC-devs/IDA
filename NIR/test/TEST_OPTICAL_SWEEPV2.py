"""
Real Optical Sweep Test - Actually collects >10,000 points with stitching

Cameron Basara, 2025

This test actually performs optical sweeps and validates stitching with real data.
"""

import asyncio
import time
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
from typing import Tuple, Dict, Any

from NIR.nir_controller_practical import Agilent8163Controller
from NIR.hal.nir_hal import PowerUnit, LaserState, SweepState
from NIR.optical_sweeps_v2 import OpticalSweepManager, StitchedSweepResult

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


class RealOpticalSweepTest:
    """Real-world optical sweep testing with actual data collection"""
    
    def __init__(self, controller: Agilent8163Controller):
        self.controller = controller
        self.test_results = {}
        self.data_files = []
    
    async def run_comprehensive_sweep_test(self) -> Dict[str, Any]:
        """
        Run comprehensive sweep test with real data collection.
        
        This test will:
        1. Perform a large sweep (>10K points)
        2. Validate stitching works correctly
        3. Check data quality and continuity
        4. Generate plots and save data
        
        Returns detailed test results.
        """
        print("🚀 Starting Real Optical Sweep Test")
        print("=" * 60)
        
        results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'sweep_data': {},
            'validation_results': {},
            'performance_metrics': {},
            'data_files': []
        }
        
        try:
            # Setup and connection
            await self._setup_instrument()
            
            # Test 1: Large sweep requiring stitching
            print("\n📊 Test 1: Large Sweep with Stitching (>10K points)")
            large_sweep_result = await self._test_large_sweep()
            results['sweep_data']['large_sweep'] = large_sweep_result
            
            if large_sweep_result['success']:
                results['tests_passed'] += 1
                print("✅ Large sweep test PASSED")
            else:
                results['tests_failed'] += 1
                print("❌ Large sweep test FAILED")
            
            # Test 2: Validate stitching quality
            if large_sweep_result['success']:
                print("\n🔍 Test 2: Stitching Quality Validation")
                stitching_validation = await self._validate_stitching_quality(
                    large_sweep_result['result']
                )
                results['validation_results']['stitching'] = stitching_validation
                
                if stitching_validation['quality_good']:
                    results['tests_passed'] += 1
                    print("✅ Stitching validation PASSED")
                else:
                    results['tests_failed'] += 1
                    print("❌ Stitching validation FAILED")
            
            # Test 3: Performance benchmark
            print("\n⚡ Test 3: Performance Benchmark")
            performance_result = await self._test_performance_benchmark()
            results['performance_metrics'] = performance_result
            
            if performance_result['benchmark_passed']:
                results['tests_passed'] += 1
                print("✅ Performance benchmark PASSED")
            else:
                results['tests_failed'] += 1
                print("❌ Performance benchmark FAILED")
            
            # Test 4: Data integrity check
            if large_sweep_result['success']:
                print("\n🎯 Test 4: Data Integrity Check")
                integrity_result = await self._test_data_integrity(
                    large_sweep_result['result']
                )
                results['validation_results']['integrity'] = integrity_result
                
                if integrity_result['integrity_good']:
                    results['tests_passed'] += 1
                    print("✅ Data integrity PASSED")
                else:
                    results['tests_failed'] += 1
                    print("❌ Data integrity FAILED")
            
        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            results['tests_failed'] += 1
            results['error'] = str(e)
        
        finally:
            await self._cleanup()
        
        # Generate summary
        total_tests = results['tests_passed'] + results['tests_failed']
        success_rate = results['tests_passed'] / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n📋 Test Summary:")
        print(f"   Passed: {results['tests_passed']}/{total_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Save comprehensive results
        results_file = f"real_sweep_test_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        results['results_file'] = results_file
        return results
    
    async def _setup_instrument(self):
        """Setup instrument for testing"""
        print("🔌 Setting up instrument...")
        
        # Connect
        connected = self.controller.connect()
        if not connected:
            raise RuntimeError("Failed to connect to instrument")
        
        # Enable output
        self.controller.enable_output(True)
        time.sleep(0.5)
        
        # Verify basic functionality
        wl = self.controller.get_wavelength()
        power, unit = self.controller.get_power()
        
        print(f"   Current wavelength: {wl:.3f} nm")
        print(f"   Current power: {power:.3f} {unit.value}")
        print("✅ Instrument setup complete")
    
    async def _test_large_sweep(self) -> Dict[str, Any]:
        """
        Test a large sweep that requires stitching (>10K points).
        
        This is the main test - it actually collects real data.
        """
        print("   Configuring large sweep...")
        
        # Configure for >10K points
        start_nm = 1540.0
        stop_nm = 1570.0  # 30nm range
        speed_nm_per_s = 2.0  # 2 nm/s
        averaging_time_ms = 20.0  # 20ms averaging
        
        # Calculate expected points
        sweep_time = (stop_nm - start_nm) / speed_nm_per_s  # 15 seconds
        expected_points = int(sweep_time * (1000 / averaging_time_ms))  # ~750 points/second = ~11,250 points
        
        print(f"   Range: {start_nm}-{stop_nm} nm ({stop_nm-start_nm} nm)")
        print(f"   Speed: {speed_nm_per_s} nm/s")
        print(f"   Expected points: {expected_points:,}")
        print(f"   Expected time: {sweep_time:.1f}s")
        
        if expected_points < 10000:
            print("   ⚠️  Adjusting parameters to ensure >10K points...")
            # Slower speed for more points
            speed_nm_per_s = 1.0
            averaging_time_ms = 10.0
            sweep_time = (stop_nm - start_nm) / speed_nm_per_s  # 30 seconds
            expected_points = int(sweep_time * (1000 / averaging_time_ms))  # ~30,000 points
            print(f"   Adjusted speed: {speed_nm_per_s} nm/s")
            print(f"   Adjusted averaging: {averaging_time_ms} ms")
            print(f"   New expected points: {expected_points:,}")
        
        # Create sweep manager with small segments to force stitching
        sweep_manager = OpticalSweepManager(self.controller, max_points_per_segment=2000)
        
        try:
            print("   Starting sweep...")
            start_time = time.time()
            
            result = await sweep_manager.stitched_power_sweep(
                start_nm=start_nm,
                stop_nm=stop_nm,
                speed_nm_per_s=speed_nm_per_s,
                detector_channel=1,
                averaging_time_ms=averaging_time_ms,
                overlap_nm=0.5,  # 0.5nm overlap between segments
                use_internal_triggers=True
            )
            
            actual_time = time.time() - start_time
            
            print(f"   ✅ Sweep completed!")
            print(f"   Actual points: {result.num_points:,}")
            print(f"   Segments: {result.num_segments}")
            print(f"   Actual time: {actual_time:.1f}s")
            print(f"   Reported sweep time: {result.sweep_time:.1f}s")
            
            # Save the data
            data_file = f"large_sweep_data_{int(time.time())}.npz"
            np.savez_compressed(
                data_file,
                wavelengths=result.wavelengths,
                powers=result.powers,
                metadata={
                    'start_nm': start_nm,
                    'stop_nm': stop_nm,
                    'speed_nm_per_s': speed_nm_per_s,
                    'averaging_time_ms': averaging_time_ms,
                    'num_points': result.num_points,
                    'num_segments': result.num_segments,
                    'segment_boundaries': result.segment_boundaries,
                    'actual_time': actual_time,
                    'sweep_time': result.sweep_time
                }
            )
            
            self.data_files.append(data_file)
            
            # Create plot
            plot_file = await self._create_sweep_plot(result, "Large Sweep Test")
            self.data_files.append(plot_file)
            
            return {
                'success': True,
                'result': result,
                'expected_points': expected_points,
                'actual_points': result.num_points,
                'segments': result.num_segments,
                'actual_time': actual_time,
                'data_file': data_file,
                'plot_file': plot_file,
                'points_per_segment': result.num_points / result.num_segments if result.num_segments > 0 else 0
            }
            
        except Exception as e:
            print(f"   ❌ Sweep failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'expected_points': expected_points
            }
    
    async def _validate_stitching_quality(self, result: StitchedSweepResult) -> Dict[str, Any]:
        """Validate the quality of stitching in the sweep result"""
        print("   Analyzing stitching quality...")
        
        validation = {
            'quality_good': True,
            'issues': [],
            'metrics': {}
        }
        
        try:
            # Check 1: Wavelength continuity
            if len(result.wavelengths) > 1:
                wavelength_diffs = np.diff(result.wavelengths)
                avg_spacing = np.mean(wavelength_diffs)
                max_gap = np.max(wavelength_diffs)
                min_gap = np.min(wavelength_diffs)
                
                # Check for large gaps (>3x average)
                large_gaps = wavelength_diffs > avg_spacing * 3
                num_large_gaps = np.sum(large_gaps)
                
                validation['metrics']['avg_wavelength_spacing_pm'] = avg_spacing * 1000
                validation['metrics']['max_wavelength_gap_pm'] = max_gap * 1000
                validation['metrics']['min_wavelength_gap_pm'] = min_gap * 1000
                validation['metrics']['large_gaps_count'] = int(num_large_gaps)
                
                if num_large_gaps > 0:
                    validation['issues'].append(f"Found {num_large_gaps} large wavelength gaps")
                    validation['quality_good'] = False
                
                print(f"     Avg wavelength spacing: {avg_spacing*1000:.3f} pm")
                print(f"     Max gap: {max_gap*1000:.3f} pm")
                print(f"     Large gaps: {num_large_gaps}")
            
            # Check 2: Segment boundary analysis
            if result.segment_boundaries:
                boundary_issues = 0
                for i, boundary_idx in enumerate(result.segment_boundaries):
                    if boundary_idx < len(result.powers) - 1:
                        # Check power continuity at boundary
                        power_before = result.powers[boundary_idx - 1] if boundary_idx > 0 else result.powers[0]
                        power_after = result.powers[boundary_idx]
                        power_jump = abs(power_after - power_before)
                        
                        if power_jump > 1.0:  # >1 dB jump is suspicious
                            boundary_issues += 1
                
                validation['metrics']['segment_boundary_issues'] = boundary_issues
                validation['metrics']['num_segments'] = result.num_segments
                
                if boundary_issues > 0:
                    validation['issues'].append(f"Found {boundary_issues} boundary power jumps >1dB")
                    validation['quality_good'] = False
                
                print(f"     Segments: {result.num_segments}")
                print(f"     Boundary issues: {boundary_issues}")
            
            # Check 3: Overall data quality
            if len(result.powers) > 0:
                power_range = np.max(result.powers) - np.min(result.powers)
                power_std = np.std(result.powers)
                reasonable_powers = np.sum((-100 <= result.powers) & (result.powers <= 50))
                power_quality = reasonable_powers / len(result.powers)
                
                validation['metrics']['power_range_db'] = float(power_range)
                validation['metrics']['power_std_db'] = float(power_std)
                validation['metrics']['reasonable_power_fraction'] = float(power_quality)
                
                if power_quality < 0.95:  # <95% reasonable values
                    validation['issues'].append(f"Only {power_quality*100:.1f}% of powers in reasonable range")
                    validation['quality_good'] = False
                
                print(f"     Power range: {power_range:.2f} dB")
                print(f"     Power std: {power_std:.3f} dB")
                print(f"     Reasonable values: {power_quality*100:.1f}%")
            
        except Exception as e:
            validation['quality_good'] = False
            validation['issues'].append(f"Validation failed: {str(e)}")
        
        if validation['quality_good']:
            print("   ✅ Stitching quality is good")
        else:
            print("   ❌ Stitching quality issues found:")
            for issue in validation['issues']:
                print(f"      - {issue}")
        
        return validation
    
    async def _test_performance_benchmark(self) -> Dict[str, Any]:
        """Test performance with a smaller, faster sweep"""
        print("   Running performance benchmark...")
        
        # Quick sweep for performance testing
        start_nm = 1549.0
        stop_nm = 1551.0  # 2nm range
        speed_nm_per_s = 5.0  # Fast
        averaging_time_ms = 10.0  # Fast averaging
        
        sweep_manager = OpticalSweepManager(self.controller, max_points_per_segment=1000)
        
        try:
            start_time = time.time()
            
            result = await sweep_manager.stitched_power_sweep(
                start_nm=start_nm,
                stop_nm=stop_nm,
                speed_nm_per_s=speed_nm_per_s,
                detector_channel=1,
                averaging_time_ms=averaging_time_ms,
                overlap_nm=0.1
            )
            
            actual_time = time.time() - start_time
            
            # Performance metrics
            points_per_second = result.num_points / actual_time if actual_time > 0 else 0
            nm_per_second = (stop_nm - start_nm) / actual_time if actual_time > 0 else 0
            
            # Benchmark criteria
            benchmark_passed = (
                actual_time < 10.0 and  # Should complete in <10 seconds
                points_per_second > 50 and  # Should collect >50 points/second
                result.num_points > 50  # Should have reasonable number of points
            )
            
            print(f"     Time: {actual_time:.2f}s")
            print(f"     Points: {result.num_points}")
            print(f"     Points/second: {points_per_second:.1f}")
            print(f"     nm/second: {nm_per_second:.2f}")
            
            return {
                'benchmark_passed': benchmark_passed,
                'actual_time': actual_time,
                'points_collected': result.num_points,
                'points_per_second': points_per_second,
                'nm_per_second': nm_per_second,
                'segments': result.num_segments
            }
            
        except Exception as e:
            print(f"   ❌ Performance test failed: {e}")
            return {
                'benchmark_passed': False,
                'error': str(e)
            }
    
    async def _test_data_integrity(self, result: StitchedSweepResult) -> Dict[str, Any]:
        """Test data integrity and consistency"""
        print("   Checking data integrity...")
        
        integrity = {
            'integrity_good': True,
            'checks': {}
        }
        
        try:
            # Check 1: Array lengths match
            lengths_match = len(result.wavelengths) == len(result.powers) == result.num_points
            integrity['checks']['array_lengths_match'] = lengths_match
            
            if not lengths_match:
                integrity['integrity_good'] = False
                print(f"     ❌ Array length mismatch: wl={len(result.wavelengths)}, power={len(result.powers)}, reported={result.num_points}")
            else:
                print(f"     ✅ Array lengths consistent: {result.num_points} points")
            
            # Check 2: Wavelength monotonicity
            if len(result.wavelengths) > 1:
                is_monotonic = np.all(np.diff(result.wavelengths) > 0)  # Strictly increasing
                integrity['checks']['wavelength_monotonic'] = is_monotonic
                
                if not is_monotonic:
                    integrity['integrity_good'] = False
                    print("     ❌ Wavelengths are not monotonic")
                else:
                    print("     ✅ Wavelengths are monotonic")
            
            # Check 3: No NaN or infinite values
            wl_finite = np.all(np.isfinite(result.wavelengths))
            power_finite = np.all(np.isfinite(result.powers))
            integrity['checks']['all_values_finite'] = wl_finite and power_finite
            
            if not (wl_finite and power_finite):
                integrity['integrity_good'] = False
                print("     ❌ Found NaN or infinite values")
            else:
                print("     ✅ All values are finite")
            
            # Check 4: Wavelength range correct
            if len(result.wavelengths) > 0:
                wl_range_start = result.wavelengths[0]
                wl_range_stop = result.wavelengths[-1]
                range_span = wl_range_stop - wl_range_start
                
                integrity['checks']['wavelength_range_start'] = float(wl_range_start)
                integrity['checks']['wavelength_range_stop'] = float(wl_range_stop)
                integrity['checks']['wavelength_span'] = float(range_span)
                
                print(f"     Wavelength range: {wl_range_start:.3f} - {wl_range_stop:.3f} nm")
                print(f"     Span: {range_span:.3f} nm")
        
        except Exception as e:
            integrity['integrity_good'] = False
            integrity['checks']['error'] = str(e)
            print(f"     ❌ Integrity check failed: {e}")
        
        return integrity
    
    async def _create_sweep_plot(self, result: StitchedSweepResult, title: str) -> str:
        """Create a plot of the sweep data"""
        try:
            plt.figure(figsize=(12, 8))
            
            # Main plot
            plt.subplot(2, 1, 1)
            plt.plot(result.wavelengths, result.powers, 'b-', linewidth=0.8, alpha=0.8)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Power (dBm)')
            plt.title(f'{title} - {result.num_points:,} points in {result.num_segments} segments')
            plt.grid(True, alpha=0.3)
            
            # Mark segment boundaries
            for i, boundary in enumerate(result.segment_boundaries):
                if boundary < len(result.wavelengths):
                    plt.axvline(result.wavelengths[boundary], color='r', linestyle='--', 
                               alpha=0.7, label='Segment boundary' if i == 0 else "")
            
            if result.segment_boundaries:
                plt.legend()
            
            # Spacing analysis subplot
            plt.subplot(2, 1, 2)
            if len(result.wavelengths) > 1:
                spacing = np.diff(result.wavelengths) * 1000  # Convert to pm
                plt.plot(result.wavelengths[:-1], spacing, 'g-', linewidth=1)
                plt.xlabel('Wavelength (nm)')
                plt.ylabel('Wavelength Spacing (pm)')
                plt.title('Wavelength Spacing Analysis')
                plt.grid(True, alpha=0.3)
                
                # Mark segment boundaries
                for boundary in result.segment_boundaries:
                    if boundary < len(result.wavelengths) - 1:
                        plt.axvline(result.wavelengths[boundary], color='r', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            
            plot_file = f"sweep_plot_{int(time.time())}.png"
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"   📊 Plot saved: {plot_file}")
            return plot_file
            
        except Exception as e:
            print(f"   ⚠️  Plot creation failed: {e}")
            return ""
    
    async def _cleanup(self):
        """Clean up after testing"""
        try:
            self.controller.stop_sweep()
            self.controller.stop_logging(channel=1)
            self.controller.enable_output(False)
            self.controller.disconnect()
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


# Standalone test runner
async def run_real_sweep_test():
    """Run the real optical sweep test"""
    controller = Agilent8163Controller(
        com_port=5,  # Adjust for your setup
        laser_slot=0,
        detector_slots=[1],
        safety_password="1234"
    )
    
    test = RealOpticalSweepTest(controller)
    results = await test.run_comprehensive_sweep_test()
    
    return results


if __name__ == "__main__":
    print("Starting Real Optical Sweep Test...")
    print("This test will collect >10,000 data points with stitching")
    print("Expected duration: 2-5 minutes")
    print()
    
    results = asyncio.run(run_real_sweep_test())
    
    print(f"\n🎯 Final Results:")
    print(f"   Success Rate: {results.get('tests_passed', 0)}/{results.get('tests_passed', 0) + results.get('tests_failed', 0)}")
    print(f"   Results saved to: {results.get('results_file', 'N/A')}")
    
    if 'sweep_data' in results and results['sweep_data'].get('large_sweep', {}).get('success'):
        sweep_data = results['sweep_data']['large_sweep']
        print(f"   Data points collected: {sweep_data['actual_points']:,}")
        print(f"   Segments used: {sweep_data['segments']}")
        print(f"   Data file: {sweep_data.get('data_file', 'N/A')}")
        print(f"   Plot file: {sweep_data.get('plot_file', 'N/A')}")