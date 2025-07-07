from lab_gui import *
from remi import start, App

command_path = os.path.join("database", "command.json")

class limit(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(limit, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

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
        limit_setting_container = StyledContainer(variable_name="limit_setting_container", left=0, top=0, height=150, width=295)

        StyledLabel(
            container=limit_setting_container, text="X Range", variable_name="x_range", left=0, top=10,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.x_left_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="x_left_lim", left=80, top=10,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="to", variable_name="x_to", left=160, top=10,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        self.x_right_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="x_right_lim", left=180, top=10,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="um", variable_name="x_um", left=255, top=10,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=limit_setting_container, text="Y Range", variable_name="y_range", left=0, top=42,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.y_left_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="y_left_lim", left=80, top=42,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="to", variable_name="y_to", left=160, top=42,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        self.y_right_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="y_right_lim", left=180, top=42,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="um", variable_name="y_um", left=255, top=42,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=limit_setting_container, text="Z Range", variable_name="z_range", left=0, top=74,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.z_left_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="z_left_lim", left=80, top=74,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="to", variable_name="z_to", left=160, top=74,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        self.z_right_lim = StyledSpinBox(
            container=limit_setting_container, variable_name="z_right_lim", left=180, top=74,
            width=55, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="um", variable_name="z_um", left=255, top=74,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        self.confirm_btn = StyledButton(
            container=limit_setting_container, text="Confirm", variable_name="confirm_btn",
            left=115, top=110, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.limit_setting_container = limit_setting_container
        return limit_setting_container

    def onclick_confirm(self):
        print("Confirm Limit")

    def execute_command(self, path=command_path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key == "stage_lim_x_left":
                self.x_left_lim.set_value(val)
            elif key == "stage_lim_x_right":
                self.x_right_lim.set_value(val)
            elif key == "stage_lim_y_left":
                self.y_left_lim.set_value(val)
            elif key == "stage_lim_y_right":
                self.y_right_lim.set_value(val)
            elif key == "stage_lim_z_left":
                self.z_left_lim.set_value(val)
            elif key == "stage_lim_z_right":
                self.z_right_lim.set_value(val)
            elif key == "stage_lim_confirm" and val == True:
                self.onclick_confirm()

if __name__ == "__main__":
    configuration = {
        "config_project_name": "limit",
        "config_address": "0.0.0.0",
        "config_port": 7002,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(limit,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
