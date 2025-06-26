# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/File Import/files_gui.py
# Compiled at: 2023-02-14 23:45:16
# Size of source mod 2**32: 22753 bytes
from remi.gui import *
from remi import start, App
import os, sys, time
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


import glob
sys.path.insert(1, os.path.join(main_path, "MMC 100"))
import stage, coordinates, shutil
try:
    os.remove("./database_ramdisk/transformed.json")
except:
    pass

stage_init = stage.stage()
while int(stage_init.dict["stage_inuse"]) == 1:
    stage_init.reload_parameters()

stage_init.update_parameter("stage_inuse", "1")
stage_init.open_port()
stage_init.update_parameter("stage_inuse", "0")

class files(App):

    def __init__(self, *args, **kwargs):
        global stage_init
        self.stage = stage_init
        if "editing_mode" not in kwargs.keys():
            (super(files, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return files.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        file_container = Container()
        file_container.attr_editor_newclass = False
        file_container.css_height = "435px"
        file_container.css_left = "0px"
        file_container.css_margin = "0px"
        file_container.css_position = "absolute"
        file_container.css_top = "0px"
        file_container.css_width = "350px"
        file_container.variable_name = "file_container"
        uploader = FileUploader()
        uploader.attr_editor_newclass = False
        uploader.css_height = "20px"
        uploader.css_left = "20px"
        uploader.css_margin = "0px"
        uploader.css_position = "absolute"
        uploader.css_top = "20px"
        uploader.css_width = "310px"
        uploader.multiple_selection_allowed = False
        uploader.savepath = "./res/"
        uploader.variable_name = "uploader"
        file_container.append(uploader, "uploader")
        first_mark = DropDown()
        first_mark.attr_editor_newclass = False
        first_mark.css_height = "30px"
        first_mark.css_left = "20px"
        first_mark.css_margin = "0px"
        first_mark.css_position = "absolute"
        first_mark.css_top = "60.0px"
        first_mark.css_width = "150px"
        first_mark.variable_name = "first_mark"
        file_container.append(first_mark, "first_mark")
        second_mark = DropDown()
        second_mark.attr_editor_newclass = False
        second_mark.css_height = "30px"
        second_mark.css_left = "20px"
        second_mark.css_margin = "0px"
        second_mark.css_position = "absolute"
        second_mark.css_top = "115px"
        second_mark.css_width = "150px"
        second_mark.variable_name = "second_mark"
        file_container.append(second_mark, "second_mark")
        third_mark = DropDown()
        third_mark.attr_editor_newclass = False
        third_mark.css_height = "30px"
        third_mark.css_left = "20px"
        third_mark.css_margin = "0px"
        third_mark.css_position = "absolute"
        third_mark.css_top = "170px"
        third_mark.css_width = "150px"
        third_mark.variable_name = "third_mark"
        file_container.append(third_mark, "third_mark")
        cord1_x = Label()
        cord1_x.attr_editor_newclass = False
        cord1_x.css_font_size = "100%"
        cord1_x.css_height = "20px"
        cord1_x.css_left = "180.0px"
        cord1_x.css_margin = "0px"
        cord1_x.css_position = "absolute"
        cord1_x.css_right = "2px"
        cord1_x.css_top = "60px"
        cord1_x.css_width = "100px"
        cord1_x.text = "X:"
        cord1_x.variable_name = "cord1_x"
        file_container.append(cord1_x, "cord1_x")
        cord1_y = Label()
        cord1_y.attr_editor_newclass = False
        cord1_y.css_font_size = "100%"
        cord1_y.css_height = "20px"
        cord1_y.css_left = "180px"
        cord1_y.css_margin = "0px"
        cord1_y.css_position = "absolute"
        cord1_y.css_top = "75px"
        cord1_y.css_width = "100px"
        cord1_y.text = "Y:"
        cord1_y.variable_name = "cord1_y"
        file_container.append(cord1_y, "cord1_y")
        cord1_z = Label()
        cord1_z.attr_editor_newclass = False
        cord1_z.css_font_size = "100%"
        cord1_z.css_height = "20px"
        cord1_z.css_left = "180px"
        cord1_z.css_margin = "0px"
        cord1_z.css_position = "absolute"
        cord1_z.css_top = "90px"
        cord1_z.css_width = "100px"
        cord1_z.text = "Z:"
        cord1_z.variable_name = "cord1_z"
        file_container.append(cord1_z, "cord1_z")
        cord2_x = Label()
        cord2_x.attr_editor_newclass = False
        cord2_x.css_font_size = "100%"
        cord2_x.css_height = "20px"
        cord2_x.css_left = "180px"
        cord2_x.css_margin = "0px"
        cord2_x.css_position = "absolute"
        cord2_x.css_top = "115px"
        cord2_x.css_width = "100px"
        cord2_x.text = "X:"
        cord2_x.variable_name = "cord2_x"
        file_container.append(cord2_x, "cord2_x")
        cord2_y = Label()
        cord2_y.attr_editor_newclass = False
        cord2_y.css_font_size = "100%"
        cord2_y.css_height = "20px"
        cord2_y.css_left = "180px"
        cord2_y.css_margin = "0px"
        cord2_y.css_position = "absolute"
        cord2_y.css_top = "130px"
        cord2_y.css_width = "100px"
        cord2_y.text = "Y:"
        cord2_y.variable_name = "cord2_y"
        file_container.append(cord2_y, "cord2_y")
        cord2_z = Label()
        cord2_z.attr_editor_newclass = False
        cord2_z.css_font_size = "100%"
        cord2_z.css_height = "20px"
        cord2_z.css_left = "180px"
        cord2_z.css_margin = "0px"
        cord2_z.css_position = "absolute"
        cord2_z.css_top = "145px"
        cord2_z.css_width = "100px"
        cord2_z.text = "Z:"
        cord2_z.variable_name = "cord2_z"
        file_container.append(cord2_z, "cord2_z")
        cord3_x = Label()
        cord3_x.attr_editor_newclass = False
        cord3_x.css_font_size = "100%"
        cord3_x.css_height = "20px"
        cord3_x.css_left = "180px"
        cord3_x.css_margin = "0px"
        cord3_x.css_position = "absolute"
        cord3_x.css_top = "170px"
        cord3_x.css_width = "100px"
        cord3_x.text = "X:"
        cord3_x.variable_name = "cord3_x"
        file_container.append(cord3_x, "cord3_x")
        cord3_y = Label()
        cord3_y.attr_editor_newclass = False
        cord3_y.css_font_size = "100%"
        cord3_y.css_height = "20px"
        cord3_y.css_left = "180px"
        cord3_y.css_margin = "0px"
        cord3_y.css_position = "absolute"
        cord3_y.css_top = "185px"
        cord3_y.css_width = "100px"
        cord3_y.text = "Y:"
        cord3_y.variable_name = "cord3_y"
        file_container.append(cord3_y, "cord3_y")
        cord3_z = Label()
        cord3_z.attr_editor_newclass = False
        cord3_z.css_font_size = "100%"
        cord3_z.css_height = "20px"
        cord3_z.css_left = "180px"
        cord3_z.css_margin = "0px"
        cord3_z.css_position = "absolute"
        cord3_z.css_top = "200px"
        cord3_z.css_width = "100px"
        cord3_z.text = "Z:"
        cord3_z.variable_name = "cord3_z"
        file_container.append(cord3_z, "cord3_z")
        check_cord1 = CheckBox()
        check_cord1.attr_editor_newclass = False
        check_cord1.css_height = "30px"
        check_cord1.css_left = "320px"
        check_cord1.css_margin = "0px"
        check_cord1.css_position = "absolute"
        check_cord1.css_top = "60px"
        check_cord1.css_width = "30px"
        check_cord1.variable_name = "check_cord1"
        file_container.append(check_cord1, "check_cord1")
        check_cord2 = CheckBox()
        check_cord2.attr_editor_newclass = False
        check_cord2.css_height = "30px"
        check_cord2.css_left = "320px"
        check_cord2.css_margin = "0px"
        check_cord2.css_position = "absolute"
        check_cord2.css_top = "115px"
        check_cord2.css_width = "30px"
        check_cord2.variable_name = "check_cord2"
        file_container.append(check_cord2, "check_cord2")
        check_cord3 = CheckBox()
        check_cord3.attr_editor_newclass = False
        check_cord3.css_height = "30px"
        check_cord3.css_left = "320px"
        check_cord3.css_margin = "0px"
        check_cord3.css_position = "absolute"
        check_cord3.css_top = "170px"
        check_cord3.css_width = "30px"
        check_cord3.variable_name = "check_cord3"
        file_container.append(check_cord3, "check_cord3")
        transform = Button()
        transform.attr_editor_newclass = False
        transform.css_font_size = "80%"
        transform.css_height = "30px"
        transform.css_left = "235px"
        transform.css_margin = "0px"
        transform.css_position = "absolute"
        transform.css_top = "245px"
        transform.css_width = "100px"
        transform.text = "Transform"
        transform.variable_name = "transform"
        file_container.append(transform, "transform")
        restore = Button()
        restore.attr_editor_newclass = False
        restore.css_font_size = "80%"
        restore.css_height = "30px"
        restore.css_left = "85px"
        restore.css_margin = "0px"
        restore.css_position = "absolute"
        restore.css_top = "245px"
        restore.css_width = "120px"
        restore.text = "Restore Coordinates"
        restore.variable_name = "restore"
        file_container.append(restore, "restore")
        move_to_mark = DropDown()
        move_to_mark.attr_editor_newclass = False
        move_to_mark.css_height = "30px"
        move_to_mark.css_left = "85px"
        move_to_mark.css_margin = "0px"
        move_to_mark.css_position = "absolute"
        move_to_mark.css_top = "300px"
        move_to_mark.css_width = "120px"
        move_to_mark.variable_name = "move_to_mark"
        file_container.append(move_to_mark, "move_to_mark")
        gotomark = Button()
        gotomark.attr_editor_newclass = False
        gotomark.css_font_size = "80%"
        gotomark.css_height = "30px"
        gotomark.css_left = "235px"
        gotomark.css_margin = "0px"
        gotomark.css_position = "absolute"
        gotomark.css_top = "300px"
        gotomark.css_width = "100px"
        gotomark.text = "Go To Mark"
        gotomark.variable_name = "gotomark"
        file_container.append(gotomark, "gotomark")
        file_container.children["uploader"].ondata.do(self.ondata_uploader)
        file_container.children["first_mark"].onchange.do(self.onchange_first_mark)
        file_container.children["second_mark"].onchange.do(self.onchange_second_mark)
        file_container.children["third_mark"].onchange.do(self.onchange_third_mark)
        file_container.children["check_cord1"].onchange.do(self.onchange_check_cord1)
        file_container.children["check_cord2"].onchange.do(self.onchange_check_cord2)
        file_container.children["check_cord3"].onchange.do(self.onchange_check_cord3)
        file_container.children["transform"].onclick.do(self.onclick_transform)
        file_container.children["restore"].onclick.do(self.onclick_restore)
        file_container.children["move_to_mark"].onchange.do(self.onchange_move_to_mark)
        file_container.children["gotomark"].onclick.do(self.onclick_gotomark)
        file_container.children["move_to_mark"].empty()
        self.file_container = file_container
        return self.file_container

    def ondata_uploader(self, emitter, filedata, filename):
        cleanupFiles = glob.glob("./res/*")
        cleanupFiles.remove("./res/" + filename)
        for cleanupFile in cleanupFiles:
            os.remove(cleanupFile)

        print("./res/" + filename)
        try:
            os.remove("./database_ramdisk/coordinates.json")
        except:
            pass

        self.gds = coordinates.coordinates(("./res/" + filename), read_file=True, name="./database_ramdisk/coordinates.json")
        devices = self.gds.listdevicenames()
        self.file_container.children["first_mark"].empty()
        self.file_container.children["second_mark"].empty()
        self.file_container.children["third_mark"].empty()
        self.file_container.children["move_to_mark"].empty()
        self.file_container.children["check_cord1"].set_value(0)
        self.file_container.children["check_cord2"].set_value(0)
        self.file_container.children["check_cord3"].set_value(0)
        self.file_container.children["cord1_x"].set_text("X:")
        self.file_container.children["cord1_y"].set_text("Y:")
        self.file_container.children["cord1_z"].set_text("Z:")
        self.file_container.children["cord2_x"].set_text("X:")
        self.file_container.children["cord2_y"].set_text("Y:")
        self.file_container.children["cord2_z"].set_text("Z:")
        self.file_container.children["cord3_x"].set_text("X:")
        self.file_container.children["cord3_y"].set_text("Y:")
        self.file_container.children["cord3_z"].set_text("Z:")
        self.file_container.children["first_mark"].append(devices)
        self.file_container.children["second_mark"].append(devices)
        self.file_container.children["third_mark"].append(devices)
        self.file_container.children["move_to_mark"].append(["Mark 1", "Mark 2", "Mark 3"])
        self.first_mark_name = devices[0]
        self.second_mark_name = devices[0]
        self.third_mark_name = devices[0]
        self.first_mark_set = 0
        self.second_mark_set = 0
        self.third_mark_set = 0
        self.move_mark_number = 1

    def onchange_first_mark(self, emitter, new_value):
        self.first_mark_name = new_value

    def onchange_second_mark(self, emitter, new_value):
        self.second_mark_name = new_value

    def onchange_third_mark(self, emitter, new_value):
        self.third_mark_name = new_value

    def onchange_check_cord1(self, emitter, value):
        if int(value) == 1:
            self.first_mark_position = self.stage.read_position()
            print(self.first_mark_position)
            self.file_container.children["cord1_x"].set_text("X: " + str(round(self.first_mark_position[0], 2)))
            self.file_container.children["cord1_y"].set_text("Y: " + str(round(self.first_mark_position[1], 2)))
            self.file_container.children["cord1_z"].set_text("Z: " + str(round(self.first_mark_position[2], 2)))
            self.first_mark_set = 1
        else:
            self.first_mark_set = 0

    def onchange_check_cord2(self, emitter, value):
        if int(value) == 1:
            self.second_mark_position = self.stage.read_position()
            print(self.second_mark_position)
            self.file_container.children["cord2_x"].set_text("X: " + str(round(self.second_mark_position[0], 2)))
            self.file_container.children["cord2_y"].set_text("Y: " + str(round(self.second_mark_position[1], 2)))
            self.file_container.children["cord2_z"].set_text("Z: " + str(round(self.second_mark_position[2], 2)))
            self.second_mark_set = 1
        else:
            self.second_mark_set = 0

    def onchange_check_cord3(self, emitter, value):
        if int(value) == 1:
            self.third_mark_position = self.stage.read_position()
            print(self.third_mark_position)
            self.file_container.children["cord3_x"].set_text("X: " + str(round(self.third_mark_position[0], 2)))
            self.file_container.children["cord3_y"].set_text("Y: " + str(round(self.third_mark_position[1], 2)))
            self.file_container.children["cord3_z"].set_text("Z: " + str(round(self.third_mark_position[2], 2)))
            self.third_mark_set = 1
        else:
            self.third_mark_set = 0

    def onclick_transform(self, emitter):
        if self.first_mark_set == 1 and self.second_mark_set == 1 and self.third_mark_set == 1:
            print("First mark is: " + self.first_mark_name)
            print("Second mark is: " + self.second_mark_name)
            print("Third mark is: " + self.third_mark_name)
            devicenumbers = [self.gds.finddevicenumber(self.first_mark_name)[0],
             self.gds.finddevicenumber(self.second_mark_name)[0],
             self.gds.finddevicenumber(self.third_mark_name)[0]]
            return_value = self.gds.apply_transform(devicenumbers, self.first_mark_position, self.second_mark_position, self.third_mark_position)
            if return_value == 0:
                print("Transformed")
                shutil.copy("./database_ramdisk/coordinates.json", "./database_ramdisk/transformed.json")
                shutil.copy("./database_ramdisk/transformed.json", "transformed_backup.json")
            else:
                print("Transformed failed!!")
                print("Check the marks and retry")
        else:
            print("Not all marks have been found")
            if self.first_mark_set != 1:
                print("First mark not found!")
            if self.second_mark_set != 1:
                print("Second mark not found!")
        if self.third_mark_set != 1:
            print("Third mark not found!")

    def onclick_restore(self, emitter):
        try:
            shutil.copy("transformed_backup.json", "./database_ramdisk/transformed.json")
        except:
            print("Could not restore previous coordinates!!")

    def onchange_move_to_mark(self, emitter, new_value):
        if "Mark 1" in new_value:
            self.move_mark_number = 1
        else:
            if "Mark 2" in new_value:
                self.move_mark_number = 2
            else:
                if "Mark 3" in new_value:
                    self.move_mark_number = 3

    def onclick_gotomark(self, emitter):
        self.move_to_mark(self.move_mark_number)

    def move_to_mark(self, mark_number):
        if mark_number == 1:
            if self.first_mark_set != 1:
                print("First mark not found!")
                return -1
            mark_position = self.first_mark_position
        else:
            if mark_number == 2:
                if self.second_mark_set != 1:
                    print("Second mark not found!")
                    return -1
                mark_position = self.second_mark_position
            else:
                if mark_number == 3:
                    if self.third_mark_set != 1:
                        print("Third mark not found!")
                        return -1
                        mark_position = self.third_mark_position
                    else:
                        print("Mark number " + str(mark_number) + " doesn't exist!")
                        return -1
                else:
                    try:
                        self.stage.reload_parameters()
                        current = float(self.stage.dict["z_position"])
                        original_z = current
                        print(current)
                        print("move up " + str(float(250.0) - current))
                        self.stage.move_z_axis(float(250.0) - current)
                        current = float(250.0) - current
                    except:
                        print("safe z movement too small!!")
                        print("something is wrong!!")
                        print("don't move anymore")
                        return

                status = self.stage.status(3)
                while status == "0":
                    status = self.stage.status(3)

                self.stage.update_parameter("z_position", float(current))
                time.sleep(0.25)
                current_position = self.stage.read_position()
                print(current_position)
                distance = [
                 float(mark_position[0]) - float(current_position[0]),
                 float(mark_position[1]) - float(current_position[1]),
                 float(mark_position[2]) - float(current_position[2])]
                print(distance)
                try:
                    self.stage.reload_parameters()
                    current = float(self.stage.dict["x_position"])
                    self.stage.move_x_axis(distance[0])
                    current = current + float(distance[0])
                except:
                    print("x movement too small")

                status = self.stage.status(1)
                while status == "0":
                    status = self.stage.status(1)

                self.stage.update_parameter("x_position", float(current))
                try:
                    self.stage.reload_parameters()
                    current = float(self.stage.dict["y_position"])
                    self.stage.move_y_axis(distance[1])
                    current = current + float(distance[1])
                except:
                    print("y movement too small")

                status = self.stage.status(2)
                while status == "0":
                    status = self.stage.status(2)

                self.stage.update_parameter("y_position", float(current))
                time.sleep(0.25)
                try:
                    self.stage.reload_parameters()
                    current = float(self.stage.dict["z_position"])
                    print("z distance to move " + str(distance[2]))
                    self.stage.move_z_axis(distance[2])
                    current = current + float(distance[2])
                except:
                    print("safe z movement too small")

                status = self.stage.status(3)
                while status == "0":
                    status = self.stage.status(3)

                print(self.stage.read_position())
                self.stage.update_parameter("z_position", float(current + original_z))


configuration = {'config_project_name': '"files"', 'config_address': '"0.0.0.0"', 'config_port': 10081, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(files, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
