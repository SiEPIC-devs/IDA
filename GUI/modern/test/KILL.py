import asyncio
import time

from modern.test.motor_stage_manager_w_debug import StageManager, StageConfiguration
from modern.test.motors_hal import AxisType, MotorEvent, MotorEventType

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
    cfg = StageConfiguration(
        com_port="/dev/ttyUSB0",       
        baudrate=38400,
        timeout=0.3,
        # (all other fields use their defaults)
    )
    mgr = StageManager(cfg)

    # Initialize just the X axis
    x = AxisType.X
    y = AxisType.Y
    z = AxisType.Z
    fr = AxisType.ROTATION_FIBER
    cp = AxisType.ROTATION_CHIP
    all = [x,y,z,fr,cp]

    print(">>> Initializing X …")
    ok = await mgr.initialize(axes=all)
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
