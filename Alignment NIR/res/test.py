import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os

filename = 'Heat_Map_2024-01-30_17-48-15.txt'
save_fig = True

data = np.loadtxt(filename, delimiter=',')

fig, ax = plt.subplots(figsize=(8, 8))
min_value = np.nanmin(data)
max_value = np.nanmax(data)

heatmap = ax.imshow(
    data,
    origin='upper',
    cmap='gist_heat_r',
    vmin=min_value - 3,
    vmax=max_value + 1,
    interpolation='nearest'
)

ax.set_title('Area Sweep Heat Map', fontsize=16)
ax.set_xlabel('X Position Index')
ax.set_ylabel('Y Position Index')

num_x = data.shape[1]
num_y = data.shape[0]
ax.set_xticks(np.arange(0, num_x, 1))
ax.set_yticks(np.arange(0, num_y, 1))

divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.05)
plt.colorbar(heatmap, cax=cax, label='Power (dBm)')

def onclick(event):
    if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
        x = int(np.round(event.xdata))
        y = int(np.round(event.ydata))
        if 0 <= x < num_x and 0 <= y < num_y:
            value = data[y, x]
            print(f"Clicked at (x={x}, y={y}), Value = {value:.3f} dBm")

fig.canvas.mpl_connect('button_press_event', onclick)

plt.tight_layout()
plt.show()

if save_fig:
    outname = os.path.splitext(filename)[0] + '.png'
    fig.savefig(outname, dpi=300)
    print(f"Saved figure as: {outname}")
