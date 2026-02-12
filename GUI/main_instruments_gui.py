from remi import start, App
import os, threading, webview, sys
from GUI.lib_gui import *

shared_path = os.path.join("database", "shared_memory.json")

class instruments(App):
    def __init__(self, *args, **kwargs):
        self.configuration = {"stage": "", "sensor": "", "tec": "", "smu": ""}
        self.configuration_check = {}
        self.stage_connect_btn = None
        self.sensor_connect_btn = None
        self.tec_connect_btn = None
        self.smu_connect_btn = None
        self.terminal = None
        self.stage_dd = None
        self.sensor_dd = None
        self.tec_dd = None
        self.stage_configure_btn = None
        self.sensor_configure_btn = None
        self.tec_configure_btn = None
        self.camera_btn = None
        self.calibration_btn = None
        self.force_btn = None
        self._user_stime = None
        
        # Track last processed states to avoid duplicate prints
        self._last_stage_check = None
        self._last_sensor_check = None
        self._last_tec_check = None
        self._last_smu_check = None
        if "editing_mode" not in kwargs:
            super(instruments, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.terminal.terminal_refresh()
        stime = get_shared_memory_mtime()

        if stime != self._user_stime:
            self._user_stime = stime
            data = SharedMemory.read({})
            if data:
                config_check = data.get("Configuration_check", {})
                if isinstance(config_check, dict):
                    self.configuration_check = config_check
                
                # Update NIR configuration display
                self._update_nir_config_display(data)

        self.after_configuration()

    def after_configuration(self):
        if self.configuration_check["stage"] == 1 and self._last_stage_check != 1:
            self._last_stage_check = 1
            self.stage_connect_btn.set_text("Connect")
            self.configuration_check["stage"] = 0
            self.configuration["stage"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Stage")
            self.lock_all(0)
        elif self.configuration_check["stage"] == 2 and self._last_stage_check != 2:
            self._last_stage_check = 2
            self.stage_connect_btn.set_text("Disconnect")
            # Don't reset to 0 - keep it at 2 to indicate connected state
            print("Stage Connection Successful")
            self.lock_all(0)
        elif self.configuration_check["stage"] == 0:
            self._last_stage_check = 0

        if self.configuration_check["sensor"] == 1 and self._last_sensor_check != 1:
            self._last_sensor_check = 1
            self.sensor_connect_btn.set_text("Connect")
            self.configuration_check["sensor"] = 0
            self.configuration["sensor"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Sensor")
            self.lock_all(0)
        elif self.configuration_check["sensor"] == 2 and self._last_sensor_check != 2:
            self._last_sensor_check = 2
            self.sensor_connect_btn.set_text("Disconnect")
            # Don't reset to 0 - keep it at 2 to indicate connected state
            print("Sensor Connection Successful")
            self.lock_all(0)
        elif self.configuration_check["sensor"] == 0:
            self._last_sensor_check = 0

        if self.configuration_check["tec"] == 1 and self._last_tec_check != 1:
            self._last_tec_check = 1
            self.tec_connect_btn.set_text("Connect")
            self.configuration_check["tec"] = 0
            self.configuration["tec"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect Tec")
            self.lock_all(0)
        elif self.configuration_check["tec"] == 2 and self._last_tec_check != 2:
            self._last_tec_check = 2
            self.tec_connect_btn.set_text("Disconnect")
            # Don't reset to 0 - keep it at 2 to indicate connected state
            print("Tec Connection Successful")
            self.lock_all(0)
        elif self.configuration_check["tec"] == 0:
            self._last_tec_check = 0

        if self.configuration_check.get("smu") == 1 and self._last_smu_check != 1:
            self._last_smu_check = 1
            self.smu_connect_btn.set_text("Connect")
            self.configuration_check["smu"] = 0
            self.configuration["smu"] = ""
            file = File(
                "shared_memory", "Configuration", self.configuration,
                "Configuration_check", self.configuration_check)
            file.save()
            print("Fail To Connect SMU")
            self.lock_all(0)
        elif self.configuration_check.get("smu") == 2 and self._last_smu_check != 2:
            self._last_smu_check = 2
            self.smu_connect_btn.set_text("Disconnect")
            # Don't reset to 0 - keep it at 2 to indicate connected state
            print("SMU Connection Successful")
            self.lock_all(0)
        elif self.configuration_check.get("smu") == 0:
            self._last_smu_check = 0

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

        for idx, key in enumerate(("stage", "sensor", "tec", "smu")):
            # Label
            StyledLabel(
                container=instruments_container, variable_name=f"label_{key}",
                text={"stage": "Stage:",
                    "sensor": "Laser / Detector:",
                    "tec": "TEC:",
                    "smu": "SMU:"}[key],
                left=0, top=15 + idx * 40, width=150, height=20,
                font_size=100, color="#444", align="right"
            )

            # DropDown
            setattr(self, f"{key}_dd", StyledDropDown(
                container=instruments_container,
                text={"stage": ["MMC100_controller", "Corvus_controller", "scylla_controller"],
                    "sensor": ["8164B_NIR", "luna_controller", "Dummy_B"],
                    "tec": ["srs_ldc_502", "srs_ldc_501", "Dummy_B"],
                    "smu": ["keithley_2600", "Dummy_A", "Dummy_B"]}[key],
                variable_name=f"set_{key}",
                left=160, top=10 + idx * 40, width=180, height=30
            ))

            # Connect button (ALWAYS FIRST, ALWAYS SAME POSITION)
            setattr(self, f"{key}_connect_btn", StyledButton(
                container=instruments_container,
                text="Connect",
                variable_name=f"connect_{key}",
                left=360, top=10 + idx * 40,
                normal_color="#007BFF", press_color="#0056B3"
            ))

        # Configure button 
        setattr(self, f"stage_configure_btn", StyledButton(
            container=instruments_container,
            text="Configure VISA",
            variable_name=f"configure_stage",
            left=480, top=10,
            normal_color="#007BFF", press_color="#0056B3"))

        # Camera button (same size, below Configure VISA)
        setattr(self, f"camera_btn", StyledButton(
            container=instruments_container,
            text="Camera",
            variable_name=f"camera_btn",
            left=480, top=50,
            normal_color="#17A2B8", press_color="#117A8B"))
        
        # Calibration button (below Camera button)
        setattr(self, f"calibration_btn", StyledButton(
            container=instruments_container,
            text="Calibration",
            variable_name=f"calibration_btn",
            left=480, top=90,
            normal_color="#28A745", press_color="#1E7E34"))
        
        # Force button (below Calibration button)
        setattr(self, f"force_btn", StyledButton(
            container=instruments_container,
            text="Force",
            variable_name=f"force_btn",
            left=480, top=130,
            normal_color="#28A745", press_color="#1E7E34"))
               

        # NIR Configuration Display
        nir_config_container = StyledContainer(
            container=instruments_container,
            variable_name="nir_config_container",
            left=0, top=220, height=120, width=650, bg_color=False
        )
        
        StyledLabel(
            container=nir_config_container,
            text="NIR Configuration:",
            variable_name="nir_config_header",
            left=10, top=5, width=200, height=20,
            font_size=110, color="#333", bold=True
        )
        
        StyledLabel(
            container=nir_config_container,
            text="Laser GPIB:",
            variable_name="laser_gpib_label",
            left=10, top=30, width=100, height=20,
            font_size=100, color="#666"
        )
        
        self.laser_gpib_display = StyledLabel(
            container=nir_config_container,
            text="Not configured",
            variable_name="laser_gpib_display",
            left=120, top=30, width=200, height=20,
            font_size=100, color="#333"
        )
        
        StyledLabel(
            container=nir_config_container,
            text="Detector GPIB:",
            variable_name="detector_gpib_label",
            left=10, top=55, width=100, height=20,
            font_size=100, color="#666"
        )
        
        self.detector_gpib_display = StyledLabel(
            container=nir_config_container,
            text="Single mainframe mode",
            variable_name="detector_gpib_display",
            left=120, top=55, width=200, height=20,
            font_size=100, color="#333"
        )
        
        StyledLabel(
            container=nir_config_container,
            text="Mode:",
            variable_name="nir_mode_label",
            left=10, top=80, width=100, height=20,
            font_size=100, color="#666"
        )
        
        self.nir_mode_display = StyledLabel(
            container=nir_config_container,
            text="Single Mainframe",
            variable_name="nir_mode_display",
            left=120, top=80, width=200, height=20,
            font_size=100, color="#333", bold=True
        )

        # Terminal
        terminal_container = StyledContainer(
            container=instruments_container,
            variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True  # Moved down for NIR config
        )

        self.terminal = Terminal(
            container=terminal_container,
            variable_name="terminal_text",
            left=10, top=15, width=610, height=100
        )

        # Connect handlers
        self.stage_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_stage_connect_btn))
        self.sensor_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_sensor_connect_btn))
        self.tec_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_tec_connect_btn))
        self.smu_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_smu_connect_btn))

        # Configure handlers (only if present)
        if hasattr(self, "stage_configure_btn"):
            self.stage_configure_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure_btn))
        if hasattr(self, "camera_btn"):
            self.camera_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_camera_btn))
        if hasattr(self, "calibration_btn"):
            self.calibration_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_calibration_btn))
        if hasattr(self, "force_btn"):
            self.force_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_force_btn))

        # Set default dropdown values
        self.stage_dd.set_value("Corvus_controller")
        self.sensor_dd.set_value("8164B_NIR")
        self.tec_dd.set_value("srs_ldc_501")
        self.smu_dd.set_value("keithley_2600")

        self.instruments_container = instruments_container
        return instruments_container


    def onclick_stage_connect_btn(self):
        if self.stage_connect_btn.get_text() == "Connect":
            self.configuration["stage"] = self.stage_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.stage_connect_btn.set_text("Connecting")
            # self.lock_all(1)
        else:
            self.configuration["stage"] = ""
            self.configuration_check["stage"] = 0  # Reset for reconnection
            file = File("shared_memory", "Configuration", self.configuration,
                       "Configuration_check", self.configuration_check)
            file.save()
            self.stage_connect_btn.set_text("Connect")

    def onclick_sensor_connect_btn(self):
        if self.sensor_connect_btn.get_text() == "Connect":
            self.configuration["sensor"] = self.sensor_dd.get_value()
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.sensor_connect_btn.set_text("Connecting")
            # self.lock_all(1)
        else:
            self.configuration["sensor"] = ""
            self.configuration_check["sensor"] = 0  # Reset for reconnection
            file = File("shared_memory", "Configuration", self.configuration,
                       "Configuration_check", self.configuration_check)
            file.save()
            self.sensor_connect_btn.set_text("Connect")

    def onclick_tec_connect_btn(self):
        if self.tec_connect_btn.get_text() == "Connect":
            self.configuration["tec"] = self.tec_dd.get_value()
            self.configuration_check["tec"] = 0
            file = File("shared_memory", "Configuration", self.configuration,
                       "Configuration_check", self.configuration_check)
            file.save()
            self.tec_connect_btn.set_text("Connecting")
            # self.lock_all(1)
        else:
            self.configuration["tec"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.tec_connect_btn.set_text("Connect")

    def onclick_smu_connect_btn(self):
        if self.smu_connect_btn.get_text() == "Connect":
            self.configuration["smu"] = self.smu_dd.get_value()
            self.configuration_check["smu"] = 0
            file = File("shared_memory", "Configuration", self.configuration,
                       "Configuration_check", self.configuration_check)
            file.save()
            self.smu_connect_btn.set_text("Connecting")
        else:
            self.configuration["smu"] = ""
            file = File("shared_memory", "Configuration", self.configuration)
            file.save()
            self.smu_connect_btn.set_text("Connect")

    def onclick_configure_btn(self):
        # Direct webview window opening (server already running from runner.py)
        local_ip = '127.0.0.1'
        webview.create_window(
            'Connection Config',
            f'http://{local_ip}:7005',
            width=223 + web_w,
            height=336 + web_h,
            resizable=True,
            on_top=True
        )

    def onclick_camera_btn(self):
        import subprocess
        import sys
        import threading
        script_path = os.path.join(os.path.dirname(__file__), "open_ucm_camera.py")
        if not os.path.isfile(script_path):
            print(f"[Warn] Camera script not found: {script_path}")
            return

        python_exec = sys.executable
        if sys.platform.startswith("win"):
            if python_exec.lower().endswith("python.exe"):
                candidate = os.path.join(os.path.dirname(python_exec), "pythonw.exe")
                if os.path.isfile(candidate):
                    python_exec = candidate
            self.camera_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            self.camera_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path])

        def _wait_and_restore():
            try:
                proc.wait()
            finally:
                if hasattr(self, "camera_btn"):
                    self.camera_btn.set_enabled(True)

        threading.Thread(target=_wait_and_restore, daemon=True).start()

    def onclick_calibration_btn(self):
        import subprocess
        import sys
        import threading
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ForceFeedback", "calibration.py")
        if not os.path.isfile(script_path):
            print(f"[Warn] Calibration script not found: {script_path}")
            return

        python_exec = sys.executable
        if sys.platform.startswith("win"):
            if python_exec.lower().endswith("python.exe"):
                candidate = os.path.join(os.path.dirname(python_exec), "pythonw.exe")
                if os.path.isfile(candidate):
                    python_exec = candidate
            self.calibration_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            self.calibration_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path])

        def _wait_and_restore():
            try:
                proc.wait()
            finally:
                if hasattr(self, "calibration_btn"):
                    self.calibration_btn.set_enabled(True)

        threading.Thread(target=_wait_and_restore, daemon=True).start()

    def onclick_force_btn(self):
        import subprocess
        import sys
        import threading
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ForceFeedback", "zns_v6_plot_cal.py")
        if not os.path.isfile(script_path):
            print(f"[Warn] Force feedback script not found: {script_path}")
            return

        python_exec = sys.executable
        if sys.platform.startswith("win"):
            if python_exec.lower().endswith("python.exe"):
                candidate = os.path.join(os.path.dirname(python_exec), "pythonw.exe")
                if os.path.isfile(candidate):
                    python_exec = candidate
            self.force_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            self.force_btn.set_enabled(False)
            proc = subprocess.Popen([python_exec, script_path])

        def _wait_and_restore():
            try:
                proc.wait()
            finally:
                if hasattr(self, "force_btn"):
                    self.force_btn.set_enabled(True)

        threading.Thread(target=_wait_and_restore, daemon=True).start()

    def _update_nir_config_display(self, data):
        """Update NIR configuration display from shared memory data."""
        try:
            nir_config = data.get("Port", {})
            
            laser_gpib = nir_config.get("laser_gpib", "Not configured")
            detector_gpib = nir_config.get("detector_gpib", None)
            detector_gpib = detector_gpib[0] if detector_gpib is not None else None

            # Update laser GPIB display
            if hasattr(self, 'laser_gpib_display'):
                self.laser_gpib_display.set_text(str(laser_gpib) if laser_gpib else "Not configured")
            
            # Update detector GPIB display and mode
            if hasattr(self, 'detector_gpib_display') and hasattr(self, 'nir_mode_display'):
                if detector_gpib:
                    self.detector_gpib_display.set_text(str(detector_gpib))
                    self.nir_mode_display.set_text("Multiple Mainframes")
                    self.nir_mode_display.set_style({"color": "#28A745"})  # Green for multi-MF
                else:
                    self.detector_gpib_display.set_text("Single mainframe mode")
                    self.nir_mode_display.set_text("Single Mainframe")
                    self.nir_mode_display.set_style({"color": "#007BFF"})  # Blue for single MF
                    
        except Exception as e:
            print(f"[Warn] NIR config display update failed: {e}")

    def run_in_thread(self, func):
        """Run function in thread."""
        import threading
        threading.Thread(target=func, daemon=True).start()

def run_remi():
    start(
        instruments,
        address="0.0.0.0",
        port=9101,
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
    # local_ip = get_local_ip()
    local_ip = '127.0.0.1'
    webview.create_window(
        "Main Window",
        f"http://{local_ip}:9101",
        width=0,
        height=0,
        resizable=True,
        hidden=True,
    )
    webview.start()
