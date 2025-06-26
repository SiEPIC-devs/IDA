# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Alignment NIR/alignment_gui.py
# Compiled at: 2021-04-15 19:50:48
# Size of source mod 2**32: 20323 bytes
from remi.gui import *
from remi import start, App
import os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import area_sweep
area_sweep = area_sweep.alignment()
area_sweep.update_parameter("detector_chn_align", 1)
area_sweep.update_parameter("step_away_x_align", 5)
area_sweep.update_parameter("step_away_y_align", 5)
area_sweep.update_parameter("step_size_x_during_align", 5)
area_sweep.update_parameter("step_size_y_during_align", 5)
import shutil
shutil.copyfile("./nonewplots.png", os.path.join(main_path, "Plot", "./res/nonewplots.png"))

class alignment_gui(App):

    def __init__(self, *args, **kwargs):
        global area_sweep
        self.area_sweep = area_sweep
        self.step_x = 10
        self.step_size_x = 1
        self.step_y = 10
        self.step_size_y = 1
        self.step_x_align = int(self.area_sweep.dict["step_away_x_align"])
        self.step_size_x_align = float(self.area_sweep.dict["step_size_x_during_align"])
        self.step_y_align = int(self.area_sweep.dict["step_away_y_align"])
        self.step_size_y_align = float(self.area_sweep.dict["step_size_y_during_align"])
        self.detector = int(self.area_sweep.dict["detector_chn_align"])
        if "editing_mode" not in kwargs.keys():
            (super(alignment_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.alignment_container.children["x_step_count"].set_value(int(self.step_x))
        self.alignment_container.children["y_step_count"].set_value(int(self.step_y))
        self.alignment_container.children["x_step_size"].set_value(self.step_size_x)
        self.alignment_container.children["y_step_size"].set_value(self.step_size_y)
        self.alignment_container.children["x_step_count_alignment"].set_value(int(self.step_x_align))
        self.alignment_container.children["y_step_count_alignment"].set_value(int(self.step_y_align))
        self.alignment_container.children["x_step_size_alignment"].set_value(self.step_size_x_align)
        self.alignment_container.children["y_step_size_alignment"].set_value(self.step_size_y_align)
        self.alignment_container.children["detector_setting"].set_value(self.detector)

    def main(self):
        return alignment_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        alignment_container = Container()
        alignment_container.attr_editor_newclass = False
        alignment_container.css_height = "150.0px"
        alignment_container.css_left = "0px"
        alignment_container.css_margin = "0px"
        alignment_container.css_position = "absolute"
        alignment_container.css_top = "0px"
        alignment_container.css_visibility = "visible"
        alignment_container.css_width = "345.0px"
        alignment_container.variable_name = "alignment_container"
        x_step_count = SpinBox()
        x_step_count.attr_editor_newclass = False
        x_step_count.attr_max = "200.0"
        x_step_count.attr_min = "1.0"
        x_step_count.attr_step = "1"
        x_step_count.attr_value = "10.0"
        x_step_count.css_font_size = "100%"
        x_step_count.css_height = "30px"
        x_step_count.css_left = "40px"
        x_step_count.css_margin = "0px"
        x_step_count.css_position = "absolute"
        x_step_count.css_top = "40px"
        x_step_count.css_width = "50px"
        x_step_count.variable_name = "x_step_count"
        alignment_container.append(x_step_count, "x_step_count")
        x_step_size = SpinBox()
        x_step_size.attr_editor_newclass = False
        x_step_size.attr_max = "100.0"
        x_step_size.attr_min = "0.25"
        x_step_size.attr_step = "1"
        x_step_size.attr_value = "5.0"
        x_step_size.css_height = "30px"
        x_step_size.css_left = "100px"
        x_step_size.css_margin = "0px"
        x_step_size.css_position = "absolute"
        x_step_size.css_top = "40px"
        x_step_size.css_width = "50px"
        x_step_size.variable_name = "x_step_size"
        alignment_container.append(x_step_size, "x_step_size")
        y_step_count = SpinBox()
        y_step_count.attr_editor_newclass = False
        y_step_count.attr_max = "200.0"
        y_step_count.attr_min = "1.0"
        y_step_count.attr_step = "1"
        y_step_count.attr_value = "10.0"
        y_step_count.css_height = "30px"
        y_step_count.css_left = "40px"
        y_step_count.css_margin = "0px"
        y_step_count.css_position = "absolute"
        y_step_count.css_top = "80px"
        y_step_count.css_width = "50px"
        y_step_count.variable_name = "y_step_count"
        alignment_container.append(y_step_count, "y_step_count")
        y_step_size = SpinBox()
        y_step_size.attr_editor_newclass = False
        y_step_size.attr_max = "100.0"
        y_step_size.attr_min = "0.25"
        y_step_size.attr_step = "1"
        y_step_size.attr_value = "5.0"
        y_step_size.css_height = "30px"
        y_step_size.css_left = "100px"
        y_step_size.css_margin = "0px"
        y_step_size.css_position = "absolute"
        y_step_size.css_top = "80px"
        y_step_size.css_width = "50px"
        y_step_size.variable_name = "y_step_size"
        alignment_container.append(y_step_size, "y_step_size")
        start_area_sweep = Button()
        start_area_sweep.attr_editor_newclass = False
        start_area_sweep.css_height = "30px"
        start_area_sweep.css_left = "45.0px"
        start_area_sweep.css_margin = "0px"
        start_area_sweep.css_position = "absolute"
        start_area_sweep.css_top = "115px"
        start_area_sweep.css_width = "100px"
        start_area_sweep.text = "Area Scan"
        start_area_sweep.variable_name = "start_area_sweep"
        alignment_container.append(start_area_sweep, "start_area_sweep")
        label_x = Label()
        label_x.attr_editor_newclass = False
        label_x.css_height = "15px"
        label_x.css_left = "25px"
        label_x.css_margin = "0px"
        label_x.css_position = "absolute"
        label_x.css_top = "48px"
        label_x.css_width = "15px"
        label_x.text = "X:"
        label_x.variable_name = "label_x"
        alignment_container.append(label_x, "label_x")
        label_y = Label()
        label_y.attr_editor_newclass = False
        label_y.css_height = "15.0px"
        label_y.css_left = "25px"
        label_y.css_margin = "0px"
        label_y.css_position = "absolute"
        label_y.css_top = "88px"
        label_y.css_width = "15.0px"
        label_y.text = "Y:"
        label_y.variable_name = "label_y"
        alignment_container.append(label_y, "label_y")
        label_step_count = Label()
        label_step_count.attr_editor_newclass = False
        label_step_count.css_font_size = "100%"
        label_step_count.css_height = "30.0px"
        label_step_count.css_left = "40px"
        label_step_count.css_margin = "0px"
        label_step_count.css_position = "absolute"
        label_step_count.css_text_align = "center"
        label_step_count.css_top = "7px"
        label_step_count.css_width = "45.0px"
        label_step_count.text = "Step Count"
        label_step_count.variable_name = "label_step_count"
        alignment_container.append(label_step_count, "label_step_count")
        label_step_size = Label()
        label_step_size.attr_editor_newclass = False
        label_step_size.css_height = "30.0px"
        label_step_size.css_left = "100px"
        label_step_size.css_margin = "0px"
        label_step_size.css_position = "absolute"
        label_step_size.css_text_align = "center"
        label_step_size.css_top = "7px"
        label_step_size.css_width = "45px"
        label_step_size.text = "Step Size"
        label_step_size.variable_name = "label_step_size"
        alignment_container.append(label_step_size, "label_step_size")
        x_step_count_alignment = SpinBox()
        x_step_count_alignment.attr_editor_newclass = False
        x_step_count_alignment.attr_max = "200"
        x_step_count_alignment.attr_min = "0"
        x_step_count_alignment.attr_step = "1"
        x_step_count_alignment.attr_value = "10.0"
        x_step_count_alignment.css_font_size = "100%"
        x_step_count_alignment.css_height = "30px"
        x_step_count_alignment.css_left = "180px"
        x_step_count_alignment.css_margin = "0px"
        x_step_count_alignment.css_position = "absolute"
        x_step_count_alignment.css_top = "40px"
        x_step_count_alignment.css_width = "50px"
        x_step_count_alignment.variable_name = "x_step_count_alignment"
        alignment_container.append(x_step_count_alignment, "x_step_count_alignment")
        x_step_size_alignment = SpinBox()
        x_step_size_alignment.attr_editor_newclass = False
        x_step_size_alignment.attr_max = "100.0"
        x_step_size_alignment.attr_min = "0"
        x_step_size_alignment.attr_step = "1"
        x_step_size_alignment.attr_value = "5.0"
        x_step_size_alignment.css_height = "30px"
        x_step_size_alignment.css_left = "240px"
        x_step_size_alignment.css_margin = "0px"
        x_step_size_alignment.css_position = "absolute"
        x_step_size_alignment.css_top = "40px"
        x_step_size_alignment.css_width = "50px"
        x_step_size_alignment.variable_name = "x_step_size_alignment"
        alignment_container.append(x_step_size_alignment, "x_step_size_alignment")
        y_step_count_alignment = SpinBox()
        y_step_count_alignment.attr_editor_newclass = False
        y_step_count_alignment.attr_max = "200"
        y_step_count_alignment.attr_min = "0"
        y_step_count_alignment.attr_step = "1"
        y_step_count_alignment.attr_value = "10"
        y_step_count_alignment.css_height = "30px"
        y_step_count_alignment.css_left = "180px"
        y_step_count_alignment.css_margin = "0px"
        y_step_count_alignment.css_position = "absolute"
        y_step_count_alignment.css_top = "80px"
        y_step_count_alignment.css_width = "50px"
        y_step_count_alignment.variable_name = "y_step_count_alignment"
        alignment_container.append(y_step_count_alignment, "y_step_count_alignment")
        y_step_size_alignment = SpinBox()
        y_step_size_alignment.attr_editor_newclass = False
        y_step_size_alignment.attr_max = "100.0"
        y_step_size_alignment.attr_min = "0"
        y_step_size_alignment.attr_step = "1"
        y_step_size_alignment.attr_value = "5.0"
        y_step_size_alignment.css_height = "30px"
        y_step_size_alignment.css_left = "240px"
        y_step_size_alignment.css_margin = "0px"
        y_step_size_alignment.css_position = "absolute"
        y_step_size_alignment.css_top = "80px"
        y_step_size_alignment.css_width = "50px"
        y_step_size_alignment.variable_name = "y_step_size_alignment"
        alignment_container.append(y_step_size_alignment, "y_step_size_alignment")
        start_alignment = Button()
        start_alignment.attr_editor_newclass = False
        start_alignment.css_height = "30px"
        start_alignment.css_left = "185.0px"
        start_alignment.css_margin = "0px"
        start_alignment.css_position = "absolute"
        start_alignment.css_top = "115px"
        start_alignment.css_width = "100px"
        start_alignment.text = "Start Alignment"
        start_alignment.variable_name = "start_alignment"
        alignment_container.append(start_alignment, "start_alignment")
        label_x_alignment = Label()
        label_x_alignment.attr_editor_newclass = False
        label_x_alignment.css_height = "15px"
        label_x_alignment.css_left = "165px"
        label_x_alignment.css_margin = "0px"
        label_x_alignment.css_position = "absolute"
        label_x_alignment.css_top = "48px"
        label_x_alignment.css_width = "15px"
        label_x_alignment.text = "X:"
        label_x_alignment.variable_name = "label_x_alignment"
        alignment_container.append(label_x_alignment, "label_x_alignment")
        label_y_alignment = Label()
        label_y_alignment.attr_editor_newclass = False
        label_y_alignment.css_height = "15.0px"
        label_y_alignment.css_left = "165px"
        label_y_alignment.css_margin = "0px"
        label_y_alignment.css_position = "absolute"
        label_y_alignment.css_top = "88px"
        label_y_alignment.css_width = "15.0px"
        label_y_alignment.text = "Y:"
        label_y_alignment.variable_name = "label_y_alignment"
        alignment_container.append(label_y_alignment, "label_y_alignment")
        label_step_count_alignment = Label()
        label_step_count_alignment.attr_editor_newclass = False
        label_step_count_alignment.css_font_size = "100%"
        label_step_count_alignment.css_height = "30.0px"
        label_step_count_alignment.css_left = "180px"
        label_step_count_alignment.css_margin = "0px"
        label_step_count_alignment.css_position = "absolute"
        label_step_count_alignment.css_text_align = "center"
        label_step_count_alignment.css_top = "7px"
        label_step_count_alignment.css_width = "45.0px"
        label_step_count_alignment.text = "Step Count"
        label_step_count_alignment.variable_name = "label_step_count_alignment"
        alignment_container.append(label_step_count_alignment, "label_step_count_alignment")
        label_step_size_alignment = Label()
        label_step_size_alignment.attr_editor_newclass = False
        label_step_size_alignment.css_height = "30.0px"
        label_step_size_alignment.css_left = "240px"
        label_step_size_alignment.css_margin = "0px"
        label_step_size_alignment.css_position = "absolute"
        label_step_size_alignment.css_text_align = "center"
        label_step_size_alignment.css_top = "7px"
        label_step_size_alignment.css_width = "45px"
        label_step_size_alignment.text = "Step Size"
        label_step_size_alignment.variable_name = "label_step_size_alignment"
        alignment_container.append(label_step_size_alignment, "label_step_size_alignment")
        label_detector = Label()
        label_detector.attr_editor_newclass = False
        label_detector.css_height = "30.0px"
        label_detector.css_left = "290px"
        label_detector.css_margin = "0px"
        label_detector.css_position = "absolute"
        label_detector.css_text_align = "center"
        label_detector.css_top = "7px"
        label_detector.css_width = "45px"
        label_detector.text = "Detector"
        label_detector.variable_name = "label_detector"
        alignment_container.append(label_detector, "label_detector")
        detector_setting = SpinBox()
        detector_setting.attr_editor_newclass = False
        detector_setting.attr_max = "2"
        detector_setting.attr_min = "1"
        detector_setting.attr_step = "1"
        detector_setting.attr_value = "1"
        detector_setting.css_height = "30px"
        detector_setting.css_left = "300px"
        detector_setting.css_margin = "0px"
        detector_setting.css_position = "absolute"
        detector_setting.css_top = "40px"
        detector_setting.css_width = "30px"
        detector_setting.variable_name = "detector_setting"
        alignment_container.append(detector_setting, "detector_setting")
        alignment_container.children["x_step_count"].onchange.do(self.onchange_x_step_count)
        alignment_container.children["x_step_size"].onchange.do(self.onchange_x_step_size)
        alignment_container.children["y_step_count"].onchange.do(self.onchange_y_step_count)
        alignment_container.children["y_step_size"].onchange.do(self.onchange_y_step_size)
        alignment_container.children["start_area_sweep"].onclick.do(self.onclick_start_area_sweep)
        alignment_container.children["x_step_count_alignment"].onchange.do(self.onchange_x_step_count_alignment)
        alignment_container.children["x_step_size_alignment"].onchange.do(self.onchange_x_step_size_alignment)
        alignment_container.children["y_step_count_alignment"].onchange.do(self.onchange_y_step_count_alignment)
        alignment_container.children["y_step_size_alignment"].onchange.do(self.onchange_y_step_size_alignment)
        alignment_container.children["detector_setting"].onchange.do(self.onchange_detector_setting)
        alignment_container.children["start_alignment"].onclick.do(self.onclick_start_alignment)
        self.alignment_container = alignment_container
        return self.alignment_container

    def onchange_x_step_count(self, emitter, value):
        self.step_x = int(round(float(value), 0))
        self.alignment_container.children["x_step_count"].set_value(int(round(float(value), 0)))

    def onchange_x_step_size(self, emitter, value):
        self.step_size_x = float(value)

    def onchange_y_step_count(self, emitter, value):
        self.step_y = int(round(float(value), 0))
        self.alignment_container.children["y_step_count"].set_value(int(round(float(value), 0)))

    def onchange_y_step_size(self, emitter, value):
        self.step_size_y = float(value)

    def onclick_start_area_sweep(self, emitter):
        print("start")
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        import shutil
        shutil.copyfile("./scaninprogress.png", os.path.join(main_path, "Plot", "./res/scaninprogress.png"))
        self.area_sweep.run_area_sweep_trigger(self.detector, self.step_x, self.step_y, self.step_size_x, self.step_size_y)

    def onchange_x_step_count_alignment(self, emitter, value):
        self.step_x_align = int(round(float(value), 0))
        self.area_sweep.update_parameter("step_away_x_align", self.step_x_align)
        self.alignment_container.children["x_step_count_alignment"].set_value(int(round(float(value), 0)))

    def onchange_x_step_size_alignment(self, emitter, value):
        self.step_size_x_align = float(value)
        self.area_sweep.update_parameter("step_size_x_during_align", self.step_size_x_align)

    def onchange_y_step_count_alignment(self, emitter, value):
        self.step_y_align = int(round(float(value), 0))
        self.alignment_container.children["y_step_count_alignment"].set_value(int(round(float(value), 0)))
        self.area_sweep.update_parameter("step_away_y_align", self.step_y_align)

    def onchange_y_step_size_alignment(self, emitter, value):
        self.step_size_y_align = float(value)
        self.area_sweep.update_parameter("step_size_y_during_align", self.step_size_y_align)

    def onchange_detector_setting(self, emitter, value):
        self.detector = int(round(float(value), 0))
        if self.detector > 2:
            self.detector = 2
        else:
            if self.detector < 1:
                self.detector = 1
        self.alignment_container.children["detector_setting"].set_value(self.detector)
        self.area_sweep.update_parameter("detector_chn_align", self.detector)

    def onclick_start_alignment(self, emitter):
        self.area_sweep.align_to_device_trigger()


configuration = {
 'config_project_name': '"alignment_gui"', 'config_address': '"0.0.0.0"', 'config_port': 8085, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(alignment_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
