from lab_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, lab_coordinates, asyncio, datetime
from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
#from motors.stage_controller import StageController
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration
from measure.area_sweep import AreaSweep
from measure.fine_align import FineAlign
from measure.config.area_sweep_config import AreaSweepConfiguration
from measure.config.fine_align_config import FineAlignConfiguration

filename = "coordinates.json"

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")
w = 6
h = 17

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
        self.port = {}

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

        self.nir_configure = None
        self.nir_manager = None

        self.past_laser_on = 0
        self.past_wvl = None
        self.past_power = None

        self.data = None

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
            self.run_in_thread(self.execute_command())

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
                    self.scanpos = data.get("ScanPos", {})
                    self.sweep = data.get("Sweep", {})
                    self.name = data.get("DeviceName", "")
                    self.port = data.get("Port", {})
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
        else:
            auto = 1

        wl, d1, d2 = self.nir_manager.sweep(start_nm=self.sweep["start"], stop_nm=self.sweep["end"], step_nm=self.sweep["step"], laser_power_dbm=self.sweep["power"])

        x = wl
        y = np.vstack([d1, d2])
        fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        diagram = plot(x, y, "spectral_sweep", fileTime, self.user, name, self.project)
        p = Process(target=diagram.generate_plots)
        p.start()
        p.join()

        if auto == 0:
            if self.sweep["done"] == "Laser On":
                self.nir_manager.enable_laser(True)
            else:
                self.nir_manager.enable_laser(False)

            self.sweep_count = 0
            self.sweep["sweep"] = 0
            file = File("shared_memory", "Sweep", self.sweep)
            file.save()
        print("Sweep Done")

    def scan_move(self):
        x_pos = self.scanpos["x"] * self.area_s["x_step"] + self.stage_x_pos
        y_pos = self.scanpos["y"] * self.area_s["y_step"] + self.stage_y_pos
        asyncio.run(self.stage_manager.move_axis(AxisType.X, x_pos, False))
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, y_pos, False))
        print(f"Move to: {x_pos}, {y_pos}")
        self.scanpos["move"] = 0
        file = File("shared_memory", "ScanPos", self.scanpos)
        file.save()

    def after_configuration(self):
        if self.configuration["stage"] != "" and self.configuration_stage == 0:
            self.configuration_stage = 1

            self.gds = lab_coordinates.coordinates(("./res/" + filename), read_file=False,
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
            asyncio.run(self.stage_manager.initialize_all(
                [AxisType.X, AxisType.Y, AxisType.Z, AxisType.ROTATION_CHIP, AxisType.ROTATION_FIBER])
            )
            self.stage_window = webview.create_window(
                'Stage Control',
                f'http://{local_ip}:8000',
                width=672-w, height=407-h,
                x=800, y=465,
                resizable=True,
                hidden=False
            )
            print("Stage Connected")

        elif self.configuration["stage"] == "" and self.configuration_stage == 1:
            self.configuration_stage = 0
            if self.stage_window:
                self.stage_window.destroy()
                self.stage_window = None
            self.stage_manager.shutdown()
            print("Stage Disconnected")

        if self.configuration["sensor"] != "" and self.configuration_sensor == 0:
            self.nir_configure = NIRConfiguration()
            self.nir_configure.com_port = self.port["sensor"]
            self.nir_manager = NIRManager(self.nir_configure)
            self.nir_manager.connect()
            self.configuration_sensor = 1
            self.sensor_window = webview.create_window(
                'Sensor Control',
                f'http://{local_ip}:8001',
                width=672-w, height=197-h,
                x=800, y=255,
                resizable=True,
                hidden=False
            )
            print("Sensor Connected")

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
                self.run_in_thread(self.do_auto_sweep)

            elif self.auto_sweep == 0 and self.count == 1:
                self.lock_all(0)
                self.count = 0

            if self.scanpos["move"] == 1 and (self.scanpos["x"] != self.pre_x or self.scanpos["y"] != self.pre_y):
                self.run_in_thread(self.scan_move)
                self.pre_x = self.scanpos["x"]
                self.pre_y = self.scanpos["y"]

    def do_auto_sweep(self):
        i = 0
        while i < (len(self.filter)):
            if self.auto_sweep == 0:
                break

            key = list(self.filter.keys())
            x = float(self.filter[key[i]][0])
            y = float(self.filter[key[i]][1])

            print(f"Move to Device {i + 1} [{x}, {y}]")

            asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))

            self.onclick_start()

            self.laser_sweep(name=self.devices[int(key[i])])

            file = File("shared_memory", "DeviceName", self.devices[int(key[i])], "DeviceNum", int(key[i]))
            file.save()

            i += 1

        print("The Auto Sweep Is Finished")
        time.sleep(1)
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    def lock_all(self, value):
        enabled = value == 0
        widgets_to_check = [self.stage_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            if isinstance(widget, (Button, SpinBox, CheckBox, DropDown)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

    def construct_ui(self):
        stage_control_container = StyledContainer(
            container=None, variable_name="stage_control_container", left=0, top=0, height=350, width=650
        )

        xyz_container = StyledContainer(
            container=stage_control_container, variable_name="xyz_container", left=0, top=20, height=300, width=410
        )

        self.stop_btn = StyledButton(
            container=xyz_container, text="Stop", variable_name="stop_button", font_size=100,
            left=125, top=10, width=90, height=30, normal_color="#dc3545", press_color="#c82333"
        )

        self.lock_box = StyledCheckBox(
            container=xyz_container, variable_name="lock_box",
            left=225, top=10, width=10, height=10, position="absolute"
        )

        StyledLabel(
            container=xyz_container, text="Lock", variable_name="lock_label",
            left=255, top=17, width=80, height=50, font_size=100, color="#222"
        )

        labels = ["X", "Y", "Z", "Chip", "Fiber"]
        top_positions = [70, 110, 150, 190, 230]
        left_arrows = ["⮜", "⮟", "Down", "⭮", "⭮"]
        right_arrows = ["⮞", "⮝", "Up", "⭯", "⭯"]
        var_prefixes = ["x", "y", "z", "chip", "fiber"]
        position_texts = [f"{0}", f"{0}", f"{0}", f"{0}", f"{0}"]
        position_unit = ["um", "um", "um", "deg", "deg"]
        init_value = ["10.0", "10.0", "10.0", "0.1", "0.1"]

        for i in range(5):
            prefix = var_prefixes[i]
            top = top_positions[i]

            StyledLabel(
                container=xyz_container, text=labels[i], variable_name=f"{prefix}_label", left=0, top=top,width=55,
                height=30, font_size=100, color="#222", flex=True, bold=True, justify_content="right"
            )

            setattr(self, f"{prefix}_left_btn", StyledButton(
                container=xyz_container, text=left_arrows[i], variable_name=f"{prefix}_left_button", font_size=100,
                left=65, top=top, width=50, height=30, normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f"{prefix}_input", StyledSpinBox(
                container=xyz_container, variable_name=f"{prefix}_step", min_value=0, max_value=1000,
                value=init_value[i], step=0.1, left=125, top=top, width=73, height=30, position="absolute"
            ))

            setattr(self, f"{prefix}_right_btn", StyledButton(
                container=xyz_container, text=right_arrows[i], variable_name=f"{prefix}_right_button", font_size=100,
                left=225, top=top, width=50, height=30, normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f"{prefix}_position_lb", StyledLabel(
                container=xyz_container, text=position_texts[i], variable_name=f"{prefix}_position_lb",
                left=280, top=top, width=70, height=30, font_size=100, color="#222", flex=True, bold=True,
                justify_content="right"
            ))

            setattr(self, f"{prefix}_position_unit", StyledLabel(
                container=xyz_container, text=position_unit[i], variable_name=f"{prefix}_position_unit",
                left=355, top=top, width=40, height=30, font_size=100, color="#222", flex=True, bold=True,
                justify_content="left"
            ))

        limits_container = StyledContainer(
            container=stage_control_container, variable_name="limits_container",
            left=430, top=20, height=90, width=90, border=True
        )

        StyledLabel(
            container=limits_container, text="Home Lim", variable_name="limits_label",
            left=12, top=-12, width=66, height=20, font_size=100, color="#444", position="absolute",
            flex=True, on_line=True, justify_content="center"
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
            left=540, top=20, height=90, width=90, border=True
        )

        StyledLabel(
            container=fine_align_container, text="Fine Align", variable_name="fine_align_label",
            left=12.5, top=-12, width=65, height=20, font_size=100, color="#444", position="absolute",
            flex=True, on_line=True, justify_content="center"
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
            left=430, top=130, height=90, width=90, border=True
        )

        StyledLabel(
            container=area_scan_container, text="Area Scan", variable_name="area_scan_label",
            left=13, top=-12, width=65, height=20, font_size=100, color="#444", position="absolute",
            flex=True, on_line=True, justify_content="center"
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
            left=430, top=240, height=88, width=200, border=True
        )

        StyledLabel(
            container=move_container, text="Move To Device", variable_name="move_label",
            left=50, top=-12, width=100, height=20, font_size=100, color="#444", position="absolute",
            flex=True, on_line=True, justify_content="center"
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
        self.load_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_load))
        self.move_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move))
        self.limit_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_limit_setting_btn))
        self.fine_align_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fine_align_setting_btn))
        self.scan_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_scan_setting_btn))
        self.lock_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_lock_box, emitter, value))
        self.move_dd.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_move_dd, emitter, value))

        self.move_btn.set_enabled(False)
        self.stage_control_container = stage_control_container
        return stage_control_container

    def onclick_stop(self):
        asyncio.run(self.stage_manager.emergency_stop())
        print("Stop")

    def onclick_home(self):
        print("Start Home")
        home = self.limit
        x = home["x"]
        y = home["y"]
        z = home["z"]
        chip = home["chip"]
        fiber = home["fiber"]

        if x == "Yes":
            asyncio.run(self.stage_manager.home_limits(AxisType.X))
        if y == "Yes":
            asyncio.run(self.stage_manager.home_limits(AxisType.Y))
        if z == "Yes":
            asyncio.run(self.stage_manager.home_limits(AxisType.Z))
        if chip == "Yes":
            asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_CHIP))
        if fiber == "Yes":
            asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_FIBER))
        print("Home Finished")

    def onclick_start(self):
        print("Start Fine Align")
        config = FineAlignConfiguration()
        config.scan_window = self.fine_a["window_size"]
        config.step_size = self.fine_a["step_size"]
        config.gradient_iters = self.fine_a["max_iters"]
        fine_align = FineAlign(config.to_dict(), self.stage_manager, self.nir_manager)
        asyncio.run(fine_align.begin_fine_align())
        print("Fine Align Finished")

    def onclick_scan(self):
        self.scan_btn.set_enabled(False)
        print("Start Scan")
        if self.area_s["plot"] == "New":
            self.stage_x_pos = self.memory.x_pos
            self.stage_y_pos = self.memory.y_pos
            config = AreaSweepConfiguration()
            config.x_size = int(self.area_s["x_size"])
            config.x_step = int(self.area_s["x_step"])
            config.y_size = int(self.area_s["y_size"])
            config.y_step = int(self.area_s["y_step"])
            area_sweep = AreaSweep(config, self.stage_manager, self.nir_manager)
            self.data = asyncio.run(area_sweep.begin_sweep())
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            diagram = plot(filename="heat_map", fileTime=fileTime, user=self.user, project=self.project, data=self.data)
            p = Process(target=diagram.heat_map)
            p.start()
            p.join()
            print("Done Scan")
        elif self.area_s["plot"] == "Previous":
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            diagram = plot(filename="heat_map", fileTime=fileTime, user=self.user, project=self.project, data=self.data)
            p = Process(target=diagram.heat_map)
            p.start()
            p.join()
        print("Done Scan")
        self.scan_btn.set_enabled(True)

    def onclick_x_left(self):
        value = float(self.x_input.get_value())
        print(f"X Left {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.X, -value, True, wait_for_completion = False))
        print(self.nir_manager.read_power())

    def onclick_x_right(self):
        value = float(self.x_input.get_value())
        print(f"X Right {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.X, value, True, wait_for_completion = False))

    def onclick_y_left(self):
        value = float(self.y_input.get_value())
        print(f"Y Left {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, -value, True, wait_for_completion = False))

    def onclick_y_right(self):
        value = float(self.y_input.get_value())
        print(f"Y Right {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, value, True, wait_for_completion = False))

    def onclick_z_left(self):
        value = float(self.z_input.get_value())
        print(f"Z Down {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, -value, True, wait_for_completion = False))

    def onclick_z_right(self):
        value = float(self.z_input.get_value())
        print(f"Z Up {value} um")
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, value, True, wait_for_completion = False))

    def onclick_chip_left(self):
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CW {value} deg")
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, -value, True, wait_for_completion = False))

    def onclick_chip_right(self):
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CCW {value} deg")
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, value, True, wait_for_completion = False))

    def onclick_fiber_left(self):
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CW {value} deg")
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, -value, True, wait_for_completion = False))

    def onclick_fiber_right(self):
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CCW {value} deg")
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, value, True, wait_for_completion = False))

    def onclick_load(self):
        self.gds = lab_coordinates.coordinates(("./res/" + filename), read_file=False,
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

            asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))

            file = File("shared_memory", "DeviceName", selected_device, "DeviceNum", index+1)
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

            if isinstance(widget, (Button, DropDown, SpinBox)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

            if self.move_dd.get_value() != "N/A" and enabled is True:
                self.move_btn.set_enabled(True)
            else:
                self.move_btn.set_enabled(False)

        print("Unlocked" if enabled else "Locked")

    def onchange_move_dd(self, emitter, value):
        self.move_dd.attributes["title"] = value

    def onclick_limit_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7002",
            width=222-w,
            height=266-h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_fine_align_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=222-w,
            height=236-h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_scan_setting_btn(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7004",
            width=222-w,
            height=266-h,
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
                device = self.devices[int(val-1)]
                self.move_dd.set_value(device)

        if stage == 1:
            print("stage record")
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
        'Stage Control',
        f'http://{local_ip}:8000',
        width=672, height=407,
        x=800, y=465,
        resizable=True,
        hidden=True
    )

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

    webview.start(func=disable_scroll)
