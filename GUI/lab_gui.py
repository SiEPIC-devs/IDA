from remi.gui import *
import os
import time
from multiprocessing import Process
from time import sleep, monotonic
from modern.config.stage_position import *
from modern.config.stage_config import *
from modern.utils.shared_memory import *
from modern.hal.motors_hal import AxisType
import gc

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
    def __init__(self, variable_name, left, top, width=650, height=650, border=False, bg_color=False, color = "#DCDCDC",
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
    def __init__(self, variable_name, left, top, width=300, height=30, position="absolute", percent=False, container=None):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_margin = "0px"
        self.multiple_selection_allowed = False
        self.savepath = "./res/"
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
                "background-color": "#e4e9f0",
                "color": "#1a1a1a",
                "border-bottom": "2px solid #c8c8c8",
                "padding": "1px 2px"
            }))
        self.append(trh)
        for r in range(row - 1):
            tr = TableRow()
            bg = "#ffffff" if r % 2 == 0 else "#f6f7f9"
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
        sp = StagePosition(shared_struct=raw)
        # write into shared memory
        sp.set_positions(AxisType.X, 123.456)
        sp.set_homed(AxisType.X)

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()

    def reader_pos(self):
        # give writer a moment
        sleep(0.1)
        shm, raw = open_shared_stage_position("stage_position")
        sp = StagePosition(shared_struct=raw)
        self.x_pos = sp.x.position
        self.y_pos = sp.y.position
        self.z_pos = sp.z.position
        self.fr_pos = sp.fr.position
        self.cp_pos = sp.cp.position

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()
