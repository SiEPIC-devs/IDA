# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/MMC_100/zero_xyz.py
# Compiled at: 2021-04-25 13:15:02
# Size of source mod 2**32: 524 bytes
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
stage.home_axis(3, 1)
stage.home_axis(2, 1)
stage.home_axis(1, 1)
stage.update_parameter("stage_inuse", "0")
