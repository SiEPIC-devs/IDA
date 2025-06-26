# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/NIR Detector/detector_gui.py
# Compiled at: 2021-02-15 17:27:20
# Size of source mod 2**32: 6821 bytes
from remi.gui import *
from remi import start, App
import NIR_detector, time, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


detector = NIR_detector.detector()
while int(detector.dict["detector_inuse"]) == 1:
    detector.reload_parameters()

detector.update_parameter("detector_inuse", "1")
detector.open_port()
detector.detector_init()
detector.close_port()
detector.update_parameter("detector_inuse", "0")
detector.update_parameter("detector_init", "1")

class detector_gui(App):

    def __init__(self, *args, **kwargs):
        global detector
        self.detector = detector
        if "editing_mode" not in kwargs.keys():
            (super(detector_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            self.detector.reload_parameters()
            self.detector_container.children["gain"].set_value(float(self.detector.dict["detector_power_range"].split("dbm")[0]))
            if int(self.detector.dict["measurement_inprogress"]) == 0:
                if int(self.detector.dict["detector_inuse"]) == 0:
                    if int(self.detector.dict["detector_init"]) == 1:
                        self.detector.update_parameter("detector_inuse", "1")
                        self.detector.open_port()
                        self.detector_container.children["detector_1_power"].set_text(str(round(self.detector.detector_read_power(1), 2)))
                        self.detector_container.children["detector_2_power"].set_text(str(round(self.detector.detector_read_power(2), 2)))
                        self.detector.close_port()
                        self.detector.update_parameter("detector_inuse", "0")
        except:
            print("detector read error!!")
            self.detector.update_parameter("detector_inuse", "0")
            time.sleep(5)

    def main(self):
        return detector_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        detector_container = Container()
        detector_container.attr_editor_newclass = False
        detector_container.css_height = "75px"
        detector_container.css_left = "0px"
        detector_container.css_margin = "0px"
        detector_container.css_position = "absolute"
        detector_container.css_top = "0px"
        detector_container.css_visibility = "visible"
        detector_container.css_width = "345.0px"
        detector_container.variable_name = "detector_container"
        gain = SpinBox()
        gain.attr_editor_newclass = False
        gain.attr_max = "30.0"
        gain.attr_min = "-40.0"
        gain.attr_step = "10.00"
        gain.attr_value = "-0.0"
        gain.css_font_size = "100%"
        gain.css_height = "30px"
        gain.css_left = "70.0px"
        gain.css_margin = "0px"
        gain.css_position = "absolute"
        gain.css_top = "20.0px"
        gain.css_width = "50px"
        gain.variable_name = "gain"
        detector_container.append(gain, "gain")
        gain_label = Label()
        gain_label.attr_editor_newclass = False
        gain_label.css_height = "40px"
        gain_label.css_left = "10.0px"
        gain_label.css_margin = "0px"
        gain_label.css_position = "absolute"
        gain_label.css_top = "20.0px"
        gain_label.css_width = "60px"
        gain_label.text = "Power Range dBm"
        gain_label.variable_name = "gain_label"
        detector_container.append(gain_label, "gain_label")
        detector_1_power = Label()
        detector_1_power.attr_editor_newclass = False
        detector_1_power.css_height = "20px"
        detector_1_power.css_left = "135.0px"
        detector_1_power.css_margin = "0px"
        detector_1_power.css_position = "absolute"
        detector_1_power.css_top = "30.0px"
        detector_1_power.css_width = "85px"
        detector_1_power.text = "power dbm"
        detector_1_power.variable_name = "detector_1_power"
        detector_container.append(detector_1_power, "detector_1_power")
        detector_2_power = Label()
        detector_2_power.attr_editor_newclass = False
        detector_2_power.css_height = "20px"
        detector_2_power.css_left = "225px"
        detector_2_power.css_margin = "0px"
        detector_2_power.css_position = "absolute"
        detector_2_power.css_top = "30px"
        detector_2_power.css_width = "85px"
        detector_2_power.text = "power dbm"
        detector_2_power.variable_name = "detector_2_power"
        detector_container.append(detector_2_power, "detector_2_power")
        detector_container.children["gain"].onchange.do(self.onchange_gain)
        self.detector_container = detector_container
        return self.detector_container

    def onchange_gain(self, emitter, value):
        if int(self.detector.dict["detector_inuse"]) == 0:
            if int(self.detector.dict["detector_init"]) == 1:
                self.detector.update_parameter("detector_inuse", "1")
                self.detector.open_port()
                print("Set gain to " + str(value) + "dbm")
                detector.update_parameter("detector_power_range", str(value) + "dbm")
                self.detector.close_port()
                self.detector.update_parameter("detector_inuse", "0")


configuration = {
 'config_project_name': '"detector_gui"', 'config_address': '"0.0.0.0"', 'config_port': 8084, 
 'config_multiple_instance': False, 'config_enable_file_cache': True, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(detector_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
