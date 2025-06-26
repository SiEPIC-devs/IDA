# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Plot/plot_gui.py
# Compiled at: 2023-02-15 01:51:16
# Size of source mod 2**32: 8715 bytes
from remi.gui import *
from remi import start, App
import os, shutil, glob, time, datetime, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]
sys.path.insert(1, os.path.join(main_path, "MMC 100"))
import micronix_stage_xy as stage_xy

class plot_gui(App):

    def __init__(self, *args, **kwargs):
        self.old_image = ""
        if "editing_mode" not in kwargs.keys():
            (super(plot_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        files_path = os.path.join("./res/", "*")
        files = sorted((glob.iglob(files_path)), key=(os.path.getctime), reverse=True)
        files_only = []
        for i in range(0, len(files)):
            if os.path.isdir(files[i]):
                continue
            files_only.append(files[i])

        files = files_only
        for i in range(2, len(files)):
            os.remove(files[i])

        image = files[0]
        image = image.split("/")
        if self.old_image != str(image[2]):
            time.sleep(2)
            self.old_image = str(image[2])
        else:
            return
            if "html" in image[2].split(".")[-1]:
                if self.image_object_present == True:
                    self.plot_container.remove_child(self.plot_container.children["plot_img"])
                    self.image_object_present = False
                else:
                    if self.html_object_present == False:
                        files_path = os.path.join("./res/liveplot/", "*")
                        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
                        files = sorted((glob.iglob(files_path)), key=(os.path.getctime), reverse=True)
                        for file in files:
                            os.remove(file)

                        self.html_file_name = "plot" + str(fileTime) + ".html"
                        shutil.copyfile("./res/" + image[2], "./res//liveplot/" + self.html_file_name)
                        plot_html = Widget(_type="iframe", width="100%", height="100%", margin="0px")
                        plot_html.attributes["src"] = "https://10.2.137.107/liveplot/" + self.html_file_name
                        plot_html.attr_editor_newclass = False
                        plot_html.attr_src = ""
                        plot_html.css_height = "435px"
                        plot_html.css_left = "5px"
                        plot_html.css_margin = "0px"
                        plot_html.css_position = "absolute"
                        plot_html.css_top = "5px"
                        plot_html.css_width = "435px"
                        plot_html.variable_name = "plot_img"
                        self.plot_container.append(plot_html, "html_obj")
                        self.html_object_present = True
                    else:
                        files_path = os.path.join("./res/liveplot/", "*")
                        fileTime = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d_%H-%M-%S")
                        files = sorted((glob.iglob(files_path)), key=(os.path.getctime), reverse=True)
                        for file in files:
                            os.remove(file)

                        self.html_file_name = "plot" + str(fileTime) + ".html"
                        shutil.copyfile("./res/" + image[2], "./res//liveplot/" + self.html_file_name)
                    try:
                        plot_html.attributes["src"] = "https://10.2.137.107/liveplot/" + self.html_file_name
                    except UnboundLocalError:
                        plot_html = Widget(_type="iframe", width="100%", height="100%", margin="0px")
                        plot_html.attributes["src"] = "https://10.2.137.107/liveplot/" + self.html_file_name
                        plot_html.attr_editor_newclass = False
                        plot_html.attr_src = ""
                        plot_html.css_height = "435px"
                        plot_html.css_left = "5px"
                        plot_html.css_margin = "0px"
                        plot_html.css_position = "absolute"
                        plot_html.css_top = "5px"
                        plot_html.css_width = "435px"
                        plot_html.variable_name = "plot_img"
                        self.plot_container.append(plot_html, "html_obj")
                        self.html_object_present = True

            else:
                if self.html_object_present == True:
                    self.plot_container.remove_child(self.plot_container.children["html_obj"])
                    self.html_object_present = False
                if self.image_object_present == False:
                    self.plot_container.append(self.image_object, "plot_img")
                    self.image_object_present = True
                self.plot_container.children["plot_img"].set_image("my_res:" + str(image[2]))

    def main(self):
        return plot_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        plot_container = Container()
        plot_container.attr_editor_newclass = False
        plot_container.css_height = "450px"
        plot_container.css_left = "0px"
        plot_container.css_margin = "0px"
        plot_container.css_position = "absolute"
        plot_container.css_top = "0px"
        plot_container.css_width = "450px"
        plot_container.variable_name = "plot_container"
        plot_img = Image()
        plot_img.attr_editor_newclass = False
        plot_img.attr_src = ""
        plot_img.css_height = "440px"
        plot_img.css_left = "5px"
        plot_img.css_margin = "0px"
        plot_img.css_position = "absolute"
        plot_img.css_top = "5px"
        plot_img.css_width = "440px"
        plot_img.variable_name = "plot_img"
        self.image_object = plot_img
        self.image_object_present = True
        self.html_object_present = False
        plot_container.append(plot_img, "plot_img")
        plot_container.children["plot_img"].onmousedown.do(self.onmousedown_plot_img)
        self.plot_container = plot_container
        return self.plot_container

    def onmousedown_plot_img(self, emitter, x, y):
        click_x = int(round(float(x), 0))
        click_y = int(round(float(y), 0))
        splitimagename = self.old_image.split("_")
        if "PlotHeatMap" == splitimagename[0]:
            if stage_xy.check_inuse() == 1:
                return
            plotzero_x = float(splitimagename[2])
            plotzero_y = float(splitimagename[3])
            plotdistance_x = float(splitimagename[5])
            plotdistance_y = float(splitimagename[6])
            xpos = float(stage_xy.get_x_position())
            ypos = float(stage_xy.get_y_position())
            PLOT_RIGHT_X = 371
            PLOT_BOTTOM_Y = 380
            PLOT_TOP_Y = 64
            PLOT_LEFT_X = 55
            if click_x < PLOT_LEFT_X:
                return
            if click_x > PLOT_RIGHT_X:
                return
            if click_y < PLOT_TOP_Y:
                return
            if click_y > PLOT_BOTTOM_Y:
                return
            distance_plot_orig_x = PLOT_RIGHT_X - click_x
            distance_plot_orig_y = PLOT_BOTTOM_Y - click_y
            pixel_um_x = plotdistance_x / (PLOT_RIGHT_X - PLOT_LEFT_X)
            pixel_um_y = plotdistance_y / (PLOT_BOTTOM_Y - PLOT_TOP_Y)
            stagexmov = round(-1.0 * distance_plot_orig_x * pixel_um_x + (plotzero_x - xpos), 1)
            stageymov = round(distance_plot_orig_y * pixel_um_y + (plotzero_y - ypos), 1)
            stage_xy.move_x_distance(stagexmov)
            stage_xy.move_y_distance(stageymov)


configuration = {
 'config_project_name': '"plot_gui"', 'config_address': '"0.0.0.0"', 'config_port': 9086, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(plot_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
