from lab_gui import *
from remi import start, App

command_path = os.path.join("database", "command.json")

class fine_align(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(fine_align, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

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
        fine_align_setting_container = StyledContainer(
            variable_name="fine_align_setting_container", left=0, top=0, height=180, width=200
        )

        StyledLabel(
            container=fine_align_setting_container, text="X Count", variable_name="x_count_lb", left=0,
            top=10, width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.x_count = StyledSpinBox(
            container=fine_align_setting_container, variable_name="x_count_in", left=80, top=10, value=20,
            width=50, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text=" ", variable_name="x_count_um", left=150, top=10,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=fine_align_setting_container, text="X Step", variable_name="x_length_lb", left=0, top=42,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.x_length = StyledSpinBox(
            container=fine_align_setting_container, variable_name="x_length_in", left=80, top=42, value=0.1,
            width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um", variable_name="x_length_um", left=150, top=42,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=fine_align_setting_container, text="Y Count", variable_name="y_count_lb", left=0,
            top=74,width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.y_count = StyledSpinBox(
            container=fine_align_setting_container, variable_name="y_count_in", left=80, top=74, value=20,
            width=50, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text=" ", variable_name="y_count_um", left=150, top=74,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=fine_align_setting_container, text="Y Step", variable_name="y_length_lb", left=0, top=106,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.y_length = StyledSpinBox(
            container=fine_align_setting_container, variable_name="y_length_in", left=80, top=106, value=0.1,
            width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um", variable_name="y_length_um", left=150, top=106,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        self.confirm_btn = StyledButton(
            container=fine_align_setting_container, text="Confirm", variable_name="confirm_btn",
            left=68, top=142, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.fine_align_setting_container = fine_align_setting_container
        return fine_align_setting_container

    def onclick_confirm(self):
        value = {
            "x_count": float(self.x_count.get_value()),
            "x_length": float(self.x_length.get_value()),
            "y_count": float(self.y_count.get_value()),
            "y_length": float(self.y_length.get_value())
        }
        file = File("shared_memory", "FineA", value)
        file.save()
        print("Confirm Fine Align Setting")

    def execute_command(self, path=command_path):
        fa = 0
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
            if key.startswith("fa_set") and record == 0:
                fa = 1
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
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "fa_x_count":
                self.x_count.set_value(val)
            elif key == "fa_x_length":
                self.x_length.set_value(val)
            elif key == "fa_y_count":
                self.y_count.set_value(val)
            elif key == "fa_y_length":
                self.y_length.set_value(val)
            elif key == "fa_confirm":
                self.onclick_confirm()

        if fa == 1:
            print("fa record")
            file = File("command", "command", new_command)
            file.save()

if __name__ == "__main__":
    configuration = {
        "config_project_name": "fine_align",
        "config_address": "0.0.0.0",
        "config_port": 7003,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(fine_align,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
