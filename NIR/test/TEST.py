# basic_test.py
import numpy as np
from NIR.nir_controller import NIR8164

def main():
    # tweak these if your setup differs
    COM_PORT = 3          # Prologix / USB-Serial port number
    GPIB_ADDR = 20        # HP816x frame address
    START_NM = 1530.00
    STOP_NM  = 1530.05
    STEP_NM  = 0.01
    POWER_DBM = 1.0

    ctrl = NIR8164(com_port=COM_PORT, gpib_addr=GPIB_ADDR)

    print(f"connecting (COM{COM_PORT}, GPIB {GPIB_ADDR}) …")
    ok = ctrl.connect()
    if not ok:
        print("connect() returned False")
        return
    print("connected.")

    # optional: set power and enable output if those helpers exist in your controller
    try:
        from time import sleep
        ctrl.set_power(5.0)
        sleep(3)
        ctrl.set_power(POWER_DBM)
        print(f"laser power set to {POWER_DBM} dBm")
    except Exception as e:
        print(f"set_laser_power failed: {e}")

    if hasattr(ctrl, "enable_output"):
        try:
            ctrl.enable_output(True)
            print("laser output enabled")
        except Exception as e:
            print(f"enable_output(True) failed: {e}")

    # do a tiny sweep
    print(f"sweeping {START_NM:.3f} → {STOP_NM:.3f} nm @ {STEP_NM:.3f} nm …")
    try:
        wl, ch1, ch2 = ctrl.optical_sweep(
            start_nm=START_NM,
            stop_nm=STOP_NM,
            step_nm=STEP_NM,
            laser_power_dbm=POWER_DBM,
            num_scans=0
        )
    except Exception as e:
        print(f"optical_sweep failed: {e}")
        # try to safely turn off / disconnect even on failure
        try:
            if hasattr(ctrl, "enable_output"):
                ctrl.enable_output(False)
        finally:
            ctrl.disconnect()
        return

    n = wl.size
    print(f"sweep done. points={n}")
    if n:
        print(f"wl range: {wl[0]:.6f} → {wl[-1]:.6f} nm | step≈{np.median(np.diff(wl)):.6f} nm")
        print(f"ch1 first 5: {np.array2string(ch1[:5], precision=3)}")
        if ch2 is not None and ch2.size == n:
            print(f"ch2 first 5: {np.array2string(ch2[:5], precision=3)}")

    # optional: disable output after
    if hasattr(ctrl, "enable_output"):
        try:
            ctrl.enable_output(False)
            print("laser output disabled")
        except Exception as e:
            print(f"enable_output(False) failed: {e}")

    ctrl.disconnect()
    print("disconnected.")

if __name__ == "__main__":
    main()
