# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/NIR Detector/NIR_detector.py
# Compiled at: 2021-04-16 01:41:26
# Size of source mod 2**32: 39564 bytes
"""
Detector Control Module

19-06-18 Created this module

Remember to sync the object after each method is called!!
"""
import agilent_8163a as ag8163a, telnetlib, socket, time, numpy, struct, pickle
preferred_path = ""
MAX_WINDOW_WIDTH = 65535
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


class detector:
    __doc__ = "\n    Inherited functions:\n    set_serial()\n    get_serial()\n    set_address()\n    get_address()\n    serial_write()\n    read()\n    query()\n    reset*(\n    checksqr()\n    read_stb()\n    "

    def __init__(self):
        detector_parameters = [
         'detector_model', 
         'detector_inuse', 
         'detector_init', 
         'measurement_inprogress', 
         'detector_power_range', 
         'detector_averaging_time', 
         'detector_total_time', 
         'detector_decision_threshold', 
         'detector_USB_Address', 
         'detector_gpibAddress', 
         'detector_ipAddress', 
         'detector_ipPort', 
         'detector_slot', 
         'detector_sensor_min_wavelength', 
         'detector_sensor_max_wavelength', 
         'detector_sensor_current_wavelength']
        default_values = [
         "0"] * len(detector_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "NIR Detector", "NIR_detector"))
        except:
            self.dict = dict(zip(detector_parameters, default_values))
            self.save_obj(self.dict, os.path.join(main_path, "NIR Detector", "NIR_detector"))

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
            self.save_obj(self.dict, os.path.join(main_path, "NIR Detector", "NIR_detector"))
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
        self.dict = self.load_obj(os.path.join(main_path, "NIR Detector", "NIR_detector"))

    def read_error_and_clear_status(self):
        """
        read error and clear status
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.check_error() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8", "ignore")
        if '-420,"Query UNTERMINATED"' in string or '420,"Query UNTERMINATED"' in string:
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            return
        print(string)
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def open_port(self, **kwargs):
        """
        Initializes a Serial object and sets serial.

        **kwargs gives the option to initialize parameters in the future
        """
        self.telnet_connection = telnetlib.Telnet(host=(self.dict["detector_ipAddress"]), port=(int(self.dict["detector_ipPort"])), timeout=5)
        self.telnet_connection.set_option_negotiation_callback(set_max_window_size)

    def close_port(self):
        self.telnet_connection.close()

    def detector_init(self):
        """
        Before calling detector_init we should know:

        gpibAddress
        detector model
        number of channels
        averaging time
        detector_sensor_current_wavelength
        detector power range
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.identity() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Current mainframe:")
        for element in string.split(","):
            print("{}".format(element))

        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.options() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print(string)
        if self.dict["detector_model"] in string:
            pass
        else:
            print("{} not found".format(self.dict["detector_model"]))
            return
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            if self.detector_slot():
                pass
            else:
                return
                self.set_sensor_power_reading(self.dict["detector_slot"], "CONT", "1")
                self.read_sensor_boundary_wavelength("1")
                self.set_detector_averaging_time(self.dict["detector_averaging_time"])
                self.set_sensor_wavelength("1")
                self.set_sensor_wavelength("2")
                self.set_sensor_power_unit("1", "0")
                self.set_sensor_power_unit("2", "0")
                self.set_sensor_autoranging("1")
                self.set_sensor_power_range("1", self.dict["detector_power_range"])
                self.set_sensor_autoranging("1")
                self.set_sensor_power_range("2", self.dict["detector_power_range"])
                self.set_sensor_autoranging("1")

    def set_sensor_power_reading(self, slot, additional, on_off):
        """
        Sets the reading mode on the power sensors.

        Use FETC[n]:CHAN[m]:POW? to retrieve data
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sensor_power_reading(slot, additional, on_off) + "\n").encode(encoding="UTF-8"))

    def set_sensor_power_range(self, channel, power_range):
        """
        Sets the power range of the instrument.

        Example
        power_range: -10.000000DBM
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_power_sensor_range(self.dict["detector_slot"], channel, power_range) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_power_sensor_range(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Current channel {} sensor power range: {}".format(channel, string))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def set_sensor_autoranging(self, on_off):
        """
        0:OFF
        1:ON
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.power_sensor_autorange(self.dict["detector_slot"], on_off) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.is_power_sensor_autoranging(self.dict["detector_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Autoranging?: {}; 0:OFF, 1:ON".format(string))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def set_sensor_power_unit(self, channel, unit):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.power_sensor_unit(self.dict["detector_slot"], channel, unit) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_power_sensor_unit(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Current units: {}; 0:dbm, 1:Watts".format(string))
        self.read_error_and_clear_status()

    def read_sensor_boundary_wavelength(self, channel):
        """
        Queries the current sensor wavelength
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sensor_wavelength((self.dict["detector_slot"]), channel, additional="MIN") + "\n").encode(encoding="UTF-8"))
        self.update_parameter("detector_sensor_min_wavelength", self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sensor_wavelength((self.dict["detector_slot"]), channel, additional="MAX") + "\n").encode(encoding="UTF-8"))
        self.update_parameter("detector_sensor_max_wavelength", self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def set_sensor_wavelength(self, channel):
        """
        Sets the current sensor wavelength
        """
        if float(self.dict["detector_sensor_current_wavelength"]) < float(self.dict["detector_sensor_min_wavelength"]) or float(self.dict["detector_sensor_current_wavelength"]) > float(self.dict["detector_sensor_max_wavelength"]):
            return
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_sensor_wavelength(self.dict["detector_slot"], channel, self.dict["detector_sensor_current_wavelength"]) + "\n").encode(encoding="UTF-8"))
        self.read_error_and_clear_status()
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_sensor_wavelength(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Current sensor wavelength is {}".format(string))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def set_detector_averaging_time(self, averaging_time):
        """
        Sets the current averaging time of the module
        self.dict['detector_averaging_time']
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_detector_averaging_time(self.dict["detector_slot"], averaging_time) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_detector_averaging_time(self.dict["detector_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Current Averaging time: {} seconds".format(string))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))

    def detector_slot(self):
        """
        Checks wheter the detector is among the installed modules.

        If found, saves the slot of the detector.
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.options() + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
        print("Current modules installed: {}".format(string))
        if self.dict["detector_model"] in string:
            pass
        else:
            print("Detector was not found")
            return False
            temp_dict = dict(enumerate(string.split(", ")))
            temp_dict = dict(zip(temp_dict.values(), temp_dict.keys()))
            print(temp_dict)
            self.update_parameter("detector_slot", str(temp_dict[self.dict["detector_model"]]))
            print("Detector was found in slot {}".format(self.dict["detector_slot"]))
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
            return True

    def detector_read_power(self, channel):
        averaging_time = self.dict["detector_averaging_time"]
        averaging_time = averaging_time.split("ms")
        averaging_time = float(averaging_time[0]) / 1000
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.clear_status() + "\n").encode(encoding="UTF-8"))
        time.sleep(averaging_time)
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_power(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        while string == "":
            time.sleep(averaging_time)
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_power(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
            string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

        time.sleep(averaging_time)
        return float(string)

    def set_detector_incoming_trigger_response(self, response):
        """
        This setting allows the sweep to wait for a hardware or software
        trigger before beginning, after all configuration commands are
        sent

        - IGN - ignore incoming trigger
        - SME - start single measurement. One sample is performed and result is stored in data array
        - CME - start complete measurement
        - NEXT - Perform next step of a stepped sweep
        - SWS - Start a sweep cycle
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_incoming_trigger_response(self.dict["detector_slot"], response) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_incoming_trigger_response(self.dict["detector_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Detector incoming trigger response has been set to {}".format(string))

    def set_detector_output_trigger_timing(self, channel, additional):
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
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_detector_output_trigger_timing(self.dict["detector_slot"], channel, additional) + "\n").encode(encoding="UTF-8"))
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_detector_output_trigger_timing(self.dict["detector_slot"], channel) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print("Detector output trigger timing has been set to {}".format(string))

    def set_detector_data_acquisition(self, additional, start_stop):
        """
        Enables/disables the logging, MinMAX, or stability data acquisition function mode

        additional:
        LOGG - 
        STAB - 
        MINMAC -

        STOP
        STAR
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_detector_data_acquisition(self.dict["detector_slot"], additional, start_stop) + "\n").encode(encoding="UTF-8"))

    def read_detector_data_acquisition(self):
        """
        returns the function mode, and the status of the data acquistion function
        """
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_detector_data_acquisition(self.dict["detector_slot"]) + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8", "ignore")
        return string

    def read_detector_logging_data_old(self, fileTime, channel, num_samples):
        """
        returns the data array of the last data acquisition function
        """
        print("Querying logging data...")
        print("Will be reading {} samples".format(num_samples))
        samples_read = 0
        converted_binary_block = []
        count = 1
        while True:
            samples_to_read = (num_samples - samples_read) * 4
            binary_raw = []
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_data(self.dict["detector_slot"], str(channel)) + "\n").encode(encoding="UTF-8"))
            import re
            idx, obj, binary_block = self.telnet_connection.expect([re.compile(b'\n')], timeout=30)
            binary_raw.extend(binary_block)
            print(binary_block)
            print(int(chr(binary_block[1])))
            bytestoread = int(binary_block[2[:int(chr(binary_block[1])) + 2]])
            print(bytestoread)
            print(len(binary_block[(int(chr(binary_block[1])) + 2)[:None]]))
            failed_reads = 0
            previous_length = 0
            while True:
                idx, obj, read = self.telnet_connection.expect([re.compile(b'\n')], timeout=0.1)
                binary_raw.extend(read)
                if len(binary_raw) >= bytestoread + 2:
                    print("done reading")
                    break
                elif previous_length == len(binary_raw):
                    failed_reads = failed_reads + 1
                else:
                    failed_reads = 0
                if failed_reads > 3:
                    break
                print("reading so far")
                print(len(binary_raw))
                previous_length = len(binary_raw)
                time.sleep(0.1)

            if len(binary_raw) >= bytestoread + 2:
                print("done reading 2")
            else:
                print("trying new read")
                self.read_error_and_clear_status()
                failed_reads = 0
                print(str((len(binary_raw) - int(chr(binary_block[1])) - 1) / 4))
                print(str(bytestoread / 4 - (len(binary_raw) - int(chr(binary_block[1])) - 1) / 4))
                self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_block(self.dict["detector_slot"], str(channel), str((len(binary_raw) - int(chr(binary_block[1])) - 1) / 4), str(bytestoread / 4 - (len(binary_raw) - int(chr(binary_block[1])) - 1) / 4)) + "\n").encode(encoding="UTF-8"))
                while True:
                    idx, obj, read = self.telnet_connection.expect([re.compile(b'\n')], timeout=0.1)
                    binary_raw.extend(read)
                    if len(binary_raw) >= bytestoread + 2:
                        print("done reading")
                        break
                    elif previous_length == len(binary_raw):
                        failed_reads = failed_reads + 1
                    else:
                        failed_reads = 0
                    if failed_reads > 3:
                        self.read_error_and_clear_status()
                        print(str((len(binary_raw) - int(chr(binary_block[1])) - 1) / 4))
                        print(str(bytestoread / 4 - (len(binary_raw) - int(chr(binary_block[1])) - 1) / 4))
                        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_block(self.dict["detector_slot"], str(channel), str((len(binary_raw) - int(chr(binary_block[1])) - 1) / 4), str(bytestoread / 4 - (len(binary_raw) - int(chr(binary_block[1])) - 1) / 4)) + "\n").encode(encoding="UTF-8"))
                        failed_reads = 0
                        print("reset read")
                    print("reading so far")
                    print(len(binary_raw))
                    previous_length = len(binary_raw)
                    time.sleep(0.1)

                print(binary_raw)
                self.read_error_and_clear_status()
                binary_raw = bytes(binary_raw)
                if samples_read == 0:
                    start_index = binary_raw.index(b'#')
                else:
                    start_index = -5
                print("------------------")
                print(len(binary_raw))
                print("------------------")
                print(binary_raw)
                print(chr(binary_raw[start_index + 6 - 1]))
                failcount = 0
                for i in range(start_index + 6 - 1, len(binary_raw), 4):
                    while True:
                        try:
                            buf = bytes([binary_raw[i], binary_raw[i + 1], binary_raw[i + 2], binary_raw[i + 3]])
                            value = float(struct.unpack_from("<f", buf)[0])
                            converted_binary_block.append(value)
                            break
                            if value < 1:
                                if value > -100:
                                    converted_binary_block.append(value)
                                    break
                            if failcount < 4:
                                i = i + 1
                            else:
                                if failcount < 12:
                                    i = i - 1
                                else:
                                    failcount = 0
                                    converted_binary_block.append(float("nan"))
                                    break
                            failcount = failcount + 1
                        except:
                            if failcount > 4:
                                failcount = 0
                                converted_binary_block.append(float("nan"))
                                break
                            i = i + 1
                            failcount = failcount + 1

                samples_read = len(converted_binary_block)
                print("--------------------------block length------")
                print(len(converted_binary_block))
                print("--------------------------------------------")
                print("Reading {}, {} data points have been read thus far.".format(count, samples_read))
                count += 1
                if len(converted_binary_block) >= num_samples:
                    break
                break
                print("retry")
                binary_raw = []
                converted_binary_block = []

        print("A total of {} data points was returned after {} readings".format(len(converted_binary_block), count - 1))
        print("-----------------------------------------------")
        print(converted_binary_block)
        print("-----------------done detector read------------" + str(samples_read) + "--------")
        return converted_binary_block

    def read_detector_logging_data(self, channel, num_samples):
        """
        returns the data array of the last data acquisition function
        """
        print("Querying logging data...")
        print("Will be reading {} samples".format(num_samples))
        samples_read = 0
        converted_binary_block = []
        count = 1
        while True:
            samples_to_read = num_samples - samples_read
            print(num_samples * 4 + 8)
            if num_samples * 4 + 8 < 1514:
                blocksize = samples_to_read * 4 + 8
            else:
                blocksize = 1514
            binary_raw = []
            self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.read_block(self.dict["detector_slot"], str(channel), str(samples_read), str(samples_to_read)) + "\n").encode(encoding="UTF-8"))
            telnetsocket = self.telnet_connection.get_socket()
            import re
            binary_block = []
            read = telnetsocket.recv(blocksize)
            binary_block.extend(read)
            if num_samples * 4 + 8 > 1514:
                while len(binary_block) < samples_to_read * 4 + 8:
                    try:
                        read = telnetsocket.recv(blocksize)
                        binary_block.extend(read)
                    except:
                        break

            break

        start_index = 0
        failcount = 0
        for i in range(int(chr(binary_block[start_index + 1])) + 2, len(binary_block), 4):
            try:
                buf = bytes([binary_block[i], binary_block[i + 1], binary_block[i + 2], binary_block[i + 3]])
                value = 10 * numpy.log10(float(struct.unpack_from("<f", buf)[0])) + 30
                converted_binary_block.append(value)
            except:
                converted_binary_block.append(float("nan"))

        del converted_binary_block[-1]
        return converted_binary_block

    def power_sensor_head_response(self, slot, head):
        """
        Dunno?
        """
        message = ag8163a.agilent_8163a_mainframe.power_sensor_head_response(slot, head)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        for wavelength, response_factor in string:
            print("WL: %s m, RF: %s" % (wavelength, response_factor))

        return string

    def power_sensor_reference(self, slot, channel, levelindb):
        """
        Sets the sensor reference value
        """
        message = power_sensor_reference(slot, channel, levelindb)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        print("power_sensor reference set to %f" % levelindb)

    def power_sensor_logging_result(self, channel, offset, samples):
        data = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        while "COMPLETE" in data:
            data = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

        tries = 0
        while tries < 5:
            try:
                message = ag8163a.agilent_8163a_mainframe.power_sensor_logging_result(self.dict["detector_slot"], channel, offset, samples)
                self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
                data = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
                print(data)
                startindex = 0
                for i in range(len(data)):
                    if data[i] == b'#':
                        print(i)
                        startindex = i
                        break

                print(data[startindex])
                if data[startindex] != b'#':
                    print("Error reading log data")
                    tries += 1
                    self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
                    continue
                numberofdigits = int(chr(data[startindex + 1]))
                numberofbytes = ""
                print(numberofdigits)
            except:
                self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
                tries += 1

        if tries == 5:
            print("could not read data")
            return []
        for i in range(startindex + 2, startindex + 2 + numberofdigits):
            numberofbytes += chr(data[i])

        numberofbytes = int(numberofbytes)
        floatdata = list()
        for i in range(startindex + 2 + numberofdigits, startindex + numberofbytes + 2 + numberofdigits, 4):
            byteread = data[i[:i + 4]]
            powerinwatts = struct.unpack("f", byteread)
            powerindbm = 10 * numpy.log10(powerinwatts) + 30
            floatdata.append(powerindbm[0])

        print(len(floatdata))
        print(floatdata)
        return floatdata

    def power_sensor_wait_for_logging_result(self, slot, channel, timeout):
        while True:
            message = ag8163a.agilent_8163a_mainframe.power_sensor_logging_state(slot, channel)
            self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
            result = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")
            print(result)
            if "COMPLETE" in result:
                return 0
            if timeout <= 0:
                print("power sensor timeout!!")
                return -1
            print("wait")
            time.sleep(1)
            timeout -= 1

    def enable_trigger(self):
        """
        Output tirgger connector automatically
        The same as DEFault but a trigger at the Input Trigger Connector generates a trigger at the output trigger connector automatically 
        """
        message = ag8163a.agilent_8163a_mainframe.enable_trigger()
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))

    def disable_trigger_rearm(self, trigger):
        """
        Sets the arming response of a channel to an incoming trigger
        """
        message = ag8163a.agilent_8163a_mainframe.disable_trigger_rearm(trigger)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))

    def enable_output_trigger_rearm(self, trigger):
        """
        Sets the arming response of a channel to an outgoing trigger
        """
        message = ag8163a.agilent_8163a_mainframe.enable_output_trigger_rearm(trigger)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))

    def read_trigger(self):
        message = ag8163a.agilent_8163a_mainframe.read_trigger()
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        print(string)

    def set_continuous(self, slot, channel):
        message = ag8163a.agilent_8163a_mainframe.set_continuous(slot, channel)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))

    def read_power(self, slot, channel):
        offscalecount = 5
        while True:
            try:
                message = ag8163a.agilent_8163a_mainframe.read_power(slot, channel)
                self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
                errorvalue = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
                errorvalue = errorvalue.split()
                power = float(errorvalue[len(errorvalue) - 1])
                if power < -5:
                    break
                if power == 3.402823e+38:
                    if offscalecount > 0:
                        offscalecount -= 1
                    else:
                        power = -100
                        break
            except:
                time.sleep(0.5)
                self.read()
                time.sleep(1)
                print("power read error!")
                print(errorvalue)

        return power

    def read_sensor(self, string):
        self.telnet_connection.write((string + "\n").encode(encoding="UTF-8"))
        print(self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5))

    def write_sensor(self, string):
        self.telnet_connection.write((string + "\n").encode(encoding="UTF-8"))

    def detector_read(self):
        self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)

    def reset(self):
        data = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        while data != "":
            data = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
            print("fail")

    def slot_full(self, slot):
        """
        Gpib returns 0 if slot is full, and 1 if slot is empty
        Function returns False if slot is empty and True if it is full
        """
        message = ag8163a.agilent_8163a_mainframe.slot_full(slot)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        status = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        if status:
            return False
        return True

    def is_power_sensor(self, slot):
        """
        Determines if a slot holds a power sensor
        """
        message = ag8163a.agilent_8163a_mainframe.is_power_sensor(slot)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        string = self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5)
        if "81635A" in string:
            return True
        return False

    def set_stab_settings(self, slot, total_time, period, averaging_time):
        message = "SENS" + str(slot) + ":FUNC:PAR:STAB " + str(total_time) + "," + str(period) + "," + str(averaging_time)
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))

    def read_stab_settings(self, slot):
        self.telnet_connection.write(("SENS" + str(slot) + ":FUNC:PAR:STAB?" + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")

    def set_detector_sensor_logging(self, slot, detector_logging_num_samples, averagetime):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_detector_sensor_logging(str(slot), str(detector_logging_num_samples), str(averagetime)) + "\n").encode(encoding="UTF-8"))

    def read_detector_sensor_logging(self, slot):
        message = "SENS" + str(slot) + ":FUNC:PAR:LOGG?"
        self.telnet_connection.write((message + "\n").encode(encoding="UTF-8"))
        return self.telnet_connection.read_until(str("\n").encode(encoding="UTF-8"), 5).decode("UTF-8")

    def set_hardware_trigger(self, mode):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.set_hardware_trigger_config(mode) + "\n").encode(encoding="UTF-8"))

    def send_trigger(self):
        self.telnet_connection.write((ag8163a.agilent_8163a_mainframe.send_trigger("1") + "\n").encode(encoding="UTF-8"))
