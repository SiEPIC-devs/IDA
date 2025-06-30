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
        sensor_control_container = StyledContainer(
            container=None, variable_name="sensor_control_container", left=0, top=0, height=100, width=300
        )

        StyledCheckBox(
            container=sensor_control_container, variable_name="on_box", left=20, top=10, width=10,
            height=10, position="absolute"
        )

        StyledLabel(
            container=sensor_control_container, text="On", variable_name="on_label", left=50, top=10,
            width=40, height=30, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=sensor_control_container, text="Tem [°C]", variable_name="wvl_label", left=0, top=55,
            width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.minus_tem = StyledButton(
            container=sensor_control_container, text="⮜", variable_name="wvl_left_button", font_size=100,
            left=90, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )
        self.plus_tem = StyledButton(
            container=sensor_control_container, text="⮞", variable_name="wvl_right_button", font_size=100,
            left=222, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.tem = StyledSpinBox(
            container=sensor_control_container, variable_name="wvl_input", left=135, top=55, min_value=0,
            max_value=100, value=25, step=0.1, width=65, height=24, position="absolute"
        )

        self.minus_tem.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_tem))
        self.plus_tem.do_onclick(lambda *_: self.run_in_thread(self.onclick_plus_tem))
        self.tem.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_tem, emitter, value))

        self.sensor_control_container = sensor_control_container
        return sensor_control_container

    def onclick_minus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < 0: value = 0.0
        if value > 100: value = 100.0
        self.tem.set_value(value)
        print(f"TEC temperature: {value:.1f} °C")

    def onclick_plus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < 0: value = 0.0
        if value > 100: value = 100.0
        self.tem.set_value(value)
        print(f"TEC temperature: {value:.1f} °C")

    def onchange_tem(self, emitter, value):
        print(f"TEC temperature: {value:.1f} °C")

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
    start(
        stage_control,
        address="0.0.0.0", port=8002,
        start_browser=False, multiple_instance=False
    )


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
        'TEC Control',
        f'http://{local_ip}:8002',
        width=322, height=157,
        x=800, y=100,
        resizable=True
    )
    webview.start(func=disable_scroll)
