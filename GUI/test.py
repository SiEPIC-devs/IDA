import serial, time

ser = serial.Serial('COM5', 115200, timeout=1)  # 如无回显可试 9600
def w(s): ser.write((s+'\n').encode())
def r(n=4096): return ser.read(n).decode(errors='ignore')

# —— 初始化 Prologix（每次脚本启动都显式设一次）——
w('++mode 1')          # 控制器模式
w('++addr 20')         # 你的 GPIB 地址
w('++auto 1')          # 手动读
w('++eoi 1')           # 用 EOI 作为响应结束
w('++eos 2')           # CR+LF 作为行结束（双保险）
w('++read_tmo_ms 5000')# Prologix 自身读超时

# —— 验证联通性 ——
#w('++ver'); time.sleep(0.1); print(r(256))

# —— 发送查询 → 等待 → 触发读取 → 读回 ——
w('FETC1:CHAN1:POW?')  # 你已验证可用的 SCPI
time.sleep(0.2)        # 给功率计一点积分/稳定时间
w('++read eoi')
print(r())             # 打印读回数据
w('FETC1:CHAN1:POW?')  # 你已验证可用的 SCPI
time.sleep(0.2)        # 给功率计一点积分/稳定时间
w('++read eoi')
print(r())
