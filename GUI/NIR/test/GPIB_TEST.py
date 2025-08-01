#!/usr/bin/env python3
"""
Simple GPIB connection test for Agilent 8163A

Cameron Basara, 2025

This script tests basic connectivity to the Agilent 8163A via Prologix GPIB-USB converter.
"""

import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from NIR.nir_controller_practical import Agilent8163ControllerPractical
import asyncio

async def test_connection():
    """Test basic connection to the Agilent 8163A"""
    
    print("=== Agilent 8163A GPIB Connection Test ===")
    
    # Initialize controller
    # Change COM port number as needed (3 = COM3, 4 = COM4, etc.)
    controller = Agilent8163ControllerPractical(
        com_port=5,  # Adjust this to your COM port
        laser_slot=0,
        detector_slots=['1'],
        timeout=5000
    )
    
    try:
        print("Attempting to connect...")
        
        # Test connection
        if await controller.connect():
            print("✓ Connection successful!")
            
            # Test basic identity query
            print(f"✓ Instrument ID: {controller.instrument_id}")
            
            # Test basic laser queries
            try:
                print("\nTesting basic laser queries...")
                
                # Get wavelength limits
                min_wl, max_wl = await controller.get_wavelength_limits()
                print(f"✓ Wavelength limits: {min_wl:.1f} - {max_wl:.1f} nm")
                
                # Get current wavelength
                current_wl = await controller.get_wavelength()
                print(f"✓ Current wavelength: {current_wl:.3f} nm")
                
                # Get power limits
                min_power, max_power = await controller.get_power_limits()
                print(f"✓ Power limits: {min_power:.1f} - {max_power:.1f} dBm")
                
                # Get current power
                current_power, unit = await controller.get_power()
                print(f"✓ Current power: {current_power:.3f} {unit.value}")
                
                # Get output state
                output_state = await controller.get_output_state()
                print(f"✓ Output enabled: {output_state}")
                
            except Exception as e:
                print(f"✗ Error during laser queries: {e}")
            
            try:
                print("\nTesting detector queries...")
                
                # Test power reading
                power_reading = await controller.read_power(channel=1)
                print(f"✓ Power reading: {power_reading.value:.3f} {power_reading.unit.value} @ {power_reading.wavelength:.3f} nm")
                
            except Exception as e:
                print(f"✗ Error during detector queries: {e}")
                
        else:
            print("✗ Connection failed!")
            return False
            
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False
        
    finally:
        # Clean disconnect
        try:
            if await controller.disconnect():
                print("✓ Disconnected successfully")
            else:
                print("⚠ Disconnect warning")
        except Exception as e:
            print(f"✗ Disconnect error: {e}")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    asyncio.run(test_connection())    
