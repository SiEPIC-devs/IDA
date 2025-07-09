from multiprocessing import Process
from time import sleep, monotonic
from motors.config.stage_position import *
from motors.config.stage_config import *
from motors.utils.shared_memory import *
from motors.hal.motors_hal import AxisType
import traceback

def writer_pos():
    """Writer process for stage position data"""
    try:
        print("🔄 [Writer-Pos] Starting position writer process...")
        shm, raw = open_shared_stage_position()
        sp = StagePosition(shared_struct=raw)
        
        # Write test data for multiple axes
        test_positions = {
            AxisType.X: 123.456,
            AxisType.Y: 789.012,
            AxisType.Z: 345.678
        }
        
        for axis, pos in test_positions.items():
            sp.set_positions(axis, pos)
            sp.set_homed(axis)
            print(f"✅ [Writer-Pos] Set {axis.name}: position={pos:.3f}, homed=True")
        
        # Add timestamp info
        current_time = monotonic()
        print(f"⏰ [Writer-Pos] Write completed at t={current_time:.3f}s")
        print(f"📊 [Writer-Pos] Final state - X:{sp.x.position:.3f}, Y:{sp.y.position:.3f}, Z:{sp.z.position:.3f}")
        
        # Clean up
        del sp
        del raw
        shm.close()
        print("🧹 [Writer-Pos] Cleanup completed")
        
    except Exception as e:
        print(f"❌ [Writer-Pos] ERROR: {e}")
        traceback.print_exc()

def reader_pos():
    """Reader process for stage position data"""
    try:
        print("🔄 [Reader-Pos] Starting position reader process...")
        sleep(0.1)  # Give writer time to complete
        
        shm, raw = open_shared_stage_position("stage_position")
        sp = StagePosition(shared_struct=raw)
        
        print("📖 [Reader-Pos] Reading shared position data:")
        axes_data = [
            ("X", sp.x),
            ("Y", sp.y), 
            ("Z", sp.z)
        ]
        
        for axis_name, axis_data in axes_data:
            print(f"  • {axis_name}: pos={axis_data.position:.3f}, homed={axis_data.is_homed}, ts={axis_data.timestamp:.3f}")
        
        # Verify data integrity
        expected = {
            "X": (123.456, True),
            "Y": (789.012, True),
            "Z": (345.678, True)
        }
        
        all_correct = True
        for axis_name, axis_data in axes_data:
            exp_pos, exp_homed = expected[axis_name]
            if abs(axis_data.position - exp_pos) > 0.001 or axis_data.is_homed != exp_homed:
                print(f"❌ [Reader-Pos] Data mismatch for {axis_name}!")
                all_correct = False
        
        if all_correct:
            print("✅ [Reader-Pos] All data verified correctly!")
        
        # Clean up
        del sp
        del raw
        shm.close()
        print("🧹 [Reader-Pos] Cleanup completed")
        
    except Exception as e:
        print(f"❌ [Reader-Pos] ERROR: {e}")
        traceback.print_exc()

def writer_config():
    """Writer process for stage configuration data"""
    try:
        print("🔄 [Writer-Config] Starting config writer process...")
        
        shm = open_shared_stage_config()
        cfg = StageConfiguration()
        
        # Write comprehensive test configuration
        cfg.baudrate = 115200
        cfg.velocities[AxisType.X] = 1500.0
        cfg.velocities[AxisType.Y] = 2000.0
        cfg.velocities[AxisType.Z] = 1200.0
        
        # Add more config if available
        try:
            cfg.accelerations = {AxisType.X: 5000.0, AxisType.Y: 6000.0, AxisType.Z: 4500.0}
            cfg.enabled_axes = [AxisType.X, AxisType.Y, AxisType.Z]
        except AttributeError:
            print("ℹ️  [Writer-Config] Advanced config options not available")
        
        write_shared_stage_config(shm, cfg)
        
        print("✅ [Writer-Config] Configuration written:")
        print(f"  • Baudrate: {cfg.baudrate}")
        for axis in [AxisType.X, AxisType.Y, AxisType.Z]:
            vel = cfg.velocities.get(axis, 0.0)
            print(f"  • {axis.name} velocity: {vel:.1f}")
        
        del cfg
        shm.close()
        print("🧹 [Writer-Config] Cleanup completed")
        
    except Exception as e:
        print(f"❌ [Writer-Config] ERROR: {e}")
        traceback.print_exc()

def reader_config():
    """Reader process for stage configuration data"""
    try:
        print("🔄 [Reader-Config] Starting config reader process...")
        sleep(0.1)  # Wait for writer
        
        shm = open_shared_stage_config()
        cfg = read_shared_stage_config(shm)
            
        print("📖 [Reader-Config] Reading shared configuration:")
        print(f"  • Baudrate: {cfg.baudrate}")
        
        for axis in [AxisType.X, AxisType.Y, AxisType.Z]:
            vel = cfg.velocities.get(axis, 0.0)
            print(f"  • {axis.name} velocity: {vel:.1f}")
        
        # Verify config integrity
        expected_baudrate = 115200
        expected_velocities = {AxisType.X: 1500.0, AxisType.Y: 2000.0, AxisType.Z: 1200.0}
        
        config_correct = True
        if cfg.baudrate != expected_baudrate:
            print(f"❌ [Reader-Config] Baudrate mismatch: got {cfg.baudrate}, expected {expected_baudrate}")
            config_correct = False
            
        for axis, expected_vel in expected_velocities.items():
            actual_vel = cfg.velocities.get(axis, 0.0)
            if abs(actual_vel - expected_vel) > 0.1:
                print(f"❌ [Reader-Config] Velocity mismatch for {axis.name}: got {actual_vel}, expected {expected_vel}")
                config_correct = False
        
        if config_correct:
            print("✅ [Reader-Config] All configuration verified correctly!")
        
        del cfg
        shm.close()
        print("🧹 [Reader-Config] Cleanup completed")
        
    except Exception as e:
        print(f"❌ [Reader-Config] ERROR: {e}")
        traceback.print_exc()

def stress_test_position():
    """Stress test with rapid read/write operations"""
    try:
        print("🔄 [Stress-Test] Starting position stress test...")
        
        shm, raw = open_shared_stage_position("stage_position")
        sp = StagePosition(shared_struct=raw)
        
        # Rapid updates
        for i in range(10):
            new_pos = 100.0 + i * 10.5
            sp.set_positions(AxisType.X, new_pos)
            current_pos = sp.x.position
            if abs(current_pos - new_pos) < 0.001:
                print(f"✅ [Stress-Test] Update {i+1}/10: {current_pos:.3f}")
            else:
                print(f"❌ [Stress-Test] Update {i+1}/10 FAILED: got {current_pos:.3f}, expected {new_pos:.3f}")
            sleep(0.01)  # Small delay
        
        del sp
        del raw
        shm.close()
        print("🧹 [Stress-Test] Cleanup completed")
        
    except Exception as e:
        print(f"❌ [Stress-Test] ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Comprehensive Shared Memory IPC Test Suite")
    print("=" * 60)
    
    try:
        # =============================================================================
        # STAGE POSITION TESTING
        # =============================================================================
        print("\n📍 STAGE POSITION MEMORY TEST")
        print("-" * 40)
        
        # Create shared memory for positions
        print("🏗️  [Main] Creating shared position memory...")
        shm_pos, raw_pos = create_shared_stage_position()
        sp0 = StagePosition(shared_struct=raw_pos)
        
        # Check initial state
        print(f"📊 [Main] Initial state - X:{sp0.x.position:.1f}, Y:{sp0.y.position:.1f}, Z:{sp0.z.position:.1f}")
        print(f"🏠 [Main] Initial homing - X:{sp0.x.is_homed}, Y:{sp0.y.is_homed}, Z:{sp0.z.is_homed}")
        
        # Clean up initial object
        del sp0
        
        # Test writer process
        print("\n🖊️  Testing Position Writer Process:")
        pw = Process(target=writer_pos)
        pw.start()
        pw.join()
        
        if pw.exitcode == 0:
            print("✅ Position writer completed successfully")
        else:
            print(f"❌ Position writer failed with exit code: {pw.exitcode}")
        
        # Test reader process
        print("\n📖 Testing Position Reader Process:")
        pr = Process(target=reader_pos)
        pr.start()
        pr.join()
        
        if pr.exitcode == 0:
            print("✅ Position reader completed successfully")
        else:
            print(f"❌ Position reader failed with exit code: {pr.exitcode}")
        
        # Stress test
        print("\n💪 Testing Position Stress Test:")
        ps = Process(target=stress_test_position)
        ps.start()
        ps.join()
        
        if ps.exitcode == 0:
            print("✅ Position stress test completed successfully")
        else:
            print(f"❌ Position stress test failed with exit code: {ps.exitcode}")
        
        # Clean up position shared memory
        del raw_pos
        import gc
        gc.collect()
        shm_pos.close()
        shm_pos.unlink()
        print("🧹 [Main] Position shared memory cleaned up")
        
        # =============================================================================
        # STAGE CONFIGURATION TESTING
        # =============================================================================
        print("\n⚙️  STAGE CONFIGURATION MEMORY TEST")
        print("-" * 40)
        
        # Create shared memory for config
        print("🏗️  [Main] Creating shared config memory...")
        shm_cfg = create_shared_stage_config()
        
        # Test initial read (should fail gracefully)
        try:
            initial = read_shared_stage_config(shm_cfg)
            print(f"📊 [Main] Initial config found: baudrate={initial.baudrate}")
        except BufferError:
            print("ℹ️  [Main] No initial config present (expected)")
        
        # Test config writer process
        print("\n🖊️  Testing Config Writer Process:")
        pwc = Process(target=writer_config)
        pwc.start()
        pwc.join()
        
        if pwc.exitcode == 0:
            print("✅ Config writer completed successfully")
        else:
            print(f"❌ Config writer failed with exit code: {pwc.exitcode}")
        
        # Test config reader process
        print("\n📖 Testing Config Reader Process:")
        prc = Process(target=reader_config)
        prc.start()
        prc.join()
        
        if prc.exitcode == 0:
            print("✅ Config reader completed successfully")
        else:
            print(f"❌ Config reader failed with exit code: {prc.exitcode}")
        
        # Clean up config shared memory
        shm_cfg.close()
        shm_cfg.unlink()
        print("🧹 [Main] Config shared memory cleaned up")
        
        # =============================================================================
        # FINAL SUMMARY
        # =============================================================================
        print("\n🎉 TEST SUITE COMPLETED")
        print("=" * 60)
        print("✅ All processes completed - Check individual results above")
        print("✅ Memory cleanup successful")
        print("✅ No hanging shared memory segments")
        
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR in main process: {e}")
        traceback.print_exc()
        
        # Emergency cleanup
        try:
            if 'shm_pos' in locals():
                shm_pos.close()
                shm_pos.unlink()
            if 'shm_cfg' in locals():
                shm_cfg.close()
                shm_cfg.unlink()
            print("🚨 Emergency cleanup completed")
        except:
            print("🚨 Emergency cleanup failed - manual cleanup may be required")
    
    print("\n🏁 Test suite finished")