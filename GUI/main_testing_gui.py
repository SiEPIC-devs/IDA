from GUI.lib_gui import *
from remi import start, App
from GUI import lib_coordinates
import threading, math, json, os, time, webview, wx, shutil
from GUI.lib_tsp import TSPSolver

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")
desktop_path = os.path.join("UserData")

def fmt(val):
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val)
    

class testing(App):
    """Testing GUI with per-device timer that updates status and elapsed/remaining time."""

    def __init__(self, *args, **kwargs):
        # ------------------------------------------------------------------ LOAD DATA
        self._user_mtime = None
        self._first_command_check = True
        self._user_stime = None
        self.notopen = True
        self.running = False
        self.cur_user = ""
        self.image_path = ""
        self.project = ""
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

        self._last_user = ""
        self._last_user_paths = []
        self.pre_num = 1

        self.new_command = {}
        self.elapsed = 0
        self.remaining = 0
        self.file_format = ""
        self.path = ""
        self._bias_enabled = False  # Track bias state from shared_memory
        self._devices_ready = False  # True after TSP solve / file load

        if "editing_mode" not in kwargs:
            super(testing, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ------------------------------------------------------------------ REMI HOOKS
    def idle(self):
        self.terminal.terminal_refresh()
        try:
            mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            mtime = None
        
        stime = get_shared_memory_mtime()

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
                data = SharedMemory.read({})
                if data:
                    self.cur_user = data.get("User", "").strip()
                    image_path = data.get("Image", "")
                    if image_path != self.image_path:
                        self.image_path = image_path
                        self.display_plot.set_image(f"my_res:{self.image_path}")
                    self.serial_list = set(data.get("Selection", []))
                    self.device_num = data.get("DeviceNum", 0)
                    self.auto_sweep = data.get("AutoSweep", 0)
                    self.project = data.get("Project", "")

                    # Track bias enabled state for start button validation
                    sweep_data = data.get("Sweep", {})
                    bias_cfg = sweep_data.get("bias_voltage", {})
                    self._bias_enabled = bias_cfg.get("enabled", False)

            if self.auto_sweep == 1 and self.device_num != self.pre_num:
                self.status[self.device_num - 1] = "1"
                self.build_table_rows()
                self.pre_num = self.device_num

                self.remaining -= 1
                self.elapsed += 1
                self.elapsed_device.set_text(str(self.elapsed))
                self.remaining_device.set_text(str(self.remaining))
        self.update_file_format()
        self.update_path()
        self._update_start_button_state()

    def main(self):
        return testing.construct_ui(self)

    def update_file_format(self):
        file_format = self.file_dd.get_value()
        value = {"csv": 0, "mat": 0, "png": 0, "pdf": 0}
        if self.file_format != file_format:
            self.file_format = file_format
            if file_format == "All":
                value = {"csv": 1, "mat": 1, "png": 1, "pdf": 1}
            elif file_format == ".csv + .png":
                value = {"csv": 1, "mat": 0, "png": 1, "pdf": 0}
            elif file_format == ".csv + .pdf":
                value = {"csv": 1, "mat": 0, "png": 0, "pdf": 1}
            elif file_format == ".mat + .png":
                value = {"csv": 0, "mat": 1, "png": 1, "pdf": 0}
            elif file_format == ".mat + .pdf":
                value = {"csv": 0, "mat": 1, "png": 0, "pdf": 1}
            file = File("shared_memory", "FileFormat", value)
            file.save()

    def update_path(self):
        path = self.save_path_input.get_text().strip()
        if path != self.path:
            self.path = path
            file = File("shared_memory", "FilePath", self.path)
            file.save()

    # ------------------------------------------------------------------ TABLE RENDERING (SCROLL, NO PAGES)
    def build_table_rows(self):
        table = self.table
        data_rows = list(table.children.values())[1:]  # children[0] is the header row

        needed = len(self.filtered_idx)
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
                global_idx = self.filtered_idx[row_idx]
                cells = list(row.children.values())

                # alternate row background by row_idx
                bg = "#ffffff" if (row_idx % 2) == 0 else "#f6f7f9"
                for c in cells:
                    c.style.update({"display": "table-cell", "background-color": bg})

                cells[0].set_text(self.devicename[global_idx])
                cells[0].attributes["title"] = self.devicename[global_idx]

                cells[1].set_text(self.status[global_idx])
                cells[1].attributes["title"] = self.status[global_idx]
            else:
                for c in row.children.values():
                    c.style["display"] = "none"

    # ------------------------------------------------------------------ THREAD HELPERS
    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

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

        self.file_dd = StyledDropDown(
            container=path_container,
            text=["All", ".csv + .png", ".csv + .pdf", ".mat + .png", ".mat + .pdf"],
            variable_name="save_file_dd",
            left=90, top=55, width=180, height=30
        )

        # self.save_btn = StyledButton(
        #     container=path_container, text="Save", variable_name="Save",
        #     left=275, top=15, width=90, height=30, normal_color="#007BFF", press_color="#0056B3"
        # )

        self.open_btn = StyledButton(
            container=path_container, text="Open Path", variable_name="open_path",
            left=275, top=55, width=90, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        self.display_plot = StyledImageBox(
            container=self.image_container, variable_name="display_plot",
            left=5, top=5, width=375, height=360, image_path="my_res:TSP/none.png"
        )

        # --- SETTING BLOCK --- 
        setting_container = StyledContainer(
            container=testing_container, variable_name="setting_container",
            left=400, top=10, height=475, width=240
        )

        self.sweep_type_dd = StyledDropDown(
            container=setting_container, text=["Laser Sweep", "EO"], variable_name="laser_sweep",
            left=0, top=0, width=120, height=30
        )

        self.setting_btn = StyledButton(
            container=setting_container, text="Setting", variable_name="setting",
            left=131, top=2.5, width=50, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        headers = ["Device", "Status"]
        self.col_widths = [100, 40]

        # Scrollable table container
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

        self.elapsed_device = StyledLabel(
            container=setting_container, text="N/A", variable_name="elapsed_time",
            left=165, top=375, width=75, height=25, font_size=100, color="#222", border=True, flex=True
        )

        self.remaining_device = StyledLabel(
            container=setting_container, text="N/A", variable_name="remaining_time",
            left=165, top=415, width=75, height=25, font_size=100, color="#222", border=True, flex=True
        )

        self.tsp_btn = StyledButton(
            container=setting_container, text="Solve", variable_name="solve_tsp",
            left=0, top=335, width=70, height=30
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
        self.tsp_btn.do_onclick(lambda *_: self.run_in_thread(self.tsp_solve))
        self.start_btn.do_onclick(lambda *_: self.run_in_thread(self.start_sequence))
        self.stop_btn.do_onclick(lambda *_: self.run_in_thread(self.stop_sequence))
        self.open_btn.do_onclick(lambda *_: self.run_in_thread(self.open_file_path))
        # self.save_btn.do_onclick(lambda *_: self.run_in_thread(self.save_file))
        self.setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_laser_sweep_setting_btn))

        # -------------------------------------------------- TERMINAL BLOCK
        terminal_container = StyledContainer(
            container=testing_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text",
            left=10, top=15, width=610, height=100
        )

        # initial state
        self.start_btn.set_enabled(False)
        self.stop_btn.set_enabled(False)
        self.build_table_rows()
        self.testing_container = testing_container
        return testing_container

    # --- SEQUENCE CONTROL --- 
    def start_sequence(self):
        self.status = ["0"] * len(self.devicename)
        self.pre_num = -1
        self.build_table_rows()
        filtered = {str(i + 1): self.coordinate[i][0:2] for i in self.filtered_idx}
        self.elapsed = 0
        self.remaining = len(filtered)
        self.elapsed_device.set_text(str(self.elapsed))
        self.remaining_device.set_text(str(self.remaining))
        sweep_type = self.sweep_type_dd.get_value()  # "Laser Sweep" or "EO"
        SharedMemory.update({"AutoSweep": 1, "DeviceNum": -1, "AutoSweepType": sweep_type})

    def stop_sequence(self):
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    def _update_start_button_state(self):
        """
        Enable Start only when sweep type and bias setting are consistent:
        - Laser Sweep: bias must NOT be enabled
        - EO:          bias MUST be enabled
        Also requires devices to be loaded (_devices_ready).
        """
        if not self._devices_ready:
            return  # Don't touch the button before devices are loaded
        sweep_type = self.sweep_type_dd.get_value()
        bias_on = self._bias_enabled
        if sweep_type == "EO" and not bias_on:
            self.start_btn.set_enabled(False)
        elif sweep_type == "Laser Sweep" and bias_on:
            self.start_btn.set_enabled(False)
        else:
            self.start_btn.set_enabled(True)

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
            self._devices_ready = True
            self._update_start_button_state()

            filtered = {str(i + 1): self.coordinate[i][0:2] for i in self.filtered_idx}
            self.remaining = len(filtered)
            self.elapsed = 0
            file = File("shared_memory", "Image", f"TSP/{solver.path}", "Filtered", filtered)
            file.save()
        else:
            print("You need to load the file first!")

    def load_file(self):
        # Always read fresh Selection from shared_memory to avoid timing issues
        # (command may trigger load_file before idle() updates serial_list)
        data = SharedMemory.read({})
        selection = data.get("Selection", [])
        if selection:
            self.serial_list = set(selection)
        
        if self.serial_list:
            self.gds = lib_coordinates.coordinates(read_file=False, name="./database/coordinates.json")
            self.number = self.gds.listdeviceparam("number")
            self.coordinate = self.gds.listdeviceparam("coordinate")
            self.polarization = self.gds.listdeviceparam("polarization")
            self.wavelength = self.gds.listdeviceparam("wavelength")
            self.type = self.gds.listdeviceparam("type")
            self.devicename = [
                f"{name} ({num})"
                for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)
            ]
            self.status = ["0"] * len(self.devicename)
            self.filtered_idx = [i - 1 for i in self.serial_list]
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
        project = self.project
        dest_root = self.save_path_input.get_text().strip()

        if not dest_root:
            print("Save path cannot be empty!")
            return

        if not project:
            print("No active project; nothing to export.")
            return

        # if project == "All":
        #     print("Export for 'All' projects is not supported; please select a single project.")
        #     return

        # --- Resolve source roots ---
        user_root = os.path.join(os.getcwd(), "UserData", self.cur_user)
        src_project_root = os.path.join(user_root, project)

        if not os.path.isdir(src_project_root):
            print(f"X Source project path does not exist: {src_project_root}")
            return

        # --- Destination project root ---
        dest_project_root = os.path.join(dest_root, self.cur_user, project)

        try:
            # Wipe any previous export in that directory
            if os.path.exists(dest_project_root):
                shutil.rmtree(dest_project_root)
                print(f"Removed existing export: {dest_project_root}")

            # Copy entire project directory with all files and subdirectories
            print(f"Copying project from: {src_project_root}")
            print(f"                  to: {dest_project_root}")
            shutil.copytree(src_project_root, dest_project_root)
            print(f"[OK] Successfully exported all project files!")
            
            # Count files for confirmation
            file_count = sum(1 for _, _, files in os.walk(dest_project_root) for _ in files)
            print(f"[OK] Total files exported: {file_count}")
            
        except Exception as e:
            print(f"Failed to export project: {e}")
            return

        try:
            file = File(
                "shared_memory",
                "ExportRequest",
                {"dest_dir": dest_project_root}
            )
            file.save()
            print(f"[OK] Export configuration saved")
        except Exception as e:
            print(f"Failed to write ExportRequest: {e}")


    def execute_command(self, path=command_path):
        test = 0
        record = 0
        new_command = {}

        try:
            data = read_command_file()
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
            elif key == "testing_file":
                self.file_dd.set_value(val)
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

    def onclick_laser_sweep_setting_btn(self):
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7109",
            width=352 + web_w,
            height=576 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )


def run_remi():
    start(
        testing,
        address="0.0.0.0",
        port=9104,
        start_browser=False,
        multiple_instance=False,
        enable_file_cache=False,
    )


if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    local_ip = '127.0.0.1'

    webview.create_window(
        "Main Window",
        f"http://{local_ip}:9104",
        width=0,
        height=0,
        resizable=True,
        hidden=True,
    )
    webview.start()
