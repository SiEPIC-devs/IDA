import asyncio
import time

from motor_stage_manager_w_debug import StageManager, StageConfiguration
from motors_hal import AxisType, MotorEvent, MotorEventType

def print_event(event: MotorEvent):
    timestamp = event.timestamp
    axis = event.axis.name
    evtype = event.event_type.name
    details = event.data
    print(f"<<< [{timestamp:.3f}] {axis} -> {evtype} -> {details}")

async def comprehensive_xy_test():
    """Comprehensive test of X and Y axis commands"""
    
    # Setup
    cfg = StageConfiguration(
        com_port="/dev/ttyUSB0",       
        baudrate=38400,
        timeout=0.3,
    )
    mgr = StageManager(cfg)
    mgr.add_event_callback(print_event)
    
    x = AxisType.X
    y = AxisType.Y
    
    print("=== COMPREHENSIVE X/Y AXIS TEST ===")
    
    # 1. INITIALIZATION
    print("\n>>> 1. Initializing X and Y axes...")
    ok = await mgr.initialize(axes=[x, y])
    print(f"Initialization result: {ok}")
    if not ok:
        print("Failed to initialize - exiting")
        return
    
    await asyncio.sleep(1)
    
    # 2. HOMING SEQUENCE
    print("\n>>> 2. Homing both axes...")
    print("Homing X positive limit...")
    await mgr.home_axis(x, direction=1)
    
    print("Homing Y positive limit...")
    await mgr.home_axis(y, direction=1)
    
    print("Homing X negative limit...")
    await mgr.home_axis(x, direction=0)
    
    print("Homing Y negative limit...")
    await mgr.home_axis(y, direction=0)
    
    await asyncio.sleep(2)
    
    # 3. ABSOLUTE MOVEMENTS
    print("\n>>> 3. Testing absolute movements...")
    print("Moving X to 1000 um...")
    await mgr.move_single_axis(x, position=1000.0, relative=False)
    
    print("Moving Y to 2000 um...")
    await mgr.move_single_axis(y, position=2000.0, relative=False)
    
    await asyncio.sleep(1)
    
    # 4. RELATIVE MOVEMENTS
    print("\n>>> 4. Testing relative movements...")
    print("Moving X +500 um relative...")
    await mgr.move_single_axis(x, position=500.0, relative=True)
    
    print("Moving Y -300 um relative...")
    await mgr.move_single_axis(y, position=-300.0, relative=True)
    
    await asyncio.sleep(1)
    
    # 5. POSITION QUERIES
    print("\n>>> 5. Querying positions...")
    x_pos = await mgr.get_position(x)
    y_pos = await mgr.get_position(y)
    
    if x_pos:
        print(f"X position: {x_pos.actual:.2f} um (theoretical: {x_pos.theoretical:.2f})")
    if y_pos:
        print(f"Y position: {y_pos.actual:.2f} um (theoretical: {y_pos.theoretical:.2f})")
    
    all_pos = await mgr.get_all_positions()
    print(f"All positions: X={all_pos[x]:.1f}, Y={all_pos[y]:.1f}")
    
    # 6. MOVEMENT WITH CUSTOM VELOCITY
    print("\n>>> 6. Testing custom velocity...")
    print("Moving X to 0 with velocity 1000...")
    await mgr.move_single_axis(x, position=0.0, velocity=1000.0)
    
    # 7. STOP COMMANDS
    print("\n>>> 7. Testing stop commands...")
    print("Starting Y movement and stopping it...")
    await mgr.move_single_axis(y, position=5000.0, wait_for_completion=False)
    await asyncio.sleep(0.2)  # Let it start moving
    await mgr.stop_axis(y)
    
    await asyncio.sleep(1)
    
    # 8. COORDINATED MOVEMENTS
    print("\n>>> 8. Testing coordinated movements...")
    print("Moving both axes to center...")
    # Start both moves without waiting
    await mgr.move_single_axis(x, position=0.0, wait_for_completion=False)
    await mgr.move_single_axis(y, position=0.0, wait_for_completion=False)
    
    # Wait for both to complete
    print("Waiting for all moves to complete...")
    completed = await mgr.wait_for_all_moves_complete(timeout=10.0)
    print(f"All moves completed: {completed}")
    
    # 9. STATE QUERIES
    print("\n>>> 9. Checking states...")
    x_state = await mgr.get_state(x)
    y_state = await mgr.get_state(y)
    print(f"X state: {x_state.name if x_state else 'None'}")
    print(f"Y state: {y_state.name if y_state else 'None'}")
    
    is_moving = await mgr.is_any_axis_moving()
    print(f"Any axis moving: {is_moving}")
    
    # 10. FINAL POSITIONS
    print("\n>>> 10. Final position check...")
    final_pos = await mgr.get_all_positions()
    print(f"Final X: {final_pos[x]:.2f} um")
    print(f"Final Y: {final_pos[y]:.2f} um")
    
    # 11. STATUS REPORT
    print("\n>>> 11. Status report...")
    status = mgr.get_status()
    print(f"Connected: {status['connected']}")
    print(f"Initialized axes: {[ax.name for ax in status['initialized_axes']]}")
    print(f"Last positions: X={status['last_positions'].get(x, 0):.1f}, Y={status['last_positions'].get(y, 0):.1f}")
    
    # 12. CLEANUP
    print("\n>>> 12. Disconnecting...")
    await mgr.disconnect_all()
    print("Test completed!")

async def error_handling_test():
    """Test error handling scenarios"""
    print("\n=== ERROR HANDLING TEST ===")
    
    cfg = StageConfiguration()
    mgr = StageManager(cfg)
    
    # Test commands on uninitialized axes
    print("\n>>> Testing commands on uninitialized axes...")
    result = await mgr.move_single_axis(AxisType.X, 100.0)
    print(f"Move uninitialized axis result: {result}")
    
    result = await mgr.home_axis(AxisType.Y, 1)
    print(f"Home uninitialized axis result: {result}")
    
    pos = await mgr.get_position(AxisType.X)
    print(f"Get position uninitialized axis: {pos}")

if __name__ == "__main__":
    asyncio.run(comprehensive_xy_test())
    asyncio.run(error_handling_test())