# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Camera/camera.py
# Compiled at: 2021-04-19 13:58:26
# Size of source mod 2**32: 2354 bytes
import pickle

class camera:

    def __init__(self):
        camera_parameters = [
         'image_right_x', 
         'image_bottom_y', 
         'image_top_y', 
         'image_left_x', 
         'pixels_per_um_x', 
         'pixels_per_um_y', 
         'camera_gc_position_x', 
         'camera_gc_position_y', 
         'actual_gc_position_x', 
         'actual_gc_position_y']
        default_values = [
         "0"] * len(camera_parameters)
        try:
            import os, sys
            cwd = os.getcwd()
            main_path = os.path.split(cwd)
            main_path = main_path[0]
            self.dict = self.load_obj(os.path.join(main_path, "Camera", "camera"))
        except:
            self.dict = dict(zip(camera_parameters, default_values))
            self.save_obj(self.dict, "camera")

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
            self.save_obj(self.dict, os.path.join(main_path, "Camera", "camera"))
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

    def camera_init(self):
        self.dict = self.load_obj("camera")
        self.update_parameter("camera_initilized", 1)
        return 0

    def reload_parameters(self):
        import os, sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        self.dict = self.load_obj(os.path.join(main_path, "Camera", "camera"))
