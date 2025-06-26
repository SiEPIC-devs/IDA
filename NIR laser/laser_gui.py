# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Downloads/laser_gui.py
# Compiled at: 2022-09-12 22:42:27
# Size of source mod 2**32: 14410 bytes
from remi.gui import *
from remi import start, App
import laser as laserNIR, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR Detector"))
import NIR_detector
detector = NIR_detector.detector()
laser = laserNIR.laser()
while int(laser.dict["laser_inuse"]) == 1:
    laser.reload_parameters()

laser.update_parameter("laser_inuse", "1")
while int(detector.dict["detector_inuse"]) == 1:
    detector.reload_parameters()

detector.update_parameter("detector_inuse", "1")
import laser_functions
laser.open_port()
laser.laser_init()
laser.close_port()
laser.update_parameter("laser_inuse", "0")
laser.update_parameter("laser_init", "1")
detector.update_parameter("detector_inuse", "0")

class laser_gui(App):

    def __init__(self, *args, **kwargs):
        global detector
        global laser
        self.laser = laser
        self.detector = detector
        if "editing_mode" not in kwargs.keys():
            (super(laser_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        laser.reload_parameters()
        self.laser_container.children["wavelength"].set_value(float(laser.dict["laser_current_wavelength"]))
        self.laser_container.children["start_wavelength"].set_value(float(laser.dict["laser_sweep_start_wavelength"]))
        self.laser_container.children["stop_wavelength"].set_value(float(laser.dict["laser_sweep_stop_wavelength"]))
        self.laser_container.children["step_wavelength"].set_value(float(laser.dict["laser_sweep_step_size"]))
        self.laser_container.children["laser_on"].set_value(int(laser.dict["laser_power_state"]))

    def main(self):
        return laser_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        laser_container = Container()
        laser_container.attr_editor_newclass = False
        laser_container.css_height = "75px"
        laser_container.css_left = "0px"
        laser_container.css_margin = "0px"
        laser_container.css_position = "absolute"
        laser_container.css_top = "0px"
        laser_container.css_visibility = "visible"
        laser_container.css_width = "345.0px"
        laser_container.variable_name = "laser_container"
        laser_on = CheckBoxLabel()
        laser_on.attr_editor_newclass = False
        laser_on.css_align_items = "center"
        laser_on.css_display = "flex"
        laser_on.css_flex_direction = "row"
        laser_on.css_font_size = "100%"
        laser_on.css_height = "30px"
        laser_on.css_justify_content = "space-around"
        laser_on.css_left = "5px"
        laser_on.css_margin = "0px"
        laser_on.css_position = "absolute"
        laser_on.css_top = "5px"
        laser_on.css_width = "100px"
        laser_on.text = "Laser On"
        laser_on.variable_name = "laser_on"
        laser_container.append(laser_on, "laser_on")
        wavelength = SpinBox()
        wavelength.attr_editor_newclass = False
        wavelength.attr_max = "1670.0"
        wavelength.attr_min = "1400.0"
        wavelength.attr_step = "0.01"
        wavelength.attr_value = "1550.0"
        wavelength.css_font_size = "100%"
        wavelength.css_height = "30px"
        wavelength.css_left = "10.0px"
        wavelength.css_margin = "0px"
        wavelength.css_position = "absolute"
        wavelength.css_top = "30.0px"
        wavelength.css_width = "70px"
        wavelength.variable_name = "wavelength"
        laser_container.append(wavelength, "wavelength")
        start_wavelength = SpinBox()
        start_wavelength.attr_editor_newclass = False
        start_wavelength.attr_max = "1670.0"
        start_wavelength.attr_min = "1400.0"
        start_wavelength.attr_step = "0.01"
        start_wavelength.attr_value = "1400.0"
        start_wavelength.css_font_size = "100%"
        start_wavelength.css_height = "30px"
        start_wavelength.css_left = "135.0px"
        start_wavelength.css_margin = "0px"
        start_wavelength.css_position = "absolute"
        start_wavelength.css_top = "30.0px"
        start_wavelength.css_width = "70px"
        start_wavelength.variable_name = "start_wavelength"
        laser_container.append(start_wavelength, "start_wavelength")
        stop_wavelength = SpinBox()
        stop_wavelength.attr_editor_newclass = False
        stop_wavelength.attr_max = "1670.0"
        stop_wavelength.attr_min = "1400.0"
        stop_wavelength.attr_step = "0.01"
        stop_wavelength.attr_value = "1670.0"
        stop_wavelength.css_font_size = "100%"
        stop_wavelength.css_height = "30px"
        stop_wavelength.css_left = "210.0px"
        stop_wavelength.css_margin = "0px"
        stop_wavelength.css_position = "absolute"
        stop_wavelength.css_top = "30.0px"
        stop_wavelength.css_width = "70px"
        stop_wavelength.variable_name = "stop_wavelength"
        laser_container.append(stop_wavelength, "stop_wavelength")
        step_wavelength = SpinBox()
        step_wavelength.attr_editor_newclass = False
        step_wavelength.attr_max = "1"
        step_wavelength.attr_min = "0.0001"
        step_wavelength.attr_step = "0.01"
        step_wavelength.attr_value = "0.01"
        step_wavelength.css_font_size = "100%"
        step_wavelength.css_height = "30px"
        step_wavelength.css_left = "85.0px"
        step_wavelength.css_margin = "0px"
        step_wavelength.css_position = "absolute"
        step_wavelength.css_top = "30.0px"
        step_wavelength.css_width = "45px"
        step_wavelength.variable_name = "step_wavelength"
        laser_container.append(step_wavelength, "step_wavelength")
        sweep = Button()
        sweep.attr_editor_newclass = False
        sweep.css_font_size = "100%"
        sweep.css_height = "30px"
        sweep.css_left = "285.0px"
        sweep.css_margin = "0px"
        sweep.css_position = "absolute"
        sweep.css_top = "30.0px"
        sweep.css_width = "50px"
        sweep.text = "Sweep"
        sweep.variable_name = "sweep"
        laser_container.append(sweep, "sweep")
        label_sweep_range = Label()
        label_sweep_range.attr_editor_newclass = False
        label_sweep_range.css_font_size = "100%"
        label_sweep_range.css_height = "30px"
        label_sweep_range.css_left = "165.0px"
        label_sweep_range.css_margin = "0px"
        label_sweep_range.css_position = "absolute"
        label_sweep_range.css_top = "10px"
        label_sweep_range.css_width = "100px"
        label_sweep_range.text = "Sweep Range"
        label_sweep_range.variable_name = "label_sweep_range"
        laser_container.append(label_sweep_range, "label_sweep_range")
        laser_container.children["laser_on"].onchange.do(self.onchange_laser_on)
        laser_container.children["wavelength"].onchange.do(self.onchange_wavelength)
        laser_container.children["start_wavelength"].onchange.do(self.onchange_start_wavelength)
        laser_container.children["stop_wavelength"].onchange.do(self.onchange_stop_wavelength)
        laser_container.children["step_wavelength"].onchange.do(self.onchange_step_wavelength)
        laser_container.children["sweep"].onclick.do(self.onclick_sweep)
        self.laser_container = laser_container
        return self.laser_container

    def onchange_laser_on(self, emitter, value):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                self.laser.update_parameter("laser_inuse", "1")
                laser.open_port()
                if value == 1:
                    self.laser.turn_laser_on()
                else:
                    self.laser.turn_laser_off()
                laser.close_port()
                self.laser.update_parameter("laser_inuse", "0")

    def onchange_wavelength(self, emitter, value):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                self.laser.update_parameter("laser_inuse", "1")
                laser.open_port()
                self.laser.set_laser_current_wavelength(float(value))
                laser.update_parameter("laser_current_wavelength", str(float(value)))
                laser.close_port()
                self.laser.update_parameter("laser_inuse", "0")

    def onchange_start_wavelength(self, emitter, value):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                self.laser.update_parameter("laser_inuse", "1")
                laser.open_port()
                start, stop, resolution, speed = self.laser.check_sweep_parameters(start=(float(value)))
                self.laser.set_sweep_start(float(start))
                self.laser.set_sweep_stop(float(stop))
                self.laser.set_laser_sweep_step_size(float(resolution))
                self.laser.set_continuous_sweep_speed(float(speed))
                laser.update_parameter("laser_sweep_start_wavelength", str(float(start)))
                laser.update_parameter("laser_sweep_stop_wavelength", str(float(stop)))
                laser.update_parameter("laser_sweep_step_size", str(float(resolution)))
                laser.update_parameter("laser_continuous_sweep_speed", str(float(speed)) + "nm/s")
                laser.close_port()
                self.laser.update_parameter("laser_inuse", "0")

    def onchange_stop_wavelength(self, emitter, value):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                self.laser.update_parameter("laser_inuse", "1")
                laser.open_port()
                start, stop, resolution, speed = self.laser.check_sweep_parameters(stop=(float(value)))
                self.laser.set_sweep_start(float(start))
                self.laser.set_sweep_stop(float(stop))
                self.laser.set_laser_sweep_step_size(float(resolution))
                self.laser.set_continuous_sweep_speed(float(speed))
                laser.update_parameter("laser_sweep_start_wavelength", str(float(start)))
                laser.update_parameter("laser_sweep_stop_wavelength", str(float(stop)))
                laser.update_parameter("laser_sweep_step_size", str(float(resolution)))
                laser.update_parameter("laser_continuous_sweep_speed", str(float(speed)) + "nm/s")
                laser.close_port()
                self.laser.update_parameter("laser_inuse", "0")

    def onchange_step_wavelength(self, emitter, value):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                self.laser.update_parameter("laser_inuse", "1")
                laser.open_port()
                start, stop, resolution, speed = self.laser.check_sweep_parameters(resolution=(float(value)))
                self.laser.set_sweep_start(float(start))
                self.laser.set_sweep_stop(float(stop))
                self.laser.set_laser_sweep_step_size(float(resolution))
                self.laser.set_continuous_sweep_speed(float(speed))
                laser.update_parameter("laser_sweep_start_wavelength", str(float(start)))
                laser.update_parameter("laser_sweep_stop_wavelength", str(float(stop)))
                laser.update_parameter("laser_sweep_step_size", str(float(resolution)))
                laser.update_parameter("laser_continuous_sweep_speed", str(float(speed)) + "nm/s")
                laser.close_port()
                self.laser.update_parameter("laser_inuse", "0")

    def onclick_sweep(self, emitter):
        self.laser.reload_parameters()
        if int(self.laser.dict["laser_inuse"]) == 0:
            if int(self.laser.dict["laser_init"]) == 1:
                import shutil
                shutil.copyfile("./scaninprogress.png", os.path.join(main_path, "Plot", "./res/scaninprogress.png"))
                self.detector.reload_parameters()
                if int(self.detector.dict["detector_init"]) == 0:
                    print("no detector init")
                    return 1
                while int(self.detector.dict["detector_inuse"]) == 1:
                    self.detector.reload_parameters()
                    continue

                self.detector.update_parameter("detector_inuse", "1")
                self.laser.update_parameter("laser_inuse", "1")
                self.laser.update_parameter("laser_power_state", "1")
                sweep_count = 0
                while sweep_count < 2:
                    if str(self.laser.dict["laser_sweep_direction"]) == "reverse":
                        sweep_return = laser_functions.spectrum_sweep_reverse("./manual scans/Spectral_Sweep_")
                    else:
                        sweep_return = laser_functions.spectrum_sweep("./manual scans/Spectral_Sweep_")
                    if sweep_return == 3:
                        sweep_count = sweep_count + 1
                        continue
                    else:
                        if sweep_return == 2:
                            sweep_count = sweep_count + 1
                            continue
                    break

                self.laser.update_parameter("laser_inuse", "0")
                self.detector.update_parameter("detector_inuse", "0")


configuration = {
 'config_project_name': '"laser_gui"', 'config_address': '"0.0.0.0"', 'config_port': 8083, 
 'config_multiple_instance': False, 'config_enable_file_cache': True, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(laser_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
