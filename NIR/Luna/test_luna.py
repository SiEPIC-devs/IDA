from NIR.Luna.luna_controller import LunaController
import pyvisa as visa
import time

luna = LunaController()

aok = luna.connect()
if aok:
    # print('Hello')
    pass
else: 
    print('Goodbyes')
    raise
# ------------------------
# Laser getters
# ------------------------
# print('wl: ', luna.get_wavelength())
# luna.set_wavelength(1570.0)
# time.sleep(1)
# print('wl: ', luna.get_wavelength())

# ------------------------
# Laser setters
# ------------------------
# onoff = luna.get_output_state()
# print('on/off?: ', onoff)
# luna.enable_output(True) 
# onoff = luna.get_output_state()
# print('on/off?: ', onoff)

# ------------------------
# Insertion loss
# ------------------------
for _ in range(1,11):
    print(luna.read_power())
    # time.sleep(1)

# ------------------------
# Sweep
# ------------------------
# luna.read_power()
# d = luna.optical_sweep(
#     start_nm=1530,
#     stop_nm=1570,
#     step_nm=0.01,  # Doesnt matter
#     laser_power_dbm=0,  # Doesnt matter
# )

import matplotlib.pyplot as plt

def plot_ova_results(wavelength_nm, insertion_loss, group_delay):
    """
    Simple 2x1 plot:
      - Top: Wavelength vs Insertion Loss
      - Bottom: Wavelength vs Group Delay
    """
    fig, axes = plt.subplots(2, 1, sharex=True)

    # --- Insertion Loss ---
    axes[0].plot(wavelength_nm, insertion_loss)
    axes[0].set_ylabel("Insertion Loss (dB)")
    axes[0].set_title("OVA Measurement")
    axes[0].grid(True)

    # --- Group Delay ---
    axes[1].plot(wavelength_nm, group_delay)
    axes[1].set_xlabel("Wavelength (nm)")
    axes[1].set_ylabel("Group Delay (ps)")
    axes[1].grid(True)

    plt.tight_layout()
    plt.show()

# plot_ova_results(
#     wavelength_nm=d[:,0],
#     insertion_loss=d[:,2],
#     group_delay=d[:,3]
# )