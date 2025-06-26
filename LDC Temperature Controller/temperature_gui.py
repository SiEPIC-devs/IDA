# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/LDC Temperature Controller/temperature_gui.py
# Compiled at: 2023-02-15 01:13:04
# Size of source mod 2**32: 5806 bytes
from remi.gui import *
from remi import start, App
import LDC502 as temperature_controller, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
controller = temperature_controller.controller()
controller.controller_init()

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class temperature_gui(App):

    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs.keys():
            (super(temperature_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        temperature = "Current Temperature: " + str(round(controller.read_temperature(), 2)) + "C"
        self.temperature_container.children["controller_on"].set_value(int(controller.read_onoff()))
        self.temperature_container.children["temperature_reading"].set_text(temperature)
        self.temperature_container.children["temperaure_setpoint"].set_value(float(controller.get_setpoint()))

    def main(self):
        return temperature_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        temperature_container = Container()
        temperature_container.attr_editor_newclass = False
        temperature_container.css_height = "150.0px"
        temperature_container.css_left = "0px"
        temperature_container.css_margin = "0px"
        temperature_container.css_position = "absolute"
        temperature_container.css_top = "0px"
        temperature_container.css_visibility = "visible"
        temperature_container.css_width = "345.0px"
        temperature_container.variable_name = "temperature_container"
        temperaure_setpoint = SpinBox()
        temperaure_setpoint.attr_editor_newclass = False
        temperaure_setpoint.attr_max = "50.0"
        temperaure_setpoint.attr_min = "0"
        temperaure_setpoint.attr_step = "1"
        temperaure_setpoint.attr_value = "25.0"
        temperaure_setpoint.css_font_size = "100%"
        temperaure_setpoint.css_height = "20px"
        temperaure_setpoint.css_left = "70.0px"
        temperaure_setpoint.css_margin = "0px"
        temperaure_setpoint.css_position = "absolute"
        temperaure_setpoint.css_top = "50.0px"
        temperaure_setpoint.css_width = "55px"
        temperaure_setpoint.variable_name = "temperaure_setpoint"
        temperature_container.append(temperaure_setpoint, "temperaure_setpoint")
        setpoint_lable = Label()
        setpoint_lable.attr_editor_newclass = False
        setpoint_lable.css_height = "15px"
        setpoint_lable.css_left = "10.0px"
        setpoint_lable.css_margin = "0px"
        setpoint_lable.css_position = "absolute"
        setpoint_lable.css_top = "52px"
        setpoint_lable.css_width = "50.0px"
        setpoint_lable.text = "Setpoint"
        setpoint_lable.variable_name = "setpoint_lable"
        temperature_container.append(setpoint_lable, "setpoint_lable")
        temperature_reading = Label()
        temperature_reading.attr_editor_newclass = False
        temperature_reading.css_height = "20px"
        temperature_reading.css_left = "145.0px"
        temperature_reading.css_margin = "0px"
        temperature_reading.css_position = "absolute"
        temperature_reading.css_top = "52px"
        temperature_reading.css_width = "200.0px"
        temperature_reading.text = "Temperature:"
        temperature_reading.variable_name = "temperature_reading"
        temperature_container.append(temperature_reading, "temperature_reading")
        controller_on = CheckBoxLabel()
        controller_on.attr_editor_newclass = False
        controller_on.css_align_items = "center"
        controller_on.css_display = "flex"
        controller_on.css_flex_direction = "row"
        controller_on.css_font_size = "100%"
        controller_on.css_height = "30px"
        controller_on.css_justify_content = "space-around"
        controller_on.css_left = "4px"
        controller_on.css_margin = "0px"
        controller_on.css_position = "absolute"
        controller_on.css_top = "80px"
        controller_on.css_width = "120px"
        controller_on.text = "Controller On"
        controller_on.variable_name = "controller_on"
        temperature_container.append(controller_on, "controller_on")
        temperature_container.children["controller_on"].onchange.do(self.onchange_controller_on)
        temperature_container.children["temperaure_setpoint"].onchange.do(self.onchange_temperaure_setpoint)
        self.temperature_container = temperature_container
        return self.temperature_container

    def onchange_temperaure_setpoint(self, emitter, value):
        controller.set_temperature(value)

    def onchange_controller_on(self, emitter, value):
        controller.TEC_onoff(value)


configuration = {
 'config_project_name': '"temperature_gui"', 'config_address': '"0.0.0.0"', 'config_port': 8086, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(temperature_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
