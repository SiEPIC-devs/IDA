import asyncio
import serial                 # we’ll override Serial before StageControl imports it
from utils.fake_serial_helper import FakeSerial
from motor_stage_manager import StageManager, StageConfiguration
from motors_hal import AxisType, MotorEvent, MotorEventType

# 1) Monkey‐patch serial.Serial so that StageControl picks up FakeSerial:
serial.Serial = FakeSerial

# 2) A simple event callback that prints each event:
def print_event(ev: MotorEvent):
    ts = ev.timestamp
    ax = ev.axis.name
    et = ev.event_type.name
    data = ev.data
    print(f"[{ts:.3f}] {ax} → {et} → {data}")

async def demo():
    # 3) Build a config & the manager
    cfg = StageConfiguration(
        com_port="FAKE",    # value is ignored by FakeSerial
        baudrate=38400,
        timeout=0.3
    )
    mgr = StageManager(cfg)
    mgr.add_event_callback(print_event)

    # 4) Initialize X,Y (fake connection always “succeeds”)
    print("Initializing X and Y …")
    ok = await mgr.initialize([AxisType.X, AxisType.Y])
    print("initialize returned:", ok)

    # 5) Home X
    print("\nHoming X …")
    homed_x = await mgr.home_axis(AxisType.X, direction=0)
    print("home_axis(X) returned:", homed_x)

    # 6) Home Y
    print("\nHoming Y …")
    homed_y = await mgr.home_axis(AxisType.Y, direction=1)
    print("home_axis(Y) returned:", homed_y)

    # 7) Move X to +1000 μm
    print("\nMoving X to 1000 μm …")
    moved_x = await mgr.move_single_axis(AxisType.X, 1000.0, relative=False)
    print("move_single_axis(X) returned:", moved_x)

    # 8) Coordinated move X→2000, Y→500
    print("\nCoordinated move X→2000, Y→500 …")
    from motor_stage_manager import MoveCommand
    cmd = MoveCommand(
        axes={AxisType.X: 2000.0, AxisType.Y: 500.0},
        velocity=1200.0,
        coordinated_motion=True,
        relative=False
    )
    results = await mgr.move_multiple_axes(cmd)
    print("move_multiple_axes returned:", results)

    # 9) Start a long relative Y move and then stop it
    print("\nStarting long relative move on Y …")
    long_task = asyncio.create_task(
        mgr.move_single_axis(AxisType.Y, 5000.0, relative=True)
    )
    await asyncio.sleep(0.05)  # let it “start”
    print("Stopping Y …")
    stop_y = await mgr.stop_axis(AxisType.Y)
    print("stop_axis(Y) returned:", stop_y)
    await long_task  # wait for it to finish cleanup

    # 10) Read back positions
    print("\nReading positions …")
    pos_x = await mgr.get_position(AxisType.X)
    pos_y = await mgr.get_position(AxisType.Y)
    print(f"X position: {pos_x.actual if pos_x else 'None'} μm")
    print(f"Y position: {pos_y.actual if pos_y else 'None'} μm")

    # 11) Disconnect
    print("\nDisconnecting …")
    await mgr.disconnect()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(demo())
