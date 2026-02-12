# uncompyle6 version 3.9.2
# Python bytecode version base 3.7.0 (3394)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: /home/pi/Desktop/new GUI/main_gui.py
# Compiled at: 2023-02-14 23:59:31
# Size of source mod 2**32: 11801 bytes
from IPython.lib.display import IFrame

from GUI.lib_gui import *
from remi.gui import *
from remi import start, App, gui
import threading, webview, signal, socket, time

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class NIR_Measurment_System(App):

    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs.keys():
            (super(NIR_Measurment_System, self).__init__)(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def construct_ui(self):
        # ip_address = get_local_ip()
        ip_address = '127.0.0.1'
        main = StyledContainer(variable_name="main", left=0, top=0, height=715, width=650)
        #
        # stage = StyledContainer(
        #     container=main, variable_name="stage", left=700, top=365, height=350, width=650, border=True
        # )
        # iframe_stage = gui.Widget(_type='iframe')
        # iframe_stage.attributes['src'] = f'http://{ip_address}:8000'
        # iframe_stage.attributes['frameborder'] = '0'
        # iframe_stage.attributes['allowfullscreen'] = 'true'
        # iframe_stage.style['width'] = '100%'
        # iframe_stage.style['height'] = '100%'
        # iframe_stage.style['border'] = '0'
        # stage.append(iframe_stage, key='ext_site')
        #
        # sensor = StyledContainer(
        #     container=main, variable_name="sensor", left=700, top=205, height=140, width=650, border=True
        # )
        # iframe_sensor = gui.Widget(_type='iframe')
        # iframe_sensor.attributes['src'] = f'http://{ip_address}:8001'
        # iframe_sensor.attributes['frameborder'] = '0'
        # iframe_sensor.attributes['allowfullscreen'] = 'true'
        # iframe_sensor.style['width'] = '100%'
        # iframe_sensor.style['height'] = '100%'
        # iframe_sensor.style['border'] = '0'
        # sensor.append(iframe_sensor, key='ext_site')
        #
        # tec = StyledContainer(
        #     container=main, variable_name="tec", left=700, top=85, height=100, width=300, border=True
        # )
        # iframe_tec = gui.Widget(_type='iframe')
        # iframe_tec.attributes['src'] = f'http://{ip_address}:8002'
        # iframe_tec.attributes['frameborder'] = '0'
        # iframe_tec.attributes['allowfullscreen'] = 'true'
        # iframe_tec.style['width'] = '100%'
        # iframe_tec.style['height'] = '100%'
        # iframe_tec.style['border'] = '0'
        # tec.append(iframe_tec, key='ext_site')
        #
        # command = StyledContainer(
        #     container=main, variable_name="command", left=1020, top=105, height=80, width=400, border=True
        # )
        # iframe_command = gui.Widget(_type='iframe')
        # iframe_command.attributes['src'] = f'http://{ip_address}:8003'
        # iframe_command.attributes['frameborder'] = '0'
        # iframe_command.attributes['allowfullscreen'] = 'true'
        # iframe_command.style['width'] = '100%'
        # iframe_command.style['height'] = '100%'
        # iframe_command.style['border'] = '0'
        # command.append(iframe_command, key='ext_site')


        main_tab = TabBox()
        main_tab.attr_editor_newclass = False
        main_tab.css_align_content = "center"
        main_tab.css_align_items = "center"
        main_tab.css_height = "100%"
        main_tab.css_left = "0px"
        main_tab.css_margin = "0px"
        main_tab.css_position = "inherit"
        main_tab.css_top = "0px"
        main_tab.css_width = "100%"
        main_tab.variable_name = "main_tab"

        tab_cfg = [
            ("Start", 9109),
            ("Instruments", 9101),
            ("Registration", 9102),
            ("Devices", 9103),
            ("Testing", 9104),
        ]

        def make_iframe(port: int):
            w = Widget(_type="iframe", width="100%", height="100%", margin="0px")
            w.attributes.update({
                "src": f"http://{ip_address}:{port}",
                "width": "100%",
                "height": "100%",
            })
            w.style["border"] = "none"
            return w

        for title, port in tab_cfg:
            frame = make_iframe(port)
            setattr(self, title.lower(), frame)
            main_tab.add_tab(frame, title)

        main.append(main_tab, "main_tab")
        self.main = main
        # print("Welcome To Probe Stage")
        return self.main


def run_remi():
    start(NIR_Measurment_System,
          address='0.0.0.0', port=80,
          start_browser=False,
          multiple_instance=False)


def disable_scroll():
    try:
        webview.windows[0].evaluate_js("""
            document.documentElement.style.overflow = 'hidden';
            document.body.style.overflow = 'hidden';
        """)
    except Exception as e:
        print("JS Wrong", e)


if __name__ == '__main__':
    # local_ip = get_local_ip()
    local_ip = '127.0.0.1'
    
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    webview.create_window(
        'Probe Stage',
        f'http://{local_ip}:80',
        width=672+web_w, height=771+web_h,
        x= 100, y= 100,
        resizable=True
    )

    webview.start(func=disable_scroll)
