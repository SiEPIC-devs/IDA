from lab_gui import *
from remi.gui import *
from remi import start, App
import threading
import webview
import signal
import socket

class stage_control(App):
    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs:
            super(stage_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        sensor_control_container = StyledContainer(container=None, variable_name="sensor_control_container",
                                                   left=0, top=0, height=150, width=650)
        StyledCheckBox(container=sensor_control_container, variable_name="on_box", left=20, top=10,
                       width=10, height=10, position="absolute")
        StyledLabel(container=sensor_control_container, text="On", variable_name="on_label", left=50, top=10,
                    width=40, height=30, font_size=100, flex=True, justify_content="left", color="#222")
        StyledLabel(container=sensor_control_container, text="Wvl [nm]", variable_name="wvl_label", left=55, top=55,
                    width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledLabel(container=sensor_control_container, text="Pwr [dBm]", variable_name="pwr_label", left=55, top=95,
                    width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledButton(container=sensor_control_container, text="⮜", variable_name="wvl_left_button",
                     font_size=100, left=140, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3")
        StyledButton(container=sensor_control_container, text="-", variable_name="pwr_left_button",
                     font_size=130, left=140, top=95, width=40, height=25, normal_color="#007BFF", press_color="#0056B3")
        StyledTextInput(container=sensor_control_container, variable_name="wvl_input", left=185, top=55,
                        width=65, height=24, position="absolute")
        StyledTextInput(container=sensor_control_container, variable_name="pwr_input", left=185, top=95,
                        width=65, height=24, position="absolute")
        StyledButton(container=sensor_control_container, text="⮞", variable_name="wvl_right_button",
                     font_size=100, left=272, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3")
        StyledButton(container=sensor_control_container, text="+", variable_name="pwr_right_button",
                     font_size=100, left=272, top=95, width=40, height=25, normal_color="#007BFF", press_color="#0056B3")
        StyledButton(container=sensor_control_container, text="Calibrate", variable_name="calibrate_button",
                     font_size=90, left=140, top=20, width=80, height=28, normal_color="#007BFF", press_color="#0056B3")
        StyledButton(container=sensor_control_container, text="Setting", variable_name="setting_button",
                     font_size=90, left=232, top=20, width=80, height=28, normal_color="#007BFF", press_color="#0056B3")
        sweep_container = StyledContainer(container=sensor_control_container, variable_name="sweep_container",
                                          left=330, top=20, height=100, width=300, border=True)
        StyledButton(container=sweep_container, text="Sweep", variable_name="sweep_button",
                     font_size=90, left=90, top=15, width=82, height=28, normal_color="#007BFF", press_color="#0056B3")
        self.configure = StyledButton(container=sweep_container, text="Configure", variable_name="configure_button",
                                      font_size=90, left=200, top=15, width=82, height=28, normal_color="#007BFF", press_color="#0056B3")
        StyledLabel(container=sweep_container, text="Range [nm]", variable_name="range_label", left=0, top=55,
                    width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222")
        StyledTextInput(container=sweep_container, variable_name="range_start", left=90, top=55,
                        width=65, height=24, position="absolute")
        StyledLabel(container=sweep_container, text="to", variable_name="to_label", left=175, top=55,
                    width=20, height=25, font_size=100, flex=True, justify_content="center", color="#222")
        StyledTextInput(container=sweep_container, variable_name="range_end", left=200, top=55,
                        width=65, height=24, position="absolute")

        self.configure.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure))


        self.sensor_control_container = sensor_control_container
        return sensor_control_container

    def onclick_configure(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7001",
            width=262,
            height=305,
            resizable=True,
            on_top=True,
        )


def get_local_ip():
    """Automatically detect local LAN IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Fake connect to get route IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # fallback


def run_remi():
    start(stage_control,
          address="0.0.0.0", port=8001,
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
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    local_ip = get_local_ip()
    webview.create_window(
        'Sensor Control',
        f'http://{local_ip}:8001',
        width=672,
        height=207,
        resizable=True
    )

    webview.start(func=disable_scroll)
