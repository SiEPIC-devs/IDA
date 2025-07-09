import asyncio
import time

from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
from motors.config.pstage_configuration import StageConfiguration as SGE
from motors.hal.motors_hal import AxisType, MotorEvent, MotorEventType
from motors.stage_controller import StageControl


# Define a simple event callback that just prints everything it sees
def print_event(event: MotorEvent):
    # event.axis -> which axis (AxisType.X, etc.)
    # event.event_type -> which kind (MOVE_STARTED, MOVE_COMPLETE, etc.)
    # event.data -> dictionary of details (target_position, success flag, etc.)
    timestamp = event.timestamp
    axis = event.axis.name
    evtype = event.event_type.name
    details = event.data
    print(f"<<< [{timestamp:.3f}] {axis} -> {evtype} -> {details} \n")

async def demo():
    cfg = StageConfiguration()
    mgr = StageManager(cfg)
    # Add event handler
    mgr.add_event_callback(print_event)

    # Initialize just the X axis
    x = AxisType.X
    y = AxisType.Y
    z = AxisType.Z
    fr = AxisType.ROTATION_FIBER
    cp = AxisType.ROTATION_CHIP

    all = [x,y,z,fr,cp] # all
    try:
        # Initially no tasks
        assert len(mgr._tasks) == 0
        
        # Can't start tasks without motors
        await mgr.start_background_tasks()
        assert len(mgr._tasks) > 0  # Should still be 0
        
        # Initialize motors first
        success = await mgr.initialize(all)
        print(f"Total connections: {StageControl.get_connection_count()}")

        if success:
            # Tasks should be running
            for task in mgr._tasks:
                assert not task.cancelled()
                assert not task.done()
            
            print(f"RAWR Total connections: {StageControl.get_connection_count()}")


        async def home_all():
            home_x = await mgr.home_limits(x)
            if home_x:
                print(f"x lims: {mgr.config.position_limits[x]}")
            else:
                print("x failed to home")
                
            home_y = await mgr.home_limits(y)
            if home_y:
                print(f"y lims: {mgr.config.position_limits[y]}")
            else:
                print("y failed to home")

            home_z = await mgr.home_limits(z)
            if home_z:
                print(f"z lims: {mgr.config.position_limits[z]}")
            else:
                print("z failed to home")

            
            home_fr = await mgr.home_limits(fr)
            if home_fr:
                print(f"fr lims: {mgr.config.position_limits[fr]}")
            else:
                print("fr failed to home")

            home_cp = await mgr.home_limits(cp)
            if home_cp:
                print(f"fr lims: {mgr.config.position_limits[cp]}")
            else:
                print("fr failed to home")

        await home_all()
        # await mgr.home_limits(x)
        # await mgr.home_limits()

        
    finally:
        await mgr.cleanup()

if __name__ == "__main__":
    asyncio.run(demo())
