# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/stage_setup.py
# Compiled at: 2021-02-17 12:01:09
# Size of source mod 2**32: 8332 bytes
from remi.gui import *
from remi import start, App
import micronix_stage_zf as stage_zf, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class stage_setup(App):

    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs.keys():
            (super(stage_setup, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        zpos = "Z:" + str(round(stage_zf.get_z_position(), 2))
        self.stage_container.children["z_axis_position"].set_text(zpos)
        self.stage_container.children["z_axis_step_size"].set_value(float(stage_zf.get_z_step()))
        self.stage_container.children["fiber_rotation"].set_value(float(stage_zf.get_fr_angle()))

    def main(self):
        return stage_setup.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        stage_container = Container()
        stage_container.attr_editor_newclass = False
        stage_container.css_height = "150.0px"
        stage_container.css_left = "0px"
        stage_container.css_margin = "0px"
        stage_container.css_position = "absolute"
        stage_container.css_top = "0px"
        stage_container.css_visibility = "visible"
        stage_container.css_width = "345.0px"
        stage_container.variable_name = "stage_container"
        z_axis_up = Button()
        z_axis_up.attr_editor_newclass = False
        z_axis_up.css_font_size = "100%"
        z_axis_up.css_height = "20px"
        z_axis_up.css_left = "40px"
        z_axis_up.css_margin = "0px"
        z_axis_up.css_position = "absolute"
        z_axis_up.css_top = "50px"
        z_axis_up.css_width = "20px"
        z_axis_up.text = "↑"
        z_axis_up.variable_name = "z_axis_up"
        stage_container.append(z_axis_up, "z_axis_up")
        z_axis_down = Button()
        z_axis_down.attr_editor_newclass = False
        z_axis_down.css_font_size = "100%"
        z_axis_down.css_height = "20px"
        z_axis_down.css_left = "40px"
        z_axis_down.css_margin = "0px"
        z_axis_down.css_position = "absolute"
        z_axis_down.css_top = "90px"
        z_axis_down.css_width = "20px"
        z_axis_down.text = "↓"
        z_axis_down.variable_name = "z_axis_down"
        stage_container.append(z_axis_down, "z_axis_down")
        zero_z = Button()
        zero_z.attr_editor_newclass = False
        zero_z.css_font_size = "100%"
        zero_z.css_height = "20px"
        zero_z.css_left = "270px"
        zero_z.css_margin = "0px"
        zero_z.css_position = "absolute"
        zero_z.css_top = "50px"
        zero_z.css_width = "50px"
        zero_z.text = "zero z"
        zero_z.variable_name = "zero_z"
        stage_container.append(zero_z, "zero_z")
        z_axis_position = Label()
        z_axis_position.attr_editor_newclass = False
        z_axis_position.css_border_style = "none"
        z_axis_position.css_font_size = "100%"
        z_axis_position.css_height = "15.0px"
        z_axis_position.css_left = "270.0px"
        z_axis_position.css_line_height = "16px"
        z_axis_position.css_margin = "0px"
        z_axis_position.css_position = "absolute"
        z_axis_position.css_top = "75.0px"
        z_axis_position.css_width = "75.0px"
        z_axis_position.text = "Z: 100000"
        z_axis_position.variable_name = "z_axis_position"
        stage_container.append(z_axis_position, "z_axis_position")
        z_axis_step_size = SpinBox()
        z_axis_step_size.attr_editor_newclass = False
        z_axis_step_size.attr_max = "1000.0"
        z_axis_step_size.attr_min = "0.1"
        z_axis_step_size.attr_step = "1"
        z_axis_step_size.attr_value = "1000.0"
        z_axis_step_size.css_font_size = "100%"
        z_axis_step_size.css_height = "20px"
        z_axis_step_size.css_left = "180.0px"
        z_axis_step_size.css_margin = "0px"
        z_axis_step_size.css_position = "absolute"
        z_axis_step_size.css_top = "60.0px"
        z_axis_step_size.css_width = "75px"
        z_axis_step_size.variable_name = "z_axis_step_size"
        stage_container.append(z_axis_step_size, "z_axis_step_size")
        fiber_rotation = SpinBox()
        fiber_rotation.attr_editor_newclass = False
        fiber_rotation.attr_max = "45.0"
        fiber_rotation.attr_min = "0"
        fiber_rotation.attr_step = "0.01"
        fiber_rotation.attr_value = "0.7"
        fiber_rotation.css_font_size = "100%"
        fiber_rotation.css_height = "20px"
        fiber_rotation.css_left = "180.0px"
        fiber_rotation.css_margin = "0px"
        fiber_rotation.css_position = "absolute"
        fiber_rotation.css_top = "90.0px"
        fiber_rotation.css_width = "75px"
        fiber_rotation.variable_name = "fiber_rotation"
        stage_container.append(fiber_rotation, "fiber_rotation")
        z_step_label = Label()
        z_step_label.attr_editor_newclass = False
        z_step_label.css_height = "20px"
        z_step_label.css_left = "165.0px"
        z_step_label.css_margin = "0px"
        z_step_label.css_position = "absolute"
        z_step_label.css_top = "62px"
        z_step_label.css_width = "15.0px"
        z_step_label.text = "Z:"
        z_step_label.variable_name = "z_step_label"
        stage_container.append(z_step_label, "z_step_label")
        fiber_rotation_label = Label()
        fiber_rotation_label.attr_editor_newclass = False
        fiber_rotation_label.css_height = "0.0px"
        fiber_rotation_label.css_left = "85.0px"
        fiber_rotation_label.css_margin = "0px"
        fiber_rotation_label.css_position = "absolute"
        fiber_rotation_label.css_top = "92px"
        fiber_rotation_label.css_width = "105.0px"
        fiber_rotation_label.text = "Fiber Rotation:"
        fiber_rotation_label.variable_name = "fiber_rotation_label"
        stage_container.append(fiber_rotation_label, "fiber_rotation_label")
        stage_container.children["z_axis_up"].onclick.do(self.onclick_z_axis_up)
        stage_container.children["z_axis_down"].onclick.do(self.onclick_z_axis_down)
        stage_container.children["zero_z"].onclick.do(self.onclick_zero_z)
        stage_container.children["z_axis_step_size"].onchange.do(self.onchange_z_axis_step_size)
        stage_container.children["fiber_rotation"].onchange.do(self.onchange_fiber_rotation)
        self.stage_container = stage_container
        return self.stage_container

    def onclick_z_axis_up(self, emitter):
        stage_zf.move_z_distance(float(stage_zf.get_z_step()))

    def onclick_z_axis_down(self, emitter):
        if float(stage_zf.get_z_step()) > 100:
            print("Error z down movement too large!!!")
            print("Please use less then 100um for safety")
            return
        stage_zf.move_z_distance(-1.0 * float(stage_zf.get_z_step()))

    def onclick_zero_z(self, emitter):
        stage_zf.zero_stage()

    def onchange_z_axis_step_size(self, emitter, value):
        stage_zf.update_parameter("step_size_z", value)

    def onchange_fiber_rotation(self, emitter, value):
        print("rotation")
        print(value)
        stage_zf.fiber_rotation(value)


configuration = {
 'config_project_name': '"stage_setup"', 'config_address': '"0.0.0.0"', 'config_port': 8082, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(stage_setup, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
