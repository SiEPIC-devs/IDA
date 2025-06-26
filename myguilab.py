from remi.gui import *
from remi import start, App
import os

class StyledContainer(Container):
    def __init__(self, variable_name, left, top, width=650, height=650, border=False, bg_color=False, position="absolute", percent=False, container=None):
        super().__init__()
        self.css_position = f"{position}"
        self.css_left = f"{left}px"
        self.css_top = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.variable_name = variable_name
        if border == True:
            self.style["border"] = "2px solid #888"
            self.style["border-radius"] = "4px"
        if bg_color == True:
            self.style["background-color"] = "grey"
        if container:
            self.container = container
            self.container.append(self, self.variable_name)



class StyledButton(Button):
    """One‑liner to create a styled button with automatic press/release colors.

    Args:
        text (str): Button caption.
        variable_name (str): variable_name
        left (int|str): `css_left` in px (int) or any CSS string.
        top  (int|str): `css_top`  in px (int) or any CSS string.
        normal_color (str): background when idle.
        press_color  (str): background while pressing.
        width/height (str): CSS sizes, default 100×30 px.
    """

    def __init__(self, text, variable_name, left, top,
                 normal_color="#007BFF", press_color="#0056B3", width=100, height=30, font_size=80, position="absolute", percent=False, container=None):
        super().__init__(text)

        # --- base layout ---
        self.css_position = f"{position}"
        self.css_left = f"{left}px"
        self.css_top = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name

        # --- default style ---
        self.style.update({
            "background-color": normal_color,
            "color": "white",
            "border": "none",
            "border-radius": "4px",
            "box-shadow": "0 2px 5px rgba(0,0,0,0.2)",
            "cursor": "pointer",
        })
        # --- press / release feedback ---
        def press(widget, *args):
            widget.style["background-color"] = press_color
        def release(widget, *args):
            widget.style["background-color"] = normal_color
        self.onmousedown.do(press)
        self.onmouseup.do(release)
        if container:
            self.container = container
            self.container.append(self, self.variable_name)

class StyledLabel(Label):
    """Utility label: quick positioning + basic style tweaks.

    Args:
        text (str): label text
        left/top (int|str): absolute position
        width/height/font_size/color/align: optional styling shortcuts
    """
    def __init__(self, text, variable_name, left, top,
                 width=150, height=20, font_size=100, color="#444", align="left", position="absolute", percent=False, bold=False, flex=False, container=None):
        super().__init__(text)
        self.css_position = f"{position}"
        self.css_left  = f"{left}px"
        self.css_top   = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        if flex:
            self.style.update({
              "display": "flex",
               "justify-content": "right",  # 水平居中
               "align-items": "center"  # 垂直居中
        })
        else:
            self.css_text_align = align
        self.style["color"] = color
        if bold:
            self.style["font-weight"] = "bold"
        if container:
            self.container = container
            self.container.append(self, self.variable_name)


class StyledDropDown(DropDown):
    """Utility label: quick positioning + basic style tweaks.

    Args:
        text (str): label text
        left/top (int|str): absolute position
        width/height/font_size/color/align: optional styling shortcuts
    """
    def __init__(self, text, variable_name, left, top,
                 width=220, height=30, font_size=100, bg_color="#f9f9f9",
                 border = "1px solid #aaa", border_radius = "4px", padding = "3px", position="absolute", percent=False, container=None):
        super().__init__()
        self.append(text)
        self.css_position = f"{position}"
        self.css_left  = f"{left}px"
        self.css_top   = f"{top}px"
        if percent:
            self.css_width  = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        self.style["background-color"] = bg_color
        self.style["border"] = border
        self.style["border-radius"] = border_radius
        self.style["padding"] = padding
        if container:
            self.container = container
            self.container.append(self, self.variable_name)

class Terminal(TextInput):
    def __init__(self, container, variable_name, left, top,
                 width=220, height=30, percent=False):
        super().__init__(singleline=False)
        self.timestamp = -1
        self.attr_src = ""
        self.css_position = "absolute"
        self.css_left = f"{left}px"
        self.css_top = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.variable_name = variable_name
        self.style["border"] = "1px solid #444"
        self.style["background-color"] = "#1e1e1e"
        self.style["color"] = "#f0f0f0"
        self.style["font-family"] = "monospace"
        self.style["font-size"] = "13px"
        self.style["padding"] = "10px"
        self.style["border-radius"] = "6px"
        self.style["box-shadow"] = "0 0 6px rgba(0,0,0,0.3)"
        self.style["overflow-y"] = "auto"
        self.style["white-space"] = "pre-wrap"
        self.container = container
        self.container.append(self, self.variable_name)

    def terminal_refresh(self):
        file_path = os.path.join(os.getcwd(), "log.txt")
        try:
            filetime = os.path.getmtime(file_path)
        except:
            filetime = -1
        if filetime > self.timestamp:
            try:
                with open(file_path, mode="r", encoding="utf-8", errors="replace") as logfile:
                    log_text = logfile.read()
            except Exception as e:
                log_text = f"[Error reading log file] {e}"

            reversed_log = "\n".join(reversed(log_text.split("\n")))
            self.container.children["terminal_text"].set_text(reversed_log)
            self.timestamp = filetime

class StyledFileUploader(FileUploader):
    def __init__(self, variable_name, left, top, width=300, height=30, position="absolute", percent=False, container=None):
        super().__init__()
        self.css_left = f"{left}px"
        self.css_margin = "0px"
        self.css_position = f"{position}"
        self.css_top = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.multiple_selection_allowed = False
        self.savepath = "./res/"
        self.variable_name = variable_name
        if container:
            self.container = container
            self.container.append(self, self.variable_name)

class StyledTable(Table):
    def __init__(self, variable_name, left, top, height, table_width, headers, widths, row, position="absolute", container=None):
        super().__init__()
        self.css_position = f"{position}"
        self.css_left = f"{left}px"
        self.css_top = f"{top}px"
        self.css_width = f"{table_width}px"
        self.variable_name = variable_name

        self.style["border-collapse"] = "collapse"
        self.style["font-family"] = "Arial, sans-serif"
        self.style["font-size"] = "13.5px"
        self.style["color"] = "#2e2e2e"
        self.style["line-height"] = "1.4"

        trh = TableRow()
        for h, w in zip(headers, widths):
            th = TableItem(h, style={
                "width": f"{w}px",
                "height": f"{height}px",
                "font-weight": "bold",
                "text-align": "center",
                "background-color": "#e4e9f0",  # 柔和蓝灰
                "color": "#1a1a1a",
                "border-bottom": "2px solid #c8c8c8",
                "padding": "1px 2px"
            })
            trh.append(th)
        self.append(trh)

        for r in range(row - 1):
            tr = TableRow()
            bg_color = "#ffffff" if r % 2 == 0 else "#f6f7f9"
            for w in widths:
                td = TableItem("", style={
                    "width": f"{w}px",
                    "height": f"{height}px",
                    "text-align": "right",
                    "background-color": bg_color,
                    "border-bottom": "1px solid #ebebeb",
                    "padding": "1px 2px"
                })
                tr.append(td)
            self.append(tr)

        self.container = container
        self.container.append(self, self.variable_name)

class StyledCheckBox(CheckBox):
    def __init__(self, variable_name, left, top, width=30, height=30, position="absolute", percent=False, container=None):
        super().__init__()
        self.css_left = f"{left}px"
        self.css_margin = "0px"
        self.css_position = f"{position}"
        self.css_top = f"{top}px"
        if percent:
            self.css_width = f"{width}%"
            self.css_height = f"{height}%"
        else:
            self.css_width = f"{width}px"
            self.css_height = f"{height}px"
        self.variable_name = variable_name
        self.css_align_items = "left"
        if container:
            self.container = container
            self.container.append(self, self.variable_name)
