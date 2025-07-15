from remi import start, App
import os
from lab_gui import *

class instruments(App):
    def __init__(self, *args, **kwargs):
        self.timestamp = -1
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

        for idx, key in enumerate(("chip", "fiber", "laser", "detector", "tec")):
            # Label
            StyledLabel(
                container=instruments_container, variable_name=f"label_{key}",
                text={"chip": "Chip Stage:",
                      "fiber": "Fiber Stage:",
                      "laser": "Laser:",
                      "detector": "Detector:",
                      "tec": "TEC:"}[key],
                left=0, top=15 + idx * 40, width=150, height=20, font_size=100, color="#444", align="right"
            )

            # DropDown
            setattr(self, f"{key}_dd", StyledDropDown(
                container=instruments_container,
                text={"chip": ["Chip Stage A", "Chip Stage B", "Chip Stage C"],
                      "fiber": ["Fiber Stage A", "Fiber Stage B", "Fiber Stage C"],
                      "laser": ["laser A","laser B","laser C"],
                      "detector": ["detector A","detector B","detector C"],
                      "tec": ["TEC A","TEC B","TEC C"]}[key],
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

        self.chip_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_chip_connect_btn))
        self.fiber_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fiber_connect_btn))
        self.laser_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_laser_connect_btn))
        self.detector_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_detector_connect_btn))
        self.tec_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_tec_connect_btn))

        self.instruments_container = instruments_container
        return instruments_container

    def onclick_chip_connect_btn(self):
        device = self.chip_dd.get_value()
        file = File("configure", "chip", device)
        file.save()

    def onclick_fiber_connect_btn(self):
        device = self.fiber_dd.get_value()
        file = File("configure", "fiber", device)
        file.save()

    def onclick_laser_connect_btn(self):
        device = self.laser_dd.get_value()
        file = File("configure", "laser", device)
        file.save()

    def onclick_detector_connect_btn(self):
        device = self.detector_dd.get_value()
        file = File("configure", "detector", device)
        file.save()

    def onclick_tec_connect_btn(self):
        device = self.tec_dd.get_value()
        file = File("configure", "tec", device)
        file.save()



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
