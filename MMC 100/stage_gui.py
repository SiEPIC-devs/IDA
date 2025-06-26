# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/stage_gui.py
# Compiled at: 2021-04-25 15:02:10
# Size of source mod 2**32: 13620 bytes
from remi.gui import *
from remi import start, App
import micronix_stage_xy as stage_xy, os, sys

cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class stage_gui(App):

    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs.keys():
            (super(stage_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        xpos = "X:" + str(round(stage_xy.get_x_position(), 2))
        ypos = "Y:" + str(round(stage_xy.get_y_position(), 2))
        self.stage_container.children["x_axis_position"].set_text(xpos)
        self.stage_container.children["y_axis_position"].set_text(ypos)
        self.stage_container.children["x_axis_step_size"].set_value(float(stage_xy.get_x_step()))
        self.stage_container.children["y_axis_step_size"].set_value(float(stage_xy.get_y_step()))
        self.stage_container.children["rotation_step_size"].set_value(float(stage_xy.get_r_step()))

    def main(self):
        return stage_gui.construct_ui(self)

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
        y_axis_up = Button()
        y_axis_up.attr_editor_newclass = False
        y_axis_up.css_font_size = "100%"
        y_axis_up.css_height = "20px"
        y_axis_up.css_left = "40px"
        y_axis_up.css_margin = "0px"
        y_axis_up.css_position = "absolute"
        y_axis_up.css_top = "50px"
        y_axis_up.css_width = "20px"
        y_axis_up.text = "↑"
        y_axis_up.variable_name = "y_axis_up"
        stage_container.append(y_axis_up, "y_axis_up")
        y_axis_down = Button()
        y_axis_down.attr_editor_newclass = False
        y_axis_down.css_font_size = "100%"
        y_axis_down.css_height = "20px"
        y_axis_down.css_left = "40px"
        y_axis_down.css_margin = "0px"
        y_axis_down.css_position = "absolute"
        y_axis_down.css_top = "90px"
        y_axis_down.css_width = "20px"
        y_axis_down.text = "↓"
        y_axis_down.variable_name = "y_axis_down"
        stage_container.append(y_axis_down, "y_axis_down")
        x_axis_right = Button()
        x_axis_right.attr_editor_newclass = False
        x_axis_right.css_font_size = "100%"
        x_axis_right.css_height = "20px"
        x_axis_right.css_left = "60px"
        x_axis_right.css_margin = "0px"
        x_axis_right.css_position = "absolute"
        x_axis_right.css_top = "70px"
        x_axis_right.css_width = "20px"
        x_axis_right.text = "→"
        x_axis_right.variable_name = "x_axis_right"
        stage_container.append(x_axis_right, "x_axis_right")
        x_axis_left = Button()
        x_axis_left.attr_editor_newclass = False
        x_axis_left.css_bottom = "0px"
        x_axis_left.css_font_size = "100%"
        x_axis_left.css_height = "20px"
        x_axis_left.css_left = "20px"
        x_axis_left.css_margin = "0px"
        x_axis_left.css_position = "absolute"
        x_axis_left.css_top = "70px"
        x_axis_left.css_width = "20px"
        x_axis_left.text = "←"
        x_axis_left.variable_name = "x_axis_left"
        stage_container.append(x_axis_left, "x_axis_left")
        zero = Button()
        zero.attr_editor_newclass = False
        zero.css_font_size = "100%"
        zero.css_height = "20px"
        zero.css_left = "270px"
        zero.css_margin = "0px"
        zero.css_position = "absolute"
        zero.css_top = "50px"
        zero.css_width = "40px"
        zero.text = "zero"
        zero.variable_name = "zero"
        stage_container.append(zero, "zero")
        x_axis_position = Label()
        x_axis_position.attr_editor_newclass = False
        x_axis_position.css_border_style = "none"
        x_axis_position.css_font_size = "100%"
        x_axis_position.css_height = "15.0px"
        x_axis_position.css_left = "270px"
        x_axis_position.css_line_height = "16px"
        x_axis_position.css_margin = "0px"
        x_axis_position.css_position = "absolute"
        x_axis_position.css_top = "75.0px"
        x_axis_position.css_width = "75.0px"
        x_axis_position.text = "X: 100000"
        x_axis_position.variable_name = "x_axis_position"
        stage_container.append(x_axis_position, "x_axis_position")
        y_axis_position = Label()
        y_axis_position.attr_editor_newclass = False
        y_axis_position.css_font_size = "100%"
        y_axis_position.css_height = "0.0px"
        y_axis_position.css_left = "270px"
        y_axis_position.css_line_height = "16px"
        y_axis_position.css_margin = "0px"
        y_axis_position.css_position = "absolute"
        y_axis_position.css_top = "95px"
        y_axis_position.css_width = "75.0px"
        y_axis_position.text = "Y: 100000"
        y_axis_position.variable_name = "y_axis_position"
        stage_container.append(y_axis_position, "y_axis_position")
        x_axis_step_size = SpinBox()
        x_axis_step_size.attr_editor_newclass = False
        x_axis_step_size.attr_max = "10000.0"
        x_axis_step_size.attr_min = "0.1"
        x_axis_step_size.attr_step = "1"
        x_axis_step_size.attr_value = "1000.0"
        x_axis_step_size.css_font_size = "100%"
        x_axis_step_size.css_height = "20px"
        x_axis_step_size.css_left = "180px"
        x_axis_step_size.css_margin = "0px"
        x_axis_step_size.css_position = "absolute"
        x_axis_step_size.css_top = "50px"
        x_axis_step_size.css_width = "75.0px"
        x_axis_step_size.variable_name = "x_axis_step_size"
        stage_container.append(x_axis_step_size, "x_axis_step_size")
        y_axis_step_size = SpinBox()
        y_axis_step_size.attr_editor_newclass = False
        y_axis_step_size.attr_max = "10000.0"
        y_axis_step_size.attr_min = "0.1"
        y_axis_step_size.attr_step = "1"
        y_axis_step_size.attr_value = "1000.0"
        y_axis_step_size.css_font_size = "100%"
        y_axis_step_size.css_height = "20px"
        y_axis_step_size.css_left = "180px"
        y_axis_step_size.css_margin = "0px"
        y_axis_step_size.css_position = "absolute"
        y_axis_step_size.css_top = "80px"
        y_axis_step_size.css_width = "75px"
        y_axis_step_size.variable_name = "y_axis_step_size"
        stage_container.append(y_axis_step_size, "y_axis_step_size")
        rotation_step_size = SpinBox()
        rotation_step_size.attr_editor_newclass = False
        rotation_step_size.attr_max = "1.0"
        rotation_step_size.attr_min = "0"
        rotation_step_size.attr_step = "0.01"
        rotation_step_size.attr_value = "0.5"
        rotation_step_size.css_font_size = "100%"
        rotation_step_size.css_height = "20px"
        rotation_step_size.css_left = "180px"
        rotation_step_size.css_margin = "0px"
        rotation_step_size.css_position = "absolute"
        rotation_step_size.css_top = "110px"
        rotation_step_size.css_width = "75px"
        rotation_step_size.variable_name = "rotation_step_size"
        stage_container.append(rotation_step_size, "rotation_step_size")
        x_step_label = Label()
        x_step_label.attr_editor_newclass = False
        x_step_label.css_font_size = "100%"
        x_step_label.css_height = "20px"
        x_step_label.css_left = "165.0px"
        x_step_label.css_margin = "0px"
        x_step_label.css_position = "absolute"
        x_step_label.css_top = "52px"
        x_step_label.css_width = "15.0px"
        x_step_label.text = "X:"
        x_step_label.variable_name = "x_step_label"
        stage_container.append(x_step_label, "x_step_label")
        y_step_label = Label()
        y_step_label.attr_editor_newclass = False
        y_step_label.css_height = "20px"
        y_step_label.css_left = "165px"
        y_step_label.css_margin = "0px"
        y_step_label.css_position = "absolute"
        y_step_label.css_top = "82px"
        y_step_label.css_width = "15.0px"
        y_step_label.text = "Y:"
        y_step_label.variable_name = "y_step_label"
        stage_container.append(y_step_label, "y_step_label")
        chip_rotation_label = Label()
        chip_rotation_label.attr_editor_newclass = False
        chip_rotation_label.css_height = "20px"
        chip_rotation_label.css_left = "90px"
        chip_rotation_label.css_margin = "0px"
        chip_rotation_label.css_position = "absolute"
        chip_rotation_label.css_top = "112px"
        chip_rotation_label.css_width = "90.0px"
        chip_rotation_label.text = "Chip Rotation:"
        chip_rotation_label.variable_name = "chip_rotation_label"
        stage_container.append(chip_rotation_label, "chip_rotation_label")
        chip_clockwise = Button()
        chip_clockwise.attr_editor_newclass = False
        chip_clockwise.css_font_size = "100%"
        chip_clockwise.css_font_style = "normal"
        chip_clockwise.css_font_weight = "normal"
        chip_clockwise.css_height = "20px"
        chip_clockwise.css_left = "95px"
        chip_clockwise.css_margin = "0px"
        chip_clockwise.css_position = "absolute"
        chip_clockwise.css_top = "50px"
        chip_clockwise.css_width = "20px"
        chip_clockwise.text = "↻"
        chip_clockwise.variable_name = "chip_clockwise"
        stage_container.append(chip_clockwise, "chip_clockwise")
        chip_counterclock = Button()
        chip_counterclock.attr_editor_newclass = False
        chip_counterclock.css_font_size = "100%"
        chip_counterclock.css_font_style = "normal"
        chip_counterclock.css_height = "20px"
        chip_counterclock.css_left = "130px"
        chip_counterclock.css_margin = "0px"
        chip_counterclock.css_position = "absolute"
        chip_counterclock.css_top = "50px"
        chip_counterclock.css_width = "20px"
        chip_counterclock.text = "↺"
        chip_counterclock.variable_name = "chip_counterclock"
        stage_container.append(chip_counterclock, "chip_counterclock")
        stage_container.children["y_axis_up"].onclick.do(self.onclick_y_axis_up)
        stage_container.children["y_axis_down"].onclick.do(self.onclick_y_axis_down)
        stage_container.children["x_axis_right"].onclick.do(self.onclick_x_axis_right)
        stage_container.children["x_axis_left"].onclick.do(self.onclick_x_axis_left)
        stage_container.children["zero"].onclick.do(self.onclick_zero)
        stage_container.children["x_axis_step_size"].onchange.do(self.onchange_x_axis_step_size)
        stage_container.children["y_axis_step_size"].onchange.do(self.onchange_y_axis_step_size)
        stage_container.children["rotation_step_size"].onchange.do(self.onchange_rotation_step_size)
        stage_container.children["chip_clockwise"].onclick.do(self.onclick_chip_clockwise)
        stage_container.children["chip_counterclock"].onclick.do(self.onclick_chip_counterclock)
        self.stage_container = stage_container
        return self.stage_container

    def onclick_y_axis_up(self, emitter):
        stage_xy.move_y_distance(1.0 * float(stage_xy.get_y_step()))

    def onclick_y_axis_down(self, emitter):
        stage_xy.move_y_distance(-1.0 * float(stage_xy.get_y_step()))

    def onclick_x_axis_right(self, emitter):
        stage_xy.move_x_distance(-1.0 * float(stage_xy.get_x_step()))

    def onclick_x_axis_left(self, emitter):
        stage_xy.move_x_distance(1.0 * float(stage_xy.get_x_step()))

    def onclick_zero(self, emitter):
        stage_xy.zero_stage()

    def onchange_x_axis_step_size(self, emitter, value):
        stage_xy.update_parameter("step_size_x", value)

    def onchange_y_axis_step_size(self, emitter, value):
        stage_xy.update_parameter("step_size_y", value)

    def onchange_rotation_step_size(self, emitter, value):
        stage_xy.update_parameter("step_size_cr", value)

    def onclick_chip_clockwise(self, emitter):
        stage_xy.chip_rotation(-1.0 * float(stage_xy.get_r_step()))

    def onclick_chip_counterclock(self, emitter):
        stage_xy.chip_rotation(float(stage_xy.get_r_step()))


configuration = {
 'config_project_name': '"stage_gui"', 'config_address': '"0.0.0.0"', 'config_port': 8081, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(stage_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
