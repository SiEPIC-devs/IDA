from lab_gui import *
from remi import start, App

class area_scan(App):
    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        area_scan_setting_container = StyledContainer(variable_name="area_scan_setting_container", left=0, top=0, height=180, width=200)

        StyledLabel(container=area_scan_setting_container, text="X Length", variable_name="x_length_lb", left=0,
                    top=10, width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=area_scan_setting_container, variable_name="x_length_in", left=80, top=10,
                      width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=area_scan_setting_container, text="um", variable_name="x_length_um", left=150, top=10,
                    width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222")
        StyledLabel(container=area_scan_setting_container, text="X Step", variable_name="x_step_lb", left=0, top=42,
                    width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=area_scan_setting_container, variable_name="x_step_in", left=80, top=42,
                      width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=area_scan_setting_container, text="um", variable_name="x_step_um", left=150, top=42,
                    width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        StyledLabel(container=area_scan_setting_container, text="Y Length", variable_name="y_length_lb", left=0,
                    top=74,width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=area_scan_setting_container, variable_name="y_length_in", left=80, top=74,
                      width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=area_scan_setting_container, text="um", variable_name="y_length_um", left=150, top=74,
                    width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222")
        StyledLabel(container=area_scan_setting_container, text="Y Step", variable_name="y_step_lb", left=0, top=106,
                    width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledSpinBox(container=area_scan_setting_container, variable_name="y_step_in", left=80, top=106,
                      width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute")
        StyledLabel(container=area_scan_setting_container, text="um", variable_name="y_step_um", left=150, top=106,
                    width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222")

        self.confirm_btn = StyledButton(container=area_scan_setting_container, text="Confirm", variable_name="confirm_btn",
                                        left=68, top=142, height=25, width=70, font_size=90)

        self.area_scan_setting_container = area_scan_setting_container
        return area_scan_setting_container

    def onclick_add(self):
        pass

if __name__ == "__main__":
    configuration = {
        "config_project_name": "area_scan",
        "config_address": "0.0.0.0",
        "config_port": 7004,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(area_scan,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
