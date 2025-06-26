from multiprocessing import Process
from time import sleep, monotonic
from modern.config.stage_position import *
from modern.config.stage_config import *
from modern.utils.shared_memory import *
from modern.hal.motors_hal import AxisType

def writer_pos():
    shm, raw = open_shared_stage_position()
    sp = StagePosition(shared_struct=raw)
    # write into shared memory
    sp.set_positions(AxisType.X, 123.456)
    sp.set_homed(AxisType.X)
    print(f"[Writer] Wrote: X={sp.x.position:.3f}, Homed={sp.x.is_homed}")
   
    # Clean - explicitly delete the object first
    del sp
    del raw
    shm.close()

def reader_pos():
    # give writer a moment
    sleep(0.1)
    shm, raw = open_shared_stage_position("stage_position")
    sp = StagePosition(shared_struct=raw)
    print(f"[Reader] Reads: X={sp.x.position:.3f}, Homed={sp.x.is_homed}")
   
    # Clean - explicitly delete the object first
    del sp
    del raw
    shm.close()

def writer_config():
    # Attach, build a config, mutate, write it
    shm = open_shared_stage_config()
    cfg = StageConfiguration()
    cfg.baudrate = 115200
    cfg.velocities[AxisType.X] = 1500.0
    write_shared_stage_config(shm, cfg)
    print(f"[WriterCfg] Wrote: baudrate={cfg.baudrate}, X_vel={cfg.velocities[AxisType.X]:.1f}")
    del cfg
    shm.close()

def reader_config():
    sleep(0.1)  # wait for writer
    shm = open_shared_stage_config()
    cfg = read_shared_stage_config(shm)
    print(f"[ReaderCfg] Reads: baudrate={cfg.baudrate}, X_vel={cfg.velocities[AxisType.X]:.1f}")
    del cfg
    shm.close()

if __name__ == "__main__":
    # 1) Stage-position setup & test
    shm_pos, raw_pos = create_shared_stage_position()
    sp0 = StagePosition(shared_struct=raw_pos)
    print(f"[MainPos] Initial X={sp0.x}")
    
    # Clean up the initial StagePosition object
    del sp0
    
    pw = Process(target=writer_pos)
    pw.start(); pw.join()
    pr = Process(target=reader_pos)
    pr.start(); pr.join()
    
    # teardown position SHM - main process handles unlink
    del raw_pos
    import gc
    gc.collect()
    shm_pos.close()
    shm_pos.unlink()  # Only the creator should unlink
    print("[MainPos] Shared position memory unlinked.")
    
    # 2) Stage-config setup & test
    shm_cfg = create_shared_stage_config()
    # Optionally: check default before writes
    try:
        initial = read_shared_stage_config(shm_cfg)
        print(f"[MainCfg] Default baudrate={initial.baudrate}, X_vel={initial.velocities[AxisType.X]:.1f}")
    except BufferError:
        print("[MainCfg] No config present yet.")
     
    pwc = Process(target=writer_config)
    pwc.start(); pwc.join()
    prc = Process(target=reader_config)
    prc.start(); prc.join()
    # teardown config SHM - main process handles unlink
    shm_cfg.close()
    shm_cfg.unlink()  # Only the creator should unlink
    print("[MainCfg] Shared config memory unlinked. Test complete.")