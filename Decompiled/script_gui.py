# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/File Import/script_gui.py
# Compiled at: 2020-12-03 19:35:09
# Size of source mod 2**32: 7416 bytes
from remi.gui import *
from remi import start, App
import coordinates, shutil, glob, os, sys
cwd = os.getcwd()
main_path = os.path.split(cwd)
main_path = main_path[0]

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class scripts(App):

    def __init__(self, *args, **kwargs):
        self.postalignment_scriptname = ""
        self.postalignment_script_status = 0
        try:
            shutil.rmtree("./res/__pycache__")
        except:
            pass

        for file in glob.glob("./res/*"):
            file = file.split("/")[-1]
            if "__init__.py" in file:
                continue
            if "postalignment.py" in file:
                self.postalignment_script_status = 1
                continue
            if file.endswith(".py"):
                self.postalignment_scriptname = file

        print(self.postalignment_scriptname)
        print(self.postalignment_script_status)
        if self.postalignment_scriptname == "":
            self.postalignment_script_status = 0
            try:
                os.remove("./res/postalignment.py")
            except:
                pass

        if "editing_mode" not in kwargs.keys():
            (super(scripts, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.script_container.children["post_alignment_script"].set_value(self.postalignment_script_status)
        self.script_container.children["post_alignment_script_name"].set_text("Current script name: " + self.postalignment_scriptname)

    def main(self):
        return scripts.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        script_container = Container()
        script_container.attr_editor_newclass = False
        script_container.css_height = "435px"
        script_container.css_left = "0px"
        script_container.css_margin = "0px"
        script_container.css_position = "absolute"
        script_container.css_top = "0px"
        script_container.css_width = "350px"
        script_container.variable_name = "file_container"
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
        script_container.append(uploader, "uploader")
        label_post_alignment_script = Label()
        label_post_alignment_script.attr_editor_newclass = False
        label_post_alignment_script.css_height = "20px"
        label_post_alignment_script.css_left = "230.0px"
        label_post_alignment_script.css_position = "absolute"
        label_post_alignment_script.css_top = "20.0px"
        label_post_alignment_script.css_width = "80px"
        label_post_alignment_script.text = "Post alignment script enable"
        label_post_alignment_script.variable_name = "label_post_alignment_script"
        script_container.append(label_post_alignment_script, "label_post_alignment_script")
        post_alignment_script_name = Label()
        post_alignment_script_name.attr_editor_newclass = False
        post_alignment_script_name.css_height = "20px"
        post_alignment_script_name.css_left = "20.0px"
        post_alignment_script_name.css_position = "absolute"
        post_alignment_script_name.css_top = "40.0px"
        post_alignment_script_name.css_width = "180px"
        post_alignment_script_name.text = "Current script name: "
        post_alignment_script_name.variable_name = "post_alignment_script_name"
        script_container.append(post_alignment_script_name, "post_alignment_script_name")
        post_alignment_script = CheckBox()
        post_alignment_script.attr_editor_newclass = False
        post_alignment_script.css_height = "20px"
        post_alignment_script.css_left = "310px"
        post_alignment_script.css_margin = "0px"
        post_alignment_script.css_position = "absolute"
        post_alignment_script.css_top = "30px"
        post_alignment_script.css_width = "30px"
        post_alignment_script.variable_name = "post_alignment_script"
        script_container.append(post_alignment_script, "post_alignment_script")
        script_container.children["uploader"].ondata.do(self.ondata_uploader)
        script_container.children["post_alignment_script"].onchange.do(self.onchange_post_alignment_script)
        self.script_container = script_container
        return self.script_container

    def onchange_post_alignment_script(self, emitter, value):
        if int(value) == 1:
            print("enable post alignment script")
            if self.postalignment_scriptname == "":
                self.postalignment_script_status = 0
                return
            shutil.copy("./res/" + self.postalignment_scriptname, "./res/postalignment.py")
            self.postalignment_script_status = 1
        else:
            print("disable post alignment script")
            try:
                os.remove("./res/postalignment.py")
            except:
                pass

            self.postalignment_script_status = 0

    def ondata_uploader(self, emitter, filedata, filename):
        if ".py" in filename:
            pass
        else:
            print(filename + " is not a python script!!")
            os.remove("./res/" + filename)
            return
            try:
                shutil.rmtree("./res/__pycache__")
            except:
                pass

            for file in glob.glob("./res/*"):
                file = file.split("/")[-1]
                if "__init__.py" in file:
                    continue
                if file == filename:
                    continue
                if file.endswith(".py"):
                    os.remove("./res/" + file)

            shutil.copy("./res/" + filename, "./res/postalignment.py")
            self.postalignment_scriptname = filename
            self.postalignment_script_status = 1


configuration = {
 'config_project_name': '"scripts"', 'config_address': '"0.0.0.0"', 'config_port': 10083, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(scripts, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
