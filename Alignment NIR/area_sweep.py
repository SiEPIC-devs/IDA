# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Alignment NIR/area_sweep.py
# Compiled at: 2023-02-14 23:33:11
# Size of source mod 2**32: 47581 bytes
import sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "MMC 100"))
import stage
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR Detector"))
import NIR_detector as detector
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "NIR laser"))
import laser_functions, time, datetime, numpy as np, time, pickle
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
stage_init = stage.stage()
while int(stage_init.dict["stage_inuse"]) == 1:
    stage_init.reload_parameters()

stage_init.update_parameter("stage_inuse", "1")
stage_init.open_port()
stage_init.update_parameter("stage_inuse", "0")
detector_init = detector.detector()
while int(detector_init.dict["detector_inuse"]) == 1:
    detector_init.reload_parameters()

class alignment:

    def __init__(self):
        global detector_init
        global stage_init
        self.stage = stage_init
        self.detector = detector_init
        alignment_parameters = [
         'detector_chn_align', 
         'step_away_x_align', 
         'step_away_y_align', 
         'step_size_x_during_align', 
         'step_size_y_during_align']
        default_values = [
         "0"] * len(alignment_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "Alignment NIR", "Alignment"))
        except:
            self.dict = dict(zip(alignment_parameters, default_values))
            self.save_obj(self.dict, "Alignment")

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
            self.save_obj(self.dict, os.path.join(main_path, "Alignment NIR", "Alignment"))
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
        self.dict = self.load_obj(os.path.join(main_path, "Alignment NIR", "Alignment"))

    def run_area_sweep(self, detector_chn, step_away_x, step_away_y, step_size_x_during_sweep, step_size_y_during_sweep, filter_garbage=True):
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        currentmax = -200
        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        step_number_x = step_away_x * 2 + 1
        step_number_y = step_away_y * 2 + 1
        samples_read = int(step_number_x * step_number_y)
        print("Computed Samples: " + str(samples_read))
        print("Moving fiber array to starting position")
        distance_x_to_move = step_away_x * step_size_x_during_sweep
        distance_covered_x = 2 * distance_x_to_move
        print("Moving fiber array " + str(distance_x_to_move) + " um in the -x direction")
        current = float(self.stage.dict["x_position"])
        self.stage.move_x_axis(distance_x_to_move * -1)
        status = self.stage.status(1)
        while status == "0":
            status = self.stage.status(1)

        current += distance_x_to_move * -1
        self.stage.update_parameter("x_position", str(current))
        distance_y_to_move = step_away_y * step_size_y_during_sweep
        distance_covered_y = 2 * distance_y_to_move
        print("Moving fiber array " + str(distance_y_to_move) + " um in the +y direction")
        current = float(self.stage.dict["y_position"])
        self.stage.move_y_axis(distance_y_to_move)
        status = self.stage.status(2)
        while status == "0":
            status = self.stage.status(2)

        current += distance_y_to_move
        self.stage.update_parameter("y_position", str(current))
        size = (
         step_number_y, step_number_x)
        dataArray = np.zeros(size)
        xcount = 0
        ycount = 0
        start = time.time()
        while ycount < step_number_y:
            while xcount >= 0 and xcount < step_number_x:
                time.sleep(0.5)
                power_error_count = 0
                while True:
                    try:
                        power_read = self.detector.detector_read_power(detector_chn)
                        if power_read > 0:
                            print("Detector power error!!")
                            power_error_count += 1
                            if power_error_count > 2:
                                break
                            continue
                        break
                    except:
                        print("Detector read error!!")
                        time.sleep(0.5)

                if power_read > currentmax:
                    currentmax = power_read
                dataArray[(ycount, xcount)] = power_read
                xcount += (-1) ** ycount
                if xcount >= 0 and xcount < step_number_x:
                    distance = step_size_x_during_sweep * (-1) ** ycount
                    current = float(self.stage.dict["x_position"])
                    self.stage.move_x_axis(distance)
                    status = self.stage.status(1)
                    while status == "0":
                        status = self.stage.status(1)

                    current += distance
                    self.stage.update_parameter("x_position", str(current))

            xcount += (-1) ** (ycount + 1)
            ycount += 1
            if ycount < step_number_y:
                current = float(self.stage.dict["y_position"])
                self.stage.move_y_axis(step_size_y_during_sweep * -1)
                status = self.stage.status(2)
                while status == "0":
                    status = self.stage.status(2)

                current += step_size_y_during_sweep * -1
                self.stage.update_parameter("y_position", str(current))
                if ycount == 1:
                    temp = time.time()
                    total_time = (temp - start) * (step_number_y - 1)
                    print("{} remain in sweep.".format(str(datetime.timedelta(seconds=total_time))))

        end = time.time()
        print("Sweep completed in {} seconds".format(end - start))
        print(dataArray)
        np.savetxt(("./res/Heat_Map_{}.txt".format(fileTime)), dataArray, delimiter=",")
        fig = plt.figure(figsize=(44, 44), dpi=10)
        heat_map = plt.imshow(dataArray, origin="upper", cmap="gist_heat", interpolation="kaiser", extent=[-step_number_x / 2.0, step_number_x / 2.0, -step_number_y / 2.0, step_number_y / 2.0])
        plt.title("Area Scan", fontsize=100)
        plt.grid(color="r", linestyle="--", linewidth=0.5)
        plt.xticks(fontsize=64, rotation=0)
        plt.yticks(fontsize=64, rotation=0)
        divider = make_axes_locatable(plt.gca())
        cax = divider.append_axes("right", "5%", pad="3%")
        plt.colorbar(heat_map, cax=cax)
        plt.yticks(fontsize=64, rotation=0)
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        current_x = step_away_x * step_size_x_during_sweep + float(self.stage.dict["x_position"])
        current_y = -1 * step_away_y * step_size_y_during_sweep + float(self.stage.dict["y_position"])
        plt.savefig(os.path.join(main_path, "Plot", "./res/PlotHeatMap_plotzero_" + str(current_x) + "_" + str(current_y) + "_distance_" + str(distance_covered_x) + "_" + str(distance_covered_y) + "_" + fileTime + ".png"))
        max_coordinates = np.unravel_index(dataArray.argmax(), dataArray.shape)
        y_coordinate_max, x_coordinate_max = max_coordinates
        y_coordinate_max = -1 * y_coordinate_max
        x_coordinate_max -= step_away_x
        y_coordinate_max += step_away_y
        x_len = x_coordinate_max * step_size_x_during_sweep
        y_len = y_coordinate_max * step_size_y_during_sweep
        x_to_move = x_len - step_away_x * step_size_x_during_sweep
        y_to_move = y_len - -1 * step_away_y * step_size_y_during_sweep
        print("You need to move " + str(x_to_move) + " um in x")
        print("You need to move " + str(y_to_move) + " um in y")
        self.stage.update_parameter("x_position", str(current_x))
        self.stage.update_parameter("y_position", str(current_y))
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return 0

    def run_area_sweep_trigger(self, detector_chn, step_away_x, step_away_y, step_size_x_during_sweep, step_size_y_during_sweep, filter_garbage=True):
        stage_stabilization_wait = 0.03
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        currentmax = -200
        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        step_number_x = step_away_x * 2 + 1
        step_number_y = step_away_y * 2 + 1
        samples_read = int(step_number_x * step_number_y)
        print("Computed Samples: " + str(samples_read))
        averaging_time = self.detector.dict["detector_averaging_time"]
        averaging_time = averaging_time.split("ms")
        averaging_time = float(averaging_time[0]) / 1000
        laser_functions.setup_point_recording(samples_read, averaging_time, 0)
        print("Moving fiber array to starting position")
        distance_x_to_move = step_away_x * step_size_x_during_sweep
        distance_covered_x = 2 * distance_x_to_move
        print("Moving fiber array " + str(distance_x_to_move) + " um in the -x direction")
        current = float(self.stage.dict["x_position"])
        self.stage.move_x_axis(distance_x_to_move * -1)
        status = self.stage.status(1)
        self.stage.wait_for_trigger(self.stage.X_AXIS, 2)
        while self.stage.wait_for_trigger(self.stage.X_AXIS, stage_stabilization_wait) != -1:
            pass

        current += distance_x_to_move * -1
        self.stage.update_parameter("x_position", str(current))
        distance_y_to_move = step_away_y * step_size_y_during_sweep
        distance_covered_y = 2 * distance_y_to_move
        print("Moving fiber array " + str(distance_y_to_move) + " um in the +y direction")
        current = float(self.stage.dict["y_position"])
        self.stage.move_y_axis(distance_y_to_move)
        self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
        while self.stage.wait_for_trigger(self.stage.Y_AXIS, stage_stabilization_wait) != -1:
            pass

        current += distance_y_to_move
        self.stage.update_parameter("y_position", str(current))
        size = (
         step_number_y, step_number_x)
        dataArray = np.zeros(size)
        xcount = 0
        ycount = 0
        start = time.time()
        while ycount < step_number_y:
            while xcount >= 0 and xcount < step_number_x:
                time.sleep(averaging_time * 2)
                laser_functions.trigger_laser()
                time.sleep(averaging_time * 2)
                xcount += (-1) ** ycount
                if xcount >= 0:
                    if xcount < step_number_x:
                        distance = step_size_x_during_sweep * (-1) ** ycount
                        current = float(self.stage.dict["x_position"])
                        self.stage.move_x_axis(distance)
                        if self.stage.wait_for_trigger(self.stage.X_AXIS, 2) == -1:
                            print("move timeout error!!")
                    while self.stage.wait_for_trigger(self.stage.X_AXIS, stage_stabilization_wait) != -1:
                        pass

                    current += distance
                    self.stage.update_parameter("x_position", str(current))

            xcount += (-1) ** (ycount + 1)
            ycount += 1
            if ycount < step_number_y:
                current = float(self.stage.dict["y_position"])
                self.stage.move_y_axis(step_size_y_during_sweep * -1)
                self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
                while self.stage.wait_for_trigger(self.stage.Y_AXIS, stage_stabilization_wait) != -1:
                    pass

                current += step_size_y_during_sweep * -1
                self.stage.update_parameter("y_position", str(current))

        end = time.time()
        print("Sweep completed in {} seconds".format(end - start))
        data = laser_functions.read_point_recording(detector_chn, samples_read)
        laser_functions.return_laser_to_normal()
        samplecount_x = 0
        samplecount_y = 0
        stepdirection = 1
        index = 0
        while 1:
            if stepdirection == 1:
                while samplecount_x <= step_number_x - 1 and index < len(data):
                    power_value = data[index]
                    dataArray[(samplecount_y, samplecount_x)] = power_value
                    index += 1
                    samplecount_x += stepdirection

                samplecount_x -= 1
            else:
                while samplecount_x >= 0 and index < len(data):
                    power_value = data[index]
                    dataArray[(samplecount_y, samplecount_x)] = power_value
                    index += 1
                    samplecount_x += stepdirection

                samplecount_x = 0
            samplecount_y += 1
            stepdirection = stepdirection * -1
            if index == len(data):
                break

        print(index)
        np.savetxt(("./res/Heat_Map_{}.txt".format(fileTime)), dataArray, delimiter=",")
        fig = plt.figure(figsize=(44, 44), dpi=10)
        heat_map = plt.imshow(dataArray, origin="upper", cmap="gist_heat", interpolation="kaiser", extent=[-step_number_x / 2.0, step_number_x / 2.0, -step_number_y / 2.0, step_number_y / 2.0])
        plt.title("Area Scan", fontsize=100)
        plt.grid(color="r", linestyle="--", linewidth=0.5)
        plt.xticks(fontsize=64, rotation=0)
        plt.yticks(fontsize=64, rotation=0)
        divider = make_axes_locatable(plt.gca())
        cax = divider.append_axes("right", "5%", pad="3%")
        plt.colorbar(heat_map, cax=cax)
        plt.yticks(fontsize=64, rotation=0)
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        current_x = float(self.stage.dict["x_position"])
        current_y = float(self.stage.dict["y_position"])
        plt.savefig(os.path.join(main_path, "Plot", "./res/PlotHeatMap_plotzero_" + str(current_x) + "_" + str(current_y) + "_distance_" + str(distance_covered_x) + "_" + str(distance_covered_y) + "_" + fileTime + ".png"))
        max_coordinates = np.unravel_index(dataArray.argmax(), dataArray.shape)
        y_coordinate_max, x_coordinate_max = max_coordinates
        y_coordinate_max = -1 * y_coordinate_max
        x_coordinate_max -= step_away_x
        y_coordinate_max += step_away_y
        x_len = x_coordinate_max * step_size_x_during_sweep
        y_len = y_coordinate_max * step_size_y_during_sweep
        x_to_move = x_len - step_away_x * step_size_x_during_sweep
        y_to_move = y_len - -1 * step_away_y * step_size_y_during_sweep
        print("You need to move " + str(x_to_move) + " um in x")
        print("You need to move " + str(y_to_move) + " um in y")
        self.stage.update_parameter("x_position", str(current_x))
        self.stage.update_parameter("y_position", str(current_y))
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return [x_to_move, y_to_move]

    def run_area_sweep_trigger_old(self, detector_chn, step_away_x, step_away_y, step_size_x_during_sweep, step_size_y_during_sweep, filter_garbage=True):
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        currentmax = -200
        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
        step_number_x = step_away_x * 2 + 1
        step_number_y = step_away_y * 2 + 1
        samples_read = int(step_number_x * step_number_y)
        print("Computed Samples: " + str(samples_read))
        averaging_time = self.detector.dict["detector_averaging_time"]
        averaging_time = averaging_time.split("ms")
        averaging_time = float(averaging_time[0]) / 1000
        laser_functions.setup_point_recording(samples_read, averaging_time)
        print("Moving fiber array to starting position")
        distance_x_to_move = step_away_x * step_size_x_during_sweep
        distance_covered_x = 2 * distance_x_to_move
        print("Moving fiber array " + str(distance_x_to_move) + " um in the -x direction")
        current = float(self.stage.dict["x_position"])
        self.stage.move_x_axis(distance_x_to_move * -1)
        status = self.stage.status(1)
        while status == "0":
            status = self.stage.status(1)

        current += distance_x_to_move * -1
        self.stage.update_parameter("x_position", str(current))
        distance_y_to_move = step_away_y * step_size_y_during_sweep
        distance_covered_y = 2 * distance_y_to_move
        print("Moving fiber array " + str(distance_y_to_move) + " um in the +y direction")
        current = float(self.stage.dict["y_position"])
        self.stage.move_y_axis(distance_y_to_move)
        status = self.stage.status(2)
        while status == "0":
            status = self.stage.status(2)

        current += distance_y_to_move
        self.stage.update_parameter("y_position", str(current))
        size = (
         step_number_y, step_number_x)
        ycount = 0
        start = time.time()
        count_test = 0
        while ycount < step_number_y:
            count_test += 1
            time.sleep(averaging_time)
            laser_functions.trigger_laser()
            time.sleep(averaging_time)
            if (ycount + 1) % 2 == 0:
                direction = -1
            else:
                direction = 1
            trigger_count = 0
            while trigger_count < step_number_x:
                current = float(self.stage.dict["x_position"]) + step_size_x_during_sweep * direction
                self.stage.move_x_axis(distance_x_to_move * direction)
                self.stage.wait_for_trigger(self.stage.X_AXIS, 2)
                self.stage.update_parameter("x_position", str(current))
                time.sleep(averaging_time)
                laser_functions.trigger_laser()
                time.sleep(averaging_time)
                trigger_count += 1
                count_test += 1

            ycount += 1
            if ycount < step_number_y:
                current = float(self.stage.dict["y_position"]) + step_size_y_during_sweep * -1
                self.stage.move_y_axis(step_size_y_during_sweep * -1)
                self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
                self.stage.update_parameter("y_position", str(current))

        print("Actual triggers:" + str(count_test))
        data = laser_functions.read_point_recording(detector_chn, samples_read - step_number_y)
        laser_functions.return_laser_to_normal()
        end = time.time()
        print("Sweep completed in {} seconds".format(end - start))
        print(len(data))
        row = []
        samplecount_x = 0
        samplecount_y = 0
        size = (step_number_y, step_number_x)
        dataArray = np.zeros(size)
        for power_read in data:
            dataArray[(samplecount_y, samplecount_x)] = power_read
            samplecount_x += 1
            if samplecount_x > step_number_x * 2:
                samplecount_x = 0
                samplecount_y += 1

        print("Time " + str(time.time() - start))
        np.savetxt(("./res/Heat_Map_{}.txt".format(fileTime)), dataArray, delimiter=",")
        fig = plt.figure(figsize=(44, 44), dpi=10)
        heat_map = plt.imshow(dataArray, origin="upper", cmap="gist_heat", interpolation="kaiser", extent=[-step_number_x / 2.0, step_number_x / 2.0, -step_number_y / 2.0, step_number_y / 2.0])
        plt.title("Area Scan", fontsize=100)
        plt.grid(color="r", linestyle="--", linewidth=0.5)
        plt.xticks(fontsize=64, rotation=0)
        plt.yticks(fontsize=64, rotation=0)
        divider = make_axes_locatable(plt.gca())
        cax = divider.append_axes("right", "5%", pad="3%")
        plt.colorbar(heat_map, cax=cax)
        plt.yticks(fontsize=64, rotation=0)
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        current_x = step_away_x * step_size_x_during_sweep + float(self.stage.dict["x_position"])
        current_y = -1 * step_away_y * step_size_y_during_sweep + float(self.stage.dict["y_position"])
        plt.savefig(os.path.join(main_path, "Plot", "./res/PlotHeatMap_plotzero_" + str(current_x) + "_" + str(current_y) + "_distance_" + str(distance_covered_x) + "_" + str(distance_covered_y) + "_" + fileTime + ".png"))
        max_coordinates = np.unravel_index(dataArray.argmax(), dataArray.shape)
        y_coordinate_max, x_coordinate_max = max_coordinates
        y_coordinate_max = -1 * y_coordinate_max
        x_coordinate_max -= step_away_x
        y_coordinate_max += step_away_y
        x_len = x_coordinate_max * step_size_x_during_sweep
        y_len = y_coordinate_max * step_size_y_during_sweep
        x_to_move = x_len - step_away_x * step_size_x_during_sweep
        y_to_move = y_len - -1 * step_away_y * step_size_y_during_sweep
        print("You need to move " + str(x_to_move) + " um in x")
        print("You need to move " + str(y_to_move) + " um in y")
        self.stage.update_parameter("x_position", str(current_x))
        self.stage.update_parameter("y_position", str(current_y))
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return 0

    def align_to_device_gradient(self, detector_chn, step_away_x, step_away_y, step_size_x_during_sweep, step_size_y_during_sweep):
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        y_step_size = float(step_size_y_during_sweep)
        x_step_size = float(step_size_x_during_sweep)
        max_distance_x = float(step_away_x) * step_size_x_during_sweep
        max_distance_y = float(step_away_y) * step_size_y_during_sweep
        stop_step_size = 0.25
        previous_power = self.detector.detector_read_power(detector_chn)
        while abs(y_step_size) > stop_step_size or abs(x_step_size) > stop_step_size:
            count = 0
            while True:
                if self.find_slope(detector_chn, "y", 5, y_step_size / 5) < 0:
                    if self.find_slope(detector_chn, "y", 5, y_step_size / 5) > 0:
                        print("false max y")
                        continue
                    while True:
                        if self.find_slope(detector_chn, "y", 5, y_step_size * -1 / 10) < 0:
                            if self.find_slope(detector_chn, "y", 5, y_step_size * -1 / 10) > 0:
                                print("false max move back y")
                                continue
                            break
                        count = count - 1
                        print("moving y back")

                    break
                count = count + 1
                print("moving y forward")

            if count < 0:
                y_step_size = y_step_size * -1
            count = 0
            y_step_size = 1 * y_step_size / 2
            while True:
                if self.find_slope(detector_chn, "x", 5, x_step_size / 5) < 0:
                    if self.find_slope(detector_chn, "x", 5, x_step_size / 5) > 0:
                        print("false max x")
                        continue
                    while True:
                        if self.find_slope(detector_chn, "x", 5, x_step_size * -1 / 10) < 0:
                            if self.find_slope(detector_chn, "x", 5, x_step_size * -1 / 10) > 0:
                                print("false max move back x")
                                break
                            break
                        count = count - 1
                        print("moving x back")

                    break
                count = count + 1
                print("moving x forward")

            if count < 0:
                x_step_size = x_step_size * -1
            x_step_size = 1 * x_step_size / 2

        print("----------done alignment------------")
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return 0

    def align_to_device(self):
        self.reload_parameters()
        detector_chn = int(self.dict["detector_chn_align"])
        step_away_x = int(self.dict["step_away_x_align"])
        step_away_y = int(self.dict["step_away_y_align"])
        step_size_x_during_sweep = float(self.dict["step_size_x_during_align"])
        step_size_y_during_sweep = float(self.dict["step_size_y_during_align"])
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        y_step_size = float(step_size_y_during_sweep)
        x_step_size = float(step_size_x_during_sweep)
        max_distance_x = float(step_away_x) * step_size_x_during_sweep
        max_distance_y = float(step_away_y) * step_size_y_during_sweep
        stop_step_size = 0.25
        print("starting alignment")
        start = time.time()
        while abs(y_step_size) > stop_step_size or abs(x_step_size) > stop_step_size:
            if abs(y_step_size) > stop_step_size:
                try:
                    self.stage.move_y_axis(-step_away_y * y_step_size)
                    current = float(self.stage.dict["y_position"])
                    current = current - step_away_y * y_step_size
                    status = self.stage.status(2)
                    while status == "0":
                        status = self.stage.status(2)

                    self.stage.update_parameter("y_position", current)
                    self.find_max_on_line(detector_chn, "y", step_away_y * 2, y_step_size)
                except Exception as e:
                    try:
                        print(e)
                    finally:
                        e = None
                        del e

            if abs(x_step_size) > stop_step_size:
                try:
                    self.stage.move_x_axis(-step_away_x * x_step_size)
                    current = float(self.stage.dict["x_position"])
                    current = current - step_away_x * x_step_size
                    status = self.stage.status(1)
                    while status == "0":
                        status = self.stage.status(1)

                    self.stage.update_parameter("x_position", current)
                    self.find_max_on_line(detector_chn, "x", step_away_x * 2, x_step_size)
                except Exception as e:
                    try:
                        print(e)
                    finally:
                        e = None
                        del e

            y_step_size = y_step_size / 2
            x_step_size = x_step_size / 2

        print("alignment done")
        print(time.time() - start)
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return 0

    def align_to_device_trigger(self):
        stage_stabilization_wait = 0.03
        self.reload_parameters()
        detector_chn = int(self.dict["detector_chn_align"])
        step_away_x = int(self.dict["step_away_x_align"])
        step_away_y = int(self.dict["step_away_y_align"])
        step_size_x_during_sweep = float(self.dict["step_size_x_during_align"])
        step_size_y_during_sweep = float(self.dict["step_size_y_during_align"])
        self.stage.reload_parameters()
        self.detector.reload_parameters()
        if int(self.stage.dict["stage_inuse"]) == 1:
            print("stage in use")
            return 1
        if int(self.detector.dict["detector_init"]) == 0:
            print("no detector init")
            return 1
        self.stage.update_parameter("stage_inuse", "1")
        while int(self.detector.dict["detector_inuse"]) == 1:
            self.detector.reload_parameters()
            continue

        self.detector.update_parameter("detector_inuse", "1")
        self.detector.open_port()
        y_step_size = float(step_size_y_during_sweep)
        x_step_size = float(step_size_x_during_sweep)
        max_distance_x = float(step_away_x) * step_size_x_during_sweep
        max_distance_y = float(step_away_y) * step_size_y_during_sweep
        stop_step_size = 0.25
        print("starting alignment")
        start = time.time()
        while abs(y_step_size) > stop_step_size or abs(x_step_size) > stop_step_size:
            if abs(y_step_size) > stop_step_size:
                try:
                    self.stage.move_y_axis(-step_away_y * y_step_size)
                    self.stage.reload_parameters()
                    current = float(self.stage.dict["y_position"])
                    current = current - step_away_y * y_step_size
                    self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
                    while self.stage.wait_for_trigger(self.stage.Y_AXIS, stage_stabilization_wait) != -1:
                        pass

                    self.stage.update_parameter("y_position", current)
                    self.find_max_on_line_trigger(detector_chn, "y", step_away_y * 2, y_step_size)
                except Exception as e:
                    try:
                        print(e)
                    finally:
                        e = None
                        del e

            if abs(x_step_size) > stop_step_size:
                try:
                    self.stage.move_x_axis(-step_away_x * x_step_size)
                    self.stage.reload_parameters()
                    current = float(self.stage.dict["x_position"])
                    current = current - step_away_x * x_step_size
                    self.stage.wait_for_trigger(self.stage.X_AXIS, 2)
                    while self.stage.wait_for_trigger(self.stage.X_AXIS, stage_stabilization_wait) != -1:
                        pass

                    self.stage.update_parameter("x_position", current)
                    self.find_max_on_line_trigger(detector_chn, "x", step_away_x * 2, x_step_size)
                except Exception as e:
                    try:
                        print(e)
                    finally:
                        e = None
                        del e

            y_step_size = y_step_size / 2
            x_step_size = x_step_size / 2

        print("alignment done")
        print(time.time() - start)
        self.detector.close_port()
        self.stage.update_parameter("stage_inuse", "0")
        self.detector.update_parameter("detector_inuse", "0")
        return 0

    def find_slope(self, detector, axis, test_points, step_size):
        powers = []
        for i in range(0, test_points):
            if axis == "x":
                self.stage.move_x_axis(step_size)
                self.stage.reload_parameters()
                current = float(self.stage.dict["x_position"])
                current = current + step_size
                status = self.stage.status(1)
                while status == "0":
                    status = self.stage.status(1)

                self.stage.update_parameter("x_position", current)
            else:
                self.stage.move_y_axis(step_size)
                self.stage.reload_parameters()
                current = float(self.stage.dict["y_position"])
                current = current + step_size
                status = self.stage.status(2)
                while status == "0":
                    status = self.stage.status(2)

                self.stage.update_parameter("y_position", current)
            current_power = self.detector.detector_read_power(detector)
            powers.append(current_power)

        dpower = np.diff(powers) / step_size
        print(powers)
        print(dpower)
        print(np.mean(dpower))
        return np.mean(dpower)

    def find_max_on_line(self, detector, axis, test_points, step_size):
        powers = []
        if axis == "x":
            current = float(self.stage.dict["x_position"])
        else:
            current = float(self.stage.dict["y_position"])
        for i in range(0, test_points):
            if axis == "x":
                self.stage.move_x_axis(step_size)
                current = current + step_size
                status = self.stage.status(1)
                while status == "0":
                    status = self.stage.status(1)

                self.stage.update_parameter("x_position", current)
            else:
                self.stage.move_y_axis(step_size)
                current = current + step_size
                status = self.stage.status(2)
                while status == "0":
                    status = self.stage.status(2)

                self.stage.update_parameter("y_position", current)
            current_power = self.detector.detector_read_power(detector)
            powers.append(current_power)

        max_index = powers.index(max(powers))
        move_distance = -step_size * (test_points - max_index)
        if axis == "x":
            current = current + move_distance
            self.stage.move_x_axis(move_distance)
            while status == "0":
                status = self.stage.status(1)

            self.stage.update_parameter("x_position", current)
        else:
            current = current + move_distance
            self.stage.move_y_axis(move_distance)
            while status == "0":
                status = self.stage.status(1)

            self.stage.update_parameter("y_position", current)

    def find_max_on_line_trigger(self, detector, axis, test_points, step_size):
        powers = []
        averaging_time = self.detector.dict["detector_averaging_time"]
        averaging_time = averaging_time.split("ms")
        averaging_time = float(averaging_time[0]) / 1000
        stage_stabilization_wait = 0.03
        if axis == "x":
            self.stage.reload_parameters()
            current = float(self.stage.dict["x_position"])
        else:
            self.stage.reload_parameters()
            current = float(self.stage.dict["y_position"])
        for i in range(0, test_points):
            if axis == "x":
                self.stage.move_x_axis(step_size)
                current = current + step_size
                self.stage.wait_for_trigger(self.stage.X_AXIS, 2)
                while self.stage.wait_for_trigger(self.stage.X_AXIS, stage_stabilization_wait) != -1:
                    pass

                self.stage.update_parameter("x_position", current)
            else:
                self.stage.move_y_axis(step_size)
                current = current + step_size
                self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
                while self.stage.wait_for_trigger(self.stage.Y_AXIS, stage_stabilization_wait) != -1:
                    pass

                self.stage.update_parameter("y_position", current)
            time.sleep(averaging_time * 2)
            current_power = self.detector.detector_read_power(detector)
            time.sleep(averaging_time * 2)
            powers.append(current_power)

        max_index = powers.index(max(powers))
        move_distance = -step_size * (test_points - max_index)
        if axis == "x":
            current = current + move_distance
            self.stage.move_x_axis(move_distance)
            self.stage.wait_for_trigger(self.stage.X_AXIS, 2)
            while self.stage.wait_for_trigger(self.stage.X_AXIS, stage_stabilization_wait) != -1:
                pass

            self.stage.update_parameter("x_position", current)
        else:
            current = current + move_distance
            self.stage.move_y_axis(move_distance)
            self.stage.wait_for_trigger(self.stage.Y_AXIS, 2)
            while self.stage.wait_for_trigger(self.stage.Y_AXIS, stage_stabilization_wait) != -1:
                pass

            self.stage.update_parameter("y_position", current)
