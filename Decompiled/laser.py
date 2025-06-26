# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Downloads/laser.py
# Compiled at: 2022-09-12 22:42:07
# Size of source mod 2**32: 34013 bytes
"""
Laser Control Module

20-06-18 Created this module

CAUTION: Make sure to pass in parameters to ag8163a methods as strings
"""
import agilent_8163a as ag8163a, time, numpy, telnetlib, struct, pickle
MAX_WINDOW_WIDTH = 65000
MAX_WINDOW_HEIGHT = 5000
from telnetlib import DO, DONT, IAC, WILL, WONT, NAWS, SB, SE

def set_max_window_size(tsocket, command, option):
    """
    Set Window size to resolve line width issue
    Set Windows size command: IAC SB NAWS <16-bit value> <16-bit value> IAC SE
    --> inform the Telnet server of the window width and height.
    Refer to https://www.ietf.org/rfc/rfc1073.txt
    :param tsocket: telnet socket object
    :param command: telnet Command
    :param option: telnet option
    :return: None
    """
    if option == NAWS:
        width = struct.pack("H", MAX_WINDOW_WIDTH)
        height = struct.pack("H", MAX_WINDOW_HEIGHT)
        tsocket.send(IAC + WILL + NAWS)
        tsocket.send(IAC + SB + NAWS + width + height + IAC + SE)
    else:
        if command in (DO, DONT):
            tsocket.send(IAC + WONT + option)
        else:
            if command in (WILL, WONT):
                tsocket.send(IAC + DONT + option)


class laser:
    __doc__ = "\n    Inherited functions:\n    set_serial()\n    get_serial()\n    set_address()\n    get_address()\n    serial_write()\n    read()\n    query()\n    reset*(\n    checksqr()\n    read_stb()\n    "

    def __init__(self):
        laser_parameters = [
         'laser_model', 
         'laser_min_power', 
         'laser_max_power', 
         'laser_current_power', 
         'laser_current_wavelength', 
         'laser_min_wavelength', 
         'laser_max_wavelength', 
         'laser_ipAddress', 
         'laser_ipPort', 
         'laser_board_index', 
         'laser_password', 
         'laser_slot', 
         'laser_power_state', 
         'laser_COM_port', 
         'laser_continuous_sweep_speed', 
         'laser_sweep_step_size', 
         'laser_sweep_start_wavelength', 
         'laser_sweep_stop_wavelength', 
         'laser_max_points', 
         'laser_min_points', 
         'laser_max_sweep_speed', 
         'laser_min_averaging', 
         'laser_min_step', 
         'laser_inuse', 
         'laser_sweep_direction', 
         'laser_init']
        default_values = [
         "0"] * len(laser_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "NIR laser", "NIR_laser"))
        except:
            self.dict = dict(zip(laser_parameters, default_values))
            self.save_obj(self.dict, os.path.join(main_path, "NIR laser", "NIR_laser"))

    def update_parameter(self, key, val):
        """
        Updates the corresponding value of a key in the dictionary
        """
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        if key in self.dict:
            self.dict[key] = val
            self.save_obj(self.dict, os.path.join(main_path, "NIR laser", "NIR_laser"))
        else:
            print("%s does not exist" % key)

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
                pass

        f.close()
        return data

    def reload_parameters(self):
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        self.dict = self.load_obj(os.path.join(main_path, "NIR laser", "NIR_laser"))

    def read_error_and_clear_status(self):
        """
        read error and clear status
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.check_error() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        if '-420,"Query UNTERMINATED"' in string:
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            return
        print(string)
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def open_port(self, **kwargs):
        """
        Initializes a Serial object and sets serial.

        **kwargs gives the option to initialize parameters in the future
        """
        self.telnet_connection = telnetlib.Telnet(host=(self.dict["laser_ipAddress"]), port=(int(self.dict["laser_ipPort"])), timeout=5)
        self.telnet_connection.set_option_negotiation_callback(set_max_window_size)
        self.lock_laser("0")

    def close_port(self):
        self.telnet_connection.close()

    def laser_init(self):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write("*RST\n".encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.identity() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Current mainframe:")
        for element in string.split(","):
            print("{}".format(element))

        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        if self.laser_slot():
            pass
        else:
            return
            self.read_power_setting()
            self.set_laser_current_wavelength(self.dict["laser_current_wavelength"])
            self.set_laser_current_power(self.dict["laser_current_power"])
            self.read_wavelength_setting()
            self.set_regulated_path("LOWS")
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_current(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
            string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
            if "0" in string:
                print("Laser is OFF")
            else:
                if "1" in string:
                    print("Laser is ON")

    def set_regulated_path(self, path):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_regulated_path(self.dict["laser_slot"], path) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_regulated_path(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print(string)
        self.read_error_and_clear_status()

    def check_sweep_parameters(self, start=None, stop=None, resolution=None):
        self.reload_parameters()
        current_step = float(self.dict["laser_sweep_step_size"])
        current_start = float(self.dict["laser_sweep_start_wavelength"])
        current_stop = float(self.dict["laser_sweep_stop_wavelength"])
        min_wavelength = float(self.dict["laser_min_wavelength"])
        max_wavelength = float(self.dict["laser_max_wavelength"])
        max_points = int(self.dict["laser_max_points"])
        min_points = int(self.dict["laser_min_points"])
        max_speed = float(self.dict["laser_max_sweep_speed"].split("nm/s")[0])
        min_averaging = float(self.dict["laser_min_averaging"])
        min_step = float(self.dict["laser_min_step"])
        change = 0
        if start != None:
            if start < min_wavelength:
                start = min_wavelength
            change = 1
        else:
            start = current_start
        print(max_wavelength)
        if stop != None:
            if stop > max_wavelength:
                stop = max_wavelength
            change = 1
        else:
            stop = current_stop
        print(start)
        print(stop)
        if change == 1:
            print(1)
            print(start)
            print(stop)
            points = (stop - start) / current_step
            resolution = current_step
            if points > max_points:
                resolution = (stop - start) / max_points
            if points < min_points:
                resolution = (stop - start) / min_points
            if resolution < min_step:
                print("Resolution high error")
                resolution = current_step
                start = current_start
                stop = current_stop
            print(points)
            print((stop - start) / resolution)
        else:
            if resolution != None:
                if resolution < min_step:
                    resolution = min_step
                if (max_wavelength - min_wavelength) / resolution < min_points:
                    print("can't fix this")
                    resolution = current_step
            else:
                points = (current_stop - current_start) / resolution
                print(points)
                if points > max_points:
                    max_bandwidth = resolution * max_points
                    current_bandwidth = current_stop - current_start
                    bandwidth_adjust = (current_bandwidth - max_bandwidth) / 2
                    start = start + bandwidth_adjust
                    stop = stop - bandwidth_adjust
                    print("over max")
                elif points < min_points:
                    min_bandwidth = resolution * min_points
                    current_bandwidth = current_stop - current_start
                    bandwidth_adjust = (min_bandwidth - current_bandwidth) / 2
                    start = start - bandwidth_adjust
                    stop = stop + bandwidth_adjust
                    print("-----------")
                    print(min_bandwidth)
                    print(current_bandwidth)
                    print(bandwidth_adjust)
                    print("-----------")
                    while True:
                        if start < min_wavelength:
                            start = start + bandwidth_adjust
                            stop = stop + bandwidth_adjust
                            print("!!!")
                            print(1)
                            print(start)
                            print(stop)
                            print("!!!")
                            continue
                        if stop > max_wavelength:
                            start = start - bandwidth_adjust
                            stop = stop - bandwidth_adjust
                            print("!!!")
                            print(2)
                            print(start)
                            print(stop)
                            print("!!!")
                            continue
                        break

                else:
                    resolution = current_step
        print(start)
        print(stop)
        speed = resolution / min_averaging
        print("calculated speed " + str(speed))
        if speed > max_speed:
            speed = max_speed
        else:
            if speed < 5:
                speed = 0.5
            print("speed " + str(speed))
            start = round(start, 3)
            stop = round(stop, 3)
            resolution = round(resolution, 4)
            speed = round(speed, 3)
            return [
             start, stop, resolution, speed]

    def set_laser_sweep_state(self, channel, start_stop):
        """
        gives the option to stop, start, or continue a wavelength sweep

        start_stop:
        STAR
        STOP
        CONT
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_sweep_state(self.dict["laser_slot"], channel, start_stop) + "\n").encode(encoding="UTF-8"))

    def read_laser_incoming_trigger_response(self):
        """
        SWS should be the desired output
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_incoming_trigger_response(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Laser incoming trigger response has been set to {}".format(string))

    def read_laser_sweep_parameters(self):
        """
        read sweep parameters
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_sweep_parameters(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        return string

    def arm_laser_sweep(self):
        """
        arm laser sweep
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.arm_laser_sweep(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))

    def set_laser_incoming_trigger_response(self, additional):
        """
        SWS should be the desired additional
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_incoming_trigger_response(self.dict["laser_slot"], additional) + "\n").encode(encoding="UTF-8"))

    def read_laser_sweep_state(self, channel):
        """
        returns the states of a sweep
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_sweep_state(self.dict["laser_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        return string

    def set_laser_sweep_step_size(self, size):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_sweep_step_size(self.dict["laser_slot"], str(size) + "nm") + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_sweep_step_size(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        step_size = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Setting sweep_step_size to {}".format(step_size))
        self.read_error_and_clear_status()

    def set_sweep_start_and_stop_wavelength(self, start_wavelength, stop_wavelength):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sweep_boundary_wavelength(self.dict["laser_slot"], "STAR", "MIN") + "\n").encode(encoding="UTF-8"))
        min_start_wl = float(self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        print("Minimum start wavelength: {}".format(min_start_wl))
        print("Setting sweep start wavelength to {}".format(start_wavelength))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sweep_wavelength(self.dict["laser_slot"], "STAR", str(start_wavelength) + "nm") + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sweep_boundary_wavelength(self.dict["laser_slot"], "STOP", "MAX") + "\n").encode(encoding="UTF-8"))
        max_stop_wl = float(self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        print("Maximum stop wavelength: {}".format(max_stop_wl))
        print("Setting sweep stop wavelength to {}".format(stop_wavelength))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sweep_wavelength(self.dict["laser_slot"], "STOP", str(stop_wavelength) + "nm") + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()

    def set_sweep_start(self, start_wavelength):
        self.update_parameter("laser_sweep_start_wavelength", str(start_wavelength) + "nm")
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sweep_boundary_wavelength(self.dict["laser_slot"], "STAR", "MIN") + "\n").encode(encoding="UTF-8"))
        min_start_wl = float(self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        print("Minimum start wavelength: {}".format(min_start_wl))
        print("Setting sweep start wavelength to {}".format(start_wavelength))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sweep_wavelength(self.dict["laser_slot"], "STAR", str(start_wavelength) + "nm") + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()

    def set_sweep_stop(self, stop_wavelength):
        self.update_parameter("laser_sweep_stop_wavelength", str(stop_wavelength) + "nm")
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sweep_boundary_wavelength(self.dict["laser_slot"], "STOP", "MAX") + "\n").encode(encoding="UTF-8"))
        max_stop_wl = float(self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        print("Maximum stop wavelength: {}".format(max_stop_wl))
        print("Setting sweep stop wavelength to {}".format(stop_wavelength))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sweep_wavelength(self.dict["laser_slot"], "STOP", str(stop_wavelength) + "nm") + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()

    def set_continuous_sweep_speed(self, speed):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_continuous_sweep_speed(self.dict["laser_slot"], speed) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_continuous_sweep_speed(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Current continuous Sweep Speed: {}".format(string))
        self.read_error_and_clear_status()

    def set_laser_current_wavelength(self, wavelength):
        """
        Sets the absolution laser wavelength output.

        Specify the wavelength units when passing to method
        """
        self.update_parameter("laser_current_wavelength", wavelength)
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_current_wavelength(self.dict["laser_slot"], wavelength) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()

    def set_laser_output_trigger_timing(self, additional):
        """
        Specifies when an output trigger is generated and arms the module

        Additionals:
        DIS - Never
        AVG - when a averaging time period finishes
        MEA - when a averaging time period begins
        MOD - for every leading edge of a digitally-modulated signal
        STF - when a sweep cycle finishes
        SWS - when a sweep cycle starts
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_output_trigger_timing(self.dict["laser_slot"], additional) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_output_trigger_timing(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Laser output trigger timing has been set to {}".format(string))

    def set_laser_current_power(self, power):
        """
        Set the current laser power output

        Specify the units of power in string

        power: 0.0000 dbm
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_current_power(self.dict["laser_slot"], power) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.read_power_setting()

    def read_power_setting(self):
        """
        laser is hard coded to dbm.

        Reads the current, max, min power and save them to dictionary
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.laser_power_units(self.dict["laser_slot"], "0") + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.laser_power_units(self.dict["laser_slot"], "0") + "\n").encode(encoding="UTF-8"))
        current_pow = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "dbm"
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_power((self.dict["laser_slot"]), additional="MAX") + "\n").encode(encoding="UTF-8"))
        max_pow = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "dbm"
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_power((self.dict["laser_slot"]), additional="MIN") + "\n").encode(encoding="UTF-8"))
        min_pow = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "dbm"
        print("Current laser power: {}\nMaximum laser power: {}\nMinimum laser power: {}".format(current_pow, max_pow, min_pow))
        self.read_error_and_clear_status()

    def read_wavelength_setting(self):
        """
        Reads and saves the current wl, min wl, and max wl to the dictionary, then clears status
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_wavelength(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        current_wl = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "nm"
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_wavelength((self.dict["laser_slot"]), additional="MAX") + "\n").encode(encoding="UTF-8"))
        max_wl = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "nm"
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_wavelength((self.dict["laser_slot"]), additional="MIN") + "\n").encode(encoding="UTF-8"))
        min_wl = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8") + "nm"
        print("Current laser wavelength: {}\nMin laser wavelength: {}\nMax laser wavelength: {}".format(current_wl, min_wl, max_wl))
        self.read_error_and_clear_status()

    def laser_slot(self):
        """
        Checks wheter the laser is among the installed modules.

        If found, saves the slot of the detector.
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.options() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Current modules installed: {}".format(string))
        if self.dict["laser_model"] in string:
            pass
        else:
            print("Laser was not found")
            return False
            temp_dict = dict(enumerate(string.split(", ")))
            temp_dict = dict(zip(temp_dict.values(), temp_dict.keys()))
            self.update_parameter("laser_slot", str(temp_dict[self.dict["laser_model"]]))
            print("Laser is found was slot {}".format(self.dict["laser_slot"]))
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            return True

    def lock_laser(self, on_off):
        """
        Unlocks the laser given laser password
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.lock_laser(on_off, self.dict["laser_password"]) + "\n").encode(encoding="UTF-8"))

    def turn_laser_on(self):
        """
        Turns on a particular laser on!

        Returns true if successful
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.laser_current(self.dict["laser_slot"], "1") + "\n").encode(encoding="UTF-8"))
        print("Turning laser On")
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.check_error() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        if '-420,"Query UNTERMINATED"' in string:
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        else:
            print(string)
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.update_parameter("laser_power_state", str(1))
        if "No error" in string:
            return True
        return False

    def turn_laser_off(self):
        """
        Turns on a particular laser on!

        Returns true if successful
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.laser_current(self.dict["laser_slot"], "0") + "\n").encode(encoding="UTF-8"))
        print("Turning laser Off")
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.check_error() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        if '-420,"Query UNTERMINATED"' in string:
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            return
        print(string)
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.update_parameter("laser_power_state", str(0))
        if "No error" in string:
            return True
        return False

    def set_laser_power_state(self, on_off):
        """
        Switches the laser of the chosen source on or off

        0:OFF
        1:ON
        """
        self.update_parameter("laser_power_state", str(on_off))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_power_state(self.dict["laser_slot"], on_off) + "\n").encode(encoding="UTF-8"))

    def read_laser_power_state(self):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_power_state(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def set_laser_sweep_mode(self, additional):
        """
        Sets the sweep mode

        addtional:
        STEP - Stepped sweep mode
        MAN - Manual sweep mode
        CONT - continuous sweep mode
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_sweep_mode(self.dict["laser_slot"], additional) + "\n").encode(encoding="UTF-8"))

    def set_laser_sweep_cycle(self, cycles):
        """
        Sets the number of sweep cycles.

        cycles:
        Some Integer value - 
        MIN - mimnmum programmable value
        MAX - maximum programmable vlaue
        DEF - half thhe sum of the min and the mac value
        0 - cycles continuously
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_sweep_cycles(self.dict["laser_slot"], str(cycles)) + "\n").encode(encoding="UTF-8"))

    def set_laser_directionality(self, directionality):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_sweep_directionality(self.dict["laser_slot"], str(directionality)) + "\n").encode(encoding="UTF-8"))

    def set_laser_amplitude_modulation(self, channel, on_off):
        """
        Enables and disables amplitude modulation of the laser output

        on_off:
        0:OFF
        1:ON
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_amplitude_modulation(self.dict["laser_slot"], channel, on_off) + "\n").encode(encoding="UTF-8"))

    def set_laser_lambda_logging(self, on_off):
        """
        Switches lambda logging on or off. Lambda logging records the exact wavelength of a
        tunable laser module when a trigger is generated during a continuous sweep

        
        0: OFF
        1: ON
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_laser_lambda_logging(self.dict["laser_slot"], on_off) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def operation_complete(self):
        selread_trigger_statusf.telnet_connection.write((ag8163a.agilent_8163a_mainframe.operation_complete_query() + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def set_trigger_conf(self, mode):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.trigger_config(mode) + "\n").encode(encoding="UTF-8"))

    def send_trigger(self, slot):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.send_laser_trigger(slot) + "\n").encode(encoding="UTF-8"))

    def read_trigger_status(self, slot):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_trigger_status(slot) + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def read_trigger_number(self):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_trigger_number(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def read_wavelength_points_avail(self):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_wavelength_points_avail(self.dict["laser_slot"]) + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def read_laser_wavelength_log(self, num_samples):
        print("Querying logging data...")
        converted_binary_block = []
        count = 1
        samples_read = 0
        while True:
            samples_to_read = num_samples - samples_read
            if num_samples * 8 + 8 < 1514:
                blocksize = samples_to_read * 8 + 8
            else:
                blocksize = 1514
            binary_raw = []
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_laser_wavelength_data_block(self.dict["laser_slot"], str(samples_read), str(samples_to_read)) + "\n").encode(encoding="UTF-8"))
            telnetsocket = self.telnet_connection.get_socket()
            import re
            binary_block = []
            read = telnetsocket.recv(blocksize)
            binary_block.extend(read)
            if num_samples * 8 + 8 > 1514:
                while len(binary_block) < samples_to_read * 8 + 8:
                    read = []
                    try:
                        read = telnetsocket.recv(blocksize)
                        binary_block.extend(read)
                    except:
                        break

            break

        start_index = 0
        for i in range(int(chr(binary_block[start_index + 1])) + 2, len(binary_block), 8):
            try:
                buf = bytes([binary_block[i], binary_block[i + 1], binary_block[i + 2], binary_block[i + 3], binary_block[i + 4], binary_block[i + 5], binary_block[i + 6], binary_block[i + 7]])
                value = float(struct.unpack_from("<d", buf)[0])
                converted_binary_block.append(value)
            except:
                converted_binary_block.append(float("nan"))

        del converted_binary_block[-1]
        return converted_binary_block
