#!/usr/bin/env python3
"""
Comprehensive StageControl test:
  1) home_limits
  2) connect / disconnect
  3) get_position / get_state / is_moving
  4) get_config / set_velocity / set_acceleration
  5) move_absolute / move_relative / stop / emergency_stop
  6) set_zero / wait_for_move_completion / get_move_status
"""

import asyncio
import logging
from typing import Tuple, Optional

from motors.hal.motors_hal import AxisType, MotorConfig, MotorState, Position
from motors.stage_controllerv2 import StageControl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

async def test_axis(axis: AxisType) -> bool:
    ctl = StageControl(axis)
    print(f"\n=== Testing axis {axis.name} ===")
    ok = True
    await ctl.connect()
    # Home limits first
    print("» Homing limits...", end="")
    home_ok, limits = await ctl.home_limits()
    if not home_ok or limits is None:
        print(" FAILED")
        ok = False
        await ctl.disconnect()
        return ok
    print(f" OK → limits = {limits}")

    # Connect
    print("» Connecting...", end="")
    if not await ctl.connect():
        print(" FAILED")
        ok = False
        return ok
    print(" OK")

    # 1) Position / State
    try:
        pos: Position = await ctl.get_position()
        print(f"» Position = {pos.actual:.3f} {pos.units}")
    except Exception as e:
        print(f"» get_position() FAILED: {e}")
        ok = False

    try:
        state: MotorState = await ctl.get_state()
        print(f"» State = {state.name}")
    except Exception as e:
        print(f"» get_state() FAILED: {e}")
        ok = False

    try:
        moving = await ctl.is_moving()
        print(f"» is_moving = {moving}")
    except Exception as e:
        print(f"» is_moving() FAILED: {e}")
        ok = False

    # 2) Configuration
    try:
        cfg: MotorConfig = await ctl.get_config()
        print(f"» Config = vel {cfg.max_velocity}, acc {cfg.max_acceleration}, limits {cfg.position_limits}")
    except Exception as e:
        print(f"» get_config() FAILED: {e}")
        ok = False

    try:
        half_vel = cfg.max_velocity / 2
        if await ctl.set_velocity(half_vel):
            print(f"» set_velocity({half_vel}) OK")
        else:
            print("» set_velocity() FAILED")
            ok = False
    except Exception as e:
        print(f"» set_velocity() exception: {e}")
        ok = False

    try:
        half_acc = cfg.max_acceleration / 2
        if await ctl.set_acceleration(half_acc):
            print(f"» set_acceleration({half_acc}) OK")
        else:
            print("» set_acceleration() FAILED")
            ok = False
    except Exception as e:
        print(f"» set_acceleration() exception: {e}")
        ok = False

    # 3) Moves
    mid = (limits[0] + limits[1]) / 2
    try:
        if await ctl.move_absolute(mid, wait_for_completion=True):
            print(f"» move_absolute({mid}) OK")
        else:
            print("» move_absolute() FAILED")
            ok = False
    except Exception as e:
        print(f"» move_absolute() exception: {e}")
        ok = False

    try:
        # start a relative move but then stop
        rel_task = asyncio.create_task(ctl.move_relative(10.0, wait_for_completion=False))
        await asyncio.sleep(0.05)
        if await ctl.stop():
            print("» move_relative + stop OK")
        else:
            print("» stop() FAILED")
            ok = False
    except Exception as e:
        print(f"» move_relative/stop exception: {e}")
        ok = False

    try:
        if await ctl.emergency_stop():
            print("» emergency_stop() OK")
        else:
            print("» emergency_stop() FAILED")
            ok = False
    except Exception as e:
        print(f"» emergency_stop() exception: {e}")
        ok = False

    # 4) Zero & status
    try:
        if await ctl.set_zero():
            print("» set_zero() OK")
        else:
            print("» set_zero() FAILED")
            ok = False
    except Exception as e:
        print(f"» set_zero() exception: {e}")
        ok = False

    try:
        done = await ctl.wait_for_move_completion(timeout=1.0)
        status = ctl.get_move_status()
        print(f"» wait_for_move_completion → done={done}, status={status}")
    except Exception as e:
        print(f"» wait_for_move_completion() exception: {e}")
        ok = False

    # Disconnect
    await ctl.disconnect()
    print("» Disconnected")
    return ok

async def main():
    results = []
    for ax in (AxisType.X, AxisType.Y):
        ok = await test_axis(ax)
        results.append((ax, ok))

    print("\n=== SUMMARY ===")
    overall = True
    for ax, passed in results:
        print(f"{ax.name}: {'PASS' if passed else 'FAIL'}")
        overall &= passed

    exit(0 if overall else 1)

if __name__ == "__main__":
    asyncio.run(main())
