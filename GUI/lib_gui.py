from remi.gui import *
import os
import time
from multiprocessing import Process
from time import sleep, monotonic
from motors.config.stage_position import *
from motors.config.stage_config import *
from motors.utils.shared_memory import *
from motors.hal.motors_hal import AxisType
import gc
import plotly.express as px
from pathlib import Path
import matplotlib.pyplot as plt
import shutil
import numpy as np
import pandas as pd
from scipy.io import savemat
from scipy.ndimage import gaussian_filter
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib, logging
matplotlib.use("QtAgg")
web_w = -6
web_h = -17

_ORIG_WSGI_LOG = None
_ORIG_HTTP_LOG = None
_SILENCED = False

def _silence_remi_and_http_logs():
    """静音 remi 相关 logger + HTTP 访问日志（GET / ...）。"""
    global _ORIG_WSGI_LOG, _ORIG_HTTP_LOG, _SILENCED
    if _SILENCED:
        return

    for name in ("remi", "remi.server", "remi.request", "remi.gui",
                 "websocket", "websockets"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.CRITICAL)
        lg.propagate = False
        if not lg.handlers:
            lg.addHandler(logging.NullHandler())

    try:
        import wsgiref.simple_server as _wsgi
        if not hasattr(_wsgi.WSGIRequestHandler, "_orig_log_message"):
            _wsgi.WSGIRequestHandler._orig_log_message = _wsgi.WSGIRequestHandler.log_message
        _wsgi.WSGIRequestHandler.log_message = lambda *a, **k: None
        _ORIG_WSGI_LOG = _wsgi.WSGIRequestHandler._orig_log_message
    except Exception:
        pass

    try:
        import http.server as _http
        if not hasattr(_http.BaseHTTPRequestHandler, "_orig_log_message"):
            _http.BaseHTTPRequestHandler._orig_log_message = _http.BaseHTTPRequestHandler.log_message
        _http.BaseHTTPRequestHandler.log_message = lambda *a, **k: None
        _ORIG_HTTP_LOG = _http.BaseHTTPRequestHandler._orig_log_message
    except Exception:
        pass

    _SILENCED = True

def enable_remi_logs(level=logging.INFO):
    global _SILENCED
    try:
        import wsgiref.simple_server as _wsgi
        if hasattr(_wsgi.WSGIRequestHandler, "_orig_log_message"):
            _wsgi.WSGIRequestHandler.log_message = _wsgi.WSGIRequestHandler._orig_log_message
    except Exception:
        pass
    try:
        import http.server as _http
        if hasattr(_http.BaseHTTPRequestHandler, "_orig_log_message"):
            _http.BaseHTTPRequestHandler.log_message = _http.BaseHTTPRequestHandler._orig_log_message
    except Exception:
        pass

    for name in ("remi", "remi.server", "remi.request", "remi.gui",
                 "websocket", "websockets"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.propagate = True

    _SILENCED = False

if os.environ.get("REMI_QUIET", "1") != "0":
    _silence_remi_and_http_logs()

def apply_common_style(widget, left, top, width, height, position="absolute", percent=False):
    widget.css_position = position
    widget.css_left = f"{left}px"
    widget.css_top = f"{top}px"
    if percent:
        widget.css_width = f"{width}%"
        widget.css_height = f"{height}%"
    else:
        widget.css_width = f"{width}px"
        widget.css_height = f"{height}px"

class StyledContainer(Container):
    def __init__(self, variable_name, left, top, width=650, height=650, border=False, bg_color=False, color = "#707070",
                 position="absolute", percent=False, overflow=False, container=None, line="1.5px solid #888"):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.variable_name = variable_name
        if border:
            self.style["border"] = line
            self.style["border-radius"] = "4px"
        if bg_color:
            self.style["background-color"] = color
        if overflow:
            self.style.update({
                "overflow": "auto",
                "overflow-y": "scroll",
                "overflow-x": "hidden",
                "max-height": "320px",
                "scrollbar-width": "thin",
                "border-radius": "4px",
                "padding-right": "4px"
            })
        if container:
            container.append(self, self.variable_name)

class StyledButton(Button):
    def __init__(self, text, variable_name, left, top,
                 normal_color="#007BFF", press_color="#0056B3",
                 width=100, height=30, font_size=90,
                 position="absolute", percent=False, container=None):
        super().__init__(text)
        apply_common_style(self, left, top, width, height, position, percent)

        self.variable_name  = variable_name
        self.normal_color   = normal_color
        self.press_color    = press_color
        self.style.update({
            "background-color": normal_color,
            "color": "white",
            "border": "none",
            "border-radius": "4px",
            "box-shadow": "0 2px 5px rgba(0,0,0,0.2)",
            "cursor": "pointer",
            "font-size": f"{font_size}%"
        })

        # --- 视觉反馈 ---
        self.onmousedown.do(lambda w,*a: w.style.update(
            {"background-color": self.press_color}))
        def _recover_and_call(w,*a):
            w.style.update({"background-color": self.normal_color})
            # 后台线程跑业务，避免阻塞 UI
            if hasattr(self, "_user_callback"):
                threading.Thread(
                    target=self._user_callback,
                    args=(w,*a),
                    daemon=True
                ).start()
        self.onmouseup.do(_recover_and_call)
        self.onmouseleave.do(lambda w,*a: w.style.update(
            {"background-color": self.normal_color}))

        if container:
            container.append(self, variable_name)

    # 用户用这个注册真正逻辑
    def do_onclick(self, cb):
        #self._user_callback = cb
        self._user_callback = lambda *_: cb()


class StyledLabel(Label):
    def __init__(self, text, variable_name, left, top,
                 width=150, height=20, font_size=100, color="#444", align="left", position="absolute", percent=False,
                 bold=False, flex=False, justify_content="center", on_line=False, border=False, container=None):
        super().__init__(text)
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        if flex:
            self.style.update({
                "display": "flex",
                "justify-content": justify_content,
                "align-items": "center"
            })
        else:
            self.css_text_align = align
        self.style["color"] = color
        if bold:
            self.style["font-weight"] = "bold"
        if on_line:
            self.style["background-color"] = "white"
        if border:
            self.style["border"] = "1.5px solid #888"
            self.style["border-radius"] = "4px"
        if container:
            container.append(self, self.variable_name)

class StyledDropDown(DropDown):
    def __init__(self, text, variable_name, left, top,
                 width=220, height=30, font_size=100, bg_color="#f9f9f9",
                 border="1px solid #aaa", border_radius="4px", padding="3px", position="absolute", percent=False, container=None):
        super().__init__()
        self.append(text)
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        self.style.update({
            "background-color": bg_color,
            "border": border,
            "border-radius": border_radius,
            "padding": padding
        })
        if container:
            container.append(self, self.variable_name)

class Terminal(TextInput):
    def __init__(self, container, variable_name, left, top, width=220, height=30, percent=False):
        super().__init__(singleline=False)
        self.timestamp = -1
        self.attr_src = ""
        apply_common_style(self, left, top, width, height, percent=percent)
        self.variable_name = variable_name
        self.style.update({
            "border": "1px solid #444",
            "background-color": "#1e1e1e",
            "color": "#f0f0f0",
            "font-family": "monospace",
            "font-size": "13px",
            "padding": "10px",
            "border-radius": "6px",
            "box-shadow": "0 0 6px rgba(0,0,0,0.3)",
            "overflow-y": "auto",
            "white-space": "pre-wrap"
        })
        container.append(self, self.variable_name)
        self.container = container

    def terminal_refresh(self):
        path = os.path.join(os.getcwd(), "log.txt")
        try:
            filetime = os.path.getmtime(path)
        except:
            filetime = -1
        if filetime > self.timestamp:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    log_text = f.read()
            except Exception as e:
                log_text = f"[Error reading log file] {e}"
            reversed_log = "\n".join(reversed(log_text.split("\n")))
            self.container.children["terminal_text"].set_text(reversed_log)
            self.timestamp = filetime

class StyledFileUploader(FileUploader):
    def __init__(self, variable_name, left, top, width=300, height=30, position="absolute", percent=False, container=None, savepath="./res/"):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_margin = "0px"
        self.multiple_selection_allowed = False
        self.savepath = savepath
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledTable(Table):
    def __init__(self, variable_name, left, top, height, table_width, headers, widths, row, position="absolute", container=None):
        super().__init__()
        apply_common_style(self, left, top, table_width, height, position)
        self.variable_name = variable_name
        self.style.update({
            "table-layout": "fixed",
            "width": f"{table_width}px",
            "border-collapse": "collapse",
            "font-family": "Arial, sans-serif",
            "font-size": "13.5px",
            "color": "#2e2e2e",
            "line-height": "1.4"
        })
        trh = TableRow()
        for h, w in zip(headers, widths):
            trh.append(TableItem(h, style={
                "width": f"{w}px",
                "height": f"{height}px",
                "font-weight": "bold",
                "text-align": "center",
                "background-color": "#6f7a8a",
                "color": "#1a1a1a",
                "border-bottom": "2px solid #c8c8c8",
                "padding": "1px 2px"
            }))
        self.append(trh)
        for r in range(row - 1):
            tr = TableRow()
            bg = "#9aa3af" if r % 2 == 0 else "#7b8494"
            for w in widths:
                tr.append(TableItem("", style={
                    "width": f"{w}px",
                    "height": f"{height}px",
                    "text-align": "right",
                    "background-color": bg,
                    "border-bottom": "1px solid #ebebeb",
                    "padding": "1px 2px"
                }))
            self.append(tr)
        if container:
            container.append(self, self.variable_name)

class StyledCheckBox(CheckBox):
    def __init__(self, variable_name, left, top, width=30, height=30, position="absolute", percent=False, container=None):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_margin = "5px"
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledTextInput(TextInput):
    def __init__(self, variable_name, left, top, width=150, height=30, text="", position="absolute", percent=False, container=None):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.set_text(text)
        self.variable_name = variable_name
        self.style.update({
            "padding": "0 8px",
            "border": "1px solid #aaa",
            "border-radius": "4px",
            "box-shadow": "inset 0 1px 3px rgba(0,0,0,0.1)",
            "background-color": "#fafafa",
            "font-size": "15px",
            "color": "#333",
            "line-height": f"{height}px",
            "overflow": "hidden",
            "text-align": "center",
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
            "white-space": "nowrap",
            "overflow-x": "hidden",
            "overflow-y": "hidden",
            "resize": "none"
        })
        if container:
            container.append(self, self.variable_name)

class StyledImageBox(Image):
    def __init__(self, image_path, variable_name, left, top,
                 width=400, height=300, position="absolute", percent=False, container=None):
        super().__init__(image_path, width=width, height=height)
        apply_common_style(self, left, top, width, height, position, percent)
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledSpinBox(SpinBox):
    def __init__(self, variable_name, left, top,
                 width=150, height=30, value=0,
                 step=1, min_value=None, max_value=None,
                 position="absolute", percent=False,
                 container=None):
        super().__init__()

        apply_common_style(self, left, top, width, height, position, percent)

        self.set_value(str(value))
        self.attr_step = str(step)
        if min_value is not None:
            self.attr_min = str(min_value)
        if max_value is not None:
            self.attr_max = str(max_value)

        self.variable_name = variable_name

        self.style.update({
            "padding-top": "0px",
            "padding-right": "0px",
            "padding-bottom": "0px",
            "padding-left": "15px",
            "border": "1px solid #aaa",
            "border-radius": "4px",
            "box-shadow": "inset 0 1px 3px rgba(0,0,0,0.1)",
            "background-color": "#fafafa",
            "font-size": "15px",
            "color": "#333",
            "line-height": f"{height}px",
            "text-align": "center",
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
            "white-space": "nowrap",
            "overflow": "hidden",
            "overflow-x": "hidden",
            "overflow-y": "hidden",
            "resize": "none"
        })

        if container:
            container.append(self, self.variable_name)

class Memory():
    def __init__(self):
        self.x_pos = 0
        self.y_pos = 0
        self.z_pos = 0
        self.fr_pos = 0
        self.cp_pos = 0

    def writer_pos(self):
        shm, raw = open_shared_stage_position()
        print(raw)
        sp = StagePosition(shared_struct=raw)
        # write into shared memory
        sp.set_positions(AxisType.X, 123.456)
        #sp.set_homed(AxisType.X)

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()

    def reader_pos(self):
        # give writer a moment
        # sleep(0.1)
        shm, raw = open_shared_stage_position("stage_position")
        sp = StagePosition(shared_struct=raw)
        self.x_pos = round(sp.x.position, 1)
        self.y_pos = round(sp.y.position, 1)
        self.z_pos = round(sp.z.position, 1)
        self.fr_pos = round(sp.fr.position, 1)
        self.cp_pos = round(sp.cp.position, 1)

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()

class File():
    def __init__(self, filename, data_name, data_info="", data_name2="", data_info2=""):
        self.filename = filename
        self.data_name = data_name
        self.data_name2 = data_name2
        self.data_info = data_info
        self.data_info2 = data_info2

    def _safe_write(self, data, filepath):
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_filepath, filepath)  # 原子替换

    def save(self):
        filepath = os.path.join("database", f"{self.filename}.json")
        os.makedirs("database", exist_ok=True)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        data[self.data_name] = self.data_info
        if self.data_info2 != "":
            data[self.data_name2] = self.data_info2

        self._safe_write(data, filepath)

    def init(self):
        filepath = os.path.join("database", f"{self.filename}.json")
        os.makedirs("database", exist_ok=True)
        data = {
            "User": "Guest",
            "Project": "MyProject",
            "User_add": "Guest",
            "Image": "TSP/none.png",
            "Web": "",
            "FileFormat": {"csv": 1, "mat": 1, "png": 1, "pdf": 1},
            "FilePath": "",
            "Limit": {"x": "Yes", "y": "Yes", "z": "Yes", "chip": "Yes", "fiber": "Yes"},
            "FineA": {"window_size": 20, "step_size": 2, "max_iters": 5, "detector": 1},
            "AreaS": {"x_size": 20.0, "x_step": 1.0, "y_size": 20.0, "y_step": 1.0, "plot": "New"},
            "Sweep": {"wvl": 1550.0, "speed": 1.0, "power": 1.0, "step": 0.001, "start": 1540.0, "end": 1580.0, "done": "Laser On", "sweep": 0, "on": 0},
            "ScanPos": {"x": 0, "y": 0, "move": 0},
            "StagePos": {"x": 0, "y": 0},
            "AutoSweep": 0,
            "Configuration": {"stage": "", "sensor": "", "tec": ""},
            "Configuration_check": {"stage": 0, "sensor": 0, "tec": 0},
            "Port": {"stage": 4, "sensor": 20, "tec": 3},
            "DeviceName": "Default",
            "DeviceNum": 0
        }

        self._safe_write(data, filepath)

class plot():
    def __init__(self, x=None, y=None, filename=None, fileTime=None, user=None, name=None, project=None, data=None,
                 file_format=None, file_path=""):
        if file_format is None:
            self.file_format = {"csv": 1, "mat": 1, "png": 1, "pdf": 1}
        else:
            self.file_format = file_format
        self.x = x
        self.y = y
        self.filename = filename
        self.fileTime = fileTime
        self.user = user
        self.name = name
        self.project = project
        self.data = data
        self.file_path = file_path

    def heat_map(self):
        fig, ax = plt.subplots(figsize=(7, 7))
        min_value = np.nanmin(self.data)
        max_value = np.nanmax(self.data)
        heatmap = ax.imshow(
            self.data,
            origin='lower',
            cmap='gist_heat_r',
            vmin=min_value - 3,
            vmax=max_value + 1,
            interpolation='nearest'
        )

        ax.set_title('Area Sweep Heat Map', fontsize=16)
        ax.set_xlabel('X Position Index')
        ax.set_ylabel('Y Position Index')

        num_x = self.data.shape[1]
        num_y = self.data.shape[0]
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
                    value = self.data[y, x]
                    print(f"Clicked at (x={x}, y={y}), Value = {value:.3f} dBm")
                    position = {
                        "x": x,
                        "y": y,
                        "move": 1
                    }
                    file = File("shared_memory", "ScanPos", position)
                    file.save()

        fig.canvas.mpl_connect('button_press_event', onclick)
        plt.show()

        output_dir = os.path.join(".", "UserData", self.user, self.project, "HeatMap")
        os.makedirs(output_dir, exist_ok=True)

        # Save figure
        fig_path = os.path.join(output_dir, f"{self.filename}_{self.fileTime}.png")
        fig.savefig(fig_path, dpi=300)
        print(f"✅ Saved heatmap figure: {fig_path}")

        # Save data as CSV
        csv_path = os.path.join(output_dir, f"{self.filename}_{self.fileTime}.csv")
        np.savetxt(csv_path, self.data, delimiter=",", fmt="%.4f")
        print(f"✅ Saved heatmap data: {csv_path}")

        plt.close(fig)

    def _cleanup_old_plots(self, keep: int = 1) -> None:
        self.output_dir = Path("./res/spectral_sweep")
        files = sorted(
            (p for p in self.output_dir.glob("spectral_sweep_*.png")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for p in files[keep:]:
            try:
                p.unlink()
            except OSError:
                pass

    def generate_plots(self):
        x_axis = self.x
        y_values = self.y
        filename = self.filename
        fileTime = self.fileTime
        user = self.user
        name = self.name
        project = self.project
        path = os.path.join(".", "UserData", user, project, "Spectrum", name)
        file_path = os.path.join(self.file_path, user, project, "Spectrum", name)

        try:
            plots = {"Wavelength [nm]": x_axis}
            plotnames = []
            for element in range(0, len(y_values)):
                plotname = "Detector " + str(element + 1)
                plots[plotname] = y_values[element]
                plotnames.append(plotname)
            fig = px.line(plots, x="Wavelength [nm]", y=plotnames,
                          labels={'value': "Power [dBm]", 'x': "Wavelength [nm]"})
            for i in range(0, len(y_values)):
                fig.data[i].name = str(i + 1)
            fig.update_layout(legend_title_text="Detector")
            output_html = os.path.join(path, f"{filename}_{fileTime}.html")
            os.makedirs(os.path.dirname(output_html), exist_ok=True)
            fig.write_html(output_html)

            output_html2 = os.path.join(file_path, f"{filename}_{fileTime}.html")
            os.makedirs(os.path.dirname(output_html2), exist_ok=True)
            fig.write_html(output_html2)
        except Exception as e:
            try:
                print("Exception generating html plot")
                print(e)
            finally:
                e = None
                del e
        if self.file_format["csv"] == 1:
            try:
                df = pd.DataFrame({"Wavelength [nm]": x_axis})
                for element in range(len(y_values)):
                    df[f"Detector {element + 1}"] = y_values[element]
                output_csv = os.path.join(path, f"{filename}_{fileTime}.csv")
                os.makedirs(os.path.dirname(output_csv), exist_ok=True)
                df.to_csv(output_csv, index=False)

                output_csv2 = os.path.join(file_path, f"{filename}_{fileTime}.csv")
                os.makedirs(os.path.dirname(output_csv2), exist_ok=True)
                df.to_csv(output_csv2, index=False)
            except Exception as e:
                print("Exception saving csv")
                print(e)

        if self.file_format["mat"] == 1:
            try:
                detectors_matrix = np.column_stack(y_values) if len(y_values) > 0 else np.empty((len(x_axis), 0))
                detector_names = [f"Detector {i + 1}" for i in range(len(y_values))]
                mat_dict = {
                    "wavelength_nm": np.asarray(x_axis),
                    "detectors_dbm": np.asarray(detectors_matrix),
                    "detector_names": np.array(detector_names, dtype=object),
                    "filename": np.array(filename, dtype=object),
                    "fileTime": np.array(fileTime, dtype=object),
                    "user": np.array(user, dtype=object),
                    "project": np.array(project, dtype=object),
                    "name": np.array(name, dtype=object),
                }
                output_mat = os.path.join(path, f"{filename}_{fileTime}.mat")
                os.makedirs(os.path.dirname(output_mat), exist_ok=True)
                savemat(output_mat, mat_dict)

                output_mat2 = os.path.join(file_path, f"{filename}_{fileTime}.mat")
                os.makedirs(os.path.dirname(output_mat2), exist_ok=True)
                savemat(output_mat2, mat_dict)
            except Exception as e:
                print("Exception saving mat")
                print(e)

        try:
            image_dpi = 20
            plt.figure(figsize=(100 / image_dpi, 100 / image_dpi), dpi=image_dpi)
            for element in range(0, len(y_values)):
                plt.plot(x_axis, y_values[element], linewidth=0.2, label=f"{element+1}")
            plt.xlabel("Wavelength [nm]")
            plt.ylabel("Power [dBm]")
            plt.legend(title="Detector", fontsize=8, title_fontsize=9, ncol=2, loc='upper right')
            plt.tight_layout()

            if self.file_format["pdf"] == 1:
                output_pdf = os.path.join(path, f"{filename}_{fileTime}.pdf")
                os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
                plt.savefig(output_pdf, dpi=image_dpi)

                output_pdf2 = os.path.join(file_path, f"{filename}_{fileTime}.pdf")
                os.makedirs(os.path.dirname(output_pdf2), exist_ok=True)
                plt.savefig(output_pdf2, dpi=image_dpi)

            if self.file_format["png"] == 1:
                output_png2 = os.path.join(path, f"{filename}_{fileTime}.png")
                os.makedirs(os.path.dirname(output_png2), exist_ok=True)
                plt.savefig(output_png2, dpi=300)

                output_png3= os.path.join(file_path, f"{filename}_{fileTime}.png")
                os.makedirs(os.path.dirname(output_png3), exist_ok=True)
                plt.savefig(output_png3, dpi=300)

            output_png = os.path.join(".", "res", "spectral_sweep", f"{filename}_{fileTime}.png")
            os.makedirs(os.path.dirname(output_png), exist_ok=True)
            plt.savefig(output_png, dpi=300)
            self._cleanup_old_plots(keep=1)

            plt.close()
            file = File("shared_memory", "Image", f"spectral_sweep/{filename}_{fileTime}.png", "Web", output_html)
            file.save()
        except Exception as e:
            try:
                print("Exception generating pdf plot")
                print(e)
            finally:
                e = None
                del e

import sys
from multiprocessing import Event, Value
from ctypes import c_int
from PyQt5.QtWidgets import QApplication, QProgressDialog, QProgressBar
from PyQt5.QtCore import Qt, QTimer

def run_busy_dialog(done_val: Value, cancel_evt: Event):
    app = QApplication(sys.argv)

    class CenteredBusyDialog(QProgressDialog):
        def __init__(self):
            super().__init__("In Progress…", "Cancel", 0, 0)  # 不定进度
            self.setWindowTitle("In Progress")
            self.setWindowModality(Qt.ApplicationModal)
            self.setMinimumDuration(0)
            self.setAutoClose(False)
            self.setAutoReset(False)
            self.resize(420, 160)

            bar = self.findChild(QProgressBar)
            if bar:
                bar.setTextVisible(False)
                bar.setFixedHeight(26)

            # 轮询主进程写入的完成标志
            self._poll = QTimer(self)
            self._poll.timeout.connect(self._check_done)
            self._poll.start(80)

            self.canceled.connect(self._on_cancel)

        def _on_cancel(self):
            with done_val.get_lock():
                done_val.value = -1
            cancel_evt.set()
            self._poll.stop()
            self.close()

        def _check_done(self):
            if done_val.value == 1:
                self._poll.stop()
                self.close()

        def showEvent(self, e):
            super().showEvent(e)
            screen = QApplication.primaryScreen()
            if screen:
                geo = self.frameGeometry()
                geo.moveCenter(screen.availableGeometry().center())
                self.move(geo.topLeft())

    dlg = CenteredBusyDialog()
    dlg.show()
    sys.exit(app.exec_())