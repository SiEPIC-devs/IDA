import time
import json
import os
import tempfile
import datetime

from pymodbus.client import ModbusSerialClient

PORT = "COM12"
BAUDRATE = 115200
DEVICE_ID = 1
POLL_HZ = 1          # 1 Hz is enough for shared_memory updates

# Path to shared_memory.json (relative to project root)
_SHARED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GUI", "database", "shared_memory.json")
# Dedicated file for force data — avoids cross-process race on shared_memory.json
_FORCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "GUI", "database", "force_weight.json")

def _update_shared_memory(ch1_g: float, ch2_g: float, total_g: float):
    """Write ForceWeight to a dedicated file AND merge into shared_memory.json."""
    payload = {
        "ch1": round(ch1_g, 1),
        "ch2": round(ch2_g, 1),
        "total": round(total_g, 1),
        "timestamp": datetime.datetime.now().isoformat(),
    }
    # 1. Always write dedicated file (fast, no contention)
    try:
        dir_name = os.path.dirname(_FORCE_PATH)
        fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(tmp, _FORCE_PATH)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
    except Exception:
        pass
    # 2. Merge only ForceWeight into shared_memory.json using
    #    SharedMemory.update() to avoid overwriting other keys.
    #    Import here to avoid circular imports at module level.
    try:
        import sys
        project_root = os.path.dirname(os.path.dirname(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from GUI.lib_gui import SharedMemory
        SharedMemory.update({"ForceWeight": payload})
    except Exception:
        pass

def regs_to_int32(low16: int, high16: int) -> int:
    raw = (high16 << 16) | low16
    if raw >= 0x80000000:
        raw -= 0x100000000
    return raw

def main():
    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.5,
    )
    if not client.connect():
        raise RuntimeError(f"unable to open {PORT}")

    period = 1.0 / max(POLL_HZ, 1)
    print(f"Force sensor polling started ({POLL_HZ} Hz), writing to shared_memory...")

    try:
        while True:
            rr = client.read_holding_registers(address=0x0000, count=4, device_id=DEVICE_ID)
            if rr.isError():
                print("read error:", rr)
                time.sleep(period)
                continue

            r = rr.registers
            ch1 = regs_to_int32(r[0], r[1])
            ch2 = regs_to_int32(r[2], r[3])

            ch1_g = ch1 / 10.0
            ch2_g = ch2 / 10.0
            total_g = ch1_g + ch2_g

            _update_shared_memory(ch1_g, ch2_g, total_g)

            time.sleep(period)

    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        client.close()
        print("Program terminated.")

if __name__ == "__main__":
    main()
