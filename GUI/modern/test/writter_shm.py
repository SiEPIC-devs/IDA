# writer.py
from time import sleep
from modern.utils.shared_memory import create_shared_stage_position
from modern.config.stage_position import StagePosition
from modern.hal.motors_hal import AxisType

if __name__ == "__main__":
    # 1) Create the SHM block named "stage_position" and zero it
    shm, raw = create_shared_stage_position()
    sp = StagePosition(shared_struct=raw)

    # 2) Write some data
    sp.set_positions(AxisType.X,  123.456)
    sp.set_homed(    AxisType.X)
    print(f"[writer] Wrote → X={sp.x.position:.3f}, Homed={sp.x.is_homed}")

    # 3) Keep the block alive so reader can attach...
    print("[writer] Waiting 10 s before unlinking...")
    sleep(10)

    # 4) Clean up: unmap & unlink so OS frees it
    del sp, raw
    shm.close()
    shm.unlink()
    print("[writer] Unlinked and exiting.")
