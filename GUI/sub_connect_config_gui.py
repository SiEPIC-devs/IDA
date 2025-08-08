from lab_gui import *
from remi import start, App
import serial.tools.list_ports
import threading
import os
import pyvisa, re

command_path = os.path.join("database", "command.json")

class connect_config(App):
    def __init__(self, *args, **kwargs):
        self.stage_dd = None
        self.sensor_dd = None
        self.tec_dd = None
        self._last_ports = []
        if "editing_mode" not in kwargs:
            super(connect_config, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            ports = list(serial.tools.list_ports.comports())
            com_names = [p.device for p in ports]

            # rm = pyvisa.ResourceManager()
            # visa_resources = rm.list_resources()
            # asrl_resources = [r for r in visa_resources if "ASRL" in r]

            if com_names != self._last_ports:
                self._last_ports = com_names

                self.refresh_dropdown(self.stage_dd, com_names)
                self.refresh_dropdown(self.sensor_dd, com_names)
                self.refresh_dropdown(self.tec_dd, com_names)

        except Exception as e:
            print("Error scanning ports:", e)

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        connect_config_setting_container = StyledContainer(
            variable_name="connect_config_setting_container", left=0, top=0, height=180, width=200
        )

        StyledLabel(
            container=connect_config_setting_container, text="Stage", variable_name="stage",
            left=0, top=10, width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.stage_dd = StyledDropDown(
            container=connect_config_setting_container, variable_name="stage_dd", text="N/A",
            left=70, top=10, width=100, height=25, position="absolute"
        )

        StyledLabel(
            container=connect_config_setting_container, text="Sensor", variable_name="sensor",
            left=0, top=45, width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.sensor_dd = StyledDropDown(
            container=connect_config_setting_container, variable_name="sensor_dd", text="N/A",
            left=70, top=45, width=100, height=25, position="absolute"
        )

        StyledLabel(
            container=connect_config_setting_container, text="TEC", variable_name="tec",
            left=0, top=80, width=60, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.tec_dd = StyledDropDown(
            container=connect_config_setting_container, variable_name="tec_dd", text="N/A",
            left=70, top=80, width=100, height=25, position="absolute"
        )

        self.confirm_btn = StyledButton(
            container=connect_config_setting_container, text="Confirm", variable_name="confirm_btn",
            left=68, top=142, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.connect_config_setting_container = connect_config_setting_container
        return connect_config_setting_container

    def refresh_dropdown(self, dropdown, items):
        dropdown.empty()
        if items:
            dropdown.append(items)
            dropdown.set_value(items[0])
        else:
            dropdown.append("N/A")
            dropdown.set_value("N/A")

    def onclick_confirm(self):
        selected_stage = self.stage_dd.get_value()
        selected_sensor = self.sensor_dd.get_value()
        selected_tec = self.tec_dd.get_value()
        stage_num = int(re.search(r'\d+', selected_stage).group()) if selected_stage else None
        sensor_num = int(re.search(r'\d+', selected_sensor).group()) if selected_sensor else None
        tec_num = int(re.search(r'\d+', selected_tec).group()) if selected_tec else None
        print("Stage COM:", stage_num)
        print("Sensor COM:", sensor_num)
        print("TEC COM:", tec_num)
        config = {"stage": stage_num, "sensor": sensor_num, "tec": tec_num}
        file = File("shared_memory", "Port", config)
        file.save()

if __name__ == "__main__":
    configuration = {
        "config_project_name": "connect_config",
        "config_address": "0.0.0.0",
        "config_port": 7005,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(connect_config,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
