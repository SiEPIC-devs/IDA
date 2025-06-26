# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/main_gui.py
# Compiled at: 2023-02-14 23:59:31
# Size of source mod 2**32: 11801 bytes
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


class NIR_Measurment_System(App):

    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs.keys():
            (super(NIR_Measurment_System, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return NIR_Measurment_System.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        ip_address = "10.2.137.107"
        main = Container()
        main.attr_editor_newclass = False
        main.css_height = "100%"
        main.css_left = "0%"
        main.css_margin = "0px"
        main.css_position = "absolute"
        main.css_top = "0%"
        main.css_width = "100%"
        main.variable_name = "main"
        stage_tabs = TabBox()
        stage_tabs.attr_editor_newclass = False
        stage_tabs.css_align_content = "center"
        stage_tabs.css_align_items = "center"
        stage_tabs.css_height = "215px"
        stage_tabs.css_left = "5%"
        stage_tabs.css_margin = "0px"
        stage_tabs.css_position = "inherit"
        stage_tabs.css_top = "5%"
        stage_tabs.css_width = "345px"
        stage_tabs.variable_name = "stage_tabs"
        main.append(stage_tabs, "stage_tabs")
        self.stage_control = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.stage_control.attributes["src"] = "https://" + ip_address + "/stage/"
        self.stage_control.attributes["width"] = "100%"
        self.stage_control.attributes["height"] = "100%"
        self.stage_control.style["border"] = "None"
        self.stage_setup = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.stage_setup.attributes["src"] = "https://" + ip_address + "/stage_setup/"
        self.stage_setup.attributes["width"] = "100%"
        self.stage_setup.attributes["height"] = "100%"
        self.stage_setup.style["border"] = "None"
        self.stage_temperature = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.stage_temperature.attributes["src"] = "https://" + ip_address + "/stage_temperature/"
        self.stage_temperature.attributes["width"] = "100%"
        self.stage_temperature.attributes["height"] = "100%"
        self.stage_temperature.style["border"] = "None"
        stage_tabs.add_tab(self.stage_control, "Control")
        stage_tabs.add_tab(self.stage_setup, "Setup")
        stage_tabs.add_tab(self.stage_temperature, "Temperature")
        laser_tabs = TabBox()
        laser_tabs.attr_editor_newclass = False
        laser_tabs.css_align_content = "center"
        laser_tabs.css_align_items = "center"
        laser_tabs.css_height = "215px"
        laser_tabs.css_left = "5%"
        laser_tabs.css_margin = "0px"
        laser_tabs.css_position = "inherit"
        laser_tabs.css_top = "45%"
        laser_tabs.css_width = "345px"
        laser_tabs.variable_name = "stage_tabs"
        main.append(laser_tabs, "laser_tabs")
        self.laseranddetector = Container()
        self.laseranddetector.attr_editor_newclass = False
        self.laseranddetector.css_height = "150.0px"
        self.laseranddetector.css_left = "0px"
        self.laseranddetector.css_margin = "0px"
        self.laseranddetector.css_position = "relative"
        self.laseranddetector.css_top = "0px"
        self.laseranddetector.css_visibility = "visible"
        self.laseranddetector.css_width = "345.0px"
        self.laseranddetector.variable_name = "laseranddetector"
        self.laser_controlcontainer = Container()
        self.laser_controlcontainer.attr_editor_newclass = False
        self.laser_controlcontainer.css_height = "75.0px"
        self.laser_controlcontainer.css_left = "0px"
        self.laser_controlcontainer.css_margin = "0px"
        self.laser_controlcontainer.css_position = "relative"
        self.laser_controlcontainer.css_top = "0px"
        self.laser_controlcontainer.css_visibility = "visible"
        self.laser_controlcontainer.css_background_color = "transparent"
        self.laser_controlcontainer.css_width = "345.0px"
        self.laser_controlcontainer.variable_name = "laser_controlcontainer"
        self.laser_control = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.laser_control.attributes["src"] = "https://" + ip_address + "/laser/"
        self.laser_control.attributes["width"] = "100%"
        self.laser_control.attributes["height"] = "100%"
        self.laser_control.style["border"] = "None"
        self.laser_controlcontainer.append(self.laser_control, "laser_tabs")
        self.laseranddetector.append(self.laser_controlcontainer, "laser_controlcontainer")
        self.detector_controlcontainer = Container()
        self.detector_controlcontainer.attr_editor_newclass = False
        self.detector_controlcontainer.css_height = "150.0px"
        self.detector_controlcontainer.css_left = "0px"
        self.detector_controlcontainer.css_margin = "0px"
        self.detector_controlcontainer.css_position = "relative"
        self.detector_controlcontainer.css_top = "0px"
        self.detector_controlcontainer.css_visibility = "visible"
        self.detector_controlcontainer.css_background_color = "transparent"
        self.detector_controlcontainer.css_width = "345.0px"
        self.detector_controlcontainer.variable_name = "detector_controlcontainer"
        self.laser_detector = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.laser_detector.attributes["src"] = "https://" + ip_address + "/detector/"
        self.laser_detector.attributes["width"] = "100%"
        self.laser_detector.attributes["height"] = "100%"
        self.laser_detector.style["border"] = "None"
        self.detector_controlcontainer.append(self.laser_detector, "detector_tabs")
        self.laseranddetector.append(self.detector_controlcontainer, "detector_controlcontainer")
        self.alignment = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.alignment.attributes["src"] = "https://" + ip_address + "/alignment/"
        self.alignment.attributes["width"] = "100%"
        self.alignment.attributes["height"] = "100%"
        self.alignment.style["border"] = "None"
        laser_tabs.add_tab(self.laseranddetector, "Laser")
        laser_tabs.add_tab(self.alignment, "Alignment")
        display_tabs = TabBox()
        display_tabs.attr_editor_newclass = False
        display_tabs.css_align_content = "center"
        display_tabs.css_align_items = "center"
        display_tabs.css_height = "500px"
        display_tabs.css_left = "35%"
        display_tabs.css_margin = "0px"
        display_tabs.css_position = "inherit"
        display_tabs.css_top = "5%"
        display_tabs.css_width = "450px"
        display_tabs.variable_name = "display_tabs"
        main.append(display_tabs, "display_tabs")
        self.camera = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.camera.attributes["src"] = "https://" + ip_address + "/camera/"
        self.camera.attributes["width"] = "100%"
        self.camera.attributes["height"] = "100%"
        self.camera.style["border"] = "None"
        self.terminal = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.terminal.attributes["src"] = "https://" + ip_address + "/terminal/"
        self.terminal.attributes["width"] = "100%"
        self.terminal.attributes["height"] = "100%"
        self.terminal.style["border"] = "None"
        self.plots = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.plots.attributes["src"] = "https://" + ip_address + "/plots/"
        self.plots.attributes["width"] = "100%"
        self.plots.attributes["height"] = "100%"
        self.plots.style["border"] = "None"
        display_tabs.add_tab(self.camera, "Camera")
        display_tabs.add_tab(self.terminal, "Terminal")
        display_tabs.add_tab(self.plots, "Plots")
        measurement_tabs = TabBox()
        measurement_tabs.attr_editor_newclass = False
        measurement_tabs.css_align_content = "center"
        measurement_tabs.css_align_items = "center"
        measurement_tabs.css_height = "500px"
        measurement_tabs.css_left = "70%"
        measurement_tabs.css_margin = "0px"
        measurement_tabs.css_position = "inherit"
        measurement_tabs.css_top = "5%"
        measurement_tabs.css_width = "350px"
        measurement_tabs.variable_name = "stage_tabs"
        main.append(measurement_tabs, "measurement_tabs")
        self.fileimport = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.fileimport.attributes["src"] = "https://" + ip_address + "/fileimport/"
        self.fileimport.attributes["width"] = "100%"
        self.fileimport.attributes["height"] = "100%"
        self.fileimport.style["border"] = "None"
        self.selection = Widget(_type="iframe", width="100%", height="435px", margin="0px")
        self.selection.attributes["src"] = "https://" + ip_address + "/selection/"
        self.selection.attributes["width"] = "100%"
        self.selection.attributes["height"] = "100%"
        self.selection.style["border"] = "None"
        self.postscripts = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.postscripts.attributes["src"] = "https://" + ip_address + "/scripts/"
        self.postscripts.attributes["width"] = "100%"
        self.postscripts.attributes["height"] = "100%"
        self.postscripts.style["border"] = "None"
        self.measure = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        self.measure.attributes["src"] = "https://" + ip_address + "/measure/"
        self.measure.attributes["width"] = "100%"
        self.measure.attributes["height"] = "100%"
        self.measure.style["border"] = "None"
        measurement_tabs.add_tab(self.fileimport, "File import")
        measurement_tabs.add_tab(self.selection, "Selection")
        measurement_tabs.add_tab(self.postscripts, "Scripts")
        measurement_tabs.add_tab(self.measure, "Run")
        self.main = main
        return self.main


configuration = {
 'config_project_name': '"NIR Measurment System"', 'config_address': '"0.0.0.0"', 
 'config_port': 8080, 'config_multiple_instance': False, 'config_enable_file_cache': False, 
 'config_start_browser': False, 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(NIR_Measurment_System, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
