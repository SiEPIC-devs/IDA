from lab_gui import *
from remi import start, App

class add_btn(App):
    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs:
            super(add_btn, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        laser_sweep_container = StyledContainer(variable_name="laser_sweep_container", left=0, top=0, height=250, width=240)

        StyledLabel(container=laser_sweep_container, text="Speed", variable_name="sweep_speed_lb", left=0, top=10,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=laser_sweep_container, variable_name="speed_in", left=95, top=10,
                      width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=laser_sweep_container, text="nm/s", variable_name="sweep_speed_unit", left=185, top=10,
                    width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=laser_sweep_container, text="Power", variable_name="laser_power_lb", left=0, top=42,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=laser_sweep_container, variable_name="power_in", left=95, top=42,
                      width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=laser_sweep_container, text="dBm", variable_name="laser_power_unit", left=185, top=42,
                    width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=laser_sweep_container, text="Step Size", variable_name="step_size_lb", left=0, top=74,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=laser_sweep_container, variable_name="step_size_in", left=95, top=74,
                      width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=laser_sweep_container, text="nm", variable_name="step_size_unit", left=185, top=74,
                    width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=laser_sweep_container, text="Start Wvl", variable_name="start_wvl_lb", left=0, top=106,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=laser_sweep_container, variable_name="start_wvl_in", left=95, top=106,
                      width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=laser_sweep_container, text="nm", variable_name="start_wvl_unit", left=185, top=106,
                    width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=laser_sweep_container, text="Stop Wvl", variable_name="stop_wvl_lb", left=0, top=138,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=laser_sweep_container, variable_name="stop_wvl_in", left=95, top=138,
                      width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=laser_sweep_container, text="nm", variable_name="stop_wvl_unit", left=185, top=138,
                    width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=laser_sweep_container, text="When Done", variable_name="when_done_lb", left=0, top=170,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledDropDown(container=laser_sweep_container, variable_name="when_done_dd", text=["Laser On", "Laser Off"],
                       left=95, top=170, width=110, height=24, position="absolute")

        self.cancel_btn = StyledButton(container=laser_sweep_container, text="Cancel", variable_name="cancel_btn",
                                       left=45, top=210, height=25, width=70, font_size=90)
        self.confirm_btn = StyledButton(container=laser_sweep_container, text="Confirm", variable_name="confirm_btn",
                                        left=125, top=210, height=25, width=70, font_size=90)

        self.laser_sweep_container = laser_sweep_container
        return laser_sweep_container

    def onclick_add(self):
        pass

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
