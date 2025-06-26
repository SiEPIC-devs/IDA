# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Downloads/laser_functions.py
# Compiled at: 2022-09-12 22:43:36
# Size of source mod 2**32: 29218 bytes
import os, shutil, sys, time, datetime, numpy as np
import plotly.express as px
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from multiprocessing import Process
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR laser"))
import laser as laserNIR
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR Detector"))
import NIR_detector
detector = NIR_detector.detector()
laser = laserNIR.laser()
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.OUT)
GPIO.output(7, 0)
count_trigger_laser = 0

def trigger_laser():
    global count_trigger_laser
    count_trigger_laser += 1
    GPIO.output(7, 1)
    time.sleep(0.0001)
    GPIO.output(7, 0)
    time.sleep(0.0001)


def setup_point_recording(number_of_samples, averaging_time, power_range=-1):
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    laser.read_error_and_clear_status()
    detector.read_error_and_clear_status()
    time.sleep(0.5)
    laser.set_trigger_conf("DEF")
    time.sleep(0.5)
    laser.set_laser_power_state("1")
    time.sleep(0.5)
    laser.read_laser_power_state()
    time.sleep(0.5)
    detector.set_sensor_autoranging("0")
    if power_range == -1:
        time.sleep(0.5)
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        time.sleep(0.5)
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
    else:
        time.sleep(0.5)
        detector.set_sensor_power_range("1", str(power_range) + "dbm")
        time.sleep(0.5)
        detector.set_sensor_power_range("2", str(power_range) + "dbm")
    time.sleep(1)
    print(number_of_samples)
    detector.set_detector_sensor_logging("1", str(number_of_samples), str(averaging_time) + "ms")
    time.sleep(0.5)
    detector.set_detector_incoming_trigger_response("sme")
    time.sleep(0.5)
    detector.set_sensor_power_unit("1", "1")
    time.sleep(0.5)
    detector.set_sensor_power_unit("2", "1")
    time.sleep(0.5)
    detector.set_detector_data_acquisition("logg", "star")
    time.sleep(0.5)
    while int(laser.read_trigger_status("0")) < 1:
        print("wait")

    time.sleep(0.5)
    laser.close_port()
    detector.close_port()


def read_point_recording(channel, number_of_points):
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    laser.read_error_and_clear_status()
    time.sleep(0.5)
    detector.read_error_and_clear_status()
    time.sleep(0.5)
    print(detector.power_sensor_wait_for_logging_result(1, 1, 4))
    print(detector.read_detector_sensor_logging("1"))
    time.sleep(0.5)
    print("points " + str(number_of_points))
    converted_binary_block = detector.read_detector_logging_data(str(channel), number_of_points)
    laser.close_port()
    detector.close_port()
    return converted_binary_block


def start_new_point_recording():
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    detector.set_detector_data_acquisition("lOGG", "STOP")
    laser.read_error_and_clear_status()
    detector.set_detector_data_acquisition("logg", "star")
    time.sleep(0.5)
    while int(laser.read_trigger_status("0")) < 1:
        print("wait")

    time.sleep(0.5)
    laser.close_port()
    detector.close_port()


def return_laser_to_normal():
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    laser.read_error_and_clear_status()
    detector.set_sensor_autoranging("1")
    detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
    detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
    detector.set_sensor_power_unit("1", "0")
    detector.set_sensor_power_unit("2", "0")
    detector.set_detector_data_acquisition("lOGG", "STOP")
    laser.read_error_and_clear_status()
    detector.set_detector_incoming_trigger_response("IGN")
    detector.set_detector_output_trigger_timing("", "DIS")
    laser.close_port()
    detector.close_port()


def spectrum_sweep(filename='Spectral_Sweep_'):
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    return_value = 0
    laser.read_error_and_clear_status()
    detector.read_error_and_clear_status()
    time.sleep(0.5)
    laser.set_trigger_conf("loop")
    time.sleep(0.5)
    laser.set_laser_power_state("1")
    time.sleep(0.5)
    laser.read_laser_power_state()
    time.sleep(0.5)
    laser.set_laser_output_trigger_timing("stf")
    time.sleep(0.5)
    laser.set_laser_incoming_trigger_response("sws")
    time.sleep(0.5)
    laser.set_sweep_start_and_stop_wavelength(laser.dict["laser_sweep_start_wavelength"], laser.dict["laser_sweep_stop_wavelength"])
    time.sleep(0.5)
    laser.set_laser_sweep_step_size(laser.dict["laser_sweep_step_size"])
    time.sleep(0.5)
    laser.set_laser_directionality("ONEWay")
    time.sleep(0.5)
    laser.set_laser_sweep_cycle(1)
    time.sleep(0.5)
    laser.set_continuous_sweep_speed(laser.dict["laser_continuous_sweep_speed"])
    time.sleep(0.5)
    laser.set_laser_sweep_mode("cont")
    time.sleep(0.5)
    laser.set_laser_lambda_logging("1")
    time.sleep(0.5)
    print(laser.read_laser_sweep_parameters())
    time.sleep(0.5)
    try:
        detector_logging_num_samples = int(laser.read_trigger_number())
        time.sleep(0.5)
        averaging = float(laser.dict["laser_continuous_sweep_speed"].split("nm/s")[0]) / float(laser.dict["laser_sweep_step_size"].split("nm")[0])
        averaging = 1 / averaging / 2 * 1000
    except:
        print("An unknown error occured!\nResetting laser!!")
        laser.read_error_and_clear_status()
        detector.set_sensor_autoranging("1")
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        detector.set_sensor_power_unit("1", "0")
        detector.set_sensor_power_unit("2", "0")
        detector.set_detector_data_acquisition("lOGG", "STOP")
        laser.read_error_and_clear_status()
        detector.set_detector_incoming_trigger_response("IGN")
        detector.set_detector_output_trigger_timing("", "DIS")
        return_value = 3
        laser.set_laser_current_wavelength(laser.dict["laser_current_wavelength"])
        laser.close_port()
        detector.close_port()
        return return_value
        laser.arm_laser_sweep()
        time.sleep(0.5)
        detector.set_detector_incoming_trigger_response("sme")
        time.sleep(0.5)
        detector.set_sensor_power_unit("1", "1")
        time.sleep(0.5)
        detector.set_sensor_power_unit("2", "1")
        time.sleep(0.5)
        detector.set_sensor_autoranging("0")
        time.sleep(0.5)
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        time.sleep(0.5)
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        time.sleep(0.5)
        detector.set_detector_sensor_logging("1", str(detector_logging_num_samples), str(averaging) + "ms")
        time.sleep(0.5)
        detector.set_detector_data_acquisition("logg", "star")
        time.sleep(0.5)
        while int(laser.read_trigger_status("0")) < 1:
            print("wait")

        laser.send_trigger("0")
        start = time.time()
        time.sleep(1.5)
        try:
            trigger_status = int(laser.read_trigger_status("0"))
            time.sleep(0.5)
        except:
            trigger_status = 0

        while trigger_status > 1:
            time.sleep(5)
            laser.send_trigger("0")
            print("retrigger")
            try:
                trigger_status = int(laser.read_trigger_status("0"))
            except:
                trigger_status = 0

        while True:
            try:
                sweep_status = int(laser.read_laser_sweep_state("1"))
            except:
                sweep_status = 1

            if sweep_status == 0:
                end = time.time()
                print("Sweep completed in {:8.4f} seconds".format(end - start))
                time.sleep(0.5)
                break
            else:
                temp = time.time()
                print("Sweeping, {:8.4f} seconds elapsed".format(temp - start))
                time.sleep(0.5)

        laser.read_error_and_clear_status()
        time.sleep(0.5)
        detector.read_error_and_clear_status()
        time.sleep(0.5)
        print(detector.read_detector_data_acquisition())
        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        laser.read_error_and_clear_status()
        time.sleep(0.5)
        detector.read_error_and_clear_status()
        time.sleep(0.5)
        print(detector.read_detector_sensor_logging("1"))
        time.sleep(0.5)
        converted_binary_block1 = detector.read_detector_logging_data("1", detector_logging_num_samples)
        time.sleep(0.5)
        print(detector.read_detector_sensor_logging("1"))
        time.sleep(0.5)
        converted_binary_block2 = detector.read_detector_logging_data("2", detector_logging_num_samples)
        time.sleep(0.5)
        start = float(laser.dict["laser_sweep_start_wavelength"].split("nm")[0])
        stop = float(laser.dict["laser_sweep_stop_wavelength"].split("nm")[0])
        estimated_number_of_samples = (stop - start) / float(laser.dict["laser_sweep_step_size"].split("nm")[0])
        print("---------estimate number of samples------")
        print(estimated_number_of_samples)
        print(detector_logging_num_samples)
        exception_count = 0
        while exception_count < 3:
            try:
                laser_num_samples = int(laser.read_wavelength_points_avail())
                break
            except:
                exception_count += 1
                print("Exception reading number of samples!!")
                laser_num_samples = int(estimated_number_of_samples) + 1
                time.sleep(10)

        if exception_count == 3:
            print("Using estimated number of samples")
        print(laser_num_samples)
        laser_wavelengths = laser.read_laser_wavelength_log(laser_num_samples)
        combined_block = zip(laser_wavelengths, converted_binary_block1, converted_binary_block2)
        detector_power_errors = 0
        for i in converted_binary_block1:
            if i > 100:
                detector_power_errors = detector_power_errors + 1
                return_value = 1

        if detector_power_errors != 0:
            print(str(detector_power_errors) + " power value errors detector 1!!")
        detector_power_errors = 0
        for i in converted_binary_block2:
            if i > 100:
                detector_power_errors = detector_power_errors + 1
                return_value = 1

        if detector_power_errors != 0:
            print(str(detector_power_errors) + " power value errors detector 2!!")
        if len(laser_wavelengths) < estimated_number_of_samples:
            print("laser data length error!!")
            return_value = 2
        if len(converted_binary_block1) < estimated_number_of_samples:
            print("detector 1 data length error!!")
            return_value = 2
        if len(converted_binary_block2) < estimated_number_of_samples:
            print("detector 2 data length error!!")
            return_value = 2
        with open(filename + "_" + fileTime + ".csv", "w") as file:
            for data in combined_block:
                file.write("{},{},{}\n".format(data[0], data[1], data[2]))

        file.close()
        laser.read_error_and_clear_status()
        detector.set_sensor_autoranging("1")
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        detector.set_sensor_power_unit("1", "0")
        detector.set_sensor_power_unit("2", "0")
        detector.set_detector_data_acquisition("lOGG", "STOP")
        laser.read_error_and_clear_status()
        detector.set_detector_incoming_trigger_response("IGN")
        detector.set_detector_output_trigger_timing("", "DIS")
        plot_p1 = []
        plot_p2 = []
        plot_wavelengths = []
        shortest_dataset = len(laser_wavelengths)
        if len(converted_binary_block1) < shortest_dataset:
            shortest_dataset = len(converted_binary_block1)
            print("short 1")
        if len(converted_binary_block2) < shortest_dataset:
            shortest_dataset = len(converted_binary_block2)
            print("short 2")
        for i in range(0, shortest_dataset):
            plot_p1.append(converted_binary_block1[i])
            plot_p2.append(converted_binary_block2[i])
            plot_wavelengths.append(laser_wavelengths[i] * 1000000000.0)

        p = Process(target=generate_plots, args=(plot_wavelengths, [plot_p1, plot_p2], filename, fileTime))
        p.start()
        laser.set_laser_current_wavelength(laser.dict["laser_current_wavelength"])
        laser.close_port()
        detector.close_port()
        return return_value


def generate_plots(x_axis, y_values, filename, fileTime):
    print("Start html plot")
    try:
        x_reduced = []
        plot_y_reduced = []
        for element in range(0, len(y_values)):
            plot_y_reduced.append([])

        averaging = 20
        for i in range(0, len(x_axis) - averaging, averaging):
            x_avg = 0
            y_avg = []
            for j in range(0, averaging):
                x_avg += x_axis[i + j]
                for element in range(0, len(y_values)):
                    try:
                        y_avg[element] += y_values[element][i + j]
                    except Exception as e:
                        try:
                            y_avg.append(y_values[element][i + j])
                        finally:
                            e = None
                            del e

            x_reduced.append(x_avg / averaging)
            for element in range(0, len(y_values)):
                plot_y_reduced[element].append(y_avg[element] / averaging)

        plots = {"Wavelength [nm]": x_axis}
        plotnames = []
        for element in range(0, len(y_values)):
            plotname = "Detector " + str(element + 1)
            plots[plotname] = y_values[element]
            plotnames.append(plotname)

        fig = px.line(plots, x="Wavelength [nm]", y=plotnames, labels={'value':"Power [dBm]",  'x':"Wavelength [nm]"})
        for i in range(0, len(y_values)):
            fig.data[i].name = str(i + 1)

        fig.update_layout(legend_title_text="Detector")
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        fig.write_html(filename + "_" + fileTime + ".html")
        shutil.copy(filename + "_" + fileTime + ".html", os.path.join(main_path, "Plot", "res", "Plot_Spectral_Sweep_{}.html".format(fileTime)))
        print("Done html plot")
    except Exception as e:
        try:
            print("Exception generating html plot")
            print(e)
        finally:
            e = None
            del e

    try:
        print("Start pdf plot")
        image_dpi = 20
        plt.figure(figsize=(100 / image_dpi, 100 / image_dpi), dpi=image_dpi)
        for element in range(0, len(y_values)):
            plt.plot(x_reduced, plot_y_reduced[element])

        plt.xlabel("Wavelength [nm]")
        plt.ylabel("Power [dBm]")
        plt.savefig((filename + "_" + fileTime + ".pdf"), dpi=image_dpi)
        plt.close()
        print("Done pdf plot")
    except Exception as e:
        try:
            print("Exception generating pdf plot")
            print(e)
        finally:
            e = None
            del e


def spectrum_sweep_reverse(filename='Spectral_Sweep_'):
    laser.reload_parameters()
    detector.reload_parameters()
    laser.open_port()
    detector.open_port()
    return_value = 0
    sweep_number = 0
    laser.read_error_and_clear_status()
    detector.read_error_and_clear_status()
    time.sleep(0.5)
    laser.set_trigger_conf("loop")
    time.sleep(0.5)
    laser.set_laser_power_state("1")
    time.sleep(0.5)
    laser.read_laser_power_state()
    time.sleep(0.5)
    laser.set_laser_output_trigger_timing("stf")
    time.sleep(0.5)
    laser.set_laser_incoming_trigger_response("sws")
    time.sleep(0.5)
    laser.set_sweep_start_and_stop_wavelength(laser.dict["laser_sweep_start_wavelength"], laser.dict["laser_sweep_stop_wavelength"])
    time.sleep(0.5)
    laser.set_laser_sweep_step_size(laser.dict["laser_sweep_step_size"])
    time.sleep(0.5)
    laser.set_laser_sweep_cycle(2)
    time.sleep(0.5)
    laser.set_laser_directionality("TWOWAY")
    time.sleep(0.5)
    laser.set_continuous_sweep_speed(laser.dict["laser_continuous_sweep_speed"])
    time.sleep(0.5)
    laser.set_laser_sweep_mode("cont")
    time.sleep(0.5)
    laser.set_laser_lambda_logging("1")
    time.sleep(0.5)
    print(laser.read_laser_sweep_parameters())
    time.sleep(0.5)
    try:
        detector_logging_num_samples = int(laser.read_trigger_number())
        time.sleep(0.5)
        averaging = float(laser.dict["laser_continuous_sweep_speed"].split("nm/s")[0]) / float(laser.dict["laser_sweep_step_size"].split("nm")[0])
        averaging = 1 / averaging / 2 * 1000
    except:
        print("An unknown error occured!\nResetting laser!!")
        laser.read_error_and_clear_status()
        detector.set_sensor_autoranging("1")
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        detector.set_sensor_power_unit("1", "0")
        detector.set_sensor_power_unit("2", "0")
        detector.set_detector_data_acquisition("lOGG", "STOP")
        laser.read_error_and_clear_status()
        detector.set_detector_incoming_trigger_response("IGN")
        detector.set_detector_output_trigger_timing("", "DIS")
        return_value = 3
        laser.set_laser_current_wavelength(laser.dict["laser_current_wavelength"])
        laser.close_port()
        detector.close_port()
        return return_value
        laser.arm_laser_sweep()
        time.sleep(0.5)
        detector.set_detector_incoming_trigger_response("IGN")
        time.sleep(0.5)
        detector.set_sensor_power_unit("1", "1")
        time.sleep(0.5)
        detector.set_sensor_power_unit("2", "1")
        time.sleep(0.5)
        detector.set_sensor_autoranging("0")
        time.sleep(0.5)
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        time.sleep(0.5)
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        time.sleep(0.5)
        detector.set_detector_sensor_logging("1", str(detector_logging_num_samples), str(averaging) + "ms")
        time.sleep(0.5)
        detector.set_detector_data_acquisition("logg", "star")
        time.sleep(0.5)
        while int(laser.read_trigger_status("0")) < 1:
            print("wait")

        while sweep_number < 2:
            laser.send_trigger("0")
            start = time.time()
            time.sleep(1.5)
            try:
                trigger_status = int(laser.read_trigger_status("0"))
                time.sleep(0.5)
            except:
                trigger_status = 0

            print(trigger_status)
            while not (trigger_status != 1 and sweep_number == 0):
                if not trigger_status != 3 or sweep_number == 1:
                    time.sleep(5)
                    laser.send_trigger("0")
                    print("retrigger")
                    try:
                        trigger_status = int(laser.read_trigger_status("0"))
                    except:
                        trigger_status = 0

            while True:
                try:
                    sweep_status = int(laser.read_trigger_status("0"))
                except:
                    print("sweep except")
                    sweep_status = -1

                print(sweep_status)
                if sweep_number == 0:
                    if sweep_status == 3:
                        end = time.time()
                        print("Sweep completed in {:8.4f} seconds".format(end - start))
                        time.sleep(0.5)
                        break
                elif sweep_status == 4:
                    end = time.time()
                    print("Sweep completed in {:8.4f} seconds".format(end - start))
                    time.sleep(0.5)
                    break
                temp = time.time()
                print("Sweeping, {:8.4f} seconds elapsed".format(temp - start))
                time.sleep(0.5)

            sweep_number += 1
            laser.read_error_and_clear_status()
            time.sleep(0.5)
            detector.read_error_and_clear_status()
            time.sleep(0.5)
            print(detector.read_detector_data_acquisition())
            fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
            laser.read_error_and_clear_status()
            time.sleep(0.5)
            detector.read_error_and_clear_status()
            time.sleep(0.5)
            print(detector.read_detector_sensor_logging("1"))
            time.sleep(0.5)
            converted_binary_block1 = detector.read_detector_logging_data("1", detector_logging_num_samples)
            time.sleep(0.5)
            print(detector.read_detector_sensor_logging("1"))
            time.sleep(0.5)
            converted_binary_block2 = detector.read_detector_logging_data("2", detector_logging_num_samples)
            time.sleep(0.5)
            start = float(laser.dict["laser_sweep_start_wavelength"].split("nm")[0])
            stop = float(laser.dict["laser_sweep_stop_wavelength"].split("nm")[0])
            estimated_number_of_samples = (stop - start) / float(laser.dict["laser_sweep_step_size"].split("nm")[0])
            print("---------estimate number of samples------")
            print(estimated_number_of_samples)
            print(detector_logging_num_samples)
            exception_count = 0
            while exception_count < 3:
                try:
                    laser_num_samples = int(laser.read_wavelength_points_avail())
                    break
                except:
                    exception_count += 1
                    print("Exception reading number of samples!!")
                    laser_num_samples = int(estimated_number_of_samples) + 1
                    time.sleep(10)

            if exception_count == 3:
                print("Using estimated number of samples")
            print(laser_num_samples)
            laser_wavelengths = laser.read_laser_wavelength_log(laser_num_samples)
            if sweep_number == 1:
                detector.set_detector_incoming_trigger_response("sme")
                time.sleep(10)
                continue
            combined_block = zip(laser_wavelengths, converted_binary_block1, converted_binary_block2)
            detector_power_errors = 0
            for i in converted_binary_block1:
                if i > 100:
                    detector_power_errors = detector_power_errors + 1
                    return_value = 1

            if detector_power_errors != 0:
                print(str(detector_power_errors) + " power value errors detector 1!!")
            detector_power_errors = 0
            for i in converted_binary_block2:
                if i > 100:
                    detector_power_errors = detector_power_errors + 1
                    return_value = 1

            if detector_power_errors != 0:
                print(str(detector_power_errors) + " power value errors detector 2!!")
            if len(laser_wavelengths) < estimated_number_of_samples:
                print("laser data length error!!")
                return_value = 2
            if len(converted_binary_block1) < estimated_number_of_samples:
                print("detector 1 data length error!!")
                return_value = 2
            if len(converted_binary_block2) < estimated_number_of_samples:
                print("detector 2 data length error!!")
                return_value = 2
            with open(filename + "_reverse" + "_" + fileTime + ".csv", "w") as file:
                for data in combined_block:
                    file.write("{},{},{}\n".format(data[0], data[1], data[2]))

            file.close()
            plot_p1 = []
            plot_p2 = []
            plot_wavelengths = []
            shortest_dataset = len(laser_wavelengths)
            if len(converted_binary_block1) < shortest_dataset:
                shortest_dataset = len(converted_binary_block1)
                print("short 1")
            if len(converted_binary_block2) < shortest_dataset:
                shortest_dataset = len(converted_binary_block2)
                print("short 2")
            for i in range(0, shortest_dataset):
                plot_p1.append(converted_binary_block1[i])
                plot_p2.append(converted_binary_block2[i])
                plot_wavelengths.append(laser_wavelengths[i] * 1000000000.0)

            p = Process(target=generate_plots, args=(plot_wavelengths, [plot_p1, plot_p2], filename + "_reverse_", fileTime))
            p.start()
            laser.read_error_and_clear_status()

        detector.set_sensor_autoranging("1")
        detector.set_sensor_power_range("1", detector.dict["detector_power_range"])
        detector.set_sensor_power_range("2", detector.dict["detector_power_range"])
        detector.set_sensor_power_unit("1", "0")
        detector.set_sensor_power_unit("2", "0")
        detector.set_detector_data_acquisition("lOGG", "STOP")
        laser.read_error_and_clear_status()
        detector.set_detector_incoming_trigger_response("IGN")
        detector.set_detector_output_trigger_timing("", "DIS")
        laser.set_laser_current_wavelength(laser.dict["laser_current_wavelength"])
        laser.close_port()
        detector.close_port()
        return return_value
