import asyncio
import time

from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
from motors.hal.motors_hal import AxisType, MotorEvent, MotorEventType
from motors.stage_controllerv2 import StageControl

def print_event(event: MotorEvent):
    timestamp = event.timestamp
    axis = event.axis.name
    evtype = event.event_type.name
    details = event.data
    print(f"<<< [{timestamp:.3f}] {axis} -> {evtype} -> {details}")

async def test_initialization(mgr):
    """Test initialization and background tasks"""
    print("\n=== INITIALIZATION TESTS ===")
    
    # Test task creation
    initial_tasks = len(mgr._tasks)
    await mgr.start_background_tasks()
    print(f"✓ Background tasks started: {len(mgr._tasks)} tasks")
    
    # Initialize all axes
    all_axes = [AxisType.X, AxisType.Y, AxisType.Z, AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP]
    success = await mgr.initialize(all_axes)
    print(f"✓ Initialization: {'SUCCESS' if success else 'FAILED'}")
    print(f"✓ Total connections: {StageControl.get_connection_count()}")
    
    return success

async def test_homing(mgr):
    """Test homing operations with safety checks"""
    print("\n=== HOMING TESTS ===")
    
    # Safe order: X, Y first, then Z (Y moves to safe position), then rotations
    safe_axes = [AxisType.X, AxisType.Y]
    
    for axis in safe_axes:
        print(f"Homing {axis.name} limits...")
        success = await mgr.home_limits(axis)
        if success:
            limits = mgr.config.position_limits[axis]
            print(f"✓ {axis.name} homed: {limits}")
        else:
            print(f"✗ {axis.name} homing failed")
    
    # Z-axis with Y safety (following your pattern)
    print("Homing Z with Y safety...")
    success = await mgr.home_limits(AxisType.Z)
    if success:
        limits = mgr.config.position_limits[AxisType.Z]
        print(f"✓ Z homed safely: {limits}")
    else:
        print("✗ Z homing failed")
    
    # Rotations last (most dangerous)
    for axis in [AxisType.ROTATION_FIBER, AxisType.ROTATION_CHIP]:
        print(f"Homing {axis.name} (careful!)...")
        success = await mgr.home_limits(axis)
        if success:
            limits = mgr.config.position_limits[axis]
            print(f"✓ {axis.name} homed: {limits}")
        else:
            print(f"✗ {axis.name} homing failed")

async def test_position_polling(mgr):
    """Test position polling and shared memory updates"""
    print("\n=== POSITION POLLING TEST ===")
    
    print("Testing position polling for 5 seconds...")
    start_time = time.time()
    
    while time.time() - start_time < 5:
        positions = await mgr.get_all_positions()
        print(f"Positions: {[(axis.name, f'{pos:.3f}') for axis, pos in positions.items()]}")
        await asyncio.sleep(1)
    
    print("✓ Position polling test complete")

async def test_safe_movements(mgr):
    """Test movement operations with safety constraints"""
    print("\n=== MOVEMENT TESTS ===")
    
    # Test single axis movements (small, safe distances)
    safe_distance = 100.0  # 100 microns
    
    # Test X axis
    print(f"Moving X axis {safe_distance} microns relative...")
    success = await mgr.move_single_axis(AxisType.X, safe_distance, relative=True)
    print(f"✓ X relative move: {'SUCCESS' if success else 'FAILED'}")
    
    await asyncio.sleep(1)
    
    # Move back
    success = await mgr.move_single_axis(AxisType.X, -safe_distance, relative=True)
    print(f"✓ X return move: {'SUCCESS' if success else 'FAILED'}")
    
    # Test XY coordinated movement
    print("Testing XY coordinated movement...")
    xy_move = (50.0, 50.0)
    success = await mgr.move_xy_rel(xy_move)
    print(f"✓ XY relative move: {'SUCCESS' if success else 'FAILED'}")
    
    await asyncio.sleep(1)
    
    # Return XY
    xy_return = (-50.0, -50.0)
    success = await mgr.move_xy_rel(xy_return)
    print(f"✓ XY return move: {'SUCCESS' if success else 'FAILED'}")
    
    print("⚠️  Skipping Z and rotation movements for safety")

async def test_status_operations(mgr):
    """Test status and state operations"""
    print("\n=== STATUS TESTS ===")
    
    # Test status
    status = mgr.get_status()
    print(f"✓ Status: Connected={status['connected']}, Axes={len(status['initialized_axes'])}")
    
    # Test individual axis states
    for axis in [AxisType.X, AxisType.Y]:  # Safe axes only
        state = await mgr.get_state(axis)
        pos = await mgr.get_position(axis)
        print(f"✓ {axis.name}: State={state}, Position={pos.actual if pos else 'None'}")
    
    # Test movement detection
    moving = await mgr.is_any_axis_moving()
    print(f"✓ Any axis moving: {moving}")

async def test_stop_operations(mgr):
    """Test stop and emergency stop"""
    print("\n=== STOP TESTS ===")
    
    # Start a movement and then stop it
    print("Starting movement to test stop...")
    asyncio.create_task(mgr.move_single_axis(AxisType.X, 1000.0, relative=True))
    await asyncio.sleep(0.1)  # Let movement start
    
    # Stop single axis
    success = await mgr.stop_axis(AxisType.X)
    print(f"✓ Stop X axis: {'SUCCESS' if success else 'FAILED'}")
    
    # Test emergency stop (should work even if nothing moving)
    success = await mgr.emergency_stop()
    print(f"✓ Emergency stop: {'SUCCESS' if success else 'FAILED'}")

async def test_config_operations(mgr):
    """Test configuration operations"""
    print("\n=== CONFIG TESTS ===")
    
    # Test config reload
    try:
        config = await mgr.reload_config()
        print(f"✓ Config reload: SUCCESS")
    except Exception as e:
        print(f"✗ Config reload failed: {e}")
    
    # Test load params (if axes are homed)
    try:
        success = await mgr.load_params()
        print(f"✓ Load params: {'SUCCESS' if success else 'FAILED (axes not homed?)'}")
    except Exception as e:
        print(f"✗ Load params failed: {e}")

async def comprehensive_test():
    """Run all tests in sequence"""
    print("🚀 Starting Comprehensive Stage Manager Test")
    print("=" * 50)
    
    cfg = StageConfiguration()
    mgr = StageManager(cfg)
    mgr.add_event_callback(print_event)
    
    try:
        # Run all test suites
        init_success = await test_initialization(mgr)
        
        if init_success:
            await test_homing(mgr)
            await test_position_polling(mgr)
            await test_safe_movements(mgr)
            await test_status_operations(mgr)
            await test_stop_operations(mgr)
            await test_config_operations(mgr)
        else:
            print("❌ Initialization failed, skipping other tests")
        
        print("\n" + "=" * 50)
        print("🏁 Test sequence complete!")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🧹 Cleaning up...")
        await mgr.cleanup()
        print("✓ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(comprehensive_test())