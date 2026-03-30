import time
import datetime
import collections

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

from pymodbus.client import ModbusSerialClient

PORT = "COM12"
BAUDRATE = 115200
DEVICE_ID = 1
POLL_HZ = 1          # 1 Hz is enough for shared_memory updates
PLOT_HZ = 10         # Plot refresh rate (Hz) — faster for smooth visuals

HISTORY_MAX = 120     # rolling window size (samples, at PLOT_HZ rate)

def _update_shared_memory(ch1_g: float, ch2_g: float, total_g: float):
    """Write ForceWeight into shared_memory.json."""
    payload = {
        "ch1": round(ch1_g, 1),
        "ch2": round(ch2_g, 1),
        "total": round(total_g, 1),
        "timestamp": datetime.datetime.now().isoformat(),
    }
    try:
        import sys, os
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
    plot_period = 1.0 / max(PLOT_HZ, 1)
    print(f"Force sensor polling started ({POLL_HZ} Hz), writing to shared_memory...")

    # --- Live plot setup ---
    history = collections.deque(maxlen=HISTORY_MAX)
    plt.ion()
    fig, ax = plt.subplots(figsize=(6, 2.5))
    fig.canvas.manager.set_window_title("Force Monitor")
    line, = ax.plot([], [], color="#2196F3", linewidth=1.2)
    annotation = ax.text(
        0.98, 0.95, "", transform=ax.transAxes, fontsize=11, fontweight='bold',
        ha='right', va='top', color="#2196F3",
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#2196F3', alpha=0.8)
    )
    ax.set_ylabel("Force (g)", fontsize=9)
    ax.tick_params(axis='x', labelbottom=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout(pad=0.5)

    last_sm_write = 0.0  # timestamp of last shared_memory write

    try:
        while True:
            rr = client.read_holding_registers(address=0x0000, count=4, device_id=DEVICE_ID)
            if rr.isError():
                print("read error:", rr)
                time.sleep(plot_period)
                continue

            r = rr.registers
            ch1 = regs_to_int32(r[0], r[1])
            ch2 = regs_to_int32(r[2], r[3])

            ch1_g = ch1 / 10.0
            ch2_g = ch2 / 10.0
            total_g = ch1_g + ch2_g

            # Write to shared_memory at original 1 Hz rate
            now = time.monotonic()
            if now - last_sm_write >= period:
                _update_shared_memory(ch1_g, ch2_g, total_g)
                last_sm_write = now

            # --- Update live plot (at PLOT_HZ rate) ---
            history.append(total_g)
            xs = list(range(len(history)))
            line.set_data(xs, list(history))
            ax.set_xlim(0, max(len(history) - 1, 1))
            ax.set_ylim(total_g - 20, total_g + 20)
            annotation.set_text(f"{total_g:.1f} g")
            fig.canvas.draw_idle()
            fig.canvas.flush_events()

            time.sleep(plot_period)

    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        plt.close(fig)
        client.close()
        print("Program terminated.")

if __name__ == "__main__":
    main()
