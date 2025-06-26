# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/File Import/run_gui.py
# Compiled at: 2023-07-12 01:04:23
# Size of source mod 2**32: 33030 bytes
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


import glob, pickle, time, datetime, numpy as np, math
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from multiprocessing import Process
sys.path.insert(1, os.path.join(main_path, "MMC 100"))
import stage, coordinates, shutil
stage_init = stage.stage()
while int(stage_init.dict["stage_inuse"]) == 1:
    stage_init.reload_parameters()

stage_init.update_parameter("stage_inuse", "1")
stage_init.open_port()
stage_init.update_parameter("stage_inuse", "0")
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR laser"))
import laser as laserNIR, laser_functions
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR Detector"))
import NIR_detector
detector = NIR_detector.detector()
laser = laserNIR.laser()
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "Alignment NIR"))
import area_sweep

class files(App):

    def __init__(self, *args, **kwargs):
        global detector
        global laser
        global stage_init
        self.stage = stage_init
        self.laser = laser
        self.detector = detector
        self.area_sweep = area_sweep.alignment()
        self.timestamp = 0
        self.timestamp_devices = 0
        self.run_measurement = -1
        self.number_of_scans = 1
        self.device_specific_alignment = 0
        self.use_secondary_detector = 0
        if "editing_mode" not in kwargs.keys():
            (super(files, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        if self.run_measurement == 1:
            self.file_container.children["progress"].set_max(len(self.selected_devices))
            self.file_container.children["progress"].set_value(self.measuring_device)
            if self.measuring_device < len(self.selected_devices):
                start_time = time.time()
                try:
                    self.measure_device(self.selected_devices[self.measuring_device])
                    self.measuring_device = self.measuring_device + 1
                    end_time = (time.time() - start_time) / 60
                    time_remaining = round(end_time * (len(self.selected_devices) - self.measuring_device), 0)
                    finish_date_time = datetime.datetime.now() + datetime.timedelta(minutes=time_remaining)
                    finish_date_string = finish_date_time.strftime("%b %d %-I:%M %p")
                    if self.measuring_device < len(self.selected_devices):
                        device_str = str(self.selected_devices[self.measuring_device])
                    else:
                        device_str = "done"
                    self.file_container.children["time_remaining"].set_text("Time remaining: " + str(time_remaining) + " minutes\n" + "Finished: " + finish_date_string + "\nMeasuring device: " + device_str + "\n")
                except Exception as e:
                    try:
                        print("An error occured when trying to measure device " + str(self.measuring_device))
                        print(e)
                        time.sleep(30)
                    finally:
                        e = None
                        del e

            else:
                print("All measurments done")
                self.laser.open_port()
                self.laser.turn_laser_off()
                self.laser.close_port()
                self.file_container.children["time_remaining"].set_text("All measurments done")
                self.run_measurement = 0
                self.detector.update_parameter("measurement_inprogress", "0")
        elif self.run_measurement == -1:
            self.file_container.children["time_remaining"].set_text("Press to Start")
        else:
            try:
                filetime = os.path.getmtime("./database_ramdisk/transformed.json")
            except:
                filetime = -1

            if filetime > self.timestamp:
                if self.run_measurement < 1:
                    self.timestamp = os.path.getmtime("./database_ramdisk/transformed.json")
                    self.display_labels = 0
                    self.selected_devices = []
                    self.savepath = "measurements/"
                    self.displayed_wavelength = "all"
                    self.displayed_polarization = "all"
                    self.last_device = 0
                    self.gds = coordinates.coordinates(name="./database_ramdisk/transformed.json", read_file=False)
            try:
                filetime_measure = os.path.getmtime("devices_to_measure.pkl")
                if filetime == -1:
                    filetime_measure = -1
            except:
                filetime_measure = -1

            if filetime_measure > self.timestamp_devices and self.run_measurement < 1:
                self.file_container.children["device"].empty()
                self.timestamp_devices = os.path.getmtime("devices_to_measure.pkl")
                self.selected_devices_names = []
                self.current_device = -1
                self.selected_devices = self.load_obj("devices_to_measure")
                if self.selected_devices:
                    self.current_device = self.selected_devices[0]
                    for number in self.selected_devices:
                        self.selected_devices_names.append("dev" + str(number) + "_" + self.gds.finddevicename(number))

                    self.file_container.children["device"].append(self.selected_devices_names)

    def main(self):
        return files.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        file_container = Container()
        file_container.attr_editor_newclass = False
        file_container.css_height = "435px"
        file_container.css_left = "0px"
        file_container.css_margin = "0px"
        file_container.css_position = "absolute"
        file_container.css_top = "0px"
        file_container.css_width = "350px"
        file_container.variable_name = "file_container"
        device = DropDown()
        device.attr_editor_newclass = False
        device.css_height = "30px"
        device.css_left = "20px"
        device.css_margin = "0px"
        device.css_position = "absolute"
        device.css_top = "20.0px"
        device.css_width = "180px"
        device.variable_name = "device"
        file_container.append(device, "device")
        godevice = Button()
        godevice.attr_editor_newclass = False
        godevice.css_font_size = "100%"
        godevice.css_height = "30px"
        godevice.css_left = "235px"
        godevice.css_margin = "0px"
        godevice.css_position = "absolute"
        godevice.css_top = "20px"
        godevice.css_width = "100px"
        godevice.text = "Go To Device"
        godevice.variable_name = "godevice"
        file_container.append(godevice, "godevice")
        measure = Button()
        measure.attr_editor_newclass = False
        measure.css_font_size = "100%"
        measure.css_height = "30px"
        measure.css_left = "235px"
        measure.css_margin = "0px"
        measure.css_position = "absolute"
        measure.css_top = "70px"
        measure.css_width = "100px"
        measure.text = "Measure"
        measure.variable_name = "measure"
        file_container.append(measure, "measure")
        averages = SpinBox()
        averages.attr_editor_newclass = False
        averages.attr_max = "5"
        averages.attr_min = "1"
        averages.attr_step = "1"
        averages.attr_value = "1"
        averages.css_font_size = "100%"
        averages.css_height = "30px"
        averages.css_left = "285px"
        averages.css_margin = "0px"
        averages.css_position = "absolute"
        averages.css_top = "120px"
        averages.css_width = "50px"
        averages.variable_name = "averages"
        file_container.append(averages, "averages")
        label_averages = Label()
        label_averages.attr_editor_newclass = False
        label_averages.css_height = "20px"
        label_averages.css_left = "230.0px"
        label_averages.css_position = "absolute"
        label_averages.css_top = "130.0px"
        label_averages.css_width = "50px"
        label_averages.text = "Scans"
        label_averages.variable_name = "label_averages"
        file_container.append(label_averages, "label_averages")
        label_device_specific_alignment = Label()
        label_device_specific_alignment.attr_editor_newclass = False
        label_device_specific_alignment.css_height = "20px"
        label_device_specific_alignment.css_left = "230.0px"
        label_device_specific_alignment.css_position = "absolute"
        label_device_specific_alignment.css_top = "160.0px"
        label_device_specific_alignment.css_width = "80px"
        label_device_specific_alignment.text = "Use device specific alignment wavelength"
        label_device_specific_alignment.variable_name = "label_device_specific_alignment"
        file_container.append(label_device_specific_alignment, "label_device_specific_alignment")
        device_specific_alignment = CheckBox()
        device_specific_alignment.attr_editor_newclass = False
        device_specific_alignment.css_height = "20px"
        device_specific_alignment.css_left = "310px"
        device_specific_alignment.css_margin = "0px"
        device_specific_alignment.css_position = "absolute"
        device_specific_alignment.css_top = "170px"
        device_specific_alignment.css_width = "30px"
        device_specific_alignment.variable_name = "device_specific_alignment"
        file_container.append(device_specific_alignment, "device_specific_alignment")
        label_use_secondary_detector = Label()
        label_use_secondary_detector.attr_editor_newclass = False
        label_use_secondary_detector.css_height = "20px"
        label_use_secondary_detector.css_left = "230.0px"
        label_use_secondary_detector.css_position = "absolute"
        label_use_secondary_detector.css_top = "230.0px"
        label_use_secondary_detector.css_width = "80px"
        label_use_secondary_detector.text = "Use secondary detector"
        label_use_secondary_detector.variable_name = "label_use_secondary_detector"
        file_container.append(label_use_secondary_detector, "label_use_secondary_detector")
        use_secondary_detector = CheckBox()
        use_secondary_detector.attr_editor_newclass = False
        use_secondary_detector.css_height = "20px"
        use_secondary_detector.css_left = "310px"
        use_secondary_detector.css_margin = "0px"
        use_secondary_detector.css_position = "absolute"
        use_secondary_detector.css_top = "240px"
        use_secondary_detector.css_width = "30px"
        use_secondary_detector.variable_name = "use_secondary_detector"
        file_container.append(use_secondary_detector, "use_secondary_detector")
        progress = Progress()
        progress.attr_editor_newclass = False
        progress.css_font_size = "100%"
        progress.css_height = "30px"
        progress.css_left = "20px"
        progress.css_margin = "0px"
        progress.css_position = "absolute"
        progress.css_top = "70px"
        progress.css_width = "180px"
        progress.variable_name = "progress"
        file_container.append(progress, "progress")
        time_remaining = Label()
        time_remaining.attr_editor_newclass = False
        time_remaining.css_height = "20px"
        time_remaining.css_left = "20.0px"
        time_remaining.css_margin = "0px"
        time_remaining.css_position = "absolute"
        time_remaining.css_top = "100.0px"
        time_remaining.css_width = "180px"
        time_remaining.text = "Measuring Please Wait"
        time_remaining.variable_name = "time_remaining"
        file_container.append(time_remaining, "time_remaining")
        file_container.children["device"].onchange.do(self.device)
        file_container.children["godevice"].onclick.do(self.gotodevice)
        file_container.children["measure"].onclick.do(self.measure)
        file_container.children["averages"].onchange.do(self.onchange_averages)
        file_container.children["device_specific_alignment"].onchange.do(self.onchange_device_specific_alignment)
        file_container.children["use_secondary_detector"].onchange.do(self.onchange_use_secondary_detector)
        self.file_container = file_container
        return self.file_container

    def device(self, emitter, new_value):
        split_value = new_value.split("dev")[1]
        device_number = split_value.split("_")
        device_number = int(device_number[0])
        self.current_device = device_number
        print(self.current_device)

    def gotodevice(self, emitter):
        self.stage.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 0:
            if self.run_measurement < 1:
                print("go")
                stage_init.update_parameter("stage_inuse", "1")
                print(self.current_device)
                self.move_to_device(self.current_device)
                stage_init.update_parameter("stage_inuse", "0")

    def measure(self, emitter):
        self.file_container.children["time_remaining"].set_text("Starting")
        self.stage.reload_parameters()
        while int(self.stage.dict["stage_inuse"]) == 1:
            self.stage.reload_parameters()

        self.stage.update_parameter("stage_inuse", "1")
        self.laser.reload_parameters()
        while int(self.laser.dict["laser_inuse"]) == 1:
            self.laser.reload_parameters()

        self.laser.update_parameter("laser_inuse", "1")
        self.detector.reload_parameters()
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.update_parameter("measurement_inprogress", "1")
        self.laser.open_port()
        self.laser.turn_laser_on()
        self.laser.close_port()
        self.run_measurement = 1
        self.measuring_device = 0

    def onchange_averages(self, emitter, value):
        self.number_of_scans = int(round(float(value), 0))
        self.file_container.children["averages"].set_value(self.number_of_scans)

    def onchange_device_specific_alignment(self, emitter, value):
        if int(value) == 1:
            print("set to device specific alignment")
            self.device_specific_alignment = 1
        else:
            print("set to user specified alignment")
            self.device_specific_alignment = 0

    def onchange_use_secondary_detector(self, emitter, value):
        if int(value) == 1:
            print("Enabled secondary detector")
            self.use_secondary_detector = 1
        else:
            print("Disabled secondary detector")
            self.use_secondary_detector = 0

    def measure_device(self, device):
        self.laser.open_port()
        self.detector.open_port()
        print(self.selected_devices)
        print("move to device " + str(device))
        self.move_to_device(device)
        if self.device_specific_alignment == 1:
            print("Use device specific wavelength")
            alignment_wavelength = self.get_device_alignment_wavelength(device)
        else:
            print("Use user specified wavelength")
            alignment_wavelength = float(self.laser.dict["laser_current_wavelength"])
        print("set laser to " + str(alignment_wavelength))
        self.laser.set_laser_current_wavelength(alignment_wavelength)
        print("align")
        self.stage.update_parameter("stage_inuse", "0")
        self.laser.update_parameter("laser_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        if self.use_secondary_detector == 0:
            self.area_sweep.align_to_device_trigger()
        else:
            starting_position = self.stage.read_position()
            self.area_sweep.reload_parameters()
            primary_detector = int(self.area_sweep.dict["detector_chn_align"])
            print("Primary detector is detector " + str(primary_detector))
            if primary_detector == 1:
                secondary_detector = 2
                self.area_sweep.update_parameter("detector_chn_align", str(secondary_detector))
            else:
                secondary_detector = 1
                self.area_sweep.update_parameter("detector_chn_align", str(secondary_detector))
            print("Secondary detector is detector " + str(secondary_detector))
            print("Align using secondary detector")
            self.area_sweep.align_to_device_trigger()
            power_on_secondary_detector = self.detector.detector_read_power(secondary_detector)
            self.area_sweep.update_parameter("detector_chn_align", str(primary_detector))
            self.return_to_starting_position(starting_position)
            print("Align using primary detector")
            self.area_sweep.align_to_device_trigger()
            power_on_primary_detector = self.detector.detector_read_power(primary_detector)
            if power_on_secondary_detector > power_on_primary_detector:
                print("Secondary detector has higher power")
                print("Realign using secondary detector")
                self.return_to_starting_position(starting_position)
                self.area_sweep.update_parameter("detector_chn_align", str(secondary_detector))
                self.area_sweep.align_to_device_trigger()
                self.area_sweep.update_parameter("detector_chn_align", str(primary_detector))
            else:
                self.stage.update_parameter("stage_inuse", "1")
                self.laser.update_parameter("laser_inuse", "1")
                self.detector.update_parameter("detector_inuse", "1")
                script_return = 0
                if os.path.isfile("./res/postalignment.py") == True:
                    try:
                        sys.path.append("./res")
                        import postalignment, importlib
                        importlib.reload(postalignment)
                        script_return = postalignment.script(self.savepath + "dev" + str(device) + "_" + str(self.gds.finddevicename(device)))
                    except Exception as e:
                        try:
                            print("User post alignment script error")
                            print(e)
                            script_return = -1
                            self.measuring_device = len(self.selected_devices)
                        finally:
                            e = None
                            del e

                else:
                    print("no post alignment script")
                laser_error_count = 0
                if self.number_of_scans != 1:
                    scan_label = "_scan_1"
                else:
                    scan_label = ""
            scan_count = 1
            starting_power_range = float(self.detector.dict["detector_power_range"].split("dbm")[0])
            current_power_range = starting_power_range
            print(script_return)
            if script_return != -1:
                print("sweep")
                while True:
                    try:
                        self.laser.close_port()
                        self.detector.close_port()
                        if str(self.laser.dict["laser_sweep_direction"]) == "reverse":
                            laser_error_code = laser_functions.spectrum_sweep_reverse(self.savepath + "dev" + str(device) + scan_label + "_" + str(self.gds.finddevicename(device)))
                        else:
                            laser_error_code = laser_functions.spectrum_sweep(self.savepath + "dev" + str(device) + scan_label + "_" + str(self.gds.finddevicename(device)))
                        if laser_error_code != 0:
                            self.laser.open_port()
                            self.detector.open_port()
                            print("laser data errors!!")
                            laser_error_count = laser_error_count + 1
                            if laser_error_count >= 3:
                                break
                            if laser_error_code == 1:
                                print("power out of range")
                                current_power_range = current_power_range + 10
                                print("Changing power range to " + str(current_power_range) + "dbm")
                                self.detector.update_parameter("detector_power_range", str(current_power_range) + "dbm")
                            continue
                        if scan_count < self.number_of_scans:
                            scan_count += 1
                            scan_label = "_scan_" + str(scan_count)
                            continue
                        if self.number_of_scans > 1:
                            self.calculate_average_and_replot(device, self.number_of_scans)
                        self.laser.open_port()
                        self.detector.open_port()
                        break
                    except Exception as e:
                        try:
                            print("laser sweep error")
                            print(e)
                            print("resetting")
                            time.sleep(5)
                            self.laser.open_port()
                            self.detector.open_port()
                            self.laser.turn_laser_on()
                            self.laser.set_laser_current_wavelength(float(self.laser.dict["laser_current_wavelength"]))
                            laser_error_count = laser_error_count + 1
                            if laser_error_count >= 3:
                                break
                            print("resweep")
                        finally:
                            e = None
                            del e

            else:
                print("User script returned -1 not running laser sweep")
            self.laser.close_port()
            self.detector.close_port()
            self.detector.update_parameter("detector_power_range", str(starting_power_range) + "dbm")
            self.stage.update_parameter("stage_inuse", "0")
            self.laser.update_parameter("laser_inuse", "0")
            self.detector.update_parameter("detector_inuse", "0")

    def get_device_alignment_wavelength(self, device_number):
        wavelength = float(self.gds.device_db.get(self.gds.device.number == device_number)["wavelength"])
        if wavelength > float(self.laser.dict["laser_max_wavelength"]):
            print("Device alignment wavelength exceeds laser max!!")
            print("Using laser max!!")
            wavelength = float(self.laser.dict["laser_max_wavelength"])
        else:
            if wavelength < float(self.laser.dict["laser_min_wavelength"]):
                print("Device alignment wavelength less then laser min!!")
                print("Using laser min!!")
                wavelength = float(self.laser.dict["laser_min_wavelength"])
        return round(wavelength, 2)

    def move_to_device(self, device_number):
        print(np.array(self.gds.device_db.get(self.gds.device.number == device_number)["coordinate"]))
        print(np.array(self.stage.read_position()))
        try:
            self.stage.reload_parameters()
            current = float(self.stage.dict["z_position"])
            original_z = current
            print(current)
            if float(250.0) - current < 0:
                print("Error safe z movement is negative!!")
                print("something is wrong!!")
                print("Check z zero")
                return
            print("move up " + str(float(250.0) - current))
            self.stage.move_z_axis(float(250.0) - current)
            current = float(250.0) - current
        except:
            print("safe z movement too small!!")
            print("something is wrong!!")
            print("don't move anymore")
            return
        else:
            status = self.stage.status(3)
            while status == "0":
                status = self.stage.status(3)

            self.stage.update_parameter("z_position", float(current))
            time.sleep(0.25)
            print(self.stage.read_position())
            distance = np.array(self.gds.device_db.get(self.gds.device.number == device_number)["coordinate"]) - np.array(self.stage.read_position())
            try:
                self.stage.reload_parameters()
                current = float(self.stage.dict["x_position"])
                self.stage.move_x_axis(distance[0])
                current = current + float(distance[0])
            except:
                print("x movement too small")

            status = self.stage.status(1)
            while status == "0":
                status = self.stage.status(1)

            self.stage.update_parameter("x_position", float(current))
            try:
                self.stage.reload_parameters()
                current = float(self.stage.dict["y_position"])
                self.stage.move_y_axis(distance[1])
                current = current + float(distance[1])
            except:
                print("y movement too small")

            status = self.stage.status(2)
            while status == "0":
                status = self.stage.status(2)

            self.stage.update_parameter("y_position", float(current))
            time.sleep(0.25)
            try:
                self.stage.reload_parameters()
                current = float(self.stage.dict["z_position"])
                print("z distance to move " + str(distance[2]))
                self.stage.move_z_axis(distance[2])
                current = current + float(distance[2])
            except:
                print("safe z movement too small")

            status = self.stage.status(3)
            while status == "0":
                status = self.stage.status(3)

            print(self.stage.read_position())
            self.stage.update_parameter("z_position", float(current + original_z))

    def return_to_starting_position(self, starting_position):
        distance = np.array(starting_position) - np.array(self.stage.read_position())
        try:
            self.stage.reload_parameters()
            current = float(self.stage.dict["x_position"])
            self.stage.move_x_axis(distance[0])
            current = current + float(distance[0])
        except:
            print("x movement too small")

        status = self.stage.status(1)
        while status == "0":
            status = self.stage.status(1)

        self.stage.update_parameter("x_position", float(current))
        try:
            self.stage.reload_parameters()
            current = float(self.stage.dict["y_position"])
            self.stage.move_y_axis(distance[1])
            current = current + float(distance[1])
        except:
            print("y movement too small")

        status = self.stage.status(2)
        while status == "0":
            status = self.stage.status(2)

        self.stage.update_parameter("y_position", float(current))

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

    def calculate_average_and_replot(self, device_number, number_of_scans):
        scans = []
        while not glob.glob(self.savepath + "dev" + str(device_number) + "_scan_" + str(number_of_scans) + "*.csv"):
            print("waiting for final scan")
            time.sleep(1)

        while not glob.glob(self.savepath + "dev" + str(device_number) + "_scan_" + str(number_of_scans) + "*.html"):
            print("waiting for final scan")
            time.sleep(1)

        while not glob.glob(self.savepath + "dev" + str(device_number) + "_scan_" + str(number_of_scans) + "*.pdf"):
            print("waiting for final scan")
            time.sleep(1)

        for count in range(1, number_of_scans + 1):
            potential_scans = glob.glob(self.savepath + "dev" + str(device_number) + "_scan_" + str(count) + "*")
            for file in potential_scans:
                if ".csv" in file:
                    scans.append(file)
                else:
                    if ".pdf" in file:
                        os.remove(file)

        scan_data = []
        scans.sort(key=(os.path.getctime), reverse=True)
        grabage_scans = []
        if len(scans) > number_of_scans:
            grabage_scans = scans[number_of_scans[:None]]
            scans = scans[None[:number_of_scans]]
        for file in scans:
            if "scan_1_" in file:
                filename = file.split("scan_1_")
                filename = filename[0] + filename[1]
                filename = filename.split(".csv")
                filename = str(filename[0])
                filename = filename[0[:-20]]
            f = open(file, "r")
            temp = []
            line = f.readline()
            split = line.split(",")
            elements = []
            for i in split:
                elements.append(float(i))

            temp.append(elements)
            while line:
                split = line.split(",")
                elements = []
                for i in split:
                    elements.append(float(i))

                temp.append(elements)
                line = f.readline()

            scan_data.append(temp)
            f.close()
            os.remove(file)

        for file in grabage_scans:
            os.remove(file)

        average = scan_data[0]
        for file_num in range(1, len(scan_data)):
            for line_num in range(0, len(average)):
                sample = scan_data[file_num][line_num]
                for column in range(0, len(sample)):
                    if math.isnan(average[line_num][column]) == True:
                        average[line_num][column] = sample[column]

        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        f = open(filename + "_" + fileTime + ".csv", "w")
        for line in average:
            for i in range(0, len(line) - 1):
                f.write(str(line[i]) + ",")

            f.write(str(line[i + 1]))
            f.write("\n")

        f.close()
        plot_wavelengths = []
        plot_p1 = []
        plot_p2 = []
        for line in average:
            plot_wavelengths.append(line[0] * 1000000000.0)
            plot_p1.append(line[1])
            plot_p2.append(line[2])

        p = Process(target=(laser_functions.generate_plots), args=(plot_wavelengths, [plot_p1, plot_p2], filename, fileTime))
        p.start()


configuration = {
 'config_project_name': '"files"', 'config_address': '"0.0.0.0"', 'config_port': 10084, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(files, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
