import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os

# ======== 参数配置 ========
filename = 'Heat_Map_2024-01-30_17-48-15.txt'  # 替换为你的文件名
save_fig = True  # 是否保存图片为PNG

# ======== 加载数据 ========
data = np.loadtxt(filename, delimiter=',')

# ======== 画热图 ========
fig, ax = plt.subplots(figsize=(10, 10))  # 画布大小（可调整）

heatmap = ax.imshow(
    data,
    origin='upper',
    cmap='gist_heat_r',        # 热度颜色
    interpolation='kaiser',    # 不做平滑，保持原网格感
)

ax.set_title('Area Sweep Heat Map', fontsize=16)
ax.set_xlabel('X Position Index')
ax.set_ylabel('Y Position Index')

# ======== 设置坐标轴刻度（0, 2, 4, 6, ...） ========
num_x = data.shape[1]
num_y = data.shape[0]
ax.set_xticks(np.arange(0, num_x, 1))
ax.set_yticks(np.arange(0, num_y, 1))

# 添加 colorbar（右侧颜色刻度条）
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.05)
plt.colorbar(heatmap, cax=cax, label='Power (dBm)')

# 显示网格（可选）
ax.grid(True, color='r', linestyle='--', linewidth=0.5)

# 显示图形
plt.show()

# ======== 可选保存图片 ========
if save_fig:
    outname = os.path.splitext(filename)[0] + '.png'
    plt.savefig(outname, dpi=300)
    print(f"Saved figure as: {outname}")
