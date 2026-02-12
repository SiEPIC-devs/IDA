from GUI.lib_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, socket, os, json
from LDC.ldc_manager import LDCManager
from LDC.config.ldc_config import LDCConfiguration

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


class tec_control(App):
    # Class-level shared state
    _ldc_manager = None
    _manager_lock = threading.Lock()
    
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.configuration = {}
        self.configuration_check = {}
        self.configuration_count = 0
        self.configure = None
        self.tec_window = None
        self.port = {}

        self.ld_sweep = {
            "start": 1.0,
            "end": 20.0,
            "step": 0.5,
            "dwell": 100,
            "trigger_delay": 10,
        }
        self.user = None
        self.project = None

        if "editing_mode" not in kwargs:
            super(tec_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    @property
    def ldc_manager(self):
        """Shared LDC manager across all instances"""
        return tec_control._ldc_manager
    
    @ldc_manager.setter
    def ldc_manager(self, value):
        tec_control._ldc_manager = value

    def idle(self):
        try:
            mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            mtime = None
        
        stime = get_shared_memory_mtime()

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

        if stime != self._user_stime:
            self._user_stime = stime
            data = SharedMemory.read({})
            if data:
                self.configuration = data.get("Configuration", {})
                self.configuration_check = data.get("Configuration_check", {})
                self.port = data.get("Port", {})
                self.user = data.get("User", "")
                self.project = data.get("Project", "")
                self.name = data.get("DeviceName", "")

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def after_configuration(self):
        try:
            tec_config = self.configuration.get("tec", "")
            tec_check = self.configuration_check.get("tec", -1)
            tec_port = self.port.get("tec")
            
            with tec_control._manager_lock:
                # Connect when config is set and check is 0
                if tec_config != "" and tec_check == 0 and tec_control._ldc_manager is None:
                    self.configure = LDCConfiguration()
                    self.configure.visa_address = str(tec_port)
                    # driver_types should be a string (driver name), not a dict
                    # tec_config is already the driver name like "srs_ldc_501"
                    
                    manager = LDCManager(self.configure, driver_name=tec_config)
                    success = manager.initialize()

                    if success:
                        tec_control._ldc_manager = manager
                        self.configuration_check["tec"] = 2
                        File("shared_memory", "Configuration_check", self.configuration_check).save()
                        tec_control._ldc_manager.set_temperature(25.0)
                        
                        # Open TEC control window
                        if not hasattr(self, 'tec_window') or self.tec_window is None:
                            local_ip = '127.0.0.1'
                            self.tec_window = webview.create_window(
                                'TEC Control',
                                f'http://{local_ip}:8002',
                                width=402 + web_w,
                                height=536 + web_h,
                                resizable=True,
                                hidden=False
                            )
                    else:
                        self.configuration_check["tec"] = 1
                        File("shared_memory", "Configuration_check", self.configuration_check).save()

                # Disconnect when config is cleared
                elif tec_config == "" and tec_control._ldc_manager is not None:
                    if tec_control._ldc_manager:
                        tec_control._ldc_manager.shutdown()
                        tec_control._ldc_manager = None
                    if hasattr(self, 'tec_window') and self.tec_window:
                        self.tec_window.destroy()
                        self.tec_window = None
        except Exception as e:
            print(f"[TEC] Exception: {e}")
            import traceback
            traceback.print_exc()
        
    def construct_ui(self):
        try: 
            main_container = StyledContainer(
                container=None,
                variable_name="main_container",
                left=0, top=0,
                height=480,
                width=380
            )

            # === TEC Control Section ===
            tec_container = StyledContainer(
                container=main_container,
                variable_name="tec_container",
                left=10, top=10,
                height=100,
                width=360,
                border=True
            )

            StyledLabel(
                container=tec_container,
                text="Temperature Control",
                variable_name="tec_section_label",
                left=10, top=5,
                width=160, height=25,
                font_size=110,
                bold=True,
                color="#2c3e50"
            )

            self.tec_on_box = StyledCheckBox(
                container=tec_container,
                variable_name="tec_on_box",
                left=20, top=34,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=tec_container,
                text="TEC Enable",
                variable_name="tec_on_label",
                left=50, top=41,
                width=100, height=25,
                font_size=100,
                justify_content="left"
            )

            StyledLabel(
                container=tec_container,
                text="Setpoint [°C]:",
                variable_name="temp_label",
                left=20, top=68,
                width=110, height=25,
                font_size=100,
                align="right"
            )

            self.minus_temp = StyledButton(
                container=tec_container,
                text="-",
                variable_name="temp_left_button",
                font_size=100,
                left=140, top=65,
                width=30, height=24,
                normal_color="#3498db",
                press_color="#2980b9"
            )

            self.temp_spinbox = StyledSpinBox(
                container=tec_container,
                variable_name="temp_input",
                left=175, top=65,
                min_value=15,
                max_value=75,
                value=25,
                step=0.1,
                width=55,
                height=24
            )

            self.plus_temp = StyledButton(
                container=tec_container,
                text="+",
                variable_name="temp_right_button",
                font_size=100,
                left=252, top=65,
                width=30, height=24,
                normal_color="#3498db",
                press_color="#2980b9"
            )

            # === LD Control Section ===
            ld_container = StyledContainer(
                container=main_container,
                variable_name="ld_container",
                left=10, top=120,
                height=165,
                width=360,
                border=True
            )

            StyledLabel(
                container=ld_container,
                text="Laser Diode Control",
                variable_name="ld_control_header",
                left=10, top=5,
                width=160, height=25,
                font_size=110,
                bold=True,
                color="#2c3e50"
            )

            self.ld_on_box = StyledCheckBox(
                container=ld_container,
                variable_name="ld_on_box",
                left=20, top=32,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=ld_container,
                text="LD Enable",
                variable_name="ld_on_label",
                left=50, top=39,
                width=100, height=25,
                font_size=100,
                justify_content="left"
            )

            # Current Control Row
            StyledLabel(
                container=ld_container,
                text="Current [mA]:",
                variable_name="current_label",
                left=20, top=69,
                width=110, height=24,
                font_size=95,
                align="right"
            )

            self.ld_current = StyledSpinBox(
                container=ld_container,
                variable_name="ld_current_input",
                left=140, top=65,
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=0.1,
                width=60,
                height=24
            )

            self.set_current_btn = StyledButton(
                container=ld_container,
                variable_name="set_current_btn",
                text="Set",
                left=225, top=66,
                width=55, height=24,
                font_size=90,
                normal_color="#27ae60",
                press_color="#229954"
            )

            # Current Limit Row
            StyledLabel(
                container=ld_container,
                text="I Limit [mA]:",
                variable_name="current_lim_label",
                left=20, top=100,
                width=110, height=24,
                font_size=95,
                align="right"
            )

            self.i_limit = StyledSpinBox(
                container=ld_container,
                variable_name="i_limit_input",
                left=140, top=96,
                min_value=0.1,
                max_value=500.0,
                value=100.0,
                step=1.0,
                width=60,
                height=24
            )

            self.set_i_limit_btn = StyledButton(
                container=ld_container,
                text="Set",
                variable_name="set_i_limit_btn",
                left=225, top=97,
                width=55, height=24,
                font_size=90,
                normal_color="#27ae60",
                press_color="#229954"
            )

            # Voltage Limit Row
            StyledLabel(
                container=ld_container,
                text="V Limit [V]:",
                variable_name="voltage_lim_label",
                left=20, top=131,
                width=110, height=24,
                font_size=95,
                align="right"
            )

            self.v_limit = StyledSpinBox(
                container=ld_container,
                variable_name="v_limit_input",
                left=140, top=127,
                min_value=0.1,
                max_value=10.0,
                value=2.5,
                step=0.1,
                width=60,
                height=24
            )

            self.set_v_limit_btn = StyledButton(
                container=ld_container,
                text="Set",
                variable_name="set_v_limit_btn",
                left=225, top=128,
                width=55, height=24,
                font_size=90,
                normal_color="#27ae60",
                press_color="#229954"
            )
            # === LD Current Sweep Section ===
            ld_sweep_container = StyledContainer(
                container=main_container,
                variable_name="ld_sweep_container",
                left=10, top=295,
                width=360, height=175,
                border=True
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Current Sweep",
                variable_name="sweep_section_label",
                left=10, top=5,
                width=150, height=25,
                font_size=110,
                bold=True,
                color="#2c3e50"
            )

            self.ld_sweep_btn = StyledButton(
                container=ld_sweep_container,
                text="Run Sweep",
                variable_name="ld_sweep_btn",
                left=257, top=140,
                width=85, height=25,
                font_size=95,
                normal_color="#e74c3c",
                press_color="#c0392b"
            )

            # First row: Start and End
            StyledLabel(
                container=ld_sweep_container,
                text="Start [mA]:",
                variable_name="start_sweep_label",
                left=10, top=46, width=85, height=25,
                font_size=95, align="right"
            )
            
            self.ld_start = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_start",
                left=100, top=43,
                min_value=0.1, max_value=500,
                value=1.0, step=0.1,
                width=55, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="End [mA]:",
                variable_name="end_sweep_label",
                left=185, top=46, width=80, height=25,
                font_size=95, align="right"
            )
            
            self.ld_end = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_end",
                left=270, top=43,
                min_value=0.1, max_value=500,
                value=20.0, step=0.1,
                width=55, height=24
            )

            # Second row: Step and Dwell
            StyledLabel(
                container=ld_sweep_container,
                text="Step [mA]:",
                variable_name="sweep_step_label",
                left=10, top=77, width=85, height=25,
                font_size=95, align="right"
            )
            
            self.ld_step = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_step",
                left=100, top=74,
                min_value=0.01, max_value=50,
                value=0.5, step=0.01,
                width=55, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Dwell [ms]:",
                variable_name="sweep_dwell_label",
                left=185, top=77, width=80, height=25,
                font_size=95, align="right"
            )
            
            self.ld_dwell = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_dwell",
                left=270, top=74,
                min_value=10, max_value=10000,
                value=100, step=10,
                width=55, height=24
            )

            # Third row: Trigger Delay
            StyledLabel(
                container=ld_sweep_container,
                text="Trigger Delay [ms]:",
                variable_name="sweep_trig_label",
                left=120, top=108, width=145, height=25,
                font_size=95, align="right"
            )
            
            self.ld_trig_delay = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_trig_delay",
                left=270, top=105,
                min_value=0, max_value=1000,
                value=10, step=1,
                width=55, height=24
            )

            # High Range Checkbox
            self.ld_range_high = StyledCheckBox(
                container=ld_sweep_container,
                variable_name="ld_range_box",
                left=20, top=137,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=ld_sweep_container,
                text="High Range Mode (>100mA)",
                variable_name="sweep_safety_label",
                left=50, top=143,
                width=200, height=25,
                font_size=95,
                justify_content="left",
                color="#e67e22"
            )

            # Wire up event handlers
            self.minus_temp.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_temp))
            self.plus_temp.do_onclick(lambda *_: self.run_in_thread(self.onclick_plus_temp))
            self.temp_spinbox.onchange.do(lambda e, v: self.run_in_thread(self.onchange_temp, e, v))
            self.tec_on_box.onchange.do(lambda e, v: self.run_in_thread(self.onchange_tec_box, e, v))
            
            self.ld_on_box.onchange.do(lambda e, v: self.run_in_thread(self.onchange_ld_box, e, v))
            self.set_current_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_current))
            self.set_i_limit_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_i_limit))
            self.set_v_limit_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_v_limit))
            
            self.ld_sweep_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_ld_sweep))
            self.ld_range_high.onchange.do(lambda e, v: self.run_in_thread(self.onchange_range, e, v))

            return main_container
        except Exception as e:
            print(f"Fine as well: {e}")
            import sys
            print(f"line: {sys.exc_info()[-1].tb_lineno}")    


    # === TEC Handlers ===
    
    def _safe_ldc_call(self, func, *args, **kwargs):
        """Thread-safe wrapper: grab manager ref and verify connected before calling."""
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return None
        try:
            return func(mgr, *args, **kwargs)
        except Exception as e:
            print(f"[TEC] Safe call failed: {e}")
            return None

    def onclick_minus_temp(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        value = round(float(self.temp_spinbox.get_value()), 1)
        value = round(max(15.0, min(75.0, value - 0.1)), 1)
        self.temp_spinbox.set_value(value)
        self._safe_ldc_call(lambda m, v: m.set_temperature(v), value)

    def onclick_plus_temp(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        value = round(float(self.temp_spinbox.get_value()), 1)
        value = round(max(15.0, min(75.0, value + 0.1)), 1)
        self.temp_spinbox.set_value(value)
        self._safe_ldc_call(lambda m, v: m.set_temperature(v), value)

    def onchange_temp(self, emitter, value):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        rounded_value = round(float(value), 1)
        self.temp_spinbox.set_value(rounded_value)
        self._safe_ldc_call(lambda m, v: m.set_temperature(v), rounded_value)

    def onchange_tec_box(self, emitter, value):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        if value:
            self._safe_ldc_call(lambda m: m.tec_on())
        else:
            self._safe_ldc_call(lambda m: m.tec_off())

    # === LD Handlers ===
    
    def onchange_ld_box(self, emitter, value):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        
        # Safety: require TEC ON before enabling LD
        if value and not self.tec_on_box.get_value():
            print("LD enable blocked: TEC must be ON first")
            self.ld_on_box.set_value(False)
            return
        
        if value:
            self._safe_ldc_call(lambda m: m.ld_on())
        else:
            self._safe_ldc_call(lambda m: m.ld_off())

    def onclick_set_current(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        current = float(self.ld_current.get_value())
        self._safe_ldc_call(lambda m, c: m.set_ld_current(c), current)
        print(f"LD current set to {current} mA")

    def onclick_set_i_limit(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        limit = float(self.i_limit.get_value())
        self._safe_ldc_call(lambda m, l: m.set_ld_current_limit(l), limit)
        print(f"LD current limit set to {limit} mA")

    def onclick_set_v_limit(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        limit = float(self.v_limit.get_value())
        self._safe_ldc_call(lambda m, l: m.set_ld_voltage_limit(l), limit)
        print(f"LD voltage limit set to {limit} V")

    def onchange_range(self, emitter, value):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return
        self._safe_ldc_call(lambda m, v: m.set_ld_current_range(high=bool(v)), value)
        print(f"LD range set to {'HIGH' if value else 'LOW'}")

    def onclick_ld_sweep(self):
        mgr = self.ldc_manager
        if not mgr or not mgr.is_connected():
            return

        # Safety: require TEC ON
        if not self.tec_on_box.get_value():
            print("LD sweep blocked: TEC is OFF")
            return

        start_ma = float(self.ld_start.get_value())
        stop_ma = float(self.ld_end.get_value())
        step_ma = float(self.ld_step.get_value())
        dwell_ms = int(self.ld_dwell.get_value())
        trig_delay_ms = int(self.ld_trig_delay.get_value())

        print(f"Starting LD sweep: {start_ma}->{stop_ma} mA, step={step_ma}, dwell={dwell_ms}ms")
        
        data = mgr.ld_current_sweep(
            start_ma=start_ma,
            stop_ma=stop_ma,
            step_ma=step_ma,
            dwell_ms=dwell_ms,
            trigger_delay_ms=trig_delay_ms,
        )

        # lib_gui
        plot_ld_sweep(
            scan_data=data,
            filename='IVSweep',
            fileTime=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            user=self.user,
            name=self.name,
            project=self.project
        )
        print("LD sweep complete")

    def execute_command(self, path=command_path):
        try:
            data = read_command_file()
            command = data.get("command", {})
        except Exception:
            return

        if "tec_on" in command:
            self.tec_on_box.set_value(1)
        if "tec_off" in command:
            self.tec_on_box.set_value(0)
        if "tec_temp" in command:
            self.temp_spinbox.set_value(command["tec_temp"])


def run_remi():
    start(
        tec_control,
        address="0.0.0.0",
        port=8002,
        start_browser=False,
        multiple_instance=False
    )


if __name__ == '__main__':
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    local_ip = '127.0.0.1'
    webview.create_window(
        'TEC Control',
        f'http://{local_ip}:8002',
        width=402 + web_w,
        height=536 + web_h,
        resizable=True,
        hidden=True
    )
    webview.start()