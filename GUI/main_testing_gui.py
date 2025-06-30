import shutil

from remi.gui import *
from lab_gui import *
from remi import start, App
import lab_coordinates
import threading
import math
import json
import os
import time
from lab_tsp import TSPSolver
import wx
import webview


def fmt(val):
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val)


class testing(App):
    """Testing GUI with per-device 5-second timer that updates status and elapsed/remaining time."""

    def __init__(self, *args, **kwargs):
        # ------------------------------------------------------------------ LOAD DATA
        self.init = False
        self.load_file()
        self.init = True
        # runtime flags
        self.running = False  # becomes True while measurement loop is active

        if "editing_mode" not in kwargs:
            super(testing, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ------------------------------------------------------------------ REMI HOOKS
    def idle(self):
        self.terminal.terminal_refresh()

        json_path = os.path.join(os.getcwd(), "database", "current_user.json")
        try:
            mtime = os.path.getmtime(json_path)
        except FileNotFoundError:
            mtime = None

        if mtime != getattr(self, "_user_mtime", None):
            self._user_mtime = mtime
            cur_user = ""
            if mtime is not None:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        cur_user = json.load(f).get("user", "").strip()
                except Exception as e:
                    print(f"[Warn] read json failed: {e}")

            new_path = os.path.join(os.getcwd(), "UserData", cur_user) if cur_user else ""
            if new_path and new_path != self.save_path_input.get_text():
                self.save_path_input.set_text(new_path)

    def main(self):
        return testing.construct_ui(self)

    # ------------------------------------------------------------------ UI BUILDERS
    def total_pages(self):
        return max(1, math.ceil(len(self.filtered_idx) / self.page_size))

    def build_table_rows(self):
        """Re-render table rows for current page."""
        table = self.table
        data_rows = list(table.children.values())[1:]  # children[0] is the header row

        start_i = self.page_index * self.page_size
        end_i = min(len(self.filtered_idx), start_i + self.page_size)
        page_idx_slice = self.filtered_idx[start_i:end_i]
        needed = len(page_idx_slice)
        cur = len(data_rows)

        # create extra rows if needed
        if needed > cur:
            for _ in range(needed - cur):
                tr = TableRow()
                for w in self.col_widths:
                    tr.append(TableItem("", style={
                        "width": f"{w}px",
                        "height": "30px",
                        "text-align": "center",
                        "border-bottom": "1px solid #ebebeb",
                        "padding": "1px 2px",
                        "overflow": "hidden",
                        "text-overflow": "ellipsis",
                        "white-space": "nowrap"
                    }))
                table.append(tr)
                data_rows.append(tr)

        # fill / hide rows
        for row_idx, row in enumerate(data_rows):
            if row_idx < needed:
                global_idx = page_idx_slice[row_idx]
                cells = list(row.children.values())
                bg = "#ffffff" if (start_i + row_idx) % 2 == 0 else "#f6f7f9"
                for c in cells:
                    c.style.update({"display": "table-cell", "background-color": bg})

                cells[0].set_text(self.devicename[global_idx])
                cells[0].attributes["title"] = self.devicename[global_idx]

                cells[1].set_text(self.status[global_idx])
                cells[1].attributes["title"] = self.status[global_idx]
            else:
                for c in row.children.values():
                    c.style["display"] = "none"

        # update pagination widgets
        self.page_input.set_text(str(self.page_index + 1))
        self.prev_btn.set_enabled(self.page_index != 0)
        self.next_btn.set_enabled(self.page_index + 1 < self.total_pages())
        self.total_page_label.set_text(f"/ {self.total_pages()}")

    # ------------------------------------------------------------------ THREAD HELPERS
    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    # ------------------------------------------------------------------ TIME FORMATTING
    @staticmethod
    def _sec2hms(seconds: float) -> str:
        seconds = max(0, int(seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _update_time_labels(self, elapsed_s: float, remaining_s: float):
        self.elapsed_time.set_text(self._sec2hms(elapsed_s))
        self.remaining_time.set_text(self._sec2hms(remaining_s))

    # ------------------------------------------------------------------ MEASUREMENT SEQUENCE
    def _measure_sequence(self):
        """Iterate over filtered devices, 5 s each, updating status and timers."""
        total = len(self.filtered_idx)
        if total == 0:
            return

        start_ts = time.time()
        for local_idx, global_idx in enumerate(self.filtered_idx):
            if not self.running:
                break  # stopped by user

            # wait 5 seconds in 1-second steps so labels refresh smoothly
            for _ in range(5):
                if not self.running:
                    break
                elapsed = time.time() - start_ts
                remaining = max(0, total * 5 - elapsed)
                self._update_time_labels(elapsed, remaining)
                time.sleep(1)

            if not self.running:
                break

            # mark device as done and refresh table
            self.status[global_idx] = "1"
            self.build_table_rows()

        # sequence ended (completed or stopped)
        self.running = False
        self._update_time_labels(0, 0)

    # ------------------------------------------------------------------ NAVIGATION
    def goto_prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.build_table_rows()

    def goto_next_page(self):
        if (self.page_index + 1) < self.total_pages():
            self.page_index += 1
            self.build_table_rows()

    def goto_input_page(self):
        page = int(self.page_input.get_text().strip())
        max_page = self.total_pages()
        if page < 1:
            self.page_index = 0
            self.page_input.set_text("1")
        elif page > max_page:
            self.page_index = max_page - 1
            self.page_input.set_text(f"{self.total_pages()}")
        else:
            self.page_index = page - 1
        self.build_table_rows()

    # ------------------------------------------------------------------ UI LAYOUT
    def construct_ui(self):
        testing_container = StyledContainer(container=None, variable_name="testing_container", left=0, top=0)

        # -------------------------------------------------- IMAGE BLOCK
        self.image_container = StyledContainer(container=testing_container, variable_name="image_container",
                                          left=0, top=0, height=370, width=385, bg_color=True, color="#DCDCDC")
        path_container = StyledContainer(container=testing_container, variable_name="path_container",
                                         left=10, top=370, height=110, width=370)
        StyledLabel(container=path_container, text="Save path", variable_name="save_path", left=5, top=20,
                    width=80, height=50, font_size=100, color="#222", align="left")
        StyledLabel(container=path_container, text="Save format", variable_name="save_format", left=5, top=60,
                    width=80, height=50, font_size=100, color="#222", align="left")
        self.save_path_input = StyledTextInput(container=path_container, variable_name="save_path_input", left=90, top=15,
                        width=162, height=28, position="absolute", text="")
        StyledDropDown(container=path_container, text=["Comma separated (.csv)", "Other"], variable_name="save_format_dd",
                       left=90, top=55, width=180, height=30)
        self.save_btn = StyledButton(container=path_container, text="Save", variable_name="Save",
                     left=275, top=15, width=90, height=30, normal_color="#007BFF", press_color="#0056B3")
        self.open_btn = StyledButton(container=path_container, text="Open Path", variable_name="open_path",
                     left=275, top=55, width=90, height=30, normal_color="#007BFF", press_color="#0056B3")
        self.display_plot = StyledImageBox(container=self.image_container, variable_name="display_plot", left=5, top=5,
                                           width=375, height=360, image_path="my_res:none.png")

        # -------------------------------------------------- SETTING BLOCK
        setting_container = StyledContainer(container=testing_container, variable_name="setting_container",
                                            left=400, top=10, height=475, width=240)
        StyledDropDown(container=setting_container, text=["Laser Sweep", "...."],
                       variable_name="laser_sweep", left=0, top=0, width=120, height=30)
        self.setting_btn = StyledButton(container=setting_container, text="Setting", variable_name="setting",
                                        left=131, top=2.5, width=50, height=25, normal_color="#007BFF", press_color="#0056B3")
        self.load_btn = StyledButton(container=setting_container, text="Load", variable_name="load",
                                     left=191, top=2.5, width=50, height=25, normal_color="#007BFF", press_color="#0056B3")

        headers = ["Device", "Status"]
        self.col_widths = [100, 40]
        table_container = StyledContainer(container=setting_container, variable_name="setting_container",
                                          left=0, top=40, height=260, width=235, border=True, overflow=True)
        self.table = StyledTable(container=table_container, variable_name="device_status",
                                 left=0, top=0, height=25, table_width=235, headers=headers, widths=self.col_widths, row=1)

        # ------ control buttons
        self.start_btn = StyledButton(container=setting_container, text="Start", variable_name="start",
                                      left=0, top=375, width=70, height=30, normal_color="#007BFF", press_color="#0056B3")
        self.stop_btn = StyledButton(container=setting_container, text="Stop", variable_name="stop",
                                     left=0, top=415, width=70, height=30, normal_color="#007BFF", press_color="#0056B3")

        StyledLabel(container=setting_container, text="Elapsed", variable_name="elapsed", left=80, top=382,
                    width=65, height=30, font_size=100, color="#222", align="right")
        StyledLabel(container=setting_container, text="Remaining", variable_name="remaining", left=80, top=422,
                    width=65, height=30, font_size=100, color="#222", align="right")
        self.elapsed_time = StyledLabel(container=setting_container, text="00:00:00", variable_name="elapsed_time",
                                         left=165, top=375, width=75, height=25, font_size=100, color="#222", border=True, flex=True)
        self.remaining_time = StyledLabel(container=setting_container, text="00:00:00", variable_name="remaining_time",
                                           left=165, top=415, width=75, height=25, font_size=100, color="#222", border=True, flex=True)

        # ---- pagination controls
        self.prev_btn = StyledButton(container=setting_container, text="◀", variable_name="prev_page",
                                     left=0, top=315, width=30, height=25)
        self.page_input = StyledTextInput(container=setting_container, variable_name="page_input",
                                          left=35, top=315, width=25, height=25)
        self.total_page_label = StyledLabel(container=setting_container, text=f"/ {self.total_pages()}",
                                            variable_name="page_total", left=80, top=315, width=40, height=25,
                                            flex=True, justify_content="left")
        self.jump_btn = StyledButton(container=setting_container, text="Go", variable_name="jump_page",
                                     left=110, top=315, width=40, height=25)
        self.next_btn = StyledButton(container=setting_container, text="▶", variable_name="next_page",
                                     left=155, top=315, width=30, height=25)
        self.tsp_btn = StyledButton(container=setting_container, text="Solve", variable_name="solve_tsp",
                                     left=190, top=315, width=50, height=25)

        # ---- event bindings
        self.prev_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_prev_page))
        self.next_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_next_page))
        self.jump_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_input_page))
        self.tsp_btn.do_onclick(lambda *_: self.run_in_thread(self.tsp_solve))
        self.start_btn.do_onclick(lambda *_: self.run_in_thread(self.start_sequence))
        self.stop_btn.do_onclick(lambda *_: self.run_in_thread(self.stop_sequence))
        self.load_btn.do_onclick(lambda *_: self.run_in_thread(self.load_file))
        self.open_btn.do_onclick(lambda *_: self.run_in_thread(self.open_file_path))
        self.save_btn.do_onclick(lambda *_: self.run_in_thread(self.save_file))
        self.setting_btn.do_onclick(lambda *_: self.run_in_thread(self.laser_sweep_setting))

        # -------------------------------------------------- TERMINAL BLOCK
        terminal_container = StyledContainer(container=testing_container, variable_name="terminal_container",
                                             left=0, top=500, height=150, width=650, bg_color=True)
        self.terminal = Terminal(container=terminal_container, variable_name="terminal_text",
                                 left=10, top=15, width=610, height=100)

        # vertical separator
        """StyledContainer(container=testing_container, variable_name="vertical_separator", left=390, top=0, width=1,
                        height=370, bg_color=True, color="#bbb")
        # horizontal separator
        StyledContainer(container=testing_container, variable_name="horizontal_separator", left=0, top=370, width=390,
                        height=1, bg_color=True, color="#bbb")"""

        # initial data load
        self.build_table_rows()
        self.testing_container = testing_container
        return testing_container

    # ------------------------------------------------------------------ SEQUENCE CONTROL
    def start_sequence(self):
        if not self.running:
            self.running = True
            self.run_in_thread(self._measure_sequence)

    def stop_sequence(self):
        self.running = False

    def tsp_solve(self):
        self.tsp_btn.set_enabled(False)
        self.display_plot.set_image("my_res:wait.png")
        solver = TSPSolver(
            coord_json="./database/coordinates.json",
            selected_json="./database/selection_serial.json",
            time_limit=20,
            output_dir="./res"
        )
        solver.solve_and_plot()
        print(solver.path)
        self.display_plot.set_image(f"my_res:{solver.path}")
        self.filtered_idx = solver.route_idx[1:]
        self.build_table_rows()
        self.tsp_btn.set_enabled(True)

    def load_file(self):
        file_path = os.path.join(os.getcwd(), "database", "selection_serial.json")
        if (self.init == False):
            self.serial_list = []
        else:
            with open(file_path, "r") as f:
                self.serial_list = json.load(f)
        self.timestamp = -1
        self.gds = lab_coordinates.coordinates(read_file=False, name="./database/coordinates.json")
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        self.devicename = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]
        # status list (0 = not done, 1 = done)
        self.status = ["0"] * len(self.devicename)
        self.filtered_idx = [i - 1 for i in self.serial_list]  # current filter result (list of global indices)
        self.page_size = 50
        self.page_index = 0
        if (self.init == True):
            self.build_table_rows()

    def open_file_path(self):
        app = wx.App(False)
        with wx.DirDialog(None, "Select folder to save results",
                          style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.save_path_input.set_text(dlg.GetPath())
                print(f"You choose {dlg.GetPath()}")
        app.Destroy()

    def save_file(self):
        src = os.path.join(os.getcwd(), "database", "selection_serial.json")
        dest_dir = self.save_path_input.get_text().strip()

        if not os.path.isfile(src):
            print(f"[Error] {src} does not exist.\n")
            return
        if not dest_dir:
            print("[Error] Save path is empty.\n")
            return
        if not os.path.isdir(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except Exception as e:
                print(f"[Error] Create dir failed: {e}\n")
                return

        dest = os.path.join(dest_dir, "selection_serial.json")
        try:
            shutil.copy(src, dest)
            print(f"[OK] Copied to {dest}\n")
        except Exception as e:
            print(f"[Error] Copy failed: {e}\n")

    def laser_sweep_setting(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7001",
            width=262,
            height=305,
            resizable=True,
            on_top=True,
        )

def run_remi():
    start(
        testing,
        address="0.0.0.0",
        port=9004,
        start_browser=False,
        multiple_instance=False,
        enable_file_cache=False,
    )

def get_local_ip():
    """Automatically detect local LAN IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Fake connect to get route IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # fallback


    # --------------------------------------------------------------------------- MAIN
if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    local_ip = get_local_ip()
    webview.create_window(
        "Main Window",
        f"http://{local_ip}:9004",
        width=0,
        height=0,
        resizable=True,
        hidden=True,
    )
    webview.start()
