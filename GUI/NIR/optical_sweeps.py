"""
Simple Optical Sweep Functions using NIR HAL

Cameron Basara, 2025

This demonstrates how easy optical sweeps are with clean HAL abstractions.
Replaces the 200+ line legacy nightmare with ~20 lines of readable code.
"""

import asyncio
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass

from NIR.hal.nir_hal import LaserHAL, PowerReading, WavelengthRange, SweepState
from NIR.hal.nir_factory import get_driver

import logging
logger = logging.getLogger(__name__)


@dataclass 
class SweepResult:
    """Clean sweep result data"""
    wavelengths: List[float]  # nm
    powers: List[float]       # dBm  
    sweep_time: float         # seconds
    num_points: int


async def simple_power_sweep(
    laser: LaserHAL,
    start_nm: float,
    stop_nm: float, 
    speed_nm_per_s: float,
    detector_channel: int = 1,
    averaging_time_ms: float = 100.0,
    use_hardware_triggers: bool = True
) -> SweepResult:
    """
    Perform a simple optical power vs wavelength sweep.
    
    This is what optical sweeps should look like - clean and simple.
    No GPIO pins, no external triggers, no 200-line binary parsing nightmares.
    """
    logger.info(f"Starting sweep: {start_nm}-{stop_nm}nm at {speed_nm_per_s}nm/s")
    
    # Calculate sweep parameters
    sweep_range_nm = abs(stop_nm - start_nm)
    sweep_time_s = sweep_range_nm / speed_nm_per_s
    
    # Estimate number of data points (based on averaging time)
    points_per_second = 1000 / averaging_time_ms
    estimated_points = int(sweep_time_s * points_per_second)
    
    try:
        # Configure hardware triggering for precision (if supported and requested)
        if use_hardware_triggers and hasattr(laser, 'enable_internal_triggering'):
            await laser.enable_internal_triggering()
            logger.info("Hardware triggering enabled for microsecond precision")
        
        # Configure sweep 
        await laser.set_sweep_range(start_nm, stop_nm)
        await laser.set_sweep_speed(speed_nm_per_s)
        
        # Start data logging first
        await laser.start_logging(estimated_points, averaging_time_ms, detector_channel)
        
        # Start the sweep
        start_time = time.time()
        await laser.start_sweep()
        
        # Wait for completion (with timeout)
        max_wait_time = sweep_time_s + 10.0  # 10s buffer
        sweep_completed = await laser.wait_for_sweep_completion(timeout=max_wait_time)
        
        if not sweep_completed:
            logger.error("Sweep timed out")
            await laser.stop_sweep()
            return SweepResult([], [], 0.0, 0)
        
        # Stop logging and get data
        await laser.stop_logging(detector_channel)
        logged_data = await laser.get_logged_data(detector_channel)
        
        actual_sweep_time = time.time() - start_time
        
        # Extract wavelengths and powers
        wavelengths = [reading.wavelength for reading in logged_data if reading.wavelength]
        powers = [reading.value for reading in logged_data]
        
        logger.info(f"Sweep complete: {len(logged_data)} points in {actual_sweep_time:.1f}s")
        
        return SweepResult(
            wavelengths=wavelengths,
            powers=powers,
            sweep_time=actual_sweep_time,
            num_points=len(logged_data)
        )
        
    except Exception as e:
        logger.error(f"Sweep failed: {e}")
        await laser.stop_sweep()
        await laser.stop_logging(detector_channel)
        return SweepResult([], [], 0.0, 0)


async def stepped_power_sweep(
    laser: LaserHAL,
    start_nm: float,
    stop_nm: float,
    step_nm: float,
    detector_channel: int = 1,
    dwell_time_s: float = 0.1
) -> SweepResult:
    """
    Perform a stepped sweep (software-controlled wavelength stepping).
    
    Sometimes you want more control than continuous sweeps provide.
    Still simple and clean - no external hardware needed.
    """
    logger.info(f"Starting stepped sweep: {start_nm}-{stop_nm}nm, {step_nm}nm steps")
    
    wavelengths = []
    powers = []
    
    start_time = time.time()
    
    try:
        # Disable sweep mode for manual control
        await laser.set_sweep_state(False)
        
        current_wl = start_nm
        while (current_wl <= stop_nm if start_nm < stop_nm else current_wl >= stop_nm):
            # Set wavelength and wait for stabilization
            await laser.set_wavelength(current_wl)
            await asyncio.sleep(dwell_time_s)
            
            # Read power 
            power_reading = await laser.read_power(detector_channel)
            
            wavelengths.append(current_wl)
            powers.append(power_reading.value)
            
            logger.debug(f"λ={current_wl:.3f}nm, P={power_reading.value:.2f}dBm")
            
            # Next step
            current_wl += step_nm if start_nm < stop_nm else -step_nm
            
        sweep_time = time.time() - start_time
        logger.info(f"Stepped sweep complete: {len(powers)} points in {sweep_time:.1f}s")
        
        return SweepResult(
            wavelengths=wavelengths,
            powers=powers,
            sweep_time=sweep_time,
            num_points=len(powers)
        )
        
    except Exception as e:
        logger.error(f"Stepped sweep failed: {e}")
        return SweepResult([], [], 0.0, 0)


async def multi_channel_sweep(
    laser: LaserHAL,
    start_nm: float,
    stop_nm: float,
    speed_nm_per_s: float,
    detector_channels: List[int],
    averaging_time_ms: float = 100.0
) -> dict[int, SweepResult]:
    """
    Perform sweep across multiple detector channels simultaneously.
    
    Perfect for measuring multiple fiber outputs, reference channels, etc.
    """
    logger.info(f"Multi-channel sweep on channels {detector_channels}")
    
    results = {}
    
    try:
        # Start logging on all channels
        sweep_range_nm = abs(stop_nm - start_nm)
        sweep_time_s = sweep_range_nm / speed_nm_per_s
        points_per_second = 1000 / averaging_time_ms
        estimated_points = int(sweep_time_s * points_per_second)
        
        for channel in detector_channels:
            await laser.start_logging(estimated_points, averaging_time_ms, channel)
        
        # Configure and start sweep
        await laser.set_sweep_range(start_nm, stop_nm)
        await laser.set_sweep_speed(speed_nm_per_s)
        
        start_time = time.time()
        await laser.start_sweep()
        
        # Wait for completion
        max_wait_time = sweep_time_s + 10.0
        sweep_completed = await laser.wait_for_sweep_completion(timeout=max_wait_time)
        
        if not sweep_completed:
            logger.error("Multi-channel sweep timed out")
            await laser.stop_sweep()
            for channel in detector_channels:
                await laser.stop_logging(channel)
            return {}
        
        actual_sweep_time = time.time() - start_time
        
        # Collect data from all channels
        for channel in detector_channels:
            await laser.stop_logging(channel)
            logged_data = await laser.get_logged_data(channel)
            
            wavelengths = [reading.wavelength for reading in logged_data if reading.wavelength]
            powers = [reading.value for reading in logged_data]
            
            results[channel] = SweepResult(
                wavelengths=wavelengths,
                powers=powers,
                sweep_time=actual_sweep_time,
                num_points=len(logged_data)
            )
        
        logger.info(f"Multi-channel sweep complete: {len(detector_channels)} channels")
        return results
        
    except Exception as e:
        logger.error(f"Multi-channel sweep failed: {e}")
        await laser.stop_sweep()
        for channel in detector_channels:
            await laser.stop_logging(channel)
        return {}


# Example usage function
async def demo_sweep():
    """
    Example of how easy it is to use these sweep functions.
    Compare this to the legacy 200+ line nightmares!
    """
    # Get laser controller (registered as "347_NIR")
    laser = get_driver("347_NIR")(
        ip_address="192.168.1.100",  # Replace with your IP
        laser_slot=1,
        detector_slots=[2]
    )
    
    try:
        # Connect
        await laser.connect()
        
        # Enable laser output
        await laser.enable_output(True)
        
        # Simple power sweep - this is all you need!
        result = await simple_power_sweep(
            laser=laser,
            start_nm=1520.0,
            stop_nm=1570.0, 
            speed_nm_per_s=5.0,
            detector_channel=1
        )
        
        print(f"Sweep completed: {result.num_points} points in {result.sweep_time:.1f}s")
        print(f"Power range: {min(result.powers):.2f} to {max(result.powers):.2f} dBm")
        
        # Stepped sweep for more control
        stepped_result = await stepped_power_sweep(
            laser=laser,
            start_nm=1530.0,
            stop_nm=1560.0,
            step_nm=0.1,
            detector_channel=1
        )
        
        print(f"Stepped sweep: {stepped_result.num_points} points")
        
    finally:
        await laser.safe_shutdown()


if __name__ == "__main__":
    asyncio.run(demo_sweep())