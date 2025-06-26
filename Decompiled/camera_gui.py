# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Camera/camera_gui.py
# Compiled at: 2023-02-14 23:45:11
# Size of source mod 2**32: 6100 bytes
from remi.gui import *
from remi import start, App
import camera, os, glob, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


sys.path.insert(1, os.path.join(main_path, "MMC 100"))
import micronix_stage_xy as stage_xy

class camera_gui(App):

    def __init__(self, *args, **kwargs):
        self.camera = camera.camera()
        if "editing_mode" not in kwargs.keys():
            (super(camera_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return camera_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        ip_address = "10.2.137.107"
        camera_container = Container()
        camera_container.attr_editor_newclass = False
        camera_container.css_font_size = "100%"
        camera_container.css_height = "450px"
        camera_container.css_left = "0px"
        camera_container.css_margin = "0px"
        camera_container.css_position = "absolute"
        camera_container.css_top = "0px"
        camera_container.css_width = "450px"
        camera_container.variable_name = "camera_container"
        camera_img = Widget(_type="iframe", width="100%", height="100%", margin="0px")
        camera_img.attr_editor_newclass = False
        camera_img.attributes["src"] = "https://" + ip_address + "/cameraformat/400x400.html"
        camera_img.css_height = "400px"
        camera_img.css_left = "25px"
        camera_img.css_margin = "0px"
        camera_img.css_position = "absolute"
        camera_img.css_top = "25px"
        camera_img.css_width = "400px"
        camera_img.variable_name = "camera_img"
        camera_container.append(camera_img, "camera_img")
        mouse_container = Container()
        mouse_container.attr_editor_newclass = False
        mouse_container.css_height = "400px"
        mouse_container.css_left = "25px"
        mouse_container.css_margin = "0px"
        mouse_container.css_position = "absolute"
        mouse_container.css_top = "25px"
        mouse_container.css_width = "400px"
        mouse_container.style["background"] = "none"
        mouse_container.variable_name = "mouse_container"
        camera_container.append(mouse_container, "mouse_container")
        camera_container.children["mouse_container"].onmousedown.do(self.onmousedown_camera_img)
        self.camera_container = camera_container
        return self.camera_container

    def onmousedown_camera_img(self, emitter, x, y):
        self.camera.reload_parameters()
        click_x = int(x)
        click_y = int(y)
        if stage_xy.check_inuse() == 1:
            return
        xpos = float(stage_xy.get_x_position())
        ypos = float(stage_xy.get_y_position())
        image_right_x = int(self.camera.dict["image_right_x"])
        image_bottom_y = int(self.camera.dict["image_bottom_y"])
        image_top_y = int(self.camera.dict["image_top_y"])
        image_left_x = int(self.camera.dict["image_left_x"])
        camera_gc_position_x = int(self.camera.dict["camera_gc_position_x"])
        camera_gc_position_y = int(self.camera.dict["camera_gc_position_y"])
        actual_gc_position_x = float(self.camera.dict["actual_gc_position_x"])
        actual_gc_position_y = float(self.camera.dict["actual_gc_position_y"])
        pixels_per_um_x = float(self.camera.dict["pixels_per_um_x"])
        pixels_per_um_y = float(self.camera.dict["pixels_per_um_y"])
        if click_x < image_left_x:
            return
        if click_x > image_right_x:
            return
        if click_y < image_top_y:
            return
        if click_y > image_bottom_y:
            return
        print("camera position: " + str(click_x) + "," + str(click_y))
        distance_plot_orig_x = camera_gc_position_x - click_x
        distance_plot_orig_y = camera_gc_position_y - click_y
        stagexmov = -round(distance_plot_orig_x * pixels_per_um_x - actual_gc_position_x, 1)
        stageymov = -round(distance_plot_orig_y * pixels_per_um_y - actual_gc_position_y, 1)
        print("stage move")
        print(-1 * stagexmov)
        print(-1 * stageymov)


configuration = {
 'config_project_name': '"camera_gui"', 'config_address': '"0.0.0.0"', 'config_port': 9088, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(camera_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]),
      update_interval=0.1)
