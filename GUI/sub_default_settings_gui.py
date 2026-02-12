import datetime
import json
import os
import threading

from remi import App, start
from GUI.lib_gui import *

SHARED_PATH = os.path.join("database", "shared_memory.json")


def update_detector_window_setting(mf, slot, setting_type, value):
    """Update detector window settings in compact structure.
    
    Args:
        mf: mainframe number (0 or 1)
        slot: slot number (1-4)
        setting_type: 'range', 'ref', or 'auto_range'
        value: setting value
    """
    with SharedMemory.lock():
        data = SharedMemory.read_unsafe({})

        # Initialize DetectorWindowSettings if needed
        if "DetectorWindowSettings" not in data:
            data["DetectorWindowSettings"] = {}
        
        dws = data["DetectorWindowSettings"]
        
        # Initialize MF section if needed
        mf_key = f"mf{mf}"
        if mf_key not in dws:
            dws[mf_key] = {}
        
        # Initialize slot settings if needed
        slot_str = str(slot)
        if slot_str not in dws[mf_key]:
            dws[mf_key][slot_str] = {}
        
        # Update the specific setting
        dws[mf_key][slot_str][setting_type] = value
        dws["Detector_Change"] = "1"

        SharedMemory.write_unsafe(data)


class DefaultSettingsConfig(App):
    """User and project default settings configuration panel."""

    def __init__(self, *args, **kwargs):
        # Track shared_memory.json changes
        self._user_stime = None
        self._first_check = True
        # Track last user/project so we only reload when they change
        self._last_user = None
        self._last_project = None

        # Current user and project
        self.current_user = "Guest"
        self.current_project = "MyProject"

        # Configuration manager
        self.config_manager = None

        # Current config data
        self.user_defaults = {}
        self.project_config = {}

        # Widgets - Sweep Settings
        self.sweep_power = None
        self.sweep_start = None
        self.sweep_end = None
        self.sweep_step = None

        # Widgets - Area Scan Settings (mirrors Fine Align style)
        self.area_window_size = None
        self.area_step_size = None
        self.area_primary_detector_dd = None
        self.area_plot_dd = None

        # Widgets - Fine Align Settings
        self.fa_window_size = None
        self.fa_step_size = None
        self.fa_max_iters = None
        self.fa_min_grad_ss = None
        self.fa_primary_detector = None
        self.fa_ref_wl = None
        # Extra fine-align fields
        self.fa_threshold = None
        self.fa_secondary_wl = None
        self.fa_secondary_loss = None

        # Widgets - Initial Positions
        self.init_fa = None

        # Widgets - VISA/Port Settings
        self.stage_port = None
        self.sensor_port = None

        # Widgets - Configuration Labels
        self.stage_config_dd = None
        self.sensor_config_dd = None

        # Widgets - Detector Window Settings (4 slots with buttons)
        self.ch1_range = None
        self.ch1_ref = None
        self.ch2_range = None
        self.ch2_ref = None
        self.ch3_range = None
        self.ch3_ref = None
        self.ch4_range = None
        self.ch4_ref = None
        # Auto range buttons
        self.apply_auto_btn1 = None
        self.apply_auto_btn2 = None
        self.apply_auto_btn3 = None
        self.apply_auto_btn4 = None
        # Apply range/ref buttons
        self.apply_range_btn1 = None
        self.apply_ref_btn1 = None
        self.apply_range_btn2 = None
        self.apply_ref_btn2 = None
        self.apply_range_btn3 = None
        self.apply_ref_btn3 = None
        self.apply_range_btn4 = None
        self.apply_ref_btn4 = None

        # Buttons
        self.save_user_btn = None
        self.save_project_btn = None

        # Root container reference
        self._ui_container = None

        # REMI init (support editing_mode)
        editing_mode = kwargs.pop("editing_mode", False)
        super_kwargs = {}
        if not editing_mode:
            super_kwargs["static_file_path"] = {"my_res": "./res/"}
        super(DefaultSettingsConfig, self).__init__(*args, **super_kwargs)

    # ---------------- REMI HOOKS ----------------

    def main(self):
        ui = self.construct_ui()
        self._load_from_shared()
        return ui

    def idle(self):
        """
        Reload configuration ONLY when user/project changes.
        """
        stime = get_shared_memory_mtime()

        if self._first_check:
            self._user_stime = stime
            self._first_check = False
            return

        if stime != self._user_stime:
            self._user_stime = stime
            data = SharedMemory.read({})
            if not data:
                return

            new_user = data.get("User", self.current_user)
            new_project = data.get("Project", self.current_project)

            if new_user != self.current_user or new_project != self.current_project:
                self.current_user = new_user
                self.current_project = new_project
                self._last_user = new_user
                self._last_project = new_project
                self._load_from_shared()

    # ---------------- UTIL ----------------

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    @staticmethod
    def _set_spin_safely(widget, value):
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    @staticmethod
    def _set_dropdown_safely(widget, value):
        if widget is None or value is None:
            return
        try:
            widget.set_value(str(value))
        except Exception:
            pass

    @staticmethod
    def _safe_float(widget, default):
        try:
            return float(widget.get_value())
        except Exception:
            return default

    @staticmethod
    def _safe_int(widget, default):
        try:
            return int(float(widget.get_value()))
        except Exception:
            return default

    @staticmethod
    def _safe_str(widget, default):
        try:
            val = widget.get_value()
            if val is None:
                return default
            return str(val)
        except Exception:
            return default

    # ---------------- DATA LOADING ----------------

    def _load_from_shared(self):
        try:
            data = SharedMemory.read({})

            self.current_user = data.get("User", "Guest")
            self.current_project = data.get("Project", "MyProject")
            self._last_user = self.current_user
            self._last_project = self.current_project

            from GUI.lib_gui import UserConfigManager
            self.config_manager = UserConfigManager(self.current_user, self.current_project)

            self.user_defaults = self.config_manager.get_user_defaults()
            self.project_config = self.config_manager.get_project_overrides()

            merged_config = self.config_manager.load_config()
            self._update_ui_from_config(merged_config)

            if getattr(self, "user_info_label", None) is not None:
                self.user_info_label.set_text(
                    f"User: {self.current_user} | Project: {self.current_project}"
                )

        except Exception as e:
            print(f"[Default_Settings] Error loading config: {e}")

    def _update_ui_from_config(self, config):
        # Sweep
        sweep = config.get("Sweep", {})
        self._set_spin_safely(self.sweep_power, sweep.get("power", 0.0))
        self._set_spin_safely(self.sweep_start, sweep.get("start", 1500.0))
        self._set_spin_safely(self.sweep_end, sweep.get("end", 1580.0))
        self._set_spin_safely(self.sweep_step, sweep.get("step", 0.001))

        # Area (mirrors Fine Align)
        area = config.get("AreaS", {})

        # Window size: prefer explicit window_size else x_size/y_size
        win = area.get("window_size", None)
        if win is None:
            x_sz = area.get("x_size", 50.0)
            y_sz = area.get("y_size", 50.0)
            try:
                win = x_sz if float(x_sz) == float(y_sz) else x_sz
            except Exception:
                win = 50.0
        self._set_spin_safely(self.area_window_size, win)

        # Step size: prefer explicit step_size else x_step/y_step
        step = area.get("step_size", None)
        if step is None:
            x_st = area.get("x_step", 5.0)
            y_st = area.get("y_step", 5.0)
            try:
                step = x_st if float(x_st) == float(y_st) else x_st
            except Exception:
                step = 5.0
        self._set_spin_safely(self.area_step_size, step)

        pd = str(area.get("primary_detector", "max")).upper()
        if pd not in ("CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8", "MAX"):
            pd = "MAX"
        try:
            self.area_primary_detector_dd.set_value(pd)
        except Exception:
            pass

        plot_val = area.get("plot", "New")
        if isinstance(plot_val, str):
            low = plot_val.lower()
            plot_val = "Previous" if low == "previous" else "New"
        try:
            self.area_plot_dd.set_value(plot_val)
        except Exception:
            pass

        # FineA
        fine_a = config.get("FineA", {})
        self._set_spin_safely(self.fa_window_size, fine_a.get("window_size", 10.0))
        self._set_spin_safely(self.fa_step_size, fine_a.get("step_size", 1.0))
        self._set_spin_safely(self.fa_max_iters, fine_a.get("max_iters", 10))
        self._set_spin_safely(self.fa_min_grad_ss, fine_a.get("min_gradient_ss", 0.1))
        self._set_dropdown_safely(self.fa_primary_detector, fine_a.get("detector", "Max"))
        self._set_spin_safely(self.fa_ref_wl, fine_a.get("ref_wl", 1550.0))
        self._set_spin_safely(self.fa_threshold, fine_a.get("threshold", -10.0))
        self._set_spin_safely(self.fa_secondary_wl, fine_a.get("secondary_wl", 1540.0))
        self._set_spin_safely(self.fa_secondary_loss, fine_a.get("secondary_loss", -50.0))

        # InitialPositions
        initial_pos = config.get("InitialPositions", {})
        self._set_spin_safely(self.init_fa, initial_pos.get("fa", 8.0))

        # DetectorWindowSettings - Load from compact structure
        detector_settings = config.get("DetectorWindowSettings", {})
        
        # Load MF0 settings (assuming defaults to MF0 for now)
        mf0_data = detector_settings.get("mf0", {})
        for slot in range(1, 5):
            slot_data = mf0_data.get(str(slot), {})
            range_widget = getattr(self, f'ch{slot}_range', None)
            ref_widget = getattr(self, f'ch{slot}_ref', None)
            
            self._set_spin_safely(range_widget, slot_data.get("range", -10))
            self._set_spin_safely(ref_widget, slot_data.get("ref", -30))

        # Port
        port = config.get("Port", {})
        self._set_spin_safely(self.stage_port, port.get("stage", 4))
        self._set_spin_safely(self.sensor_port, port.get("sensor", 20))

        # Configuration
        configuration = config.get("Configuration", {})
        self._set_dropdown_safely(self.stage_config_dd, configuration.get("stage", ""))
        self._set_dropdown_safely(self.sensor_config_dd, configuration.get("sensor", ""))

    # ---------------- UI CONSTRUCTION ----------------

    def construct_ui(self):
        root = StyledContainer(
            variable_name="default_settings_container",
            left=0,
            top=0,
            width=870,
            height=620,
        )

        y = 10

        StyledLabel(
            container=root,
            text=f"Default Settings",
            variable_name="title",
            left=10,
            top=y,
            width=930,
            height=25,
            font_size=120,
            flex=True,
            justify_content="center",
            color="#222",
            bold=True,
        )

        y += 30

        self.user_info_label = StyledLabel(
            container=root,
            text=f"User: {self.current_user} | Project: {self.current_project}",
            variable_name="user_info",
            left=10,
            top=y,
            width=930,
            height=20,
            font_size=90,
            flex=True,
            justify_content="center",
            color="#666",
        )

        y += 30

        col_width = 300
        col1_x = 10
        col2_x = 310
        col3_x = 560
        start_y = y

        self._create_column1_sweep_area(root, col1_x, start_y, col_width)
        self._create_column2_fine_align_positions(root, col2_x, start_y, col_width)
        self._create_column3_detector_ports_config(root, col3_x, start_y, col_width)

        self._create_save_buttons(root)

        self._ui_container = root
        return root

    def _create_column1_sweep_area(self, root, col_x, y, col_width):
        LBL_W, INP_W, UNIT_W = 90, 70, 50
        LBL_X = col_x + 10
        INP_X = LBL_X + LBL_W + 10
        UNIT_X = INP_X + INP_W + 20
        ROW = 30

        StyledLabel(
            container=root,
            text="Sweep Settings",
            variable_name="sweep_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += ROW

        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Power", "power", "dBm",
            0.0, -50, 20, 0.1,
        )
        self.sweep_power = root.children["power_in"]
        y += ROW

        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Start Wvl", "start", "nm",
            1500.0, 1456, 1583, 0.1,
        )
        self.sweep_start = root.children["start_in"]
        y += ROW

        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "End Wvl", "end", "nm",
            1580.0, 1456, 1583, 0.1,
        )
        self.sweep_end = root.children["end_in"]
        y += ROW

        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Step Size", "step", "nm",
            0.001, 0.0001, 1.0, 0.0001,
        )
        self.sweep_step = root.children["step_in"]
        y += ROW + 10

        StyledLabel(
            container=root,
            text="Area Scan Settings",
            variable_name="area_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += ROW

        # Window Size (sets BOTH X and Y size)
        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Window Size", "area_window", "um",
            50.0, 1, 1000, 1,
        )
        self.area_window_size = root.children["area_window_in"]
        y += ROW

        # Step Size (sets BOTH X and Y step)
        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Step Size", "area_step", "um",
            5.0, 0.1, 100, 0.1,
        )
        self.area_step_size = root.children["area_step_in"]
        y += ROW

        StyledLabel(
            container=root,
            text="Primary Detector",
            variable_name="area_primary_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_primary_detector_dd = StyledDropDown(
            container=root,
            text=["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8", "MAX"],
            variable_name="area_primary_detector_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute",
        )
        self.area_primary_detector_dd.set_value("MAX")
        y += ROW

        StyledLabel(
            container=root,
            text="Plot",
            variable_name="area_plot_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_plot_dd = StyledDropDown(
            container=root,
            text=["New", "Previous"],
            variable_name="area_plot_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute",
        )
        self.area_plot_dd.set_value("New")
        y += ROW + 15

        StyledLabel(
            container=root,
            text="Configuration Labels",
            variable_name="config_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        StyledLabel(
            container=root,
            text="Stage",
            variable_name="stage_config_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stage_config_dd = StyledDropDown(
            container=root,
            text=[
                "",
                "MMC100_controller",
                "Thorlabs_controller",
                "Corvus_controller",
                "Dummy_controller",
            ],
            variable_name="stage_config_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W + 40,
            height=24,
            position="absolute",
        )
        self.stage_config_dd.set_value("MMC100_controller")
        y += ROW

        StyledLabel(
            container=root,
            text="Sensor",
            variable_name="sensor_config_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sensor_config_dd = StyledDropDown(
            container=root,
            text=["", "8164B_NIR", "N7744A", "Dummy_sensor"],
            variable_name="sensor_config_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W + 40,
            height=24,
            position="absolute",
        )
        self.sensor_config_dd.set_value("8164B_NIR")

    def _create_field_3col(
        self,
        root,
        lbl_x,
        inp_x,
        unit_x,
        y,
        lbl_w,
        inp_w,
        unit_w,
        label,
        prefix,
        unit,
        value,
        min_val,
        max_val,
        step,
    ):
        StyledLabel(
            container=root,
            text=label,
            variable_name=f"{prefix}_lb",
            left=lbl_x,
            top=y,
            width=lbl_w,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        StyledSpinBox(
            container=root,
            variable_name=f"{prefix}_in",
            left=inp_x,
            top=y,
            width=inp_w,
            height=24,
            value=value,
            min_value=min_val,
            max_value=max_val,
            step=step,
            position="absolute",
        )
        if unit:
            StyledLabel(
                container=root,
                text=unit,
                variable_name=f"{prefix}_unit",
                left=unit_x,
                top=y,
                width=unit_w,
                height=24,
                font_size=100,
                flex=True,
                justify_content="left",
                color="#222",
            )

    def _create_column2_fine_align_positions(self, root, col_x, y, col_width):
        """Fine Align column with Detector at the bottom, mirroring fine_align layout."""
        LBL_X = col_x + 10
        INP_X = col_x + 100
        UNIT_X = col_x + 170
        LBL_W = 90
        INP_W = 50
        UNIT_W = 40
        ROW = 32

        StyledLabel(
            container=root,
            text="Fine Align Settings",
            variable_name="fa_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=90,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Window
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Window", "window", "um",
            10.0, 1, 100, 1,
        )
        self.fa_window_size = root.children["window_in"]
        y += ROW

        # Step Size
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Step Size", "fa_step", "um",
            1.0, 0.1, 10, 0.1,
        )
        self.fa_step_size = root.children["fa_step_in"]
        y += ROW

        # Max Iters
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Max Iters", "max_iters", "",
            10, 1, 50, 1,
        )
        self.fa_max_iters = root.children["max_iters_in"]
        y += ROW

        # Min Grad SS
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Min Grad SS", "min_grad_ss", "um",
            0.1, 0.001, 10, 0.1,
        )
        self.fa_min_grad_ss = root.children["min_grad_ss_in"]
        y += ROW
        # G.D. Threshold
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "G.D. Threshold", "fa_threshold", "dBm",
            -10.0, -100.0, 20.0, 0.1,
        )
        self.fa_threshold = root.children["fa_threshold_in"]
        y += ROW
        # Ref WL
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Ref WL", "ref_wl", "nm",
            1550.0, 1450.0, 1650.0, 0.01,
        )
        self.fa_ref_wl = root.children["ref_wl_in"]
        y += ROW

        # Secondary Ref Wvl
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Secondary Ref Wvl", "secondary_wl", "nm",
            1540.0, 1456, 1583, 0.01,
        )
        self.fa_secondary_wl = root.children["secondary_wl_in"]
        y += ROW

        # Secondary Wvl Threshold
        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Secondary Wvl Threshold", "secondary_loss", "dBm",
            -50.0, -100.0, 80.0, 0.1,
        )
        self.fa_secondary_loss = root.children["secondary_loss_in"]
        y += ROW

        # Detector (moved to bottom of Fine Align group)
        StyledLabel(
            container=root,
            text="Detector",
            variable_name="fa_detector_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.fa_primary_detector = StyledDropDown(
            container=root,
            text=["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "Max"],
            variable_name="fa_detector_dd",
            left=INP_X,
            top=y,
            width=60,
            height=24,
            position="absolute",
        )
        y += ROW + 10  # small gap after detector

        # Initial Positions
        StyledLabel(
            container=root,
            text="Initial Positions",
            variable_name="init_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Init FA", "init_fa", "deg",
            8.0, -360, 360, 0.1,
        )
        self.init_fa = root.children["init_fa_in"]
        y += ROW + 15

        # Port Settings
        StyledLabel(
            container=root,
            text="Port Settings",
            variable_name="port_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Stage Port", "stage_port", "",
            4, 1, 99, 1,
        )
        self.stage_port = root.children["stage_port_in"]
        y += ROW

        self._create_field_fine_align(
            root, LBL_X, INP_X, UNIT_X, y,
            LBL_W, INP_W, UNIT_W,
            "Sensor Port", "sensor_port", "",
            20, 1, 99, 1,
        )
        self.sensor_port = root.children["sensor_port_in"]

    def _create_field_fine_align(
        self,
        root,
        lbl_x,
        inp_x,
        unit_x,
        y,
        lbl_w,
        inp_w,
        unit_w,
        label,
        prefix,
        unit,
        value,
        min_val,
        max_val,
        step,
    ):
        StyledLabel(
            container=root,
            text=label,
            variable_name=f"{prefix}_lb",
            left=lbl_x,
            top=y,
            width=lbl_w,
            height=24,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        StyledSpinBox(
            container=root,
            variable_name=f"{prefix}_in",
            left=inp_x,
            top=y,
            width=inp_w,
            height=24,
            value=value,
            min_value=min_val,
            max_value=max_val,
            step=step,
            position="absolute",
        )
        if unit:
            StyledLabel(
                container=root,
                text=unit,
                variable_name=f"{prefix}_unit",
                left=unit_x,
                top=y,
                width=unit_w,
                height=24,
                font_size=100,
                flex=True,
                justify_content="left",
                color="#222",
            )

    def _create_column3_detector_ports_config(self, root, col_x, y, col_width):
        LBL_X = col_x
        INP_X = col_x + 70
        UNIT_X = col_x + 150
        BTN_X = col_x + 180
        ROW = 30

        StyledLabel(
            container=root,
            text="Detector Window Settings",
            variable_name="detector_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Slot 1
        StyledLabel(
            container=root,
            text="Slot 1",
            variable_name="ch1_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch1_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch1_range = StyledSpinBox(
            container=root,
            variable_name="ch1_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch1_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn1 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn1",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch1_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch1_ref = StyledSpinBox(
            container=root,
            variable_name="ch1_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch1_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn1 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn1",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        self.apply_auto_btn1 = StyledButton(
            container=root,
            text="Auto Range CH1",
            variable_name="apply_auto_btn1",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # Slot 2
        StyledLabel(
            container=root,
            text="Slot 2",
            variable_name="ch2_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch2_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch2_range = StyledSpinBox(
            container=root,
            variable_name="ch2_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch2_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn2 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn2",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch2_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch2_ref = StyledSpinBox(
            container=root,
            variable_name="ch2_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch2_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn2 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn2",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        self.apply_auto_btn2 = StyledButton(
            container=root,
            text="Auto Range CH2",
            variable_name="apply_auto_btn2",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # Slot 3
        StyledLabel(
            container=root,
            text="Slot 3",
            variable_name="ch3_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch3_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch3_range = StyledSpinBox(
            container=root,
            variable_name="ch3_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch3_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn3 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn3",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch3_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch3_ref = StyledSpinBox(
            container=root,
            variable_name="ch3_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch3_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn3 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn3",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        self.apply_auto_btn3 = StyledButton(
            container=root,
            text="Auto Range CH3",
            variable_name="apply_auto_btn3",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # Slot 4
        StyledLabel(
            container=root,
            text="Slot 4",
            variable_name="ch4_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch4_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch4_range = StyledSpinBox(
            container=root,
            variable_name="ch4_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch4_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn4 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn4",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch4_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch4_ref = StyledSpinBox(
            container=root,
            variable_name="ch4_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch4_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn4 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn4",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        self.apply_auto_btn4 = StyledButton(
            container=root,
            text="Auto Range CH4",
            variable_name="apply_auto_btn4",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )

        # Wire events
        self.apply_auto_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_autorange)
        )
        self.apply_auto_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_autorange)
        )
        self.apply_auto_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_autorange)
        )
        self.apply_auto_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_autorange)
        )

        self.apply_range_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_range)
        )
        self.apply_ref_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_ref)
        )

        self.apply_range_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_range)
        )
        self.apply_ref_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_ref)
        )

        self.apply_range_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_range)
        )
        self.apply_ref_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_ref)
        )

        self.apply_range_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_range)
        )
        self.apply_ref_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_ref)
        )

    # DETECTOR EVENT HANDLERS

    def onclick_apply_ch1_autorange(self):
        update_detector_window_setting(0, 1, "auto_range", True)
        update_detector_window_setting(0, 1, "range", None)  # Clear manual range

    def onclick_apply_ch1_range(self):
        range_val = float(self.ch1_range.get_value())
        update_detector_window_setting(0, 1, "range", range_val)
        update_detector_window_setting(0, 1, "auto_range", False)

    def onclick_apply_ch1_ref(self):
        ref_val = float(self.ch1_ref.get_value())
        update_detector_window_setting(0, 1, "ref", ref_val)

    def onclick_apply_ch2_autorange(self):
        update_detector_window_setting(0, 2, "auto_range", True)
        update_detector_window_setting(0, 2, "range", None)  # Clear manual range

    def onclick_apply_ch2_range(self):
        range_val = float(self.ch2_range.get_value())
        update_detector_window_setting(0, 2, "range", range_val)
        update_detector_window_setting(0, 2, "auto_range", False)

    def onclick_apply_ch2_ref(self):
        ref_val = float(self.ch2_ref.get_value())
        update_detector_window_setting(0, 2, "ref", ref_val)

    def onclick_apply_ch3_autorange(self):
        update_detector_window_setting(0, 3, "auto_range", True)
        update_detector_window_setting(0, 3, "range", None)  # Clear manual range

    def onclick_apply_ch3_range(self):
        range_val = float(self.ch3_range.get_value())
        update_detector_window_setting(0, 3, "range", range_val)
        update_detector_window_setting(0, 3, "auto_range", False)

    def onclick_apply_ch3_ref(self):
        ref_val = float(self.ch3_ref.get_value())
        update_detector_window_setting(0, 3, "ref", ref_val)

    def onclick_apply_ch4_autorange(self):
        update_detector_window_setting(0, 4, "auto_range", True)
        update_detector_window_setting(0, 4, "range", None)  # Clear manual range

    def onclick_apply_ch4_range(self):
        range_val = float(self.ch4_range.get_value())
        update_detector_window_setting(0, 4, "range", range_val)
        update_detector_window_setting(0, 4, "auto_range", False)

    def onclick_apply_ch4_ref(self):
        ref_val = float(self.ch4_ref.get_value())
        update_detector_window_setting(0, 4, "ref", ref_val)

    def _create_save_buttons(self, root):
        y_buttons = 570

        self.save_user_btn = StyledButton(
            container=root,
            text="Save User Defaults",
            variable_name="save_user_btn",
            left=320,
            top=y_buttons,
            width=160,
            height=35,
            normal_color="#28a745",
            press_color="#1e7e34",
            font_size=100,
        )

        self.save_project_btn = StyledButton(
            container=root,
            text="Save Project Settings",
            variable_name="save_project_btn",
            left=540,
            top=y_buttons,
            width=160,
            height=35,
            normal_color="#007bff",
            press_color="#0056b3",
            font_size=100,
        )

        self.save_user_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_user))
        self.save_project_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_save_project)
        )

    def onclick_save_user(self):
        try:
            config = self._build_config_from_ui()
            if self.config_manager:
                self.config_manager.save_user_defaults(config)
                print(f"[Default_Settings] Saved user defaults for {self.current_user}")
            else:
                print("[Default_Settings] Config manager not initialized")
            self._save_to_shared_memory(config)
        except Exception as e:
            print(f"[Default_Settings] Error saving user defaults: {e}")

    def onclick_save_project(self):
        try:
            config = self._build_config_from_ui()
            if self.config_manager:
                self.config_manager.save_project_config(config)
                print(
                    f"[Default_Settings] Saved project config for {self.current_user}/{self.current_project}"
                )
            else:
                print("[Default_Settings] Config manager not initialized")
            self._save_to_shared_memory(config)
        except Exception as e:
            print(f"[Default_Settings] Error saving project config: {e}")

    def _save_to_shared_memory(self, config):
        try:
            for section, data in config.items():
                file = File("shared_memory", section, data)
                file.save()
            flag = File("shared_memory", "LoadConfig", True)
            flag.save()
            print(f"[Default_Settings] Updated shared_memory.json")
        except Exception as e:
            print(f"[Default_Settings] Error updating shared_memory.json: {e}")

    def _build_config_from_ui(self):
        # Area Scan mirrors Fine Align: Window + Step Size
        area_window = self._safe_float(self.area_window_size, 50.0)
        area_step = self._safe_float(self.area_step_size, 5.0)

        try:
            primary_raw = str(self.area_primary_detector_dd.get_value())
        except Exception:
            primary_raw = "MAX"
        primary_norm = primary_raw.strip().upper()
        if primary_norm not in ("CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8", "MAX"):
            primary_norm = "MAX"
        primary_token = primary_norm.lower()

        try:
            plot_raw = str(self.area_plot_dd.get_value())
        except Exception:
            plot_raw = "New"
        plot_norm = "Previous" if plot_raw.lower() == "previous" else "New"

        config = {
            "Sweep": {
                "power": self._safe_float(self.sweep_power, 0.0),
                "start": self._safe_float(self.sweep_start, 1500.0),
                "end": self._safe_float(self.sweep_end, 1580.0),
                "step": self._safe_float(self.sweep_step, 0.001),
            },
            "AreaS": {
                # Always keep X/Y symmetric to mirror Fine Align
                "x_size": float(area_window),
                "y_size": float(area_window),
                "window_size": float(area_window),

                "x_step": float(area_step),
                "y_step": float(area_step),
                "step_size": float(area_step),

                # Pattern is fixed now (no dropdown)
                "pattern": "spiral",

                "primary_detector": primary_token,
                "plot": plot_norm,
            },
            "FineA": {
                "window_size": self._safe_float(self.fa_window_size, 10.0),
                "step_size": self._safe_float(self.fa_step_size, 1.0),
                "max_iters": self._safe_int(self.fa_max_iters, 10),
                "min_gradient_ss": self._safe_float(self.fa_min_grad_ss, 0.1),
                "detector": self._safe_str(self.fa_primary_detector, "Max"),
                "ref_wl": self._safe_float(self.fa_ref_wl, 1550.0),
                "threshold": self._safe_float(self.fa_threshold, -10.0),
                "secondary_wl": self._safe_float(self.fa_secondary_wl, 1540.0),
                "secondary_loss": self._safe_float(self.fa_secondary_loss, -50.0),
            },
            "InitialPositions": {
                "fa": self._safe_float(self.init_fa, 8.0),
            },
            "DetectorWindowSettings": {
                "mf0": {
                    "1": {
                        "range": self._safe_int(self.ch1_range, -10),
                        "ref": self._safe_int(self.ch1_ref, -30),
                        "auto_range": False
                    },
                    "2": {
                        "range": self._safe_int(self.ch2_range, -10),
                        "ref": self._safe_int(self.ch2_ref, -30),
                        "auto_range": False
                    },
                    "3": {
                        "range": self._safe_int(self.ch3_range, -10),
                        "ref": self._safe_int(self.ch3_ref, -30),
                        "auto_range": False
                    },
                    "4": {
                        "range": self._safe_int(self.ch4_range, -10),
                        "ref": self._safe_int(self.ch4_ref, -30),
                        "auto_range": False
                    }
                },
                "Detector_Change": "1",
            },
            "Port": {
                "stage": self._safe_int(self.stage_port, 4),
                "sensor": self._safe_int(self.sensor_port, 20),
            },
            "Configuration": {
                "stage": self._safe_str(self.stage_config_dd, ""),
                # sensor is intentionally excluded — connection should only
                # happen via the "Connect" button, never from saved settings.
            },
        }
        return config


# ---- REMI SERVER ----
def main():
    start(
        DefaultSettingsConfig,
        address="0.0.0.0",
        port=7009,
        start_browser=False,
        multiple_instance=False,
    )


if __name__ == "__main__":
    configuration = {
        "config_project_name": "default_settings",
        "config_address": "0.0.0.0",
        "config_port": 7009,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/",
    }
    start(
        DefaultSettingsConfig,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"],
    )
