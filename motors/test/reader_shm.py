# reader.py
from motors.utils.shared_memory import open_shared_stage_position
from motors.config.stage_position   import StagePosition

if __name__ == "__main__":
    # Give writer time to create & populate the block
    input("Press Enter after writer has started…")

    # 1) Attach by name to the same "stage_position"
    shm, raw = open_shared_stage_position("stage_position")
    sp = StagePosition(shared_struct=raw)

    # 2) Read back
    print(f"[reader] Reads  → X={sp.x.position:.3f}, Homed={sp.x.is_homed}")

    # 3) Clean up local mapping (don’t unlink—only creator unlinks)
    del sp, raw
    shm.close()
    print("[reader] Done.")
