import time
from collections import deque

import matplotlib.pyplot as plt
from pymodbus.client import ModbusSerialClient

PORT = "COM12"       
BAUDRATE = 115200
DEVICE_ID = 1       
POLL_HZ = 20         
WINDOW_SEC = 15     
PRINT_ENABLE = False  

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

    # plot init
    plt.ion()
    fig = plt.figure(figsize=(12, 7))
    
    # 添加窗口关闭事件处理
    window_closed = [False]  # 使用列表以便在闭包中修改
    def on_close(event):
        window_closed[0] = True
    fig.canvas.mpl_connect('close_event', on_close)
    
    # 创建主图表区域（占据大部分空间）
    ax = fig.add_axes([0.08, 0.1, 0.65, 0.8])  # [left, bottom, width, height]
    ax.set_title("ZNSV6 Realtime Weight (CH1 & CH2)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Weight raw")

    maxlen = int(WINDOW_SEC * POLL_HZ) + 5
    tbuf = deque(maxlen=maxlen)
    y1 = deque(maxlen=maxlen)
    y2 = deque(maxlen=maxlen)

    (ln1,) = ax.plot([], [], label="CH1", linewidth=2, color='blue')
    (ln2,) = ax.plot([], [], label="CH2", linewidth=2, color='orange')
    ax.legend(loc='upper left')
    
    # 在右侧创建文本显示区域（完全在图表外）
    text_str = "Time:    0.00s\n\nCH1:        0\n\nCH2:        0"
    text_box = fig.text(0.78, 0.5, text_str, 
                       fontsize=13, verticalalignment='center',
                       bbox=dict(boxstyle='round,pad=0.6', facecolor='lightblue', 
                                edgecolor='black', linewidth=1.5, alpha=0.95),
                       family='monospace', weight='bold')

    t0 = time.time()
    period = 1.0 / max(POLL_HZ, 1)

    try:
        while True:
            # 检查窗口是否已关闭
            if window_closed[0] or not plt.fignum_exists(fig.number):
                print("Window closed, exiting...")
                break
                
            # 一次读 0x0000~0x0003：CH1(0,1) + CH2(2,3)
            rr = client.read_holding_registers(address=0x0000, count=4, device_id=DEVICE_ID)
            if rr.isError():
                print("read error:", rr)
                time.sleep(period)
                continue

            r = rr.registers
            ch1 = regs_to_int32(r[0], r[1])
            ch2 = regs_to_int32(r[2], r[3])

            t = time.time() - t0
            tbuf.append(t)
            y1.append(ch1)
            y2.append(ch2)

            ln1.set_data(list(tbuf), list(y1))
            ln2.set_data(list(tbuf), list(y2))

            # 更新实时数据显示
            text_str = f"Time: {t:7.2f}s\n\nCH1: {ch1:8d}\n\nCH2: {ch2:8d}"
            text_box.set_text(text_str)

            ax.relim()
            ax.autoscale_view()
            plt.pause(0.001)

            time.sleep(period)

    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        client.close()
        plt.close(fig)
        print("Program terminated.")

if __name__ == "__main__":
    main()
