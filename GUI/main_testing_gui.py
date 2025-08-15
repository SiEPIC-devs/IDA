from lab_gui import *
from remi import start, App
import lab_coordinates, threading, math, json, os, time, webview, wx, shutil
from lab_tsp import TSPSolver
w = 6
h = 16
command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")


def fmt(val):
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val)


class testing(App):
    """Testing GUI with per-device 5-second timer that updates status and elapsed/remaining time."""

    def __init__(self, *args, **kwargs):
        # ------------------------------------------------------------------ LOAD DATA
        self._user_mtime = None
        self._first_command_check = True
        self._user_stime = None
        self.notopen = True
        self.running = False
        self.cur_user = ""
        self.image_path = ""
        self.serial_list = set()
        self.device_num = 0
        self.auto_sweep = 0

        self.gds = None
        self.number = None
        self.coordinate = None
        self.polarization = None
        self.wavelength = None
        self.type = None
        self.devicename = None
        self.status = None
        self.filtered_idx = []
        self.page_size = 50
        self.page_index = 0

        self._last_user = ""
        self._last_user_paths = []
        self.pre_num = 1

        self.new_command = {}

        if "editing_mode" not in kwargs:
            super(testing, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ------------------------------------------------------------------ REMI HOOKS
    def idle(self):
        self.terminal.terminal_refresh()
        try:
            mtime = os.path.getmtime(command_path)
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            mtime = None
            stime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.run_in_thread(self.execute_command)

        if stime != self._user_stime:
            self._user_stime = stime
            self.cur_user = ""
            if stime is not None:
                try:
                    with open(shared_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.cur_user = data.get("User", "").strip()
                        self.image_path = data.get("Image", "")
                        self.display_plot.set_image(f"my_res:{self.image_path}")
                        self.serial_list = set(data.get("Selection", []))
                        self.device_num = data.get("DeviceNum", 0)
                        self.auto_sweep = data.get("AutoSweep", 0)

                except Exception as e:
                    print(f"[Warn] read json failed: {e}")

            if self.auto_sweep == 1 and self.device_num != self.pre_num:
                self.status[self.device_num - 1] = "1"
                self.build_table_rows()
                self.pre_num = self.device_num

            self.update_path_dropdown()

    def main(self):
        return testing.construct_ui(self)

    # ------------------------------------------------------------------ UI BUILDERS
    def update_path_dropdown(self):
        """Update save format dropdown if user or contents change."""
        if not self.cur_user:
            return

        user_dir = os.path.join("UserData", self.cur_user)
        if not os.path.isdir(user_dir):
            return

        entries = [
            name for name in os.listdir(user_dir)
            if os.path.isdir(os.path.join(user_dir, name)) or name.endswith((".json", ".txt", ".csv"))
        ]
        entries_sorted = sorted(entries)

        if self.cur_user != self._last_user or entries_sorted != self._last_user_paths:
            self.path_dd.empty()
            self.path_dd.append("All")
            for name in entries_sorted:
                self.path_dd.append(name)
            self._last_user = self.cur_user
            self._last_user_paths = entries_sorted

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
        testing_container = StyledContainer(
            container=None, variable_name="testing_container", left=0, top=0
        )

        # -------------------------------------------------- IMAGE BLOCK
        self.image_container = StyledContainer(
            container=testing_container, variable_name="image_container",
            left=0, top=0, height=370, width=385, bg_color=True, color="#DCDCDC"
        )

        path_container = StyledContainer(
            container=testing_container, variable_name="path_container",
            left=10, top=370, height=110, width=370
        )

        StyledLabel(
            container=path_container, text="Save path", variable_name="save_path",
            left=5, top=20, width=80, height=50, font_size=100, color="#222", align="left"
        )

        StyledLabel(
            container=path_container, text="Save file", variable_name="save_file",
            left=5, top=60, width=80, height=50, font_size=100, color="#222", align="left"
        )

        self.save_path_input = StyledTextInput(
            container=path_container, variable_name="save_path_input",
            left=90, top=15, width=162, height=28, position="absolute", text=desktop_path
        )

        self.path_dd = StyledDropDown(
            container=path_container, text=["All", "HeatMap", "Spectrum"], variable_name="save_file_dd",
            left=90, top=55, width=180, height=30
        )

        self.save_btn = StyledButton(
            container=path_container, text="Save", variable_name="Save",
            left=275, top=15, width=90, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        self.open_btn = StyledButton(
            container=path_container, text="Open Path", variable_name="open_path",
            left=275, top=55, width=90, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        self.display_plot = StyledImageBox(
            container=self.image_container, variable_name="display_plot",
            left=5, top=5, width=375, height=360, image_path="my_res:TSP/none.png"
        )

        # -------------------------------------------------- SETTING BLOCK
        setting_container = StyledContainer(
            container=testing_container, variable_name="setting_container", left=400, top=10, height=475, width=240
        )

        StyledDropDown(
            container=setting_container, text=["Laser Sweep", "...."], variable_name="laser_sweep",
            left=0, top=0, width=120, height=30
        )

        self.setting_btn = StyledButton(
            container=setting_container, text="Setting", variable_name="setting",
            left=131, top=2.5, width=50, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.load_btn = StyledButton(
            container=setting_container, text="Load", variable_name="load",
            left=191, top=2.5, width=50, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        headers = ["Device", "Status"]
        self.col_widths = [100, 40]
        table_container = StyledContainer(
            container=setting_container, variable_name="setting_container",
            left=0, top=40, height=230, width=235, border=True, overflow=True
        )

        self.table = StyledTable(
            container=table_container, variable_name="device_status",
            left=0, top=0, height=25, table_width=235, headers=headers, widths=self.col_widths, row=1
        )

        # ------ control buttons
        self.start_btn = StyledButton(
            container=setting_container, text="Start", variable_name="start",
            left=0, top=375, width=70, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        self.stop_btn = StyledButton(
            container=setting_container, text="Stop", variable_name="stop",
            left=0, top=415, width=70, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        StyledLabel(
            container=setting_container, text="Elapsed", variable_name="elapsed",
            left=80, top=382, width=65, height=30, font_size=100, color="#222", align="right"
        )

        StyledLabel(
            container=setting_container, text="Remaining", variable_name="remaining",
            left=80, top=422, width=65, height=30, font_size=100, color="#222", align="right"
        )

        self.elapsed_time = StyledLabel(
            container=setting_container, text="00:00:00", variable_name="elapsed_time",
            left=165, top=375, width=75, height=25, font_size=100, color="#222", border=True, flex=True
        )

        self.remaining_time = StyledLabel(
            container=setting_container, text="00:00:00", variable_name="remaining_time",
            left=165, top=415, width=75, height=25, font_size=100, color="#222", border=True, flex=True
        )

        # ---- pagination controls
        self.prev_btn = StyledButton(
            container=setting_container, text="◀", variable_name="prev_page",
            left=20, top=285, width=35, height=25
        )

        self.page_input = StyledTextInput(
            container=setting_container, variable_name="page_input", left=63, top=285, width=25, height=25
        )

        self.total_page_label = StyledLabel(
            container=setting_container, text=f"/ {self.total_pages()}", variable_name="page_total",
            left=108, top=285, width=40, height=25, flex=True, justify_content="left"
        )

        self.jump_btn = StyledButton(
            container=setting_container, text="Go", variable_name="jump_page", left=138, top=285, width=40, height=25
        )

        self.next_btn = StyledButton(
            container=setting_container, text="▶", variable_name="next_page", left=186, top=285, width=35, height=25
        )

        self.tsp_btn = StyledButton(
            container=setting_container, text="Solve", variable_name="solve_tsp", left=0, top=335, width=70, height=30
        )

        self.solve_time = StyledSpinBox(
            container=setting_container, variable_name="solve_time_spin",
            left=85, top=337, width=50, height=25, min_value=1, max_value=600, step=1, value=60
        )

        StyledLabel(
            container=setting_container, text="s", variable_name="second_label",
            left=160, top=335, width=20, height=30, flex=True, justify_content="left"
        )

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
        terminal_container = StyledContainer(
            container=testing_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text",
            left=10, top=15, width=610, height=100
        )

        # initial data load
        self.start_btn.set_enabled(False)
        self.stop_btn.set_enabled(False)
        self.build_table_rows()
        self.testing_container = testing_container
        return testing_container

    # ------------------------------------------------------------------ SEQUENCE CONTROL
    def start_sequence(self):
        self.status = ["0"] * len(self.devicename)
        self.pre_num = -1
        self.build_table_rows()
        file = File("shared_memory", "AutoSweep", 1, "DeviceNum", -1)
        file.save()

    def stop_sequence(self):
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    def tsp_solve(self):
        if self.filtered_idx:
            self.tsp_btn.set_enabled(False)
            self.start_btn.set_enabled(False)
            self.stop_btn.set_enabled(False)
            self.display_plot.set_image("my_res:TSP/wait.png")
            solver = TSPSolver(
                coord_json="./database/coordinates.json",
                selected_json="./database/shared_memory.json",
                time_limit=int(self.solve_time.get_value()),
                output_dir="./res/TSP"
            )
            solver.solve_and_plot()
            print(solver.path)
            self.display_plot.set_image(f"my_res:TSP/{solver.path}")
            self.filtered_idx = solver.route_idx[1:]
            self.build_table_rows()
            self.tsp_btn.set_enabled(True)
            self.start_btn.set_enabled(True)
            self.stop_btn.set_enabled(True)

            filtered = {str(i + 1): self.coordinate[i][0:2] for i in self.filtered_idx}
            file = File("shared_memory", "Image", f"TSP/{solver.path}", "Filtered", filtered)
            file.save()
        else:
            print("You need to load the file first!")

    def load_file(self):
        if self.serial_list:
            self.gds = lab_coordinates.coordinates(read_file=False, name="./database/coordinates.json")
            self.number = self.gds.listdeviceparam("number")
            self.coordinate = self.gds.listdeviceparam("coordinate")
            self.polarization = self.gds.listdeviceparam("polarization")
            self.wavelength = self.gds.listdeviceparam("wavelength")
            self.type = self.gds.listdeviceparam("type")
            self.devicename = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]
            self.status = ["0"] * len(self.devicename)
            self.filtered_idx = [i - 1 for i in self.serial_list]  # current filter result (list of global indices)
            self.page_size = 50
            self.page_index = 0
            self.build_table_rows()
        else:
            print("No device found!")

    def open_file_path(self):
        app = wx.App(False)
        with wx.DirDialog(None, "Select folder to save results",
                          style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.save_path_input.set_text(dlg.GetPath())
                self.notopen = False
                print(f"You choose {dlg.GetPath()}")
        app.Destroy()

    def save_file(self):
        path = self.path_dd.get_value()
        dest_dir = self.save_path_input.get_text().strip()

        if path == "All":
            src = os.path.join(os.getcwd(), "UserData", self.cur_user)
            dest_path = os.path.join(dest_dir, self.cur_user)
        else:
            src = os.path.join(os.getcwd(), "UserData", self.cur_user, path)
            dest_path = os.path.join(dest_dir, self.cur_user, path)

        if not dest_dir:
            print("❌ Save path cannot be empty!")
            return

        if not os.path.exists(dest_dir):
            try:
                os.makedirs(dest_dir, exist_ok=True)
                print(f"📁 Created destination directory: {dest_dir}")
            except Exception as e:
                print(f"❌ Failed to create directory: {e}")
                return


        if os.path.exists(dest_path):
            try:
                shutil.rmtree(dest_path)
                print(f"⚠️ Removed existing directory: {dest_path}")
            except Exception as e:
                print(f"❌ Failed to remove existing directory: {e}")
                return

        try:
            shutil.copytree(src, dest_path)
            print(f"✅ Files saved to: {dest_path}")
        except Exception as e:
            print(f"❌ Copy failed: {e}")

    def execute_command(self, path=command_path):
        test = 0
        record = 0
        new_command = {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key.startswith("testing_control") and record == 0:
                test = 1
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "testing_load":
                self.load_file()
            elif key == "testing_time":
                self.solve_time.set_value(val)
            elif key == "testing_solve":
                self.tsp_solve()
            elif key == "testing_save":
                self.save_file()
            elif key == "testing_file":
                self.path_dd.set_value(val)
            elif key == "testing_path":
                self.save_path_input.set_text(val)
            elif key == "testing_stop":
                self.stop_sequence()
            elif key == "testing_start":
                self.start_sequence()
                self.auto_sweep = 1
                time.sleep(1)
            while self.auto_sweep == 1:
                time.sleep(1)

        if test == 1:
            print("testing record")
            file = File("command", "command", new_command)
            file.save()



    def laser_sweep_setting(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7001",
            width=262-w,
            height=305-h,
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
