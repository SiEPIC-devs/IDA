# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/micronix_stage_zf.py
# Compiled at: 2022-07-01 13:45:17
# Size of source mod 2**32: 3636 bytes
import stage, math, sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


stage = stage.stage()
stage.open_port()

def zero_stage():
    stage.reload_parameters()
    stage.update_parameter("z_position", "0.0")
    print("Current z position: {}".format(stage.dict["z_position"]))


import traceback

def move_z_distance(distance):
    stage.reload_parameters()
    if int(stage.dict["stage_inuse"]) == 1:
        return 1
    stage.update_parameter("stage_inuse", "1")
    if int(stage.dict["automated_move_happened"]) == 1:
        x_measured_pos, y_measured_pos, z_measured_pos = stage.read_position()
        stage.update_parameter("real_x_position", str(float(x_measured_pos)))
        stage.update_parameter("real_y_position", str(float(y_measured_pos)))
        stage.update_parameter("real_z_position", str(float(z_measured_pos)))
    else:
        x_measured_pos = float(stage.dict["real_x_position"])
        y_measured_pos = float(stage.dict["real_y_position"])
        z_measured_pos = float(stage.dict["real_z_position"])
    try:
        if z_measured_pos + distance > float(stage.dict["max_z"]) or z_measured_pos + distance < float(stage.dict["min_z"]):
            print("stage move would be outside movement limits!!")
            stage.update_parameter("automated_move_happened", str(0))
            stage.update_parameter("stage_inuse", "0")
            return 1
        stage.move_z_axis(distance)
    except:
        print("stage move error!!")
        stage.update_parameter("automated_move_happened", str(1))
        stage.update_parameter("stage_inuse", "0")
        print(traceback.format_exc())
        return 1
        status = stage.status(3)
        while status == "0":
            status = stage.status(3)

        stage.update_parameter("z_position", float(stage.dict["z_position"]) + distance)
        stage.update_parameter("real_z_position", str(float(z_measured_pos) + distance))
        stage.update_parameter("automated_move_happened", str(0))
        stage.update_parameter("stage_inuse", "0")
        return 0


def fiber_rotation(angle):
    stage.reload_parameters()
    if int(stage.dict["stage_inuse"]) == 1:
        return 1
    stage.update_parameter("stage_inuse", "1")
    current_position = get_fr_position()
    new_position = float(stage.dict["fr_pivot_distance"]) * math.tan(math.radians(float(angle))) + float(stage.dict["fr_zero_position"])
    distance = round(new_position - current_position, 3)
    print(current_position)
    print(new_position)
    print(distance)
    try:
        stage.move_fr_axis(distance)
    except:
        print("stage move error!!")
        stage.update_parameter("stage_inuse", "0")
        return 1
    else:
        status = stage.status(4)
        while status == "0":
            status = stage.status(4)

        stage.update_parameter("fr_position", float(stage.dict["fr_position"]) + distance)
        stage.update_parameter("fr_angle", angle)
        stage.update_parameter("stage_inuse", "0")


def get_z_step():
    stage.reload_parameters()
    return float(stage.dict["step_size_z"])


def get_z_position():
    stage.reload_parameters()
    return float(stage.dict["z_position"])


def get_fr_position():
    stage.reload_parameters()
    return float(stage.dict["fr_position"])


def get_fr_angle():
    stage.reload_parameters()
    return float(stage.dict["fr_angle"])


def update_parameter(key, value):
    stage.reload_parameters()
    stage.update_parameter(key, value)


def check_inuse():
    stage.reload_parameters()
    return int(stage.dict["stage_inuse"])
