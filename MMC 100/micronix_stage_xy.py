# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/micronix_stage_xy.py
# Compiled at: 2022-07-01 13:27:34
# Size of source mod 2**32: 5431 bytes
import stage, sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


stage = stage.stage()
stage.open_port()

def zero_stage():
    stage.reload_parameters()
    stage.update_parameter("x_position", "0.0")
    stage.update_parameter("y_position", "0.0")
    stage.update_parameter("r_position", "0.0")
    print("Current x position: {}".format(stage.dict["x_position"]))
    print("Current y position: {}".format(stage.dict["y_position"]))
    print("Current r position: {}".format(stage.dict["r_position"]))


def move_x_distance(distance):
    stage.reload_parameters()
    if int(stage.dict["stage_inuse"]) == 1:
        print("in use")
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
        if x_measured_pos + distance > float(stage.dict["max_x"]) or x_measured_pos + distance < float(stage.dict["min_x"]):
            print("stage move would be outside movement limits!!")
            stage.update_parameter("automated_move_happened", str(0))
            stage.update_parameter("stage_inuse", "0")
            return 1
        stage.move_x_axis(distance)
    except:
        print("stage move error!!")
        stage.update_parameter("automated_move_happened", str(1))
        stage.update_parameter("stage_inuse", "0")
        return 1
        status = stage.status(1)
        while status == "0":
            status = stage.status(1)

        stage.update_parameter("x_position", float(stage.dict["x_position"]) + distance)
        stage.update_parameter("real_x_position", str(float(x_measured_pos) + distance))
        stage.update_parameter("automated_move_happened", str(0))
        stage.update_parameter("stage_inuse", "0")
        return 0


def move_y_distance(distance):
    stage.reload_parameters()
    if int(stage.dict["stage_inuse"]) == 1:
        print("in use")
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
        if y_measured_pos + distance > float(stage.dict["max_y"]) or y_measured_pos + distance < float(stage.dict["min_y"]):
            print("stage move would be outside movement limits!!")
            stage.update_parameter("automated_move_happened", str(0))
            stage.update_parameter("stage_inuse", "0")
            return 1
        stage.move_y_axis(distance)
    except:
        print("stage move error!!")
        stage.update_parameter("automated_move_happened", str(1))
        stage.update_parameter("stage_inuse", "0")
        return 1
        status = stage.status(2)
        while status == "0":
            status = stage.status(2)

        stage.update_parameter("y_position", float(stage.dict["y_position"]) + distance)
        stage.update_parameter("real_y_position", str(float(y_measured_pos) + distance))
        stage.update_parameter("automated_move_happened", str(0))
        stage.update_parameter("stage_inuse", "0")
        return 0


def chip_rotation(distance):
    stage.reload_parameters()
    if int(stage.dict["stage_inuse"]) == 1:
        print("in use")
        return 1
    stage.update_parameter("stage_inuse", "1")
    try:
        stage.move_cr_axis(distance)
    except:
        print("stage move error!!")
        stage.update_parameter("stage_inuse", "0")
        return 1
        status = stage.status(5)
        while status == "0":
            status = stage.status(5)

        stage.update_parameter("r_position", float(stage.dict["r_position"]) + distance)
        stage.update_parameter("stage_inuse", "0")
        return 0


def get_y_step():
    stage.reload_parameters()
    return float(stage.dict["step_size_y"])


def get_y_position():
    stage.reload_parameters()
    return float(stage.dict["y_position"])


def get_x_step():
    stage.reload_parameters()
    return float(stage.dict["step_size_x"])


def get_x_position():
    stage.reload_parameters()
    return float(stage.dict["x_position"])


def get_r_step():
    stage.reload_parameters()
    return float(stage.dict["step_size_cr"])


def get_r_position():
    stage.reload_parameters()
    return float(stage.dict["r_position"])


def update_parameter(key, value):
    stage.reload_parameters()
    stage.update_parameter(key, value)


def check_inuse():
    stage.reload_parameters()
    return int(stage.dict["stage_inuse"])
