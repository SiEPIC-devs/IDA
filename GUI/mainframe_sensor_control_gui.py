from lab_gui import *
from remi.gui import *
from remi import start, App
import threading
import webview
import signal

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")

class stage_control(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
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
            self._user_stime = stime
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
                    sweep_range = data.get("SweepRange", {})
                    power = data.get("Power", "")
            except Exception as e:
                print(f"[Warn] read json failed: {e}")
                sweep_range = {}

            if power != "":
                self.pwr.set_value(power)

            if isinstance(sweep_range, dict):
                start = sweep_range.get("start")
                stop = sweep_range.get("stop")

                if start is not None and stop is not None:
                    self.range_start.set_value(start)
                    self.range_end.set_value(stop)

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        sensor_control_container = StyledContainer(
            container=None, variable_name="sensor_control_container", left=0, top=0, height=150, width=650
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
            container=sensor_control_container, text="Wvl [nm]", variable_name="wvl_label", left=55, top=55,
            width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        StyledLabel(
            container=sensor_control_container, text="Pwr [dBm]", variable_name="pwr_label", left=55, top=95,
            width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.minus_wvl = StyledButton(
            container=sensor_control_container, text="⮜", variable_name="wvl_left_button", font_size=100,
            left=140, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.minus_pwr = StyledButton(
            container=sensor_control_container, text="-", variable_name="pwr_left_button", font_size=130,
            left=140, top=95, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.wvl = StyledSpinBox(
            container=sensor_control_container, variable_name="wvl_input", left=185, top=55, min_value=0,
            max_value=2000, value=10.0, step=0.1, width=65, height=24, position="absolute"
        )

        self.pwr = StyledSpinBox(
            container=sensor_control_container, variable_name="pwr_input", left=185, top=95, min_value=-1000,
            max_value=1000, value=0.0, step=0.1, width=65, height=24, position="absolute"
        )

        self.add_wvl = StyledButton(
            container=sensor_control_container, text="⮞", variable_name="wvl_right_button", font_size=100,
            left=272, top=55, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        self.add_pwr = StyledButton(
            container=sensor_control_container, text="+", variable_name="pwr_right_button", font_size=100,
            left=272, top=95, width=40, height=25, normal_color="#007BFF", press_color="#0056B3"
        )

        StyledButton(
            container=sensor_control_container, text="Calibrate", variable_name="calibrate_button", font_size=90,
            left=140, top=20, width=80, height=28, normal_color="#007BFF", press_color="#0056B3"
        )

        StyledButton(
            container=sensor_control_container, text="Setting", variable_name="setting_button", font_size=90,
            left=232, top=20, width=80, height=28, normal_color="#007BFF", press_color="#0056B3"
        )

        sweep_container = StyledContainer(
            container=sensor_control_container, variable_name="sweep_container", left=330, top=20,
            height=100, width=300, border=True
        )

        self.sweep = StyledButton(
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
        self.sweep.do_onclick(lambda *_: self.run_in_thread(self.onclick_sweep))
        self.wvl.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_wvl, emitter, value))
        self.pwr.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_pwr, emitter, value))
        self.range_start.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_range_start, emitter, value))
        self.range_end.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_range_end, emitter, value))
        self.on_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_box, emitter, value))

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
            hidden=False
        )

    def onchange_box(self, emitter, value):
        if value:
            print("on")
        else:
            print("off")

    def onclick_minus_wvl(self):
        value = round(float(self.wvl.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < 0: value = 0.0
        if value > 2000: value = 2000.0
        self.wvl.set_value(value)
        print(f"Wavelength: {value:.1f} nm")

    def onclick_minus_pwr(self):
        value = round(float(self.pwr.get_value()), 1)
        value = round(value - 0.1, 1)
        if value < -1000: value = -1000.0
        if value > 1000: value = 1000.0
        self.pwr.set_value(value)
        print(f"Power: {value:.1f} dBm")

    def onclick_add_wvl(self):
        value = round(float(self.wvl.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < 0: value = 0.0
        if value > 2000: value = 2000.0
        self.wvl.set_value(value)
        print(f"Wavelength: {value:.1f} nm")

    def onclick_add_pwr(self):
        value = round(float(self.pwr.get_value()), 1)
        value = round(value + 0.1, 1)
        if value < -1000:  value = -1000.0
        if value > 1000: value = 1000.0
        file = File("shared_memory", "Power", value)
        file.save()
        self.pwr.set_value(f"{value:.1f}")
        print(f"Power: {value:.1f} dBm")

    def onclick_sweep(self):
        print("Sweep")

    def onchange_wvl(self, emitter, value):
        print(f"Wavelength: {value:.1f} nm")

    def onchange_pwr(self, emitter, value):
        value = float(value)
        file = File("shared_memory", "Power", value)
        file.save()
        self.pwr.set_value(f"{value:.1f}")
        print(f"Power: {value:.1f} dBm")

    def onchange_range_start(self, emitter, value):
        print(f"Range Start: {value:.1f} nm")
        value = float(value)
        shared_mem = {
            "start": round(value, 1),
            "stop": round(float(self.range_end.get_value()), 1)
        }
        file = File("shared_memory", "SweepRange", shared_mem)
        file.save()
        self.range_start.set_value(f"{value:.1f}")  # 更新显示为一位小数

    def onchange_range_end(self, emitter, value):
        print(f"Range End: {value:.1f} dBm")
        value = float(value)
        shared_mem = {
            "start": round(float(self.range_start.get_value()), 1),
            "stop": round(value, 1)
        }
        file = File("shared_memory", "SweepRange", shared_mem)
        file.save()
        self.range_end.set_value(f"{value:.1f}")

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
            if key.startswith("sensor_control") and val == True and record == 0:
                sensor = 1
            elif key.startswith("stage_control") and val == True or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") and val == True or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") and val == True or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") and val == True or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") and val == True or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") and val == True or record == 1:
                record = 1
                new_command[key] = val

            elif key == "sensor_on" and val == True:
                self.on_box.set_value(1)
            elif key == "sensor_off" and val:
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
        height=207,
        x=800,
        y=255,
        resizable=True
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
