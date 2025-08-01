"""
Optical Sweep Manager - Compliant with Hybrid Async/Sync Design

Cameron Basara, 2025

Follows the established pattern:
- Sync methods for fast operations (configuration, single reads)
- Async only for long operations (sweeps, large data collection)
- Uses asyncio.to_thread() for blocking operations in async context
"""

import asyncio
import time
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

from NIR.hal.nir_hal import LaserHAL, PowerReading, WavelengthRange, SweepState
from NIR.nir_controller_practical import Agilent8163Controller

import logging
logger = logging.getLogger(__name__)


@dataclass
class StitchedSweepResult:
    """Enhanced sweep result with stitching metadata"""
    wavelengths: np.ndarray  # nm
    powers: np.ndarray       # dBm  
    sweep_time: float        # seconds
    num_points: int
    num_segments: int = 1
    segment_boundaries: List[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easy export"""
        return {
            'wavelengths': self.wavelengths.tolist(),
            'powers': self.powers.tolist(),
            'sweep_time': self.sweep_time,
            'num_points': self.num_points,
            'num_segments': self.num_segments,
            'segment_boundaries': self.segment_boundaries
        }


class OpticalSweepManager:
    """
    Manager for complex optical sweeps with stitching.
    
    Follows hybrid async/sync design:
    - Configuration methods: SYNC (fast)
    - Sweep execution: ASYNC (long operations)
    - Data collection: ASYNC (potentially large datasets)
    """
    
    def __init__(self, laser: LaserHAL, max_points_per_segment: int = 10000):
        self.laser = laser
        self.max_points_per_segment = max_points_per_segment
        
    def should_use_stitching(self, start_nm: float, stop_nm: float, 
                           speed_nm_per_s: float, averaging_time_ms: float) -> bool:
        """SYNC: Quick calculation to determine if stitching is needed"""
        sweep_range_nm = abs(stop_nm - start_nm)
        sweep_time_s = sweep_range_nm / speed_nm_per_s
        points_per_second = 1000 / averaging_time_ms
        total_estimated_points = int(sweep_time_s * points_per_second)
        
        return total_estimated_points > self.max_points_per_segment
    
    def calculate_segments(self, start_nm: float, stop_nm: float, 
                          speed_nm_per_s: float, averaging_time_ms: float,
                          overlap_nm: float) -> List[Tuple[float, float]]:
        """SYNC: Calculate segment boundaries for stitched sweep"""
        # Calculate wavelength range per segment
        points_per_nm = (1000 / averaging_time_ms) / speed_nm_per_s
        nm_per_segment = self.max_points_per_segment / points_per_nm
        
        segments = []
        current_start = start_nm
        direction = 1 if stop_nm > start_nm else -1
        
        while (direction > 0 and current_start < stop_nm) or \
              (direction < 0 and current_start > stop_nm):
            # Calculate segment end
            segment_end = current_start + direction * nm_per_segment
            
            # Ensure we don't overshoot the final wavelength
            if direction > 0:
                segment_end = min(segment_end, stop_nm)
            else:
                segment_end = max(segment_end, stop_nm)
            
            segments.append((current_start, segment_end))
            
            # Next segment starts with overlap
            current_start = segment_end - direction * overlap_nm
        
        return segments
    
    # ASYNC: Long operations that benefit from async
    async def stitched_power_sweep(
        self,
        start_nm: float,
        stop_nm: float,
        speed_nm_per_s: float,
        detector_channel: int = 1,
        averaging_time_ms: float = 100.0,
        overlap_nm: float = 0.5,
        use_internal_triggers: bool = True
    ) -> StitchedSweepResult:
        """
        ASYNC: Perform a power sweep with automatic stitching for large datasets.
        
        This is async because it's a long operation that can take minutes.
        """
        logger.info(f"Starting stitched sweep: {start_nm}-{stop_nm}nm at {speed_nm_per_s}nm/s")
        
        # SYNC: Quick determination if stitching is needed
        needs_stitching = self.should_use_stitching(
            start_nm, stop_nm, speed_nm_per_s, averaging_time_ms
        )
        
        if not needs_stitching:
            # Single segment sweep
            logger.info("Single segment sweep - no stitching needed")
            result = await self._execute_single_segment(
                start_nm, stop_nm, speed_nm_per_s, 
                detector_channel, averaging_time_ms, 
                use_internal_triggers
            )
            return StitchedSweepResult(
                wavelengths=np.array(result['wavelengths']),
                powers=np.array(result['powers']),
                sweep_time=result['sweep_time'],
                num_points=result['num_points'],
                num_segments=1,
                segment_boundaries=[]
            )
        
        # Multi-segment sweep with stitching
        segments = self.calculate_segments(
            start_nm, stop_nm, speed_nm_per_s, 
            averaging_time_ms, overlap_nm
        )
        
        logger.info(f"Stitched sweep: {len(segments)} segments required")
        
        # Execute segments (async because it's a long operation)
        segment_results = []
        total_sweep_time = 0
        
        for i, (seg_start, seg_stop) in enumerate(segments):
            logger.info(f"Segment {i+1}/{len(segments)}: {seg_start:.1f}-{seg_stop:.1f}nm")
            
            result = await self._execute_single_segment(
                seg_start, seg_stop, speed_nm_per_s,
                detector_channel, averaging_time_ms,
                use_internal_triggers
            )
            
            segment_results.append(result)
            total_sweep_time += result['sweep_time']
            
            # Brief pause between segments
            if i < len(segments) - 1:
                await asyncio.sleep(0.5)
        
        # SYNC: Stitch segments together (data processing)
        stitched_result = await asyncio.to_thread(
            self._stitch_segments, segment_results, overlap_nm
        )
        stitched_result.sweep_time = total_sweep_time
        stitched_result.num_segments = len(segments)
        
        return stitched_result
    
    async def _execute_single_segment(
        self,
        start_nm: float,
        stop_nm: float,
        speed_nm_per_s: float,
        detector_channel: int,
        averaging_time_ms: float,
        use_internal_triggers: bool
    ) -> dict:
        """
        ASYNC: Execute a single segment sweep.
        
        Uses blocking sweep operations wrapped in asyncio.to_thread()
        """
        # Calculate parameters for this segment
        sweep_range_nm = abs(stop_nm - start_nm)
        sweep_time_s = sweep_range_nm / speed_nm_per_s
        points_per_second = 1000 / averaging_time_ms
        estimated_points = int(sweep_time_s * points_per_second)
        
        try:
            # SYNC configuration (fast operations)
            success = await asyncio.to_thread(self._configure_segment_sweep,
                start_nm, stop_nm, speed_nm_per_s, detector_channel, 
                averaging_time_ms, estimated_points, use_internal_triggers
            )
            
            if not success:
                raise RuntimeError("Failed to configure segment sweep")
            
            # ASYNC: Execute the actual sweep (long operation)
            sweep_result = await self._execute_sweep_and_collect_data(
                sweep_time_s, detector_channel, start_nm, stop_nm
            )
            
            return sweep_result
            
        except Exception as e:
            logger.error(f"Segment sweep failed: {e}")
            # Emergency cleanup (sync operations)
            await asyncio.to_thread(self._emergency_cleanup, detector_channel)
            raise
    
    def _configure_segment_sweep(self, start_nm: float, stop_nm: float, 
                               speed_nm_per_s: float, detector_channel: int,
                               averaging_time_ms: float, estimated_points: int,
                               use_internal_triggers: bool) -> bool:
        """
        SYNC: Configure all sweep parameters.
        
        This method contains all the fast configuration operations.
        """
        try:
            # Configure sweep parameters (all sync)
            self.laser.set_sweep_range(start_nm, stop_nm)
            self.laser.set_sweep_speed(speed_nm_per_s)
            
            # Configure internal triggering if requested
            if use_internal_triggers:
                self._setup_internal_triggers()
            
            # Start logging (sync operation)
            self.laser.start_logging(estimated_points, averaging_time_ms, detector_channel)
            
            return True
            
        except Exception as e:
            logger.error(f"Segment configuration failed: {e}")
            return False
    
    def _setup_internal_triggers(self):
        """SYNC: Setup internal trigger coordination (if supported)"""
        # This would configure internal triggers between laser and detector
        # Implementation depends on your specific instrument capabilities
        try:
            # Example configuration (adjust for your instrument):
            # self.laser._send_command("TRIG:CONF PASS", expect_response=False)
            # self.laser._send_command(f"TRIG{self.laser.laser_slot}:OUTP STF", expect_response=False)
            # for detector_slot in self.laser.detector_slots:
            #     self.laser._send_command(f"TRIG{detector_slot}:INP SWS", expect_response=False)
            pass
        except Exception as e:
            logger.warning(f"Internal trigger setup failed: {e}")
    
    async def _execute_sweep_and_collect_data(self, expected_sweep_time: float,
                                            detector_channel: int, start_nm: float, 
                                            stop_nm: float) -> dict:
        """
        ASYNC: Execute sweep and collect data.
        
        This is the long operation that benefits from async.
        """
        start_time = time.time()
        
        # Start sweep (sync operation in async context)
        await asyncio.to_thread(self.laser.start_sweep)
        
        # Wait for completion (this is the long operation)
        max_wait_time = expected_sweep_time + 10.0  # 10s buffer
        completed = await self._wait_for_sweep_completion(max_wait_time)
        
        if not completed:
            raise TimeoutError(f"Segment sweep timed out after {max_wait_time}s")
        
        # Stop logging and retrieve data (potentially large data transfer)
        await asyncio.to_thread(self.laser.stop_logging, detector_channel)
        
        # Get logged data (async because it can be large dataset)
        logged_data = await self.laser.get_logged_data(detector_channel)
        
        actual_sweep_time = time.time() - start_time
        
        # Extract wavelengths (sync data processing)
        wavelengths = self._extract_wavelengths(logged_data, start_nm, stop_nm)
        powers = [reading.value for reading in logged_data]
        
        return {
            'wavelengths': wavelengths,
            'powers': powers,
            'sweep_time': actual_sweep_time,
            'num_points': len(logged_data)
        }
    
    async def _wait_for_sweep_completion(self, timeout: float) -> bool:
        """
        ASYNC: Wait for sweep completion with periodic checking.
        
        Uses async sleep to avoid blocking.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check sweep state (sync operation)
            state = await asyncio.to_thread(self.laser.get_sweep_state)
            
            if state == SweepState.STOPPED:
                return True
            
            # Non-blocking sleep
            await asyncio.sleep(0.5)
        
        return False
    
    def _extract_wavelengths(self, logged_data: List[PowerReading], 
                           start_nm: float, stop_nm: float) -> List[float]:
        """SYNC: Extract or interpolate wavelengths from logged data"""
        # Check if wavelengths are included in the data
        if logged_data and logged_data[0].wavelength is not None:
            return [reading.wavelength for reading in logged_data]
        
        # Otherwise, interpolate based on sweep parameters
        num_points = len(logged_data)
        return np.linspace(start_nm, stop_nm, num_points).tolist()
    
    def _stitch_segments(self, segment_results: List[dict], 
                        overlap_nm: float) -> StitchedSweepResult:
        """
        SYNC: Stitch multiple sweep segments together.
        
        This is data processing - CPU intensive but not I/O bound.
        """
        if not segment_results:
            return StitchedSweepResult(
                wavelengths=np.array([]),
                powers=np.array([]),
                sweep_time=0,
                num_points=0
            )
        
        # Initialize with first segment
        all_wavelengths = np.array(segment_results[0]['wavelengths'])
        all_powers = np.array(segment_results[0]['powers'])
        segment_boundaries = []
        
        # Stitch remaining segments
        for i in range(1, len(segment_results)):
            seg_wavelengths = np.array(segment_results[i]['wavelengths'])
            seg_powers = np.array(segment_results[i]['powers'])
            
            # Find overlap region
            overlap_start_idx = self._find_overlap_start(
                all_wavelengths, seg_wavelengths, overlap_nm
            )
            
            if overlap_start_idx is not None:
                # Handle overlap region
                overlap_end_idx = len(all_wavelengths)
                overlap_wavelengths = all_wavelengths[overlap_start_idx:]
                
                # Find corresponding indices in new segment
                seg_overlap_indices = self._find_wavelength_indices(
                    seg_wavelengths, overlap_wavelengths
                )
                
                if seg_overlap_indices:
                    # Check power consistency in overlap
                    overlap_powers_prev = all_powers[overlap_start_idx:]
                    overlap_powers_new = seg_powers[seg_overlap_indices]
                    
                    # Log any significant discrepancies
                    power_diff = np.abs(overlap_powers_prev - overlap_powers_new)
                    if np.max(power_diff) > 0.5:  # 0.5 dB threshold
                        logger.warning(
                            f"Power discrepancy in overlap region: max {np.max(power_diff):.2f} dB"
                        )
                    
                    # Use weighted average in overlap region
                    weight = np.linspace(1, 0, len(overlap_powers_prev))
                    all_powers[overlap_start_idx:] = (
                        weight * overlap_powers_prev + 
                        (1 - weight) * overlap_powers_new
                    )
                
                # Append non-overlapping portion
                non_overlap_start = len(seg_overlap_indices) if seg_overlap_indices else 0
                all_wavelengths = np.concatenate([
                    all_wavelengths,
                    seg_wavelengths[non_overlap_start:]
                ])
                all_powers = np.concatenate([
                    all_powers,
                    seg_powers[non_overlap_start:]
                ])
                
                segment_boundaries.append(overlap_start_idx)
            else:
                # No overlap found, just concatenate
                logger.warning(f"No overlap found for segment {i}, concatenating directly")
                segment_boundaries.append(len(all_wavelengths))
                all_wavelengths = np.concatenate([all_wavelengths, seg_wavelengths])
                all_powers = np.concatenate([all_powers, seg_powers])
        
        return StitchedSweepResult(
            wavelengths=all_wavelengths,
            powers=all_powers,
            sweep_time=sum(r['sweep_time'] for r in segment_results),
            num_points=len(all_wavelengths),
            num_segments=len(segment_results),
            segment_boundaries=segment_boundaries
        )
    
    def _find_overlap_start(self, prev_wavelengths: np.ndarray, 
                           new_wavelengths: np.ndarray,
                           overlap_nm: float) -> Optional[int]:
        """SYNC: Find the start index of overlap region in previous segment"""
        if len(prev_wavelengths) == 0 or len(new_wavelengths) == 0:
            return None
            
        # Find where new segment starts relative to previous
        new_start = new_wavelengths[0]
        
        # Find closest wavelength in previous segment
        idx = np.searchsorted(prev_wavelengths, new_start)
        
        # Verify it's within expected overlap range
        if idx > 0 and idx < len(prev_wavelengths):
            actual_overlap = abs(prev_wavelengths[-1] - new_start)
            if actual_overlap <= overlap_nm * 1.5:  # Allow some tolerance
                return idx
                
        return None
    
    def _find_wavelength_indices(self, wavelengths: np.ndarray, 
                                target_wavelengths: np.ndarray) -> np.ndarray:
        """SYNC: Find indices in wavelengths array closest to target wavelengths"""
        indices = []
        for target in target_wavelengths:
            idx = np.searchsorted(wavelengths, target)
            if idx < len(wavelengths):
                indices.append(idx)
        return np.array(indices)
    
    def _emergency_cleanup(self, detector_channel: int):
        """SYNC: Emergency cleanup for failed sweeps"""
        try:
            self.laser.stop_sweep()
            self.laser.stop_logging(detector_channel)
        except Exception as e:
            logger.error(f"Emergency cleanup failed: {e}")


# ASYNC-only wrapper methods for simple sweeps
class SimpleOpticalSweeps:
    """
    Simple sweep methods that follow the async/sync pattern.
    
    For users who just want basic sweeps without stitching complexity.
    """
    
    def __init__(self, laser: LaserHAL):
        self.laser = laser
    
    async def power_sweep(self, start_nm: float, stop_nm: float, 
                         speed_nm_per_s: float, detector_channel: int = 1) -> Tuple[List[float], List[float]]:
        """
        ASYNC: Simple power sweep - no stitching.
        
        Returns (wavelengths, powers) as simple lists.
        """
        # Calculate expected time
        sweep_range = abs(stop_nm - start_nm)
        expected_time = sweep_range / speed_nm_per_s
        
        # Configure sweep (sync operations in async context)
        await asyncio.to_thread(self._configure_simple_sweep, 
                               start_nm, stop_nm, speed_nm_per_s)
        
        # Execute sweep (async because it's long)
        start_time = time.time()
        await asyncio.to_thread(self.laser.start_sweep)
        
        # Wait for completion
        timeout = expected_time + 10.0
        completed = await self._wait_for_completion(timeout)
        
        if not completed:
            await asyncio.to_thread(self.laser.stop_sweep)
            raise TimeoutError(f"Sweep timed out after {timeout}s")
        
        # Manual data collection (step through wavelengths)
        wavelengths, powers = await self._collect_sweep_data(start_nm, stop_nm, 50)
        
        actual_time = time.time() - start_time
        logger.info(f"Simple sweep completed in {actual_time:.1f}s")
        
        return wavelengths, powers
    
    def _configure_simple_sweep(self, start_nm: float, stop_nm: float, speed_nm_per_s: float):
        """SYNC: Configure simple sweep parameters"""
        self.laser.set_sweep_range(start_nm, stop_nm)
        self.laser.set_sweep_speed(speed_nm_per_s)
    
    async def _wait_for_completion(self, timeout: float) -> bool:
        """ASYNC: Wait for sweep completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            state = await asyncio.to_thread(self.laser.get_sweep_state)
            if state == SweepState.STOPPED:
                return True
            await asyncio.sleep(0.5)
        
        return False
    
    async def _collect_sweep_data(self, start_nm: float, stop_nm: float, 
                                 num_points: int) -> Tuple[List[float], List[float]]:
        """
        ASYNC: Collect data by stepping through wavelengths manually.
        
        Alternative to logging when you want more control.
        """
        wavelengths = np.linspace(start_nm, stop_nm, num_points).tolist()
        powers = []
        
        for wl in wavelengths:
            # Set wavelength and read power (sync operations)
            await asyncio.to_thread(self.laser.set_wavelength, wl)
            await asyncio.sleep(0.05)  # Settling time
            
            power_reading = await asyncio.to_thread(self.laser.read_power, 1)
            powers.append(power_reading.value)
        
        return wavelengths, powers


# Example usage following the hybrid pattern
async def demo_compliant_sweep():
    """Demo showing the compliant async/sync usage"""
    
    # Your controller (sync/async hybrid)
    controller = Agilent8163Controller(
        com_port=5,
        laser_slot=0,
        detector_slots=[1]
    )
    
    # Sweep manager follows same pattern
    sweep_manager = OpticalSweepManager(controller)
    simple_sweeps = SimpleOpticalSweeps(controller)
    
    try:
        # SYNC: Connection and basic setup
        controller.connect()
        controller.enable_output(True)
        
        # ASYNC: Long operation (stitched sweep)
        stitched_result = await sweep_manager.stitched_power_sweep(
            start_nm=1548.0,
            stop_nm=1552.0,
            speed_nm_per_s=1.0,
            detector_channel=1,
            averaging_time_ms=50.0
        )
        
        print(f"Stitched sweep: {stitched_result.num_points} points in {stitched_result.num_segments} segments")
        
        # ASYNC: Simple sweep alternative
        wavelengths, powers = await simple_sweeps.power_sweep(
            start_nm=1549.0,
            stop_nm=1551.0,
            speed_nm_per_s=2.0,
            detector_channel=1
        )
        
        print(f"Simple sweep: {len(wavelengths)} points")
        
    finally:
        # SYNC: Cleanup
        controller.enable_output(False)
        controller.disconnect()


if __name__ == "__main__":
    asyncio.run(demo_compliant_sweep())