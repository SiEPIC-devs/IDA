from remi.gui import *
from lab_gui import *
from remi import start, App
import lab_coordinates,threading, math, json
from tinydb import TinyDB, Query

command_path = os.path.join("database", "command.json")

def fmt(val):
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val)


class devices(App):
    def __init__(self, *args, **kwargs):
        self.gds = None
        self.number = []
        self.coordinate = []
        self.polarization = []
        self.wavelength = []
        self.type = []
        self.devicename = []
        self.length = 0
        self.checkbox_state = []
        self.filtered_idx = []
        self.page_size = 50
        self.page_index = 0

        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(devices, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.terminal.terminal_refresh()

        try:
            mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            mtime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return
        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

    def main(self):
        return devices.construct_ui(self)

    def build_table_rows(self):
        table = self.table
        data_rows = list(table.children.values())[1:]

        start_i = self.page_index * self.page_size
        end_i = min(len(self.filtered_idx), start_i + self.page_size)
        page_idx_slice = self.filtered_idx[start_i:end_i]
        needed = len(page_idx_slice)
        cur = len(data_rows)

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

        for row_idx, row in enumerate(data_rows):
            if row_idx < needed:
                global_idx = page_idx_slice[row_idx]
                cells = list(row.children.values())
                bg = "#ffffff" if (start_i + row_idx) % 2 == 0 else "#f6f7f9"
                for c in cells:
                    c.style.update({"display": "table-cell", "background-color": bg})

                cells[0].set_text(self.devicename[global_idx])
                cells[0].attributes["title"] = self.devicename[global_idx]
                cb_name = f"test_{global_idx}"

                if not hasattr(self, cb_name):
                    cb = StyledCheckBox(container=None, variable_name=cb_name,
                                        left=0, top=0, width=10, height=10, position="inherit")
                    cb.onchange.do(lambda emitter, value, idx=global_idx:
                                   self.checkbox_state.__setitem__(idx, value))
                    setattr(self, cb_name, cb)

                cb = getattr(self, cb_name)
                cb.set_value(self.checkbox_state[global_idx])
                cells[1].empty()
                cells[1].append(cb)
                cells[2].set_text(self.polarization[global_idx])
                cells[2].attributes["title"] = self.polarization[global_idx]
                cells[3].set_text(fmt(self.wavelength[global_idx]))
                cells[3].attributes["title"] = self.wavelength[global_idx]
                cells[4].set_text(self.type[global_idx])
                cells[4].attributes["title"] = self.type[global_idx]
                cells[5].set_text(fmt(self.coordinate[global_idx][0]))
                cells[5].attributes["title"] = fmt(self.coordinate[global_idx][0])
                cells[6].set_text(fmt(self.coordinate[global_idx][1]))
                cells[6].attributes["title"] = fmt(self.coordinate[global_idx][1])
            else:
                for c in row.children.values():
                    c.style["display"] = "none"

        self.page_input.set_text(str(self.page_index + 1))
        self.prev_btn.set_enabled(self.page_index != 0)
        self.next_btn.set_enabled(self.page_index + 1 < self.total_pages())
        self.total_page_label.set_text(f"/ {self.total_pages()}")

    def total_pages(self):
        return max(1, math.ceil(len(self.filtered_idx) / self.page_size))

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        devices_container = StyledContainer(
            variable_name="devices_container", left=0, top=0
        )

        coordinate_container = StyledContainer(
            container=devices_container, variable_name="coordinate_container",
            left=10, top=10, height=320, width=625, overflow=True, border=True
        )

        headers = ["Device ID", "Test", "Mode", "Wvl", "Type", "x", "y"]
        self.col_widths = [180, 30, 30, 50, 50, 60, 60]

        self.table = StyledTable(
            container=coordinate_container, variable_name="device_table",
            left=0, top=0, height=30, table_width=620, headers=headers, widths=self.col_widths, row=1
        )

        self.selection_container = StyledContainer(
            container=devices_container, variable_name="selection_container",
            left=10, top=350, height=100, width=625, border=True
        )

        sc = self.selection_container

        StyledLabel(
            container=sc, text="Device Selection Control", variable_name="device_selection_control",
            left=15, top=-12, width=185, height=20, font_size=120, color="#222", align="center",
            position="absolute", flex=True, on_line=True
        )

        self.device_id = StyledTextInput(
            container=sc, variable_name="selection_id", left=20, top=55, width=110, height=25
        )

        self.device_mode = StyledDropDown(
            container=sc, text=["Any", "TE", "TM"], variable_name="selection_mode",
            left=160, top=55, width=60, height=25
        )

        self.device_wvl = StyledDropDown(
            container=sc, text=["Any", "1550", "1310"], variable_name="selection_wvl",
            left=230, top=55, width=90, height=25
        )

        self.device_type = StyledDropDown(
            container=sc, text=["Any", "device", "PCM", "ybranch", "cutback"], variable_name="selection_type",
            left=330, top=55, width=90, height=25
        )

        self.filter_btn = StyledButton(
            container=sc, text="Apply Filter", variable_name="reset_filter", left=435, top=55, width=80, height=25
        )

        self.clear_btn = StyledButton(
            container=sc, text="Clear All", variable_name="clear_all", left=525, top=55, width=80, height=25
        )

        self.all_btn = StyledButton(
            container=sc, text="Select All", variable_name="select_all", left=525, top=20, width=80, height=25
        )

        self.confirm_btn = StyledButton(
            container=sc, text="Confirm", variable_name="confirm", left=435, top=20, width=80, height=25
        )

        StyledLabel(
            container=sc, text="Device ID Contains", variable_name="device_id_contains",
            left=22, top=30, width=150, height=25
        )

        StyledLabel(
            container=sc, text="Mode", variable_name="mode", left=162, top=30, width=100, height=25
        )

        StyledLabel(
            container=sc, text="Wavelength", variable_name="wavelength", left=232, top=30, width=100, height=25
        )

        StyledLabel(
            container=sc, text="Type", variable_name="type", left=332, top=30, width=100, height=25
        )

        pg = StyledContainer(
            container=devices_container, variable_name="pagination_container", left=10, top=455, height=35, width=625
        )

        self.prev_btn = StyledButton(
            container=pg, text="◀ Prev", variable_name="prev_page", left=0, top=5, width=80, height=25
        )

        self.page_input = StyledTextInput(
            container=pg, variable_name="page_input", text="1", left=100, top=5, width=25, height=25
        )

        self.total_page_label = StyledLabel(
            container=pg, text=f"/ {self.total_pages()}", variable_name="page_total",
            left=145, top=5, width=40, height=25, flex=True, justify_content="left"
        )

        self.jump_btn = StyledButton(
            container=pg, text="Go", variable_name="jump_page", left=180, top=5, width=40, height=25
        )

        self.next_btn = StyledButton(
            container=pg, text="Next ▶", variable_name="next_page", left=235, top=5, width=80, height=25
        )

        self.load_btn = StyledButton(
            container=pg, text="Load", variable_name="load_page", left=330, top=5, width=60, height=25
        )

        terminal_container = StyledContainer(
            container=devices_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text", left=10, top=15, width=610, height=100
        )

        self.prev_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_prev_page))
        self.next_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_next_page))
        self.jump_btn.do_onclick(lambda *_: self.run_in_thread(self.goto_input_page))
        self.filter_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_filter))
        self.clear_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_clear))
        self.all_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_all))
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))
        self.load_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_load))

        self.devices_container = devices_container
        self.build_table_rows()
        return devices_container

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

    def onclick_filter(self):
        id_sub = self.device_id.get_text().strip()
        mode_val = self.device_mode.get_value()
        wvl_val = self.device_wvl.get_value()
        type_val = self.device_type.get_value()

        def match(idx):
            if id_sub and id_sub not in self.devicename[idx]: return False
            if mode_val != "Any" and self.polarization[idx] != mode_val: return False
            if wvl_val != "Any" and str(self.wavelength[idx]) != wvl_val: return False
            if type_val != "Any" and self.type[idx] != type_val: return False
            return True

        self.filtered_idx = [i for i in range(self.length) if match(i)]
        self.page_index = 0
        self.build_table_rows()

    def __set_all_checkboxes(self, value: bool):
        for idx in self.filtered_idx:
            self.checkbox_state[idx] = value
            cb = getattr(self, f"test_{idx}", None)
            if cb is not None:
                cb.set_value(value)

    def onclick_clear(self):
        self.__set_all_checkboxes(False)

    def onclick_all(self):
        self.__set_all_checkboxes(True)

    def onclick_confirm(self):
        selected_idx = sorted(i+1 for i, v in enumerate(self.checkbox_state) if v)
        if not selected_idx:
            print("No device selected — serial not saved.")
            return
        file = File("shared_memory", "Selection", selected_idx)
        file.save()


    def onclick_load(self):
        self.read_file()
        self.build_table_rows()
        self.load_count = 1

    def read_file(self):
        self.gds = lab_coordinates.coordinates(read_file=False, name="./database/coordinates.json")
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        self.devicename = [f"{name} ({num})" for name, num in zip(
            self.gds.listdeviceparam("devicename"), self.number)]

        self.length = len(self.number)
        self.checkbox_state = [False] * self.length
        self.filtered_idx = list(range(self.length))
        self.page_size = 50
        self.page_index = 0

    def execute_command(self, path=command_path):
        device = 0
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
            if key.startswith("devices_control") and record == 0:
                device = 1
            elif key.startswith("testing_control") or record == 1:
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

            elif key == "devices_load":
                self.onclick_load()
            elif key == "devices_all":
                self.onclick_all()
            elif key == "devices_clear":
                self.onclick_clear()
            elif key == "devices_filter":
                self.onclick_filter()
            elif key == "devices_id":
                self.device_id.set_text(val)
            elif key == "devices_mode":
                self.device_mode.set_value(val)
            elif key == "devices_wvl":
                self.device_wvl.set_value(str(val))
            elif key == "devices_type":
                self.device_type.set_value(val)
            elif key == "devices_sel":
                for i in val:
                    self.checkbox_state[i-1] = True
                    cb = getattr(self, f"test_{i-1}", None)
                    if cb is not None:
                        cb.set_value(True)
            elif key == "devices_del":
                for i in val:
                    self.checkbox_state[i-1] = False
                    cb = getattr(self, f"test_{i-1}", None)
                    if cb is not None:
                        cb.set_value(False)
            elif key == "devices_confirm":
                self.onclick_confirm()

        if device == 1:
            print("device record")
            time.sleep(1)
            file = File("command", "command", new_command)
            file.save()



if __name__ == "__main__":
    configuration = {
        "config_project_name": "devices",
        "config_address": "0.0.0.0",
        "config_port": 9003,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }

    start(devices,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
