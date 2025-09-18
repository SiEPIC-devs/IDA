import asyncio
import time

from motors.stage_manager import StageManager, StageConfiguration
from motors.hal.motors_hal import AxisType, MotorEvent, MotorEventType

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

async def stop():
    # 2) Build a config & the manager
    cfg = StageConfiguration()
    mgr = StageManager(cfg)

    # Initialize just the X axis
    x = AxisType.X
    y = AxisType.Y
    z = AxisType.Z
    fr = AxisType.ROTATION_FIBER
    cp = AxisType.ROTATION_CHIP
    all = [x,y,z,fr,cp]

    print(">>> Initializing X …")
    ok = await mgr.initialize_all()
    if not ok:
        print(f"init failed")
        await mgr.disconnect_all()
    print(f"Initialized X: {ok}")
    
    # Wait 0.2 s, then stop
    await asyncio.sleep(0.2)
    print(">>> Calling emergency_stop() …")
    stopped = await mgr.emergency_stop()
    print("emergency stop returned:", stopped)

    # 9) Disconnect everything
    print("\n>>> Disconnecting …")
    await mgr.disconnect_all()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(stop())
