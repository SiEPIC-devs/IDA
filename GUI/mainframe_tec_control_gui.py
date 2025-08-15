from lab_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, socket
from LDC.ldc_manager import LDCManager
from LDC.config.ldc_config import LDCConfiguration
w = 6
h = 17
command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")

class tec_control(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.configuration = {}
        self.configuration_count = 0
        self.configure = None
        self.ldc_manager = None
        self.tec_window = None
        self.port = {}
        if "editing_mode" not in kwargs:
            super(tec_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            mtime = os.path.getmtime(command_path)
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            mtime = None
            stime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.configuration = data.get("Configuration", {})
                    self.port = data.get("Port", {})
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def after_configuration(self):
        if self.configuration["tec"] != "" and self.configuration_count == 0:
            self.configuration_count = 1
            self.configure = LDCConfiguration()
            self.configure.visa_address = f"ASRL{self.port['tec']}::INSTR"
            self.ldc_manager = LDCManager(self.configure)
            self.ldc_manager.initialize()
            self.ldc_manager.set_temperature(25.0)
            self.tec_window = webview.create_window(
                'TEC Control',
                f'http://{local_ip}:8002',
                width=322-w, height=157-h,
                x=800, y=100,
                resizable=True,
                hidden=False
            )
        elif self.configuration["tec"] == "" and self.configuration_count == 1:
            self.configuration_count = 0
            if self.tec_window:
                self.tec_window.destroy()
                self.tec_window = None
            self.ldc_manager.shutdown()

    def construct_ui(self):
        sensor_control_container = StyledContainer(
            container=None, variable_name="sensor_control_container", left=0, top=0, height=100, width=300
        )

        self.on_box = StyledCheckBox(
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
        self.on_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_box, emitter, value))

        self.sensor_control_container = sensor_control_container
        return sensor_control_container

    def onclick_minus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < 0: value = 0.0
        if value > 100: value = 100.0
        self.tem.set_value(value)
        self.ldc_manager.set_temperature(value)
        print(f"TEC temperature: {value:.1f} °C")

    def onclick_plus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < 0: value = 0.0
        if value > 100: value = 100.0
        self.tem.set_value(value)
        self.ldc_manager.set_temperature(value)
        print(f"TEC temperature: {value:.1f} °C")

    def onchange_tem(self, emitter, value):
        value = round(float(value), 1)
        self.ldc_manager.set_temperature(value)
        print(f"TEC temperature: {value} °C")

    def onchange_box(self, emitter, value):
        if value:
            self.ldc_manager.tec_on()
            print("TEC On")
        else:
            self.ldc_manager.tec_off()
            print("TEC Off")

    def execute_command(self, path=command_path):
        tec = 0
        record = 0
        new_command = {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key.startswith("tec_control") and record == 0:
                tec = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "tec_on":
                self.on_box.set_value(1)
                self.onchange_box(1, 1)
            elif key == "tec_off":
                self.on_box.set_value(0)
                self.onchange_box(1, 0)
            elif key == "tec_tem":
                self.tem.set_value(val)
                self.onchange_tem(1, float(val))

        if tec == 1:
            print("tec record")
            file = File("command", "command", new_command)
            file.save()

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
        tec_control,
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
        resizable=True,
        hidden=True
    )
    webview.start(func=disable_scroll)
