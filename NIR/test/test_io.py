# NIR/test/test_vi.py
import time
from NIR.nir import NIR8164

def main():
    dev = NIR8164(com_port=5, gpib_addr=20)
    print("Connecting...")
    assert dev.connect(), "connect failed"
    print("IDN ok")

    print("Configure units...")
    dev.configure_units()
    su = dev.query("SOUR0:POW:UNIT?")
    d1 = dev.query("SENS1:CHAN1:POW:UNIT?")
    d2 = dev.query("SENS1:CHAN2:POW:UNIT?")
    print("Units:", su, d1, d2)

    print("Laser power/wavelength...")
    dev.set_power_dbm(-10)
    print("P =", dev.get_power_dbm())
    dev.set_wavelength_nm(1550.0)
    print("WL =", dev.get_wavelength_nm())

    print("Detector live read...")
    try:
        p1, p2 = dev.read_power_dbm()
        print("Pch1, Pch2 =", p1, p2)
    except Exception as e:
        print("Live read skipped:", e)

    # print("Sweep setup...")
    # dev.set_sweep_range_nm(1549.9, 1550.1)
    # dev.set_sweep_step_nm(0.01)
    # dev.arm_sweep_cont_oneway()
    # dev.enable_output(True)
    # dev.start_sweep()
    # time.sleep(1.0)
    # print("Sweep state:", dev.get_sweep_state())
    # dev.stop_sweep()
    # dev.enable_output(False)

    print("Lambda scan (short)...")
    wl, ch1, ch2 = dev.optical_sweep(1548.0, 1551.0, 0.001, 5.0, 0.02)
    print("Points:", len(wl), "WL[0..-1] =", wl[0], wl[-1])
    print(ch1,ch2)

    dev.cleanup_scan()
    dev.disconnect()
    print("Done.")

if __name__ == "__main__":
    main()
