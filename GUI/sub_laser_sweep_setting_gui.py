from lab_gui import *
from remi import start, App

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")

class add_btn(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.sweep = None
        if "editing_mode" not in kwargs:
            super(add_btn, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
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
            self.execute_command()

        if stime != self._user_stime:
            self._user_stime = stime

            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sweep = data.get("Sweep", {})
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

            self.power.set_value(self.sweep["power"])
            self.start_wvl.set_value(self.sweep["start"])
            self.stop_wvl.set_value(self.sweep["end"])

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        laser_sweep_container = StyledContainer(
            variable_name="laser_sweep_container", left=0, top=0, height=250, width=240
        )

        StyledLabel(
            container=laser_sweep_container, text="Speed", variable_name="sweep_speed_lb", left=0, top=10,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.speed = StyledSpinBox(
            container=laser_sweep_container, variable_name="speed_in", left=95, top=10, value=1.0,
            width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm/s", variable_name="sweep_speed_unit", left=185, top=10,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Power", variable_name="laser_power_lb", left=0, top=42,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.power = StyledSpinBox(
            container=laser_sweep_container, variable_name="power_in", left=95, top=42, value=0.0,
            width=65, height=24, min_value=-110, max_value=30, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="dBm", variable_name="laser_power_unit", left=185, top=42,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Step Size", variable_name="step_size_lb", left=0, top=74,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.step_size = StyledSpinBox(
            container=laser_sweep_container, variable_name="step_size_in", left=95, top=74, value=0.1,
            width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="step_size_unit", left=185, top=74,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Start Wvl", variable_name="start_wvl_lb", left=0, top=106,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.start_wvl = StyledSpinBox(
            container=laser_sweep_container, variable_name="start_wvl_in", left=95, top=106, value=1540.0,
            width=65, height=24, min_value=0, max_value=2000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="start_wvl_unit", left=185, top=106,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Stop Wvl", variable_name="stop_wvl_lb", left=0, top=138,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.stop_wvl = StyledSpinBox(
            container=laser_sweep_container, variable_name="stop_wvl_in", left=95, top=138, value=1560.0,
            width=65, height=24, min_value=0, max_value=2000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="stop_wvl_unit", left=185, top=138,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="When Done", variable_name="when_done_lb", left=0, top=170,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.on_off = StyledDropDown(
            container=laser_sweep_container, variable_name="when_done_dd", text=["Laser On", "Laser Off"],
            left=95, top=170, width=110, height=24, position="absolute"
        )

        self.confirm_btn = StyledButton(
            container=laser_sweep_container, text="Confirm", variable_name="confirm_btn",
            left=88, top=210, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.laser_sweep_container = laser_sweep_container
        return laser_sweep_container

    def onclick_confirm(self):
        mem = {
            "wvl": self.sweep["wvl"],
            "speed": float(self.speed.get_value()),
            "power": float(self.power.get_value()),
            "step": float(self.step_size.get_value()),
            "start": float(self.start_wvl.get_value()),
            "end": float(self.stop_wvl.get_value()),
            "done": self.on_off.get_value(),
            "sweep": self.sweep["sweep"],
            "on": self.sweep["on"]
        }
        file = File("shared_memory", "Sweep", mem)
        file.save()

        print("Confirm Sweep Setting")

    def execute_command(self, path=command_path):
        sweep = 0
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
            if key.startswith("sweep_set") and record == 0:
                sweep = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "sweep_speed":
                self.speed.set_value(val)
            elif key == "sweep_power":
                self.power.set_value(val)
            elif key == "sweep_step_size":
                self.step_size.set_value(val)
            elif key == "sweep_start_wvl":
                self.start_wvl.set_value(val)
            elif key == "sweep_stop_wvl":
                self.stop_wvl.set_value(val)
            elif key == "sweep_done":
                if val == "on":
                    self.on_off.set_value("Laser On")
                elif val == "off":
                    self.on_off.set_value("Laser Off")
            elif key == "sweep_confirm":
                self.onclick_confirm()

        if sweep == 1:
            print("sweep record")
            file = File("command", "command", new_command)
            file.save()

if __name__ == "__main__":
    configuration = {
        "config_project_name": "add_btn",
        "config_address": "0.0.0.0",
        "config_port": 7001,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(add_btn,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
