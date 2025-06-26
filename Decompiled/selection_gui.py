# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/File Import/selection_gui.py
# Compiled at: 2021-01-10 18:19:26
# Size of source mod 2**32: 16468 bytes
from remi.gui import *
from remi import start, App
import coordinates
from itertools import chain
import os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import pickle

class selection_gui(App):

    def __init__(self, *args, **kwargs):
        self.length_of_container = 0
        self.display_labels = 0
        self.last_device = 0
        self.timestamp = 0
        print("initialize selection gui")
        if "editing_mode" not in kwargs.keys():
            (super(selection_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            filetime = os.path.getmtime("./database_ramdisk/transformed.json")
        except:
            filetime = -1
            self.display_labels = -1

        if filetime > self.timestamp:
            self.timestamp = os.path.getmtime("./database_ramdisk/transformed.json")
            self.display_labels = 0
            self.selected_devices = []
            self.displayed_wavelength = "all"
            self.displayed_polarization = "all"
            self.last_device = 0
            self.last_device_clear = 300000
            self.gds = coordinates.coordinates(name="./database_ramdisk/transformed.json", read_file=False)
            self.displayed_devices = self.gds.listselecteddevices(self.displayed_wavelength, self.displayed_polarization)
            self.selection_container.children["wavelength_dropdown"].empty()
            self.selection_container.children["polarization_dropdown"].empty()
            wavelength_list = self.gds.listdeviceparam("wavelength")
            wavelength_list = list(set(wavelength_list))
            self.selection_container.children["wavelength_dropdown"].append("all")
            self.selection_container.children["wavelength_dropdown"].append(wavelength_list)
            polarization_list = self.gds.listdeviceparam("polarization")
            polarization_list = list(set(polarization_list))
            self.selection_container.children["polarization_dropdown"].append("all")
            self.selection_container.children["polarization_dropdown"].append(polarization_list)
            self.save_obj(self.selected_devices, "devices_to_measure")
        if self.display_labels == 0:
            self.remove_device_names()
            self.displayed_devices = self.gds.listselecteddevices(self.displayed_wavelength, self.displayed_polarization)
            if self.last_device_clear == 300000:
                self.last_device_clear = len(self.displayed_devices)
            print("Loading " + str(len(self.displayed_devices)) + " devices")
            print("This may take awhile")
            print("Precentage complete")
            self.display_device_names(self.displayed_devices)
            for device in self.selected_devices:
                try:
                    self.selection_container.children[str(device)].set_value(1)
                except:
                    pass

            self.display_labels = 1
            print("done")

    def main(self):
        return selection_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        selection_container = Container()
        selection_container.attr_editor_newclass = False
        selection_container.css_height = "435px"
        selection_container.css_left = "0px"
        selection_container.css_margin = "0px"
        selection_container.css_position = "absolute"
        selection_container.css_top = "0px"
        selection_container.css_width = "350px"
        selection_container.variable_name = "selection_container"
        wavelength_dropdown = DropDown()
        wavelength_dropdown.attr_editor_newclass = False
        wavelength_dropdown.css_height = "30px"
        wavelength_dropdown.css_left = "100px"
        wavelength_dropdown.css_margin = "0px"
        wavelength_dropdown.css_position = "absolute"
        wavelength_dropdown.css_top = "30.0px"
        wavelength_dropdown.css_width = "100px"
        wavelength_dropdown.variable_name = "wavelength_dropdown"
        selection_container.append(wavelength_dropdown, "wavelength_dropdown")
        polarization_dropdown = DropDown()
        polarization_dropdown.attr_editor_newclass = False
        polarization_dropdown.css_height = "30px"
        polarization_dropdown.css_left = "25px"
        polarization_dropdown.css_margin = "0px"
        polarization_dropdown.css_position = "absolute"
        polarization_dropdown.css_top = "30px"
        polarization_dropdown.css_width = "50px"
        polarization_dropdown.variable_name = "polarization_dropdown"
        selection_container.append(polarization_dropdown, "polarization_dropdown")
        label_polarization = Label()
        label_polarization.attr_editor_newclass = False
        label_polarization.css_font_size = "100%"
        label_polarization.css_height = "15.0px"
        label_polarization.css_left = "15px"
        label_polarization.css_margin = "0px"
        label_polarization.css_position = "absolute"
        label_polarization.css_top = "10px"
        label_polarization.css_width = "90.0px"
        label_polarization.text = "Polarization"
        label_polarization.variable_name = "label_polarization"
        selection_container.append(label_polarization, "label_polarization")
        label_wavelength = Label()
        label_wavelength.attr_editor_newclass = False
        label_wavelength.css_height = "15.0px"
        label_wavelength.css_left = "115px"
        label_wavelength.css_margin = "0px"
        label_wavelength.css_position = "absolute"
        label_wavelength.css_top = "10px"
        label_wavelength.css_width = "75.0px"
        label_wavelength.text = "Wavelength"
        label_wavelength.variable_name = "label_wavelength"
        selection_container.append(label_wavelength, "label_wavelength")
        button_select_all = Button()
        button_select_all.attr_editor_newclass = False
        button_select_all.css_height = "31px"
        button_select_all.css_left = "210.0px"
        button_select_all.css_margin = "0px"
        button_select_all.css_position = "absolute"
        button_select_all.css_top = "30.0px"
        button_select_all.css_width = "75.0px"
        button_select_all.text = "Select All"
        button_select_all.variable_name = "button_select_all"
        selection_container.append(button_select_all, "button_select_all")
        button_clear_all = Button()
        button_clear_all.attr_editor_newclass = False
        button_clear_all.css_height = "31px"
        button_clear_all.css_left = "300.0px"
        button_clear_all.css_margin = "0px"
        button_clear_all.css_position = "absolute"
        button_clear_all.css_top = "30.0px"
        button_clear_all.css_width = "45.0px"
        button_clear_all.text = "Clear"
        button_clear_all.variable_name = "button_clear_all"
        selection_container.append(button_clear_all, "button_clear_all")
        selection_container.children["wavelength_dropdown"].onchange.do(self.onchange_wavelength_dropdown)
        selection_container.children["polarization_dropdown"].onchange.do(self.onchange_polarization_dropdown)
        selection_container.children["button_select_all"].onclick.do(self.onclick_button_select_all)
        selection_container.children["button_clear_all"].onclick.do(self.onclick_button_clear_all)
        self.original_container = selection_container
        self.selection_container = selection_container
        return self.selection_container

    def save_obj(self, obj, name):
        with open(name + ".pkl", "wb+") as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
            f.close()

    def load_obj(self, name):
        while True:
            try:
                with open(name + ".pkl", "rb") as f:
                    data = pickle.load(f)
                    break
            except EOFError:
                print("EOFError!!!!!!!")

        f.close()
        return data

    def onchange_wavelength_dropdown(self, emitter, new_value):
        self.displayed_wavelength = new_value
        self.display_labels = 0

    def onchange_polarization_dropdown(self, emitter, new_value):
        self.displayed_polarization = new_value
        self.display_labels = 0

    def onclick_button_select_all(self, emitter):
        print("select")
        print(self.last_device)
        device = 1
        while device <= self.last_device:
            try:
                self.selection_container.children[str(device)].set_value(1)
                try:
                    self.selected_devices.index(device)
                except:
                    self.selected_devices.append(device)

                device = device + 1
            except:
                device = device + 1

        self.selected_devices.sort()
        self.save_obj(self.selected_devices, "devices_to_measure")

    def onclick_button_clear_all(self, emitter):
        print(self.last_device)
        device = 1
        while device <= self.last_device:
            try:
                self.selection_container.children[str(device)].set_value(0)
                try:
                    self.selected_devices.pop(self.selected_devices.index(device))
                except:
                    pass

                device = device + 1
            except:
                device = device + 1

        self.selected_devices.sort()
        self.save_obj(self.selected_devices, "devices_to_measure")

    def onchange_checkbox(self, emitter, value):
        print(value)
        print(emitter.variable_name)
        if value == True:
            self.selected_devices.append(int(emitter.variable_name))
        else:
            self.selected_devices.pop(self.selected_devices.index(int(emitter.variable_name)))
        self.selected_devices.sort()
        self.save_obj(self.selected_devices, "devices_to_measure")

    def display_device_names(self, listofnames):
        count = 0
        max_length = 0
        bracket = 0
        max_devicenumber = 0
        for name in listofnames:
            name = str(name)
            if max_length < len(name):
                max_length = len(name)

        already_listed = []
        for name in listofnames:
            name = str(name)
            left = "300px"
            textboxwidth = "270px"
            if max_length > 40:
                left = str(8 * (max_length - 40) + 300) + "px"
                self.selection_container.css_width = str(8 * (max_length - 40) + 350) + "px"
                textboxwidth = str(8 * (max_length - 40) + 270) + "px"
            label = Label()
            label.attr_editor_newclass = False
            label.css_font_size = "100%"
            label.css_height = "0.0px"
            label.css_left = "25px"
            label.css_margin = "0px"
            label.css_position = "absolute"
            label.css_text_align = "right"
            label.css_top = str(80 + 20 * count) + "px"
            label.css_width = textboxwidth
            label.text = name
            devicenumber_list = self.gds.finddevicenumber(name)
            if len(devicenumber_list) == 1:
                devicenumber = devicenumber_list[0]
                if max_devicenumber < devicenumber:
                    max_devicenumber = devicenumber
                else:
                    listindex = 0
                    while True:
                        try:
                            already_listed.index(devicenumber_list[listindex])
                            devicenumber = devicenumber_list[listindex]
                            if max_devicenumber < devicenumber:
                                max_devicenumber = devicenumber
                        except:
                            already_listed.append(devicenumber_list[listindex])
                            devicenumber = devicenumber_list[listindex]
                            if max_devicenumber < devicenumber:
                                max_devicenumber = devicenumber
                            break

                        listindex = listindex + 1

                    label.variable_name = "label" + str(devicenumber)
                    self.selection_container.append(label, "label" + str(devicenumber))
                    checkbox = CheckBox()
                    checkbox.attr_editor_newclass = False
                    checkbox.css_height = "30px"
                    checkbox.css_left = left
                    checkbox.css_margin = "0px"
                    checkbox.css_position = "absolute"
                    checkbox.css_top = str(74 + 20 * count) + "px"
                    checkbox.css_width = "30px"
                    checkbox.variable_name = str(devicenumber)
                    self.selection_container.append(checkbox, str(devicenumber))
                    self.selection_container.children[str(devicenumber)].onchange.do(self.onchange_checkbox)
                count = count + 1
                loaded_count = count
                if loaded_count / len(self.displayed_devices) * 100 > bracket:
                    bracket += 10
                    print(str(round(loaded_count / len(listofnames) * 100, 2)) + "%")

        if devicenumber > self.last_device:
            self.last_device = max_devicenumber
        if 80 + 20 * count + 20 < 435:
            return
        self.selection_container.css_height = str(80 + 20 * count + 20) + "px"

    def remove_device_names(self):
        self.selection_container.css_height = "435px"
        self.selection_container.css_left = "0px"
        self.selection_container.css_margin = "0px"
        self.selection_container.css_position = "absolute"
        self.selection_container.css_top = "0px"
        self.selection_container.css_width = "350px"
        print("clear device names")
        try:
            if self.last_device_clear > 1:
                pass
            else:
                self.last_device_clear = self.last_device
        except:
            self.last_device_clear = self.last_device

        print("last device to clear: " + str(self.last_device_clear))
        devicenumber = 1
        while devicenumber <= self.last_device_clear:
            try:
                self.selection_container.remove_child(self.selection_container.get_child(str(devicenumber)))
                devicenumber = devicenumber + 1
            except Exception as e:
                try:
                    devicenumber = devicenumber + 1
                finally:
                    e = None
                    del e

        devicenumber = 1
        while devicenumber <= self.last_device_clear:
            try:
                self.selection_container.remove_child(self.selection_container.get_child("label" + str(devicenumber)))
                devicenumber = devicenumber + 1
            except Exception as e:
                try:
                    devicenumber = devicenumber + 1
                finally:
                    e = None
                    del e

        self.last_device_clear = self.last_device
        self.last_device = 0
        print("done clearing device names")


configuration = {
 'config_project_name': '"selection_gui"', 'config_address': '"0.0.0.0"', 'config_port': 10082, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(selection_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
