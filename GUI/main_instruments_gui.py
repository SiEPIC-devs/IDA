from remi import start, App
import os
from lab_gui import *

class instruments(App):
    def __init__(self, *args, **kwargs):
        self.configuration = {"stage": "", "laser": "", "detector": "", "tec": ""}
        self.stage_connect_btn = None
        self.laser_connect_btn = None
        self.detector_connect_btn = None
        self.tec_connect_btn = None
        self.terminal = None
        self.stage_dd = None
        self.laser_dd = None
        self.detector_dd = None
        self.tec_dd = None
        if "editing_mode" not in kwargs:
            super(instruments, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.terminal.terminal_refresh()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def construct_ui(self):
        instruments_container = StyledContainer(
            variable_name="instruments_container", left=0, top=0
        )

        for idx, key in enumerate(("stage", "laser", "detector", "tec")):
            # Label
            StyledLabel(
                container=instruments_container, variable_name=f"label_{key}",
                text={"stage": "Stage:",
                      "laser": "Laser:",
                      "detector": "Detector:",
                      "tec": "TEC:"}[key],
                left=0, top=15 + idx * 40, width=150, height=20, font_size=100, color="#444", align="right"
            )

            # DropDown
            setattr(self, f"{key}_dd", StyledDropDown(
                container=instruments_container,
                text={"stage": ["347_stage_control", "stage_B", "stage_C"],
                      "laser": ["347_stage_control","laser_B","laser_C"],
                      "detector": ["347_stage_control","detector_B","detector_C"],
                      "tec": ["347_stage_control","TEC_B","TEC_C"]}[key],
                variable_name=f"set_{key}", left=160, top=10 + idx * 40, width=180, height=30))

            # Configure Button
            setattr(self, f"{key}_configure_btn", StyledButton(
                container=instruments_container, text="Configure", variable_name=f"configure_{key}",
                left=360, top=10 + idx*40, normal_color="#007BFF", press_color="#0056B3"
            ))

            # Connect Button
            setattr(self, f"{key}_connect_btn", StyledButton(
                container=instruments_container, text="Connect", variable_name=f"connect_{key}",
                left=480, top=10 + idx * 40, normal_color="#007BFF", press_color="#0056B3"
            ))

        # Terminal
        terminal_container = StyledContainer(
            container=instruments_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text", left=10, top=15, width=610, height=100
        )

        self.stage_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_stage_connect_btn))
        self.laser_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_laser_connect_btn))
        self.detector_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_detector_connect_btn))
        self.tec_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_tec_connect_btn))

        self.instruments_container = instruments_container
        return instruments_container

    def onclick_stage_connect_btn(self):
        if self.stage_connect_btn.get_text() == "Connect":
            self.configuration["stage"] = self.stage_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.stage_connect_btn.set_text("Connected")
        else:
            self.configuration["stage"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.stage_connect_btn.set_text("Connect")

    def onclick_laser_connect_btn(self):
        if self.laser_connect_btn.get_text() == "Connect":
            self.configuration["laser"] = self.laser_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.laser_connect_btn.set_text("Connected")
        else:
            self.configuration["laser"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.laser_connect_btn.set_text("Connect")

    def onclick_detector_connect_btn(self):
        if self.detector_connect_btn.get_text() == "Connect":
            self.configuration["detector"] = self.detector_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.detector_connect_btn.set_text("Connected")
        else:
            self.configuration["detector"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.detector_connect_btn.set_text("Connect")

    def onclick_tec_connect_btn(self):
        if self.tec_connect_btn.get_text() == "Connect":
            self.configuration["tec"] = self.tec_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.tec_connect_btn.set_text("Connected")
        else:
            self.configuration["tec"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.tec_connect_btn.set_text("Connect")



if __name__ == "__main__":
    configuration = {
        "config_project_name": "instruments",
        "config_address": "0.0.0.0",
        "config_port": 9001,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(instruments,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
