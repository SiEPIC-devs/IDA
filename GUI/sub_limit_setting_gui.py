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

    def construct_ui(self): #150, 295
        limit_setting_container = StyledContainer(
            variable_name="limit_setting_container", left=0, top=0, height=210, width=200
        )

        StyledLabel(
            container=limit_setting_container, text="X", variable_name="x_lb", left=0, top=10,
            width=65, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.x_dd = StyledDropDown(
            container=limit_setting_container, text=["Yes", "No"], variable_name="x_dd", left=75, top=10,
            width=70, height=24, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="Y", variable_name="y_lb", left=0, top=42,
            width=65, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.y_dd = StyledDropDown(
            container=limit_setting_container, text=["Yes", "No"], variable_name="y_dd", left=75, top=42,
            width=70, height=24, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="Z", variable_name="z_lb", left=0, top=74,
            width=65, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.z_dd = StyledDropDown(
            container=limit_setting_container, text=["Yes", "No"], variable_name="z_dd", left=75, top=74,
            width=70, height=24, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="Chip", variable_name="chip_lb", left=0, top=106,
            width=65, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.chip_dd = StyledDropDown(
            container=limit_setting_container, text=["Yes", "No"], variable_name="chip_dd", left=75, top=106,
            width=70, height=24, position="absolute"
        )

        StyledLabel(
            container=limit_setting_container, text="Fiber", variable_name="fiber_lb", left=0, top=138,
            width=65, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.fiber_dd = StyledDropDown(
            container=limit_setting_container, text=["Yes", "No"], variable_name="fiber_dd", left=75, top=138,
            width=70, height=24, position="absolute"
        )

        self.confirm_btn = StyledButton(
            container=limit_setting_container, text="Confirm", variable_name="confirm_btn",
            left=65, top=170, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.limit_setting_container = limit_setting_container
        return limit_setting_container

    def onclick_confirm(self):
        lim = {
            "x": self.x_dd.get_value(),
            "y": self.y_dd.get_value(),
            "z": self.z_dd.get_value(),
            "chip": self.chip_dd.get_value(),
            "fiber": self.fiber_dd.get_value()
        }
        file = File("shared_memory", "Limit", lim)
        file.save()
        print("Confirm Limit Setting")

    def execute_command(self, path=command_path):
        lim = 0
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
            if key.startswith("lim_set") and record == 0:
                lim = 1
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

            elif key == "lim_x":
                if val.lower() == "yes":
                    self.x_dd.set_value("Yes")
                elif val.lower() == "no":
                    self.x_dd.set_value("No")
                else:
                    self.x_dd.set_value("Yes")
            elif key == "lim_y":
                if val.lower() == "yes":
                    self.y_dd.set_value("Yes")
                elif val.lower() == "no":
                    self.y_dd.set_value("No")
                else:
                    self.y_dd.set_value("Yes")
            elif key == "lim_x":
                if val.lower() == "yes":
                    self.z_dd.set_value("Yes")
                elif val.lower() == "no":
                    self.z_dd.set_value("No")
                else:
                    self.z_dd.set_value("Yes")
            elif key == "lim_chip":
                if val.lower() == "yes":
                    self.chip_dd.set_value("Yes")
                elif val.lower() == "no":
                    self.chip_dd.set_value("No")
                else:
                    self.chip_dd.set_value("Yes")
            elif key == "lim_fiber":
                if val.lower() == "yes":
                    self.fiber_dd.set_value("Yes")
                elif val.lower() == "no":
                    self.fiber_dd.set_value("No")
                else:
                    self.fiber_dd.set_value("Yes")

            elif key == "lim_confirm":
                self.onclick_confirm()

        if lim == 1:
            print("limit record")
            file = File("command", "command", new_command)
            file.save()

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
