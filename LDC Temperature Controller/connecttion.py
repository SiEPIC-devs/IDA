import pyvisa

rm   = pyvisa.ResourceManager()
inst = rm.open_resource('ASRL4::INSTR')

# 串口参数（按 NI-MAX 里看的值）
inst.baud_rate       = 9600
inst.data_bits       = 8
inst.parity          = pyvisa.constants.Parity.none
inst.stop_bits       = pyvisa.constants.StopBits.one
inst.timeout         = 5000            # 5 秒
# 关键：告诉 PyVISA 写入后自动加 '\n'，读取时以 '\n' 作为结束
inst.write_termination = '\n'
inst.read_termination  = '\n'

# 现在你可以直接用 query，它内部会做 write+read
resp = inst.query('TTRD?')
print('温度:', resp)

# 或者手动
inst.write('TTRD?')      # 会实际发送 'TTRD?\n'
print(inst.read().strip())  # 会在读到 '\n' 时返回

inst.close()
