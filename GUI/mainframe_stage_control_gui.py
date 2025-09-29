from GUI.lib_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal
from GUI import lib_coordinates
import asyncio, datetime
from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration
from measure.area_sweep import AreaSweep
from measure.fine_align import FineAlign
from measure.config.area_sweep_config import AreaSweepConfiguration
from measure.config.fine_align_config import FineAlignConfiguration
import time

filename = "coordinates.json"

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


class stage_control(App):
    def __init__(self, *args, **kwargs):
        self.memory = None
        self.configure = None
        self.stage_manager = None
        self.x_position_lb = None
        self.y_position_lb = None
        self.z_position_lb = None
        self.chip_position_lb = None
        self.fiber_position_lb = None
        self._user_mtime = None
        self._first_command_check = True
        self._user_stime = None
        self.user = "Guest"
        self.limit = {}
        self.area_s = {}
        self.fine_a = {}
        self.auto_sweep = 0
        self.count = 0
        self.filter = {}
        self.configuration = {}
        self.configuration_check = {}
        self.port = {}
        self.data_window = {}

        self.configuration_stage = 0
        self.configuration_sensor = 0
        self.project = None
        self.scanpos = {}
        self.stagepos = {}
        self.stage_x_pos = 0
        self.stage_y_pos = 0
        self.sweep = {}
        self.name = None
        self.sweep_count = 0
        self.pre_x = None
        self.pre_y = None
        self.stage_window = None
        self.sensor_window = None
        self.devices = None
        self.web = None
        self.file_format = {}
        self.file_path = None

        self.nir_configure = None
        self.nir_manager = None

        self.past_laser_on = 0
        self.past_wvl = None
        self.past_power = None

        self.data = None
        self._scan_done = Value(c_int, 0)
        self.ch_count = 0
        self.ch_last_time = 0
        self.ch_current_time = 0
        self.task_start = 0
        self._win_lock = threading.Lock()
        self.axis_locked = {"x": False, "y": False, "z": False, "chip": False, "fiber": False}
        self.area_sweep = None
        self.fine_align = None
        self.task_laser = 0

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
                    self.limit = data.get("Limit", {})
                    self.area_s = data.get("AreaS", {})
                    self.fine_a = data.get("FineA", {})
                    self.auto_sweep = data.get("AutoSweep", 0)
                    self.filter = data.get("Filtered", {})
                    self.configuration = data.get("Configuration", {})
                    self.configuration_check = data.get("Configuration_check", {})
                    self.scanpos = data.get("ScanPos", {})
                    self.sweep = data.get("Sweep", {})
                    self.name = data.get("DeviceName", "")
                    self.data_window = data.get("DataWindow", {})
                    self.port = data.get("Port", {})
                    self.web = data.get("Web", "")
                    self.file_format = data.get("FileFormat", {})
                    self.file_path = data.get("FilePath", "")
                    
                    # Read detector range and reference settings
                    detector_range_ch1 = data.get("DetectorRange_Ch1", {})
                    detector_range_ch2 = data.get("DetectorRange_Ch2", {})
                    detector_ref_ch1 = data.get("DetectorReference_Ch1", {})
                    detector_ref_ch2 = data.get("DetectorReference_Ch2", {})
                    
                    # Apply detector settings if NIR manager is available
                    if hasattr(self, 'nir_manager') and self.nir_manager and self.configuration_sensor == 1:
                        if detector_range_ch1.get("range_dbm") is not None:
                            self.nir_manager.set_power_range(detector_range_ch1["range_dbm"], 1)
                        if detector_range_ch2.get("range_dbm") is not None:
                            self.nir_manager.set_power_range(detector_range_ch2["range_dbm"], 2)
                        if detector_ref_ch1.get("ref_dbm") is not None:
                            self.nir_manager.set_power_reference(detector_ref_ch1["ref_dbm"], 1)
                        if detector_ref_ch2.get("ref_dbm") is not None:
                            self.nir_manager.set_power_reference(detector_ref_ch2["ref_dbm"], 2)
                            
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def set_power(self):
        self.nir_manager.set_power(self.sweep["power"])
        self.sweep_count = 0

    def set_wvl(self):
        self.nir_manager.set_wavelength(self.sweep["wvl"])
        self.sweep_count = 0

    def laser_on(self):
        self.nir_manager.enable_laser(self.sweep["on"])
        self.sweep_count = 0

    def laser_sweep(self, name=None):
        print("Sweep Start")
        auto = 0
        if name is None:
            name = self.name
            self.busy_dialog()
            self.task_start = 1
            self.task_laser = 1
            self.lock_all(1)
        else:
            self.task_start = 1
            auto = 1

        try:
            wl, d1, d2 = self.nir_manager.sweep(
                start_nm=self.sweep["start"],
                stop_nm=self.sweep["end"],
                step_nm=self.sweep["step"],
                laser_power_dbm=self.sweep["power"]
            )
        except Exception as e:
            print(f"[Error] Sweep failed: {e}")
            wl, d1, d2 = [], [], []

        x = wl
        y = np.vstack([d1, d2])
        fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        diagram = plot(
            x, y, "spectral_sweep", fileTime, self.user, name,
            self.project, auto, self.file_format, self.file_path
        )
        p = Process(target=diagram.generate_plots)
        p.start()
        p.join()

        if self.web != "" and auto == 0:
            file_uri = Path(self.web).resolve().as_uri()
            print(file_uri)
            webview.create_window(
                'Stage Control',
                file_uri,
                width=700, height=500,
                resizable=True,
                hidden=False
            )

        if auto == 0:
            if self.sweep["done"] == "Laser On":
                self.nir_manager.enable_laser(True)
            else:
                self.nir_manager.enable_laser(False)

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0
                self.task_laser = 0
                self.lock_all(0)

            self.sweep_count = 0
            self.sweep["sweep"] = 0
            file = File("shared_memory", "Sweep", self.sweep)
            file.save()
        print("Sweep Done")

    def scan_move(self):
        x_pos = self.scanpos["x"] * self.area_s["x_step"] + self.stage_x_pos
        y_pos = self.scanpos["y"] * self.area_s["y_step"] + self.stage_y_pos
        # Respect per-axis locks
        if not self.axis_locked["x"]:
            asyncio.run(self.stage_manager.move_axis(AxisType.X, x_pos, False))
        if not self.axis_locked["y"]:
            asyncio.run(self.stage_manager.move_axis(AxisType.Y, y_pos, False))
        print(f"Move to: {x_pos}, {y_pos}")
        self.scanpos["move"] = 0
        file = File("shared_memory", "ScanPos", self.scanpos)
        file.save()

    def after_configuration(self):
        if self.configuration["stage"] != "" and self.configuration_stage == 0 and self.configuration_check[
            "stage"] == 0:
            self.gds = lib_coordinates.coordinates(("./res/" + filename), read_file=False,
                                                   name="./database/coordinates.json")
            self.number = self.gds.listdeviceparam("number")
            self.coordinate = self.gds.listdeviceparam("coordinate")
            self.polarization = self.gds.listdeviceparam("polarization")
            self.wavelength = self.gds.listdeviceparam("wavelength")
            self.type = self.gds.listdeviceparam("type")
            self.devices = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]

            self.memory = Memory()
            self.configure = StageConfiguration()
            self.configure.driver_types[AxisType.X] = self.configuration["stage"]
            self.configure.driver_types[AxisType.Y] = self.configuration["stage"]
            self.configure.driver_types[AxisType.Z] = self.configuration["stage"]
            self.configure.driver_types[AxisType.ROTATION_CHIP] = self.configuration["stage"]
            self.configure.driver_types[AxisType.ROTATION_FIBER] = self.configuration["stage"]
            self.stage_manager = StageManager(self.configure, create_shm=True, port=self.port["stage"])
            asyncio.run_coroutine_threadsafe(
                self.stage_manager.startup(),
                main_loop
            )
            success_stage = asyncio.run(self.stage_manager.initialize_all(
                [AxisType.X, AxisType.Y, AxisType.Z, AxisType.ROTATION_CHIP, AxisType.ROTATION_FIBER])
            )
            if success_stage:
                self.configuration_stage = 1
                self.configuration_check["stage"] = 2
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()
                self.stage_window = webview.create_window(
                    'Stage Control',
                    f'http://{local_ip}:8000',
                    width=842 + web_w, height=397 + web_h,
                    x=800, y=465,
                    resizable=True,
                    hidden=False
                )
            else:
                self.configuration_stage = 0
                self.configuration_check["stage"] = 1
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()

        elif self.configuration["stage"] == "" and self.configuration_stage == 1:
            self.configuration_stage = 0
            if self.stage_window:
                self.stage_window.destroy()
                self.stage_window = None
            self.stage_manager.shutdown()
            print("Stage Disconnected")

        if self.configuration["sensor"] != "" and self.configuration_sensor == 0 and self.configuration_check[
            "sensor"] == 0:
            self.nir_configure = NIRConfiguration()
            self.nir_configure.gpib_addr = self.port["sensor"]
            self.nir_manager = NIRManager(self.nir_configure)
            success_sensor = self.nir_manager.initialize()
            if success_sensor:
                self.configuration_sensor = 1
                self.configuration_check["sensor"] = 2
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()
                self.sensor_window = webview.create_window(
                    'Sensor Control',
                    f'http://{local_ip}:8001',
                    width=672 + web_w, height=197 + web_h,
                    x=800, y=255,
                    resizable=True,
                    hidden=False
                )
            else:
                self.configuration_sensor = 0
                self.configuration_check["sensor"] = 1
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()

        elif self.configuration["sensor"] == "" and self.configuration_sensor == 1:
            self.configuration_sensor = 0
            if self.sensor_window:
                self.sensor_window.destroy()
                self.sensor_window = None
            self.nir_manager.disconnect()
            print("Sensor Disconnected")

        if self.configuration_stage == 1:
            self.memory.reader_pos()
            if self.memory.x_pos != float(self.x_position_lb.get_text()):
                self.x_position_lb.set_text(str(self.memory.x_pos))
            if self.memory.y_pos != float(self.y_position_lb.get_text()):
                self.y_position_lb.set_text(str(self.memory.y_pos))
            if self.memory.z_pos != float(self.z_position_lb.get_text()):
                self.z_position_lb.set_text(str(self.memory.z_pos))
            if self.memory.cp_pos != float(self.chip_position_lb.get_text()):
                self.chip_position_lb.set_text(str(self.memory.cp_pos))
            if self.memory.fr_pos != float(self.fiber_position_lb.get_text()):
                self.fiber_position_lb.set_text(str(self.memory.fr_pos))

        if self.configuration_sensor == 1:
            if self.sweep["sweep"] == 1 and self.sweep_count == 0:
                self.sweep_count = 1
                self.run_in_thread(self.laser_sweep)

            if self.sweep["on"] != self.past_laser_on and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_laser_on = self.sweep["on"]
                self.run_in_thread(self.laser_on)

            if self.sweep["wvl"] != self.past_wvl and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_wvl = self.sweep["wvl"]
                self.run_in_thread(self.set_wvl)

            if self.sweep["power"] != self.past_power and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_power = self.sweep["power"]
                self.run_in_thread(self.set_power)

        if self.configuration_stage == 1 and self.configuration_sensor == 1:
            if self.auto_sweep == 1 and self.count == 0:
                self.lock_all(1)
                self.count = 1

                # Calculate progress config for auto sweep
                device_count = len(self.filter) if hasattr(self, 'filter') and self.filter else 0
                if device_count > 0:
                    estimated_total = self._estimate_total_time(device_count)
                    estimated_per_device = estimated_total / device_count
                    progress_config = {
                        'total_devices': device_count,
                        'estimated_total_time': estimated_total,
                        'estimated_per_device': estimated_per_device
                    }
                    self.busy_dialog(progress_config)
                else:
                    self.busy_dialog()

                self.task_start = 1
                self.run_in_thread(self.do_auto_sweep)

            elif self.auto_sweep == 0 and self.count == 1:
                self.lock_all(0)
                self.count = 0
                self.nir_manager.cancel_sweep()
                if self.fine_align != None:
                    self.fine_align.stop_alignment()

            if self.scanpos["move"] == 1 and (self.scanpos["x"] != self.pre_x or self.scanpos["y"] != self.pre_y):
                self.run_in_thread(self.scan_move)
                self.pre_x = self.scanpos["x"]
                self.pre_y = self.scanpos["y"]

            if self.ch_count == 0:
                self.ch_count = 1
                self.run_in_thread(self.update_ch)

            self.stop_task()

    def stop_task(self):
        if self._scan_done.value == -1:
            self._scan_done.value = 0
            self.task_start = 0
            if self.area_sweep != None:
                self.area_sweep.stop_sweep()
            if self.fine_align != None:
                self.fine_align.stop_alignment()
            if self.task_laser == 1:
                self.task_laser = 0
                self.nir_manager.cancel_sweep()
            if self.auto_sweep == 1 and self.count == 1:
                self.auto_sweep = 0
                file = File("shared_memory", "AutoSweep", 0)
                file.save()
                self.nir_manager.cancel_sweep()
                if self.fine_align != None:
                    self.fine_align.stop_alignment()

            self.lock_all(0)

    def update_ch(self):
        while True:
            if self.task_start == 0:
                ch1, ch2 = self.nir_manager.read_power()
                self.ch1_val.set_text(str(ch1))
                self.ch2_val.set_text(str(ch2))
                time.sleep(1)
            else:
                print("### Waiting ###")
                time.sleep(1)

    def do_auto_sweep(self):
        device_count = len(self.filter)
        estimated_total_time = self._estimate_total_time(device_count)
        device_start_times = []

        print(f"Starting auto sweep of {device_count} devices (estimated {estimated_total_time:.0f}s total)")

        i = 0
        while i < device_count:
            print("It's " + str(i))
            if self.auto_sweep == 0:
                break

            device_start_time = time.time()
            device_start_times.append(device_start_time)
            device_num = i + 1

            key = list(self.filter.keys())
            x = float(self.filter[key[i]][0])
            y = float(self.filter[key[i]][1])

            # Update progress: Moving to device
            progress_percent = (i / device_count) * 100
            activity = f"Moving to Device {device_num}/{device_count}"
            self._write_progress_file(device_num, activity, progress_percent)
            print(f"Move to Device {device_num} [{x}, {y}]")

            # Respect per-axis locks for XY moves
            if not self.axis_locked["x"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            if not self.axis_locked["y"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))
            if self.auto_sweep == 0:
                break

            # Update progress: Fine alignment
            progress_percent = (i / device_count) * 100 + (20 / device_count)  # Add 20% for alignment
            activity = f"Device {device_num}/{device_count}: Fine alignment"
            self._write_progress_file(device_num, activity, progress_percent)

            self.onclick_start()
            if self.auto_sweep == 0:
                break

            # Update progress: Spectral sweep
            progress_percent = (i / device_count) * 100 + (70 / device_count)  # Add 70% for sweep
            activity = f"Device {device_num}/{device_count}: Spectral sweep"
            self._write_progress_file(device_num, activity, progress_percent)

            self.laser_sweep(name=self.devices[int(key[i])])

            # Update progress: Device completed
            progress_percent = ((i + 1) / device_count) * 100
            activity = f"Device {device_num}/{device_count}: Completed"
            self._write_progress_file(device_num, activity, progress_percent)

            file = File("shared_memory", "DeviceName", self.devices[int(key[i])], "DeviceNum", int(key[i]))
            file.save()

            # Calculate actual device time for learning
            device_time = time.time() - device_start_time
            print(f"Device {device_num} completed in {device_time:.1f}s")

            i += 1

        # Final completion
        self._write_progress_file(device_count, "All measurements completed", 100)

        with self._scan_done.get_lock():
            self._scan_done.value = 1
            self.task_start = 0
        print("The Auto Sweep Is Finished")
        time.sleep(1)
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    # NEW: enable/disable a single axis row widgets together
    def set_axis_enabled(self, prefix: str, enabled: bool):
        getattr(self, f"{prefix}_left_btn").set_enabled(enabled)
        getattr(self, f"{prefix}_right_btn").set_enabled(enabled)
        getattr(self, f"{prefix}_input").set_enabled(enabled)

    # NEW: checkbox handler updating the lock state
    def onchange_axis_lock(self, prefix: str, value):
        # remi CheckBox sends 1 for checked, 0 for unchecked
        self.axis_locked[prefix] = bool(value)
        self.set_axis_enabled(prefix, not self.axis_locked[prefix])
        print(f"[Axis Lock] {prefix} -> {'LOCKED' if self.axis_locked[prefix] else 'UNLOCKED'}")

    def lock_all(self, value):
        enabled = value == 0
        widgets_to_check = [self.stage_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            # keep global lock and per-axis lock checkboxes enabled
            if hasattr(widget, "variable_name"):
                vn = widget.variable_name
                if vn == "lock_box" or (isinstance(vn, str) and vn.endswith("_lock")):
                    pass
                elif isinstance(widget, (Button, SpinBox, CheckBox, DropDown)):
                    widget.set_enabled(enabled)
            elif isinstance(widget, (Button, SpinBox, CheckBox, DropDown)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

        # after UNLOCK, reapply per-axis lock disables
        if enabled:
            for pfx, is_locked in self.axis_locked.items():
                self.set_axis_enabled(pfx, not is_locked)

    def construct_ui(self):
        # -------- layout constants (positions/sizes only) --------
        LEFT_PANEL_W = 490  # wider left box so rows + Zero buttons fit cleanly
        LOCK_COL_LEFT = 18  # per-axis lock column (aligns with top lock icon)
        ICON_LEFT = 18  # big lock icon
        LABEL_LEFT = 38  # axis text column (left of readouts)
        POS_LEFT = 35  # position numeric readout
        UNIT_LEFT = 150  # unit next to readout
        BTN_L_LEFT = 185  # left jog button
        SPIN_LEFT = 245  # step spinbox
        BTN_R_LEFT = 345  # right jog button
        ZERO_LEFT = 415  # Zero button (placeholder)
        ROW_TOPS = [70, 110, 150, 190, 230]
        ROW_H = 30

        RIGHT_START = LEFT_PANEL_W + 20  # right-hand panels start after wider box
        # ---------------------------------------------------------

        stage_control_container = StyledContainer(
            container=None, variable_name="stage_control_container",
            left=0, top=0, height=320, width=830
        )

        xyz_container = StyledContainer(
            container=stage_control_container, variable_name="xyz_container",
            left=0, top=20, height=300, width=LEFT_PANEL_W  # was narrower
        )

        self.stop_btn = StyledButton(
            container=xyz_container, text="Stop", variable_name="stop_button", font_size=100,
            left=POS_LEFT, top=10, width=90, height=30, normal_color="#dc3545", press_color="#c82333"
        )

        self.lock_box = StyledCheckBox(
            container=xyz_container, variable_name="lock_box",
            left=POS_LEFT + 100, top=10, width=10, height=10, position="absolute"
        )

        StyledLabel(
            container=xyz_container, text="Lock", variable_name="lock_label",
            left=POS_LEFT + 130, top=17, width=80, height=50, font_size=100, color="#222"
        )

        # Big lock icon aligned with per-axis lock column
        StyledLabel(
            container=xyz_container, text="🔒", variable_name="per_axis_lock_icon",
            left=ICON_LEFT, top=38, width=10, height=16, font_size=160, color="#444"
        )

        labels = ["X", "Y", "Z", "Chip", "Fiber"]
        left_arrows = ["⮜", "⮟", "Down", "⭮", "⭮"]
        right_arrows = ["⮞", "⮝", "Up", "⭯", "⭯"]
        var_prefixes = ["x", "y", "z", "chip", "fiber"]
        position_texts = ["0", "0", "0", "0", "0"]
        position_unit = ["um", "um", "um", "deg", "deg"]
        init_value = ["10.0", "10.0", "10.0", "0.1", "0.1"]

        for i in range(5):
            prefix = var_prefixes[i]
            top = ROW_TOPS[i]

            # per-axis lock checkbox (aligned with header icon)
            setattr(self, f"{prefix}_lock", StyledCheckBox(
                container=xyz_container, variable_name=f"{prefix}_lock",
                left=LOCK_COL_LEFT, top=top , width=12, height=12
            ))

            # axis label (left column)
            StyledLabel(
                container=xyz_container, text=labels[i], variable_name=f"{prefix}_label",
                left=LABEL_LEFT, top=top, width=55, height=ROW_H,
                font_size=100, color="#222", flex=True, bold=True, justify_content="center"
            )

            # position readout + unit (next column)
            setattr(self, f"{prefix}_position_lb", StyledLabel(
                container=xyz_container, text=position_texts[i], variable_name=f"{prefix}_position_lb",
                left=POS_LEFT+50, top=top, width=70, height=ROW_H, font_size=100, color="#222",
                flex=True, bold=True, justify_content="left"
            ))
            setattr(self, f"{prefix}_limit_lb", StyledLabel(
                container=xyz_container, text="lim: N/A", variable_name=f"{prefix}_limit_lb",
                left=POS_LEFT, top=top + 22, width=100, height=20, font_size=70, color="#666",
                flex=True, justify_content="right"
            ))
            setattr(self, f"{prefix}_position_unit", StyledLabel(
                container=xyz_container, text=position_unit[i], variable_name=f"{prefix}_position_unit",
                left=UNIT_LEFT, top=top, width=40, height=ROW_H, font_size=100, color="#222",
                flex=True, bold=True, justify_content="left"
            ))

            # jog controls (shifted right)
            setattr(self, f"{prefix}_left_btn", StyledButton(
                container=xyz_container, text=left_arrows[i], variable_name=f"{prefix}_left_button", font_size=100,
                left=BTN_L_LEFT, top=top, width=50, height=ROW_H, normal_color="#007BFF", press_color="#0056B3"
            ))
            setattr(self, f"{prefix}_input", StyledSpinBox(
                container=xyz_container, variable_name=f"{prefix}_step", min_value=0, max_value=1000,
                value=init_value[i], step=0.1, left=SPIN_LEFT, top=top, width=73, height=ROW_H, position="absolute"
            ))
            setattr(self, f"{prefix}_right_btn", StyledButton(
                container=xyz_container, text=right_arrows[i], variable_name=f"{prefix}_right_button", font_size=100,
                left=BTN_R_LEFT, top=top, width=50, height=ROW_H, normal_color="#007BFF", press_color="#0056B3"
            ))

            # Zero button placeholder
            setattr(self, f"{prefix}_zero_btn", StyledButton(
                container=xyz_container, text="Zero", variable_name=f"{prefix}_zero_button", font_size=100,
                left=ZERO_LEFT, top=top, width=55, height=ROW_H, normal_color="#6c757d", press_color="#5a6268"
            ))

        # ---- Right-hand panels (tighter vertical spacing; start after wider left box) ----
        limits_container = StyledContainer(
            container=stage_control_container, variable_name="limits_container",
            left=RIGHT_START, top=12, height=90, width=90, border=True  # top was 20
        )
        StyledLabel(
            container=limits_container, text="Home Lim", variable_name="limits_label",
            left=12, top=-12, width=66, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.limit_setting_btn = StyledButton(
            container=limits_container, text="Setting", variable_name="limit_setting_btn", font_size=100,
            left=5, top=10, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )
        self.home_btn = StyledButton(
            container=limits_container, text="Home", variable_name="home_btn", font_size=100,
            left=5, top=50, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        fine_align_container = StyledContainer(
            container=stage_control_container, variable_name="fine_align_container",
            left=RIGHT_START + 100, top=12, height=90, width=90, border=True  # top was 20
        )
        StyledLabel(
            container=fine_align_container, text="Fine Align", variable_name="fine_align_label",
            left=12.5, top=-12, width=65, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.fine_align_setting_btn = StyledButton(
            container=fine_align_container, text="Setting", variable_name="fine_align_setting_btn", font_size=100,
            left=5, top=10, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )
        self.start_btn = StyledButton(
            container=fine_align_container, text="Start", variable_name="start_button", font_size=100,
            left=5, top=50, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        area_scan_container = StyledContainer(
            container=stage_control_container, variable_name="area_scan_container",
            left=RIGHT_START + 200, top=12, height=90, width=90, border=True  # top was 20
        )
        StyledLabel(
            container=area_scan_container, text="Area Scan", variable_name="area_scan_label",
            left=13, top=-12, width=65, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.scan_setting_btn = StyledButton(
            container=area_scan_container, text="Setting", variable_name="area_scan_setting_btn", font_size=100,
            left=5, top=10, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )
        self.scan_btn = StyledButton(
            container=area_scan_container, text="Scan", variable_name="scan_button", font_size=100,
            left=5, top=50, width=80, height=30, normal_color="#007BFF", press_color="#0056B3"
        )

        move_container = StyledContainer(
            container=stage_control_container, variable_name="move_container",
            left=RIGHT_START, top=112, height=88, width=200, border=True  # was 130
        )
        StyledLabel(
            container=move_container, text="Move To Device", variable_name="move_label",
            left=50, top=-12, width=100, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        StyledLabel(
            container=move_container, text="Move to", variable_name="move_to_label",
            left=0, top=15, width=60, height=28, font_size=100, color="#222",
            position="absolute", flex=True, justify_content="right"
        )
        self.move_dd = StyledDropDown(
            container=move_container, variable_name="move_to_dd", text="N/A",
            left=75, top=15, height=28, width=115
        )
        self.move_dd.attributes["title"] = "N/A"
        self.load_btn = StyledButton(
            container=move_container, text="Load", variable_name="load_button", font_size=100,
            left=10, top=50, width=85, height=28, normal_color="#007BFF", press_color="#0056B3"
        )
        self.move_btn = StyledButton(
            container=move_container, text="Move", variable_name="move_button", font_size=100,
            left=105, top=50, width=85, height=28, normal_color="#007BFF", press_color="#0056B3"
        )

        table_container = StyledContainer(
            container=stage_control_container, variable_name="coordinate_container",
            left=RIGHT_START, top=212, height=70, width=290, border=True  # was 240
        )
        headers = ["CH1", "CH2"]
        widths = [80, 80]
        self.table = StyledTable(
            container=table_container, variable_name="ch_table",
            left=0, top=0, height=30, table_width=290, headers=headers, widths=widths, row=2
        )
        table = self.table
        row = list(table.children.values())[1]
        self.ch1_cell, self.ch2_cell = [list(row.children.values())[i] for i in range(2)]
        self.ch1_val = StyledLabel(
            container=None, text="N/A", variable_name="ch1_val", left=0, top=0,
            width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
            percent=True, flex=True
        )
        self.ch2_val = StyledLabel(
            container=None, text="N/A", variable_name="ch2_val", left=0, top=0,
            width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
            percent=True, flex=True
        )
        self.ch1_cell.append(self.ch1_val)
        self.ch2_cell.append(self.ch2_val)

        # Wire-ups (unchanged)
        self.stop_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_stop))
        self.home_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_home))
        self.start_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_start))
        self.scan_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_scan))
        self.x_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_x_left))
        self.x_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_x_right))
        self.y_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_y_left))
        self.y_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_y_right))
        self.z_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_z_left))
        self.z_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_z_right))
        self.chip_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_chip_left))
        self.chip_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_chip_right))
        self.fiber_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fiber_left))
        self.fiber_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fiber_right))
        self.x_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "x"))
        self.y_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "y"))
        self.z_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "z"))
        self.chip_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "chip"))
        self.fiber_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "fiber"))
        self.load_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_load))
        self.move_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move))
        self.limit_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_limit_setting_btn))
        self.fine_align_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fine_align_setting_btn))
        self.scan_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_scan_setting_btn))
        self.lock_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_lock_box, emitter, value))
        self.move_dd.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_move_dd, emitter, value))
        self.x_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "x", v))
        self.y_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "y", v))
        self.z_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "z", v))
        self.chip_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "chip", v))
        self.fiber_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "fiber", v))

        self.move_btn.set_enabled(False)
        self.stage_control_container = stage_control_container
        return stage_control_container

    def onclick_stop(self):
        print("Stopping stage control")
        asyncio.run(self.stage_manager.emergency_stop())
        print("Stop")

    def onclick_home(self):
        print("Start Home")
        self.busy_dialog()
        self.lock_all(1)
        self.stop_btn.set_enabled(True)
        self.task_start = 1
        home = self.limit
        x = home["x"]
        y = home["y"]
        z = home["z"]
        chip = home["chip"]
        fiber = home["fiber"]

        if x == "Yes":
            xok, xlim = asyncio.run(self.stage_manager.home_limits(AxisType.X))
            if xok:
                self.x_limit_lb.set_text(f"lim: {round(xlim[0], 2)}~{round(xlim[1], 2)}")
        if y == "Yes":
            yok, ylim = asyncio.run(self.stage_manager.home_limits(AxisType.Y))
            if yok:
                self.y_limit_lb.set_text(f"lim: {round(ylim[0], 2)}~{round(ylim[1], 2)}")
        if z == "Yes":
            zok, zlim = asyncio.run(self.stage_manager.home_limits(AxisType.Z))
            if zok:
                self.z_limit_lb.set_text(f"lim: {round(zlim[0], 2)}~{round(zlim[1], 2)}")
        if chip == "Yes":
            cok, clim = asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_CHIP))
            if cok:
                self.chip_limit_lb.set_text(f"lim: {round(clim[0], 2)}~{3.6}")
        if fiber == "Yes":
            fok, flim = asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_FIBER))
            if fok:
                self.fiber_limit_lb.set_text(f"lim: 0~45")
        with self._scan_done.get_lock():
            self._scan_done.value = 1
            self.task_start = 0
            self.lock_all(0)
        print("Home Finished")

    def onclick_start(self):
        print("Start Fine Align")
        manual = (self.auto_sweep == 0)

        try:
            if manual:
                # Show dialog
                self.busy_dialog()
                self.task_start = 1
                self.lock_all(1)
                t0 = time.time()
                
                print("[Info] Starting fine alignment process...")

            # Build config
            config = FineAlignConfiguration()
            config.scan_window = self.fine_a["window_size"]
            config.step_size = self.fine_a["step_size"]
            config.gradient_iters = self.fine_a["max_iters"]

            # Create aligner
            self.fine_align = FineAlign(
                config.to_dict(),
                self.stage_manager, 
                self.nir_manager,
                progress=self._fa_progress,
                cancel_event=self._scan_cancel,
                debug=getattr(self,"debug",False),
                )

            # (Optional) tell the dialog we started
            try:
                self._write_progress_file(0, "Fine alignment: starting…", 1.0)
            except Exception:
                pass

            # ---- IMPORTANT: wait until alignment truly finishes ----
            # If begin_fine_align() is blocking until completion, this is enough:
            asyncio.run(self.fine_align.begin_fine_align())

            # If begin_fine_align() returns quickly and runs work in the background,
            # swap the line above with a polling loop like this (uncomment/change if your API exposes a flag):
            # asyncio.run(self.fine_align.begin_fine_align())
            # while getattr(self.fine_align, "is_running", False):
            #     time.sleep(0.2)

            # (Optional) final update
            try:
                self._write_progress_file(0, "Fine alignment: completed", 100.0)
            except Exception:
                pass

        except Exception as e:
            print(f"[FineAlign] Error: {e}")
            # show error state to the dialog
            try:
                self._write_progress_file(0, f"Fine alignment: error ({e})", 100.0)
            except Exception:
                pass
        finally:
            if manual:
                # Prevent instant flicker: ensure the dialog stayed visible a moment
                min_visible = 1.5  # seconds (increased from 0.8)
                try:
                    elapsed = time.time() - t0
                except Exception:
                    elapsed = min_visible
                if elapsed < min_visible:
                    time.sleep(min_visible - elapsed)

                # now mark done and unlock UI
                with self._scan_done.get_lock():
                    self._scan_done.value = 1
                    self.task_start = 0
                self.lock_all(0)

            self.fine_align = None
            print("Fine Align Finished")

    def _calculate_sweep_time(self):
        """Calculate estimated sweep time based on configuration"""
        try:
            start_nm = self.sweep.get("start", 1540.0)
            end_nm = self.sweep.get("end", 1580.0)
            step_nm = self.sweep.get("step", 0.001)

            # Calculate number of data points
            data_points = abs(end_nm - start_nm) / step_nm

            # Use provided formula: 11 seconds per 20k data points
            sweep_time = (data_points / 20000) * 11
            return max(sweep_time, 5)  # Minimum 5 seconds
        except:
            return 30  # Default fallback

    def _calculate_area_sweep_time(self):
        """Calculate estimated area sweep time based on configuration"""
        try:
            x_size = self.area_s.get("x_size", 20.0)
            x_step = self.area_s.get("x_step", 1.0)
            y_size = self.area_s.get("y_size", 20.0)
            y_step = self.area_s.get("y_step", 1.0)

            # Calculate grid points
            x_points = int(x_size / x_step)
            y_points = int(y_size / y_step)
            total_points = x_points * y_points

            # Estimate ~0.5 seconds per point
            return max(total_points * 0.5, 10)  # Minimum 10 seconds
        except:
            return 30  # Default fallback

    def _calculate_fine_align_time(self):
        """Calculate estimated fine alignment time based on configuration"""
        try:
            timeout = self.fine_a.get("timeout_s", 30)
            return min(timeout, 180)  # Cap at 3 minutes
        except:
            return 45  # Default fallback

    def _estimate_total_time(self, device_count):
        """Estimate total time for all devices"""
        sweep_time = self._calculate_sweep_time()
        area_time = self._calculate_area_sweep_time()
        align_time = self._calculate_fine_align_time()
        overhead_time = 10  # Movement and overhead per device

        time_per_device = sweep_time + area_time + align_time + overhead_time
        return device_count * time_per_device

    def _write_progress_file(self, current_device, activity, progress_percent):
        """Atomically write progress for the PyQt dialog to read."""
        from pathlib import Path
        import os, json, time

        try:
            # Import the same path the dialog reads
            from lib_gui import PROGRESS_PATH  # uses absolute path defined in lib_gui.py
        except Exception:
            # Fallback to a sane default if import fails
            PROGRESS_PATH = Path(__file__).resolve().parent / "database" / "progress.json"

        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)

        progress_data = {
            "current_device": int(current_device),
            "activity": str(activity),
            "progress_percent": float(progress_percent),
            "timestamp": time.time(),
        }

        tmp_path = PROGRESS_PATH.with_suffix(PROGRESS_PATH.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(progress_data, f)
            f.flush()
            os.fsync(f.fileno())  # ensure contents hit disk on some platforms
        os.replace(tmp_path, PROGRESS_PATH)  # atomic swap

    def _fa_progress(self, percent: float, msg: str):
        """Bridge FineAlign -> progress dialog (file the dialog is polling)."""
        try:
            self._write_progress_file(0, msg, float(percent))
        except Exception as e:
            print(f"[FA Progress] Error writing progress: {e}")
            pass
            
    def _as_progress(self, percent: float, msg: str):
        """Bridge AreaSweep -> progress dialog (file the dialog is polling)."""
        try:
            self._write_progress_file(0, msg, float(percent))
        except Exception:
            pass
        
    def busy_dialog(self, progress_config=None):
        self._scan_done = Value(c_int, 0)
        self._scan_cancel = Event()
        
        from lib_gui import run_busy_dialog
        
        self._busy_proc = Process(
            target=run_busy_dialog,
            args=(self._scan_done, self._scan_cancel, progress_config),
            daemon=True
        )
        self._busy_proc.start()

    def onclick_scan(self):
        print("Start Scan")
        self.busy_dialog()
        self.task_start = 1
        self.lock_all(1)
        if self.area_s["plot"] == "New":
            self.stage_x_pos = self.memory.x_pos
            self.stage_y_pos = self.memory.y_pos
            config = AreaSweepConfiguration()
            config.pattern = str(self.area_s["pattern"])
            config.x_size = int(self.area_s["x_size"])
            config.x_step = int(self.area_s["x_step"])
            config.y_size = int(self.area_s["y_size"])
            config.y_step = int(self.area_s["y_step"])
            self.area_sweep = AreaSweep(
                config, self.stage_manager, self.nir_manager,
                progress=self._as_progress,
                cancel_event=self._scan_cancel
            )
            self.data = asyncio.run(self.area_sweep.begin_sweep())
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            diagram = plot(filename="heat_map", fileTime=fileTime, user=self.user, project=self.project, data=self.data)

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0
                self.lock_all(0)

            p = Process(target=diagram.heat_map)
            p.start()
            p.join()
            self.area_sweep = None
            print("Done Scan")

        elif self.area_s["plot"] == "Previous":
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            diagram = plot(filename="heat_map", fileTime=fileTime, user=self.user, project=self.project, data=self.data)

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0

            p = Process(target=diagram.heat_map)
            p.start()
            p.join()

        print("Done Scan")

    def onclick_x_left(self):
        if self.axis_locked["x"]:
            print("[Axis Locked] X move ignored");
            return
        value = float(self.x_input.get_value())
        print(f"X Left {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.X, -value, True))
        self.lock_all(0)

    def onclick_x_right(self):
        if self.axis_locked["x"]:
            print("[Axis Locked] X move ignored");
            return
        value = float(self.x_input.get_value())
        print(f"X Right {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.X, value, True))
        self.lock_all(0)

    def onclick_y_left(self):
        if self.axis_locked["y"]:
            print("[Axis Locked] Y move ignored");
            return
        value = float(self.y_input.get_value())
        print(f"Y Left {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, -value, True))
        self.lock_all(0)

    def onclick_y_right(self):
        if self.axis_locked["y"]:
            print("[Axis Locked] Y move ignored");
            return
        value = float(self.y_input.get_value())
        print(f"Y Right {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, value, True))
        self.lock_all(0)

    def onclick_z_left(self):
        if self.axis_locked["z"]:
            print("[Axis Locked] Z move ignored");
            return
        value = float(self.z_input.get_value())
        print(f"Z Down {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, -value, True))
        self.lock_all(0)

    def onclick_z_right(self):
        if self.axis_locked["z"]:
            print("[Axis Locked] Z move ignored");
            return
        value = float(self.z_input.get_value())
        print(f"Z Up {value} um")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, value, True))
        self.lock_all(0)

    def onclick_chip_left(self):
        if self.axis_locked["chip"]:
            print("[Axis Locked] Chip move ignored");
            return
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CW {value} deg")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, -value, True))
        self.lock_all(0)

    def onclick_chip_right(self):
        if self.axis_locked["chip"]:
            print("[Axis Locked] Chip move ignored");
            return
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CCW {value} deg")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, value, True))
        self.lock_all(0)

    def onclick_fiber_left(self):
        if self.axis_locked["fiber"]:
            print("[Axis Locked] Fiber move ignored");
            return
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CW {value} deg")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, -value, True))
        self.lock_all(0)

    def onclick_fiber_right(self):
        if self.axis_locked["fiber"]:
            print("[Axis Locked] Fiber move ignored");
            return
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CCW {value} deg")
        self.lock_all(1)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, value, True))
        self.lock_all(0)

    def onclick_load(self):
        self.gds = lib_coordinates.coordinates(("./res/" + filename), read_file=False,
                                               name="./database/coordinates.json")
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        self.devices = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]

        self.move_dd.empty()
        self.move_dd.append(self.devices)
        self.move_dd.attributes["title"] = self.devices[0]
        file = File("shared_memory", "DeviceName", self.devices[0])
        file.save()
        print(self.devices)
        if not self.move_dd.get_value() == "N/A":
            self.move_btn.set_enabled(True)

    def onclick_zero(self, prefix: str):
        try:
            if getattr(self, "axis_locked", {}).get(prefix, False):
                # print(f"[Zero] Axis '{prefix}' is locked; ignoring zero request.")
                return

            # Optional: briefly lock the UI so users don't double-click
            self.lock_all(1)

            # Map UI prefix -> StageManager axis enum
            axis_map = {
                "x": AxisType.X,
                "y": AxisType.Y,
                "z": AxisType.Z,
                "chip": AxisType.ROTATION_CHIP,
                "fiber": AxisType.ROTATION_FIBER,
            }
            axis = axis_map.get(prefix)

            asyncio.run(self.stage_manager.zero_axis(axis))
        except Exception as e:
            print(f"[Zero] Error handling zero for '{prefix}': {e}")
        finally:
            # Always re-enable the UI
            with self._scan_done.get_lock():
                self._scan_done.value = 1       # only after begin_fine_align() returns
                self.task_start = 0
            self.lock_all(0)
    def onclick_move(self):
        selected_device = self.move_dd.get_value()
        print(f"Selected device: {selected_device}")

        try:
            index = self.devices.index(selected_device)
        except ValueError:
            print(f"[Error] Device '{selected_device}' not found in device list.")
            return

        try:
            device_coord = self.coordinate[index]
            x = float(device_coord[0])
            y = float(device_coord[1])
            print(f"Moving to coordinate: X={x}, Y={y}")

            if not self.axis_locked["x"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            if not self.axis_locked["y"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))

            file = File("shared_memory", "DeviceName", selected_device, "DeviceNum", index + 1)
            file.save()

            print(f"Successfully moved to device {selected_device}")
        except Exception as e:
            print(f"[Error] Failed to move to device {selected_device}: {e}")

    def onchange_lock_box(self, emitter, value):
        enabled = value == 0
        widgets_to_check = [self.stage_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            if hasattr(widget, "variable_name") and widget.variable_name == "lock_box":
                continue

            # keep per-axis lock checkboxes enabled
            if hasattr(widget, "variable_name") and isinstance(widget.variable_name,
                                                               str) and widget.variable_name.endswith("_lock"):
                pass
            elif isinstance(widget, (Button, DropDown, SpinBox)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

            if self.move_dd.get_value() != "N/A" and enabled is True:
                self.move_btn.set_enabled(True)
            else:
                self.move_btn.set_enabled(False)

        # after UNLOCK, reapply per-axis lock disables
        if enabled:
            for pfx, is_locked in self.axis_locked.items():
                self.set_axis_enabled(pfx, not is_locked)

        print("Unlocked" if enabled else "Locked")

    def onchange_move_dd(self, emitter, value):
        self.move_dd.attributes["title"] = value

    def onclick_limit_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7002",
            width=222 + web_w,
            height=266 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_fine_align_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=222 + web_w,
            height=236 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_scan_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7004",
            width=340 + web_w,
            height=400 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def execute_command(self, path=command_path):
        stage = 0
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
            if key.startswith("stage_control") and record == 0:
                stage = 1
            elif key.startswith("tec_control") or record == 1:
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

            elif key == "stage_x_step":
                self.x_input.set_value(str(val))
            elif key == "stage_y_step":
                self.y_input.set_value(str(val))
            elif key == "stage_z_step":
                self.z_input.set_value(str(val))
            elif key == "stage_chip_step":
                self.chip_input.set_value(str(val))
            elif key == "stage_fiber_step":
                self.fiber_input.set_value(str(val))

            elif key == "stage_x" and val == "left":
                self.onclick_x_left()
            elif key == "stage_y" and val == "left":
                self.onclick_y_left()
            elif key == "stage_z" and val == "left":
                self.onclick_z_left()
            elif key == "stage_chip" and val == "left":
                self.onclick_chip_left()
            elif key == "stage_fiber" and val == "left":
                self.onclick_fiber_left()

            elif key == "stage_x" and val == "right":
                self.onclick_x_right()
            elif key == "stage_y" and val == "right":
                self.onclick_y_right()
            elif key == "stage_z" and val == "right":
                self.onclick_z_right()
            elif key == "stage_chip" and val == "right":
                self.onclick_chip_right()
            elif key == "stage_fiber" and val == "right":
                self.onclick_fiber_right()

            elif key == "stage_x_left":
                self.x_input.set_value(str(val))
                self.onclick_x_left()
            elif key == "stage_y_left":
                self.y_input.set_value(str(val))
                self.onclick_y_left()
            elif key == "stage_z_left":
                self.z_input.set_value(str(val))
                self.onclick_z_left()
            elif key == "stage_chip_left":
                self.chip_input.set_value(str(val))
                self.onclick_chip_left()
            elif key == "stage_fiber_left":
                self.fiber_input.set_value(str(val))
                self.onclick_fiber_left()

            elif key == "stage_stop":
                self.onclick_stop()
            elif key == "stage_load":
                self.onclick_load()
            elif key == "stage_home":
                self.onclick_home()
            elif key == "stage_start":
                self.onclick_start()
            elif key == "stage_scan":
                self.onclick_scan()
            elif key == "stage_move":
                self.onclick_move()
            elif key == "stage_lock":
                self.lock_box.set_value(1)
                self.onchange_lock_box(val, 1)
            elif key == "stage_unlock":
                self.lock_box.set_value(0)
                self.onchange_lock_box(val, 0)
            elif key == "stage_device":
                length = len(self.devices)
                if val > length:
                    val = length
                elif val < 1:
                    val = 1
                device = self.devices[int(val - 1)]
                self.move_dd.set_value(device)
                


        if stage == 1:
            print("stage record")
            file = File("command", "command", new_command)
            file.save()

    def apply_detector_range(self, range_dbm, channel):
        """Apply detector range setting via NIR manager"""
        try:
            if self.nir_manager and self.configuration_sensor == 1:
                success = self.nir_manager.set_power_range(range_dbm, channel)
                if success:
                    print(f"Applied detector range {range_dbm} dBm to channel {channel}")
                else:
                    print(f"Failed to apply detector range {range_dbm} dBm to channel {channel}")
                return success
            else:
                print("NIR manager not available")
                return False
        except Exception as e:
            print(f"Error applying detector range: {e}")
            return False

    def apply_detector_reference(self, ref_dbm, channel):
        """Apply detector reference setting via NIR manager"""
        try:
            if self.nir_manager and self.configuration_sensor == 1:
                success = self.nir_manager.set_power_reference(ref_dbm, channel)
                if success:
                    print(f"Applied detector reference {ref_dbm} dBm to channel {channel}")
                else:
                    print(f"Failed to apply detector reference {ref_dbm} dBm to channel {channel}")
                return success
            else:
                print("NIR manager not available")
                return False
        except Exception as e:
            print(f"Error applying detector reference: {e}")
            return False


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
          address='0.0.0.0', port=8000,
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
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    threading.Thread(target=main_loop.run_forever, daemon=True).start()

    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    local_ip = get_local_ip()

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7002",
        width=222,
        height=266,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7003",
        width=222,
        height=236,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7004",
        width=222,
        height=266,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        'Stage Control',
        f'http://{local_ip}:8000',
        width=872 + web_w, height=407 + web_h,
        x=700, y=465,
        resizable=True,
        hidden=True
    )
    webview.start(func=disable_scroll)
