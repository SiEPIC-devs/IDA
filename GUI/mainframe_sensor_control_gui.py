from lab_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, datetime
import pandas as pd
w = 6
h = 16
command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")

class stage_control(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.user = "Guest"
        self.sweep = {}
        self.auto_sweep = 0
        self.count = 0
        self.configuration = {}
        self.configuration_count = 0
        self.num = 1
        self.project = None
        self.sensor = {}
        self.sensor_window = None
        self.sweep_check = 0
        if "editing_mode" not in kwargs:
            super(stage_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

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
            self.run_in_thread(self.execute_command)

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user = data.get("User", "")
                    self.project = data.get("Project", "")
                    self.sweep = data.get("Sweep", {})
                    self.auto_sweep = data.get("AutoSweep", 0)
                    self.configuration = data.get("Configuration", {})
                    self.num = data.get("DeviceNum", "")
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

            self.pwr.set_value(self.sweep["power"])
            self.wvl.set_value(self.sweep["wvl"])
            self.range_start.set_value(self.sweep["start"])
            self.range_end.set_value(self.sweep["end"])

        if self.auto_sweep == 1 and self.count == 0:
            self.count = 1
            self.lock_all(1)
        elif self.auto_sweep == 0 and self.count == 1:
            self.count = 0
            self.lock_all(0)

        if self.sweep["sweep"] == 1 and self.auto_sweep == 0:
            self.sweep_btn.set_enabled(False)
            self.sweep_check = 1
        elif self.sweep["sweep"] == 0 and self.auto_sweep == 0:
            self.sweep_btn.set_enabled(True)
            if self.sweep_check == 1:
                if self.sweep["done"] == "Laser On":
                    self.on_box.set_value(1)
                else:
                    self.on_box.set_value(0)
                self.sweep_check = 0

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def lock_all(self, value):
        enabled = value == 0
        widgets_to_check = [self.sensor_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            if isinstance(widget, (Button, SpinBox, CheckBox)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())


    def construct_ui(self):
        sensor_control_container = StyledContainer(
            container=None, variable_name="sensor_control_container", left=0, top=0, height=140, width=650
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
            container=sensor_control_container, text="Wvl [nm]", variable_name="wvl_label", left=55, top=40,
            width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        StyledLabel(
            container=sensor_control_container, text="Pwr [dBm]", variable_name="pwr_label", left=55, top=80,
            width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.minus_wvl = StyledButton(
            container=sensor_control_container, text="⮜", variable_name="wvl_left_button", font_size=100,
            left=140, top=40, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.minus_pwr = StyledButton(
            container=sensor_control_container, text="-", variable_name="pwr_left_button", font_size=130,
            left=140, top=80, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.wvl = StyledSpinBox(
            container=sensor_control_container, variable_name="wvl_input", left=185, top=40, min_value=0,
            max_value=2000, value=1550.0, step=0.1, width=65, height=24, position="absolute"
        )

        self.pwr = StyledSpinBox(
            container=sensor_control_container, variable_name="pwr_input", left=185, top=80, min_value=-1000,
            max_value=1000, value=0.0, step=0.1, width=65, height=24, position="absolute"
        )

        self.add_wvl = StyledButton(
            container=sensor_control_container, text="⮞", variable_name="wvl_right_button", font_size=100,
            left=272, top=40, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.add_pwr = StyledButton(
            container=sensor_control_container, text="+", variable_name="pwr_right_button", font_size=100,
            left=272, top=80, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        sweep_container = StyledContainer(
            container=sensor_control_container, variable_name="sweep_container", left=330, top=20,
            height=100, width=300, border=True
        )

        self.sweep_btn = StyledButton(
            container=sweep_container, text="Sweep", variable_name="sweep_button", font_size=90,
            left=90, top=15, width=82, height=28, normal_color="#007BFF", press_color="#0056B3"
        )

        self.configure = StyledButton(
            container=sweep_container, text="Configure", variable_name="configure_button", font_size=90,
            left=200, top=15, width=82, height=28, normal_color="#007BFF", press_color="#0056B3"
        )

        StyledLabel(
            container=sweep_container, text="Range [nm]", variable_name="range_label", left=0, top=55,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.range_start = StyledSpinBox(
            container=sweep_container, variable_name="range_start", left=90, top=55, min_value=0,
            max_value=2000, value=1540.0, step=0.1, width=65, height=24, position="absolute"
        )

        StyledLabel(
            container=sweep_container, text="to", variable_name="to_label", left=175, top=55,
            width=20, height=25, font_size=100, flex=True, justify_content="center", color="#222"
        )

        self.range_end = StyledSpinBox(
            container=sweep_container, variable_name="range_end", left=200, top=55, min_value=0,
            max_value=2000, value=1560.0, step=0.1, width=65, height=24, position="absolute"
        )

        self.configure.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure))
        self.minus_wvl.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_wvl))
        self.minus_pwr.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_pwr))
        self.add_wvl.do_onclick(lambda *_: self.run_in_thread(self.onclick_add_wvl))
        self.add_pwr.do_onclick(lambda *_: self.run_in_thread(self.onclick_add_pwr))
        self.sweep_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_sweep))
        self.wvl.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_wvl, emitter, value))
        self.pwr.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_pwr, emitter, value))
        self.range_start.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_range_start, emitter, value))
        self.range_end.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_range_end, emitter, value))
        self.on_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_box, emitter, value))

        self.sensor = {"wvl": 1550.0, "pwr": 0.0, "sweep": 0}

        self.sensor_control_container = sensor_control_container
        return sensor_control_container

    def onclick_configure(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7001",
            width=262-w,
            height=305-h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onchange_box(self, emitter, value):
        if value:
            self.sweep["on"] = value
            file = File("shared_memory", "Sweep", self.sweep)
            file.save()
            print("On")
        else:
            self.sweep["on"] = value
            file = File("shared_memory", "Sweep", self.sweep)
            file.save()
            print("Off")

    def onclick_minus_wvl(self):
        value = round(float(self.wvl.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < 0: value = 0.0
        if value > 2000: value = 2000.0
        self.sweep["wvl"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Wavelength: {value:.1f} nm")

    def onclick_minus_pwr(self):
        value = round(float(self.pwr.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < -1000: value = -1000.0
        if value > 1000: value = 1000.0
        self.sweep["power"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Power: {value:.1f} dBm")

    def onclick_add_wvl(self):
        value = round(float(self.wvl.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < 0: value = 0.0
        if value > 2000: value = 2000.0
        self.sweep["wvl"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Wavelength: {value:.1f} nm")

    def onclick_add_pwr(self):
        value = round(float(self.pwr.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < -1000:  value = -1000.0
        if value > 1000: value = 1000.0
        self.sweep["power"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Power: {value:.1f} dBm")

    def onclick_sweep(self):
        self.sweep["sweep"] = 1
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()


    def onchange_wvl(self, emitter, value):
        self.sweep["wvl"] = float(value)
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Wavelength: {value:.1f} nm")

    def onchange_pwr(self, emitter, value):
        self.sweep["power"] = float(value)
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()
        print(f"Power: {value:.1f} dBm")

    def onchange_range_start(self, emitter, value):
        print(f"Range Start: {value:.1f} nm")
        value = float(value)
        self.sweep["start"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()

    def onchange_range_end(self, emitter, value):
        print(f"Range End: {value:.1f} dBm")
        value = float(value)
        self.sweep["end"] = value
        file = File("shared_memory", "Sweep", self.sweep)
        file.save()

    def execute_command(self, path=command_path):
        sensor = 0
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
            if key.startswith("sensor_control") and record == 0:
                sensor = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
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

            elif key == "sensor_on":
                self.on_box.set_value(1)
            elif key == "sensor_off":
                self.on_box.set_value(0)
            elif key == "sensor_wvl":
                self.wvl.set_value(val)
                self.onchange_wvl(1, float(val))
            elif key == "sensor_pwr":
                self.pwr.set_value(val)
                self.onchange_pwr(1, float(val))
            elif key == "sensor_sweep_start":
                self.range_start.set_value(val)
                self.onchange_range_start(1, float(val))
            elif key == "sensor_sweep_end":
                self.range_end.set_value(val)
                self.onchange_range_end(1, float(val))
            elif key == "sensor_sweep":
                self.onclick_sweep()
                self.sweep["sweep"] = 1

            while self.sweep["sweep"] == 1:
                time.sleep(1)

        if sensor == 1:
            print("sensor record")
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
        stage_control,
        address="0.0.0.0", port=8001,
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
        'Sensor Control',
        f'http://{local_ip}:8001',
        width=672,
        height=197,
        x=800,
        y=255,
        resizable=True,
        hidden = True
    )

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7001",
        width=262,
        height=305,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.start(func=disable_scroll)
