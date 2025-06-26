# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/Terminal/terminal_gui.py
# Compiled at: 2020-11-10 15:23:21
# Size of source mod 2**32: 3525 bytes
from remi.gui import *
from remi import start, App
import sys

def print(string):
    term = sys.stdout
    term.write(str(string) + "\n")
    term.flush()


class terminal_gui(App):

    def __init__(self, *args, **kwargs):
        self.timestamp = -1
        if "editing_mode" not in kwargs.keys():
            (super(terminal_gui, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        import sys
        cwd = os.getcwd()
        main_path = os.path.split(cwd)
        main_path = main_path[0]
        try:
            filetime = os.path.getmtime(main_path + "/log.txt")
        except:
            filetime = -1

        if filetime > self.timestamp:
            logfile = open(main_path + "/log.txt", "r")
            reversed_log = ""
            log = logfile.read()
            log = log.split("\n")
            for line in reversed(log):
                reversed_log += line + "\n"

            self.terminal_container.children["terminal_text"].set_text(reversed_log)
            logfile.close()
            self.timestamp = filetime

    def main(self):
        return terminal_gui.construct_ui(self)

    @staticmethod
    def construct_ui(self):
        terminal_container = Container()
        terminal_container.attr_editor_newclass = False
        terminal_container.css_height = "450px"
        terminal_container.css_left = "0px"
        terminal_container.css_margin = "0px"
        terminal_container.css_position = "absolute"
        terminal_container.css_top = "0px"
        terminal_container.css_width = "450px"
        terminal_container.variable_name = "plot_container"
        terminal_text = TextInput(singleline=False)
        terminal_text.attr_editor_newclass = False
        terminal_text.attr_src = ""
        terminal_text.css_height = "440px"
        terminal_text.css_left = "5px"
        terminal_text.css_margin = "0px"
        terminal_text.css_position = "absolute"
        terminal_text.css_top = "5px"
        terminal_text.css_width = "440px"
        terminal_text.variable_name = "terminal_text"
        terminal_container.append(terminal_text, "terminal_text")
        self.terminal_container = terminal_container
        return self.terminal_container


configuration = {
 'config_project_name': '"terminal output"', 'config_address': '"0.0.0.0"', 'config_port': 9087, 
 'config_multiple_instance': False, 'config_enable_file_cache': False, 'config_start_browser': False, 
 'config_resourcepath': '"./res/"'}
if __name__ == "__main__":
    start(terminal_gui, address=(configuration["config_address"]), port=(configuration["config_port"]), multiple_instance=(configuration["config_multiple_instance"]),
      enable_file_cache=(configuration["config_enable_file_cache"]),
      start_browser=(configuration["config_start_browser"]))
