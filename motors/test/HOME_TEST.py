#!/usr/bin/env python3
import asyncio
from motors.stage_controllerv2 import StageControl
from motors.hal.motors_hal import AxisType

async def debug_home_limits(axis):
    ctl = StageControl(axis)

    await ctl.connect()

    # Wrap the send/query methods to log everything
    orig_send  = ctl._send_command
    orig_query = ctl._query_command

    async def send_debug(cmd: str):
        print(f"[DEBUG] SEND     → {cmd}")
        try:
            resp = await orig_send(cmd)
            print(f"[DEBUG] SEND resp← {resp!r}")
            return resp
        except Exception as e:
            print(f"[DEBUG] SEND error↯ {e}")
            raise

    async def query_debug(cmd: str):
        print(f"[DEBUG] QUERY    → {cmd}")
        try:
            resp = await orig_query(cmd)
            print(f"[DEBUG] QUERY resp← {resp!r}")
            return resp
        except Exception as e:
            print(f"[DEBUG] QUERY error↯ {e}")
            raise

    ctl._send_command  = send_debug
    ctl._query_command = query_debug

    print(f"\n--- Debugging home_limits on axis {axis.name} ---")
    try:
        ok, limits = await ctl.home_limits()
        print(f"\n*** home_limits returned: ok={ok}, limits={limits} ***")
    except Exception as e:
        print(f"\n*** home_limits threw: {type(e).__name__}: {e} ***")

    # Clean up
    await ctl.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_home_limits(AxisType.X))
