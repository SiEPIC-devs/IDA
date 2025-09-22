from remi import start, App
import os, threading, webview
from GUI.lib_gui import *

shared_path = os.path.join("database", "shared_memory.json")

class instruments(App):
    def __init__(self, *args, **kwargs):
        self.configuration = {"stage": "", "sensor": "", "tec": ""}
        self.configuration_check = {}
        self.stage_connect_btn = None
        self.sensor_connect_btn = None
        self.tec_connect_btn = None
        self.terminal = None
        self.stage_dd = None
        self.sensor_dd = None
        self.tec_dd = None
        self.stage_configure_btn = None
        self.sensor_configure_btn = None
        self.tec_configure_btn = None
        self._user_stime = None
        if "editing_mode" not in kwargs:
            super(instruments, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.terminal.terminal_refresh()

        try:
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            stime = None

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.configuration_check = data.get("Configuration_check", {})
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

        self.after_configuration()

    def after_configuration(self):
        if self.configuration_check["stage"] == 1:
            self.stage_connect_btn.set_text("Connect")
            self.configuration_check["stage"] = 0
            self.configuration["stage"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Stage")
            self.lock_all(0)
        elif self.configuration_check["stage"] == 2:
            self.stage_connect_btn.set_text("Disconnect")
            self.configuration_check["stage"] = 0
            file = File(
                "shared_memory", "Configuration_check", self.configuration_check)
            file.save()
            print("Stage Connection Successful")
            self.lock_all(0)

        if self.configuration_check["sensor"] == 1:
            self.sensor_connect_btn.set_text("Connect")
            self.configuration_check["sensor"] = 0
            self.configuration["sensor"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Sensor")
            self.lock_all(0)
        elif self.configuration_check["sensor"] == 2:
            self.sensor_connect_btn.set_text("Disconnect")
            self.configuration_check["sensor"] = 0
            file = File(
                "shared_memory", "Configuration_check", self.configuration_check)
            file.save()
            print("Sensor Connection Successful")
            self.lock_all(0)

        if self.configuration_check["tec"] == 1:
            self.tec_connect_btn.set_text("Connect")
            self.configuration_check["tec"] = 0
            self.configuration["tec"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Tec")
            self.lock_all(0)
        elif self.configuration_check["tec"] == 2:
            self.tec_connect_btn.set_text("Disconnect")
            self.configuration_check["tec"] = 0
            file = File(
                "shared_memory", "Configuration_check", self.configuration_check)
            file.save()
            print("Tec Connection Successful")
            self.lock_all(0)

    def lock_all(self, value):
        enabled = value == 0
        widgets_to_check = [self.instruments_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            if isinstance(widget, (Button, DropDown)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def construct_ui(self):
        instruments_container = StyledContainer(
            variable_name="instruments_container", left=0, top=0
        )

        for idx, key in enumerate(("stage", "sensor", "tec")):
            # Label
            StyledLabel(
                container=instruments_container, variable_name=f"label_{key}",
                text={"stage": "Stage:",
                      "sensor": "Sensor:",
                      "tec": "TEC:"}[key],
                left=0, top=15 + idx * 40, width=150, height=20, font_size=100, color="#444", align="right"
            )

            # DropDown
            setattr(self, f"{key}_dd", StyledDropDown(
                container=instruments_container,
                text={"stage": ["stage_control", "stage_B", "stage_C"],
                      "sensor": ["stage_control","laser_B","laser_C"],
                      "tec": ["stage_control","TEC_B","TEC_C"]}[key],
                variable_name=f"set_{key}", left=160, top=10 + idx * 40, width=180, height=30))

            # Configure Button
            setattr(self, f"{key}_configure_btn", StyledButton(
                container=instruments_container, text="Configure", variable_name=f"configure_{key}",
                left=360, top=10 + idx*40, normal_color="#007BFF", press_color="#0056B3"
            ))

            # Connect Button
            setattr(self, f"{key}_connect_btn", StyledButton(
                container=instruments_container, text="Connect", variable_name=f"connect_{key}",
                left=480, top=10 + idx * 40, normal_color="#007BFF", press_color="#0056B3"
            ))

        # Terminal
        terminal_container = StyledContainer(
            container=instruments_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text", left=10, top=15, width=610, height=100
        )

        self.stage_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_stage_connect_btn))
        self.sensor_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_sensor_connect_btn))
        self.tec_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_tec_connect_btn))
        self.stage_configure_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure_btn))
        self.sensor_configure_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure_btn))
        self.tec_configure_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure_btn))

        self.instruments_container = instruments_container
        return instruments_container

    def onclick_stage_connect_btn(self):
        if self.stage_connect_btn.get_text() == "Connect":
            self.configuration["stage"] = self.stage_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.stage_connect_btn.set_text("Connecting")
            self.lock_all(1)
        else:
            self.configuration["stage"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.stage_connect_btn.set_text("Connect")

    def onclick_sensor_connect_btn(self):
        if self.sensor_connect_btn.get_text() == "Connect":
            self.configuration["sensor"] = self.sensor_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.sensor_connect_btn.set_text("Connecting")
            self.lock_all(1)
        else:
            self.configuration["sensor"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.sensor_connect_btn.set_text("Connect")

    def onclick_tec_connect_btn(self):
        if self.tec_connect_btn.get_text() == "Connect":
            self.configuration["tec"] = self.tec_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.tec_connect_btn.set_text("Connecting")
            self.lock_all(1)
        else:
            self.configuration["tec"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.tec_connect_btn.set_text("Connect")

    def onclick_configure_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            'Stage Control',
            f'http://{local_ip}:7005',
            width=222+web_w, height=236+web_h,
            resizable=True,
            on_top=True
        )

def run_remi():
    start(
        instruments,
        address="0.0.0.0",
        port=9001,
        start_browser=False,
        multiple_instance=False,
        enable_file_cache=False,
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

if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    local_ip = get_local_ip()
    webview.create_window(
        "Main Window",
        f"http://{local_ip}:9001",
        width=0,
        height=0,
        resizable=True,
        hidden=True,
    )
    webview.start()
