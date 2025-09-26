from GUI.lib_gui import *
from remi import start, App

command_path = os.path.join("database", "command.json")

class data_window(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(data_window, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
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
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        data_window_container = StyledContainer(
            variable_name="data_window_container", left=0, top=0, height=240, width=280
        )

        # Channel 1 Settings
        StyledLabel(
            container=data_window_container, text="Channel 1", variable_name="ch1_label", left=10,
            top=15, width=100, height=25, font_size=110, flex=True, justify_content="left", color="#222", bold=True
        )

        StyledLabel(
            container=data_window_container, text="Range", variable_name="ch1_range_lb", left=10,
            top=45, width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.ch1_range = StyledSpinBox(
            container=data_window_container, variable_name="ch1_range_in", left=80, top=45, value=-10,
            width=60, height=24, min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm", variable_name="ch1_range_unit", left=160, top=45,
            width=30, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref", variable_name="ch1_ref_lb", left=10, top=75,
            width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.ch1_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch1_ref_in", left=80, top=75, value=-80,
            width=60, height=24, min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm", variable_name="ch1_ref_unit", left=160, top=75,
            width=30, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Channel 2 Settings
        StyledLabel(
            container=data_window_container, text="Channel 2", variable_name="ch2_label", left=10,
            top=115, width=100, height=25, font_size=110, flex=True, justify_content="left", color="#222", bold=True
        )

        StyledLabel(
            container=data_window_container, text="Range", variable_name="ch2_range_lb", left=10,
            top=145, width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.ch2_range = StyledSpinBox(
            container=data_window_container, variable_name="ch2_range_in", left=80, top=145, value=-10,
            width=60, height=24, min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm", variable_name="ch2_range_unit", left=160, top=145,
            width=30, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref", variable_name="ch2_ref_lb", left=10, top=175,
            width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.ch2_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch2_ref_in", left=80, top=175, value=-80,
            width=60, height=24, min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm", variable_name="ch2_ref_unit", left=160, top=175,
            width=30, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Apply buttons
        self.apply_range_btn = StyledButton(
            container=data_window_container, text="Apply Range", variable_name="apply_range_btn",
            left=190, top=45, height=24, width=80, font_size=85, normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn = StyledButton(
            container=data_window_container, text="Apply Ref", variable_name="apply_ref_btn",
            left=190, top=75, height=24, width=80, font_size=85, normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_range_btn2 = StyledButton(
            container=data_window_container, text="Apply Range", variable_name="apply_range_btn2",
            left=190, top=145, height=24, width=80, font_size=85, normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn2 = StyledButton(
            container=data_window_container, text="Apply Ref", variable_name="apply_ref_btn2",
            left=190, top=175, height=24, width=80, font_size=85, normal_color="#007BFF", press_color="#0056B3"
        )

        # Confirm button
        self.confirm_btn = StyledButton(
            container=data_window_container, text="Save Settings", variable_name="confirm_btn",
            left=95, top=210, height=25, width=90, font_size=90
        )

        # Wire up events
        self.apply_range_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch1_range))
        self.apply_ref_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch1_ref))
        self.apply_range_btn2.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch2_range))
        self.apply_ref_btn2.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch2_ref))
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.data_window_container = data_window_container
        return data_window_container

    def onclick_apply_ch1_range(self):
        range_val = float(self.ch1_range.get_value())
        # Write a sensor-scoped command so the sensor controller can consume it
        File("command", "command", {"sensor_set_range_ch1": range_val}).save()
        print(f"Applied CH1 Range (queued): {range_val} dBm")

    def onclick_apply_ch1_ref(self):
        ref_val = float(self.ch1_ref.get_value())
        File("command", "command", {"sensor_set_ref_ch1": ref_val}).save()
        print(f"Applied CH1 Reference (queued): {ref_val} dBm")

    def onclick_apply_ch2_range(self):
        range_val = float(self.ch2_range.get_value())
        File("command", "command", {"sensor_set_range_ch2": range_val}).save()
        print(f"Applied CH2 Range (queued): {range_val} dBm")

    def onclick_apply_ch2_ref(self):
        ref_val = float(self.ch2_ref.get_value())
        File("command", "command", {"sensor_set_ref_ch2": ref_val}).save()
        print(f"Applied CH2 Reference (queued): {ref_val} dBm")

    def onclick_confirm(self):
        value = {
            "ch1_range": float(self.ch1_range.get_value()),
            "ch1_ref": float(self.ch1_ref.get_value()),
            "ch2_range": float(self.ch2_range.get_value()),
            "ch2_ref": float(self.ch2_ref.get_value())
        }
        file = File("shared_memory", "DataWindow", value)
        file.save()
        print("Data Window Settings Saved")

    def execute_command(self, path=command_path):
        dw = 0
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
            if key.startswith("data_window") and record == 0:
                dw = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "data_ch1_range":
                self.ch1_range.set_value(val)
            elif key == "data_ch1_ref":
                self.ch1_ref.set_value(val)
            elif key == "data_ch2_range":
                self.ch2_range.set_value(val)
            elif key == "data_ch2_ref":
                self.ch2_ref.set_value(val)
            elif key == "data_confirm":
                self.onclick_confirm()

        if dw == 1:
            print("data window record")
            file = File("command", "command", new_command)
            file.save()

if __name__ == "__main__":
    configuration = {
        "config_project_name": "data_window",
        "config_address": "0.0.0.0",
        "config_port": 7006,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(data_window,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])