# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Camera/camera_init.py
# Compiled at: 2021-04-19 14:03:51
# Size of source mod 2**32: 874 bytes
import camera
camera = camera.camera()
camera.update_parameter("image_right_x", "400")
camera.update_parameter("image_bottom_y", "400")
camera.update_parameter("image_top_y", "0")
camera.update_parameter("image_left_x", "0")
camera.update_parameter("pixels_per_um_x", "7.9375")
camera.update_parameter("pixels_per_um_y", "7.9375")
camera.update_parameter("camera_gc_position_x", "245")
camera.update_parameter("camera_gc_position_y", "246")
camera.update_parameter("actual_gc_position_x", "0")
camera.update_parameter("actual_gc_position_y", "400")
