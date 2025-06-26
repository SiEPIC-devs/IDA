# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/zero_fiber_angle.py
# Compiled at: 2021-04-25 14:36:20
# Size of source mod 2**32: 632 bytes
import stage
stage = stage.stage()
stage.update_parameter("timeout", "0.30")
stage.update_parameter("baudrate", "38400")
stage.update_parameter("Stage_COM_port", "/dev/ttyUSB0")
stage.update_parameter("motor_velocity", "2000.0")
stage.open_port()
stage.emergency_stop()
stage.stage_init()
stage.stage_init_z()
stage.stage_init_fr()
stage.go_to_limit(3, 1)
stage.home_axis(4, 1)
stage.move_abs(4, -5.51)
stage.update_parameter("fr_position", "-5.51")
stage.update_parameter("fr_angle", "22")
stage.update_parameter("stage_inuse", "0")
