from GUI.lib_gui import *
from remi import start, App
import os, json, threading

# --- Paths to JSON files ---
SHARED_PATH = os.path.join("database", "shared_memory.json")
command_path = os.path.join("database", "command.json")


class fine_align(App):
    def __init__(self, *args, **kwargs):
        # Track command.json changes
        self._cmd_mtime = None
        self._first_command_check = True

        # Track shared_memory.json changes (for FineA)
        self._shared_mtime = None
        self._first_shared_check = True

        # Optional cache of FineA block
        self.fine_a = {}

        if "editing_mode" not in kwargs:
            super(fine_align, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ---------------- UTILITIES ----------------

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """
        Same pattern as AutoSweepConfig / area_scan:
        try float, then raw; ignore on failure.
        """
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    # --------- SAFE VALUE HELPERS ---------

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

    # ---------------- REMI HOOKS ----------------

    def idle(self):
        """
        Watch BOTH:
        - command.json -> execute_command()
        - shared_memory.json -> _load_from_shared()
        """

        # --- command.json watcher ---
        try:
            cmd_mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            cmd_mtime = None

        if self._first_command_check:
            self._cmd_mtime = cmd_mtime
            self._first_command_check = False
        else:
            if cmd_mtime != self._cmd_mtime:
                self._cmd_mtime = cmd_mtime
                self.execute_command()

        # --- shared_memory.json: only track mtime (for SlotInfo updates) ---
        # We do NOT auto-reload FineA fields here because other processes
        # write shared_memory frequently, which would overwrite the user's
        # uncommitted edits (e.g. changing the Detector dropdown).
        # Fields are loaded once in main() and refreshed after onclick_confirm().
        shared_mtime = get_shared_memory_mtime()

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        else:
            if shared_mtime != self._shared_mtime:
                self._shared_mtime = shared_mtime
                # Only update the dynamic detector list from SlotInfo,
                # do NOT overwrite user-editable fields.
                self._refresh_detector_options()

    def main(self):
        ui = self.construct_ui()
        # On first open, load FineA from shared_memory.json
        self._load_from_shared()
        return ui

    # ---------------- UI ----------------

    def construct_ui(self):
        BOX_W = 240  # container width
        fine_align_setting_container = StyledContainer(
            variable_name="fine_align_setting_container",
            left=0,
            top=0,
            height=370,   # adjust as needed
            width=BOX_W
        )

        # Layout constants for vertical stacking
        ROW = 32   # vertical spacing between rows
        y = 10     # initial top offset

        # Horizontal layout (similar style to area_scan, but scaled for 230px width)
        LBL_X = 10
        LBL_W = 90
        INP_W = 70
        UNIT_W = 30

        INP_X = LBL_X + LBL_W + 8           # right after label + small gap
        UNIT_X = INP_X + INP_W + 20         # right after input + small gap

        # ----- Window -----
        StyledLabel(
            container=fine_align_setting_container, text="Window",
            variable_name="window_size_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.window_size = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="window_size_in",
            left=INP_X, top=y,
            value=10,
            width=INP_W, height=24,
            min_value=-1000, max_value=1000,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="window_size_um",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Step Size -----
        StyledLabel(
            container=fine_align_setting_container, text="Step Size",
            variable_name="step_size_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.step_size = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="step_size_in",
            left=INP_X, top=y,
            value=1,
            width=INP_W, height=24,
            min_value=-1000, max_value=1000,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="step_size_um",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Max Iters -----
        StyledLabel(
            container=fine_align_setting_container, text="Max Iters",
            variable_name="max_iters_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.max_iters = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="max_iters_in",
            left=INP_X, top=y,
            value=10,
            width=INP_W, height=24,
            min_value=0, max_value=50,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="",
            variable_name="max_iters_um",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Min Grad SS -----
        StyledLabel(
            container=fine_align_setting_container, text="Min Grad SS",
            variable_name="min_grad_ss_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.min_grad_ss = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="min_grad_ss_in",
            left=INP_X, top=y,
            value=0.1,
            width=INP_W, height=24,
            min_value=0.001, max_value=10,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="min_grad_ss_um",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- G.D. Threshold -----
        StyledLabel(
            container=fine_align_setting_container, text="G.D. Threshold",
            variable_name="threshold_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.threshold = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="threshold_in",
            left=INP_X, top=y,
            value=-10.0,
            width=INP_W, height=24,
            min_value=-100.0, max_value=20.0,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="dBm",
            variable_name="threshold_dbm",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Ref WL -----
        StyledLabel(
            container=fine_align_setting_container, text="1st Ref",
            variable_name="ref_wl_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.ref_wl = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="ref_wl_in",
            left=INP_X, top=y,
            value=1550.0,
            width=INP_W, height=24,
            min_value=1456, max_value=1583,
            step=0.01,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="nm",
            variable_name="ref_wl_nm",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Secondary WL -----
        StyledLabel(
            container=fine_align_setting_container, text="2nd Ref",
            variable_name="secondary_wl_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.secondary_wl = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="secondary_wl_in",
            left=INP_X, top=y,
            value=1540.0,
            width=INP_W, height=24,
            min_value=1456, max_value=1583,
            step=0.01,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="nm",
            variable_name="secondary_wl_nm",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Secondary Loss -----
        StyledLabel(
            container=fine_align_setting_container, text="2nd Threshold",
            variable_name="secondary_loss_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        self.secondary_loss = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="secondary_loss_in",
            left=INP_X, top=y,
            value=-50.0,
            width=INP_W, height=24,
            min_value=-100.0, max_value=80.0,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="dBm",
            variable_name="secondary_loss_dbm",
            left=UNIT_X, top=y + 4,
            width=UNIT_W, height=25
        )
        y += ROW

        # ----- Detector (bottom) -----
        StyledLabel(
            container=fine_align_setting_container, text="Detector",
            variable_name="detector_lb",
            left=LBL_X, top=y + 4,
            width=LBL_W, height=25
        )

        # Initial options; will be overridden from SlotInfo in _load_from_shared
        self.detector = StyledDropDown(
            container=fine_align_setting_container,
            variable_name="detector",
            text=[
                "ch1", "ch2", "ch3", "ch4",
                "ch5", "ch6", "ch7", "ch8",
                "Max"],
            left=INP_X, top=y,
            width=INP_W, height=25,
            position="absolute"
        )
        y += ROW

        # ----- Confirm button (centered) -----
        btn_w = 90
        self.confirm_btn = StyledButton(
            container=fine_align_setting_container, text="Confirm",
            variable_name="confirm_btn",
            left=(BOX_W - btn_w) // 2, top=y,
            height=25, width=btn_w
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.fine_align_setting_container = fine_align_setting_container
        return fine_align_setting_container

    # ---------------- LOAD FROM shared_memory.json (FineA) ----------------

    def _load_from_shared(self):
        data = SharedMemory.read({})
        if not data:
            return

        # ----- Build detector list dynamically from SlotInfo -----
        slot_info = data.get("SlotInfo") or []
        channel_labels = []

        # SlotInfo entries are [slot, head], e.g. [1,0], [1,1], [4,0], [4,1]
        # Mapping: ch = 2*(slot-1) + head + 1
        for entry in slot_info:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            slot, head = entry
            try:
                slot_i = int(slot)
                head_i = int(head)
            except Exception:
                continue
            ch_num = 2 * (slot_i - 1) + head_i + 1
            channel_labels.append(f"ch{ch_num}")

        if channel_labels:
            channel_labels.append("Max")
        else:
            # Fallback if SlotInfo missing
            channel_labels = [
                "ch1", "ch2", "ch3", "ch4",
                "ch5", "ch6", "ch7", "ch8",
                "Max"]

        # Try to apply options to StyledDropDown, if the helper exists
        try:
            if hasattr(self.detector, "set_options"):
                self.detector.set_options(channel_labels)
            elif hasattr(self.detector, "update_options"):
                self.detector.update_options(channel_labels)
        except Exception:
            pass

        # ----- FineA block -----
        self.fine_a = data.get("FineA", {}) or {}

        # Scalars (window, step, grad, wavelengths)
        self._set_spin_safely(self.window_size, self.fine_a.get("window_size"))
        self._set_spin_safely(self.step_size, self.fine_a.get("step_size"))
        self._set_spin_safely(self.max_iters, self.fine_a.get("max_iters"))
        self._set_spin_safely(self.min_grad_ss, self.fine_a.get("min_gradient_ss"))
        self._set_spin_safely(self.ref_wl, self.fine_a.get("ref_wl"))
        self._set_spin_safely(self.threshold, self.fine_a.get("threshold"))
        self._set_spin_safely(self.secondary_wl, self.fine_a.get("secondary_wl"))
        self._set_spin_safely(self.secondary_loss, self.fine_a.get("secondary_loss"))

        # Detector mapping into dropdown
        det_raw = self.fine_a.get("detector", "")
        det = str(det_raw).lower()

        target = None
        for label in channel_labels:
            if label.lower() == det:
                target = label
                break

        # Special-case "max" so we accept "max", "Max", etc.
        if target is None and det == "max":
            if "Max" in channel_labels:
                target = "Max"
            elif "max" in channel_labels:
                target = "max"

        if target is not None:
            try:
                self.detector.set_value(target)
            except Exception:
                pass

    # ---------------- Save to shared_memory.json (FineA) ----------------

    def _refresh_detector_options(self):
        """Update detector dropdown OPTIONS from SlotInfo without changing the selected value."""
        data = SharedMemory.read({})
        if not data:
            return

        slot_info = data.get("SlotInfo") or []
        channel_labels = []

        for entry in slot_info:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            slot, head = entry
            try:
                slot_i = int(slot)
                head_i = int(head)
            except Exception:
                continue
            ch_num = 2 * (slot_i - 1) + head_i + 1
            channel_labels.append(f"ch{ch_num}")

        if channel_labels:
            channel_labels.append("Max")
        else:
            channel_labels = ["ch1", "ch2", "ch3", "ch4",
                              "ch5", "ch6", "ch7", "ch8", "Max"]

        # Preserve the user's current selection
        try:
            current = self.detector.get_value()
        except Exception:
            current = None

        try:
            if hasattr(self.detector, "set_options"):
                self.detector.set_options(channel_labels)
            elif hasattr(self.detector, "update_options"):
                self.detector.update_options(channel_labels)
        except Exception:
            pass

        # Restore selection if still valid
        if current and current in channel_labels:
            try:
                self.detector.set_value(current)
            except Exception:
                pass

    def onclick_confirm(self):
        value = {
            "window_size":       self._safe_float(self.window_size, 10.0),
            "step_size":         self._safe_float(self.step_size, 1.0),
            "max_iters":         self._safe_int(self.max_iters, 10),
            "min_gradient_ss":   self._safe_float(self.min_grad_ss, 0.1),
            "detector":          self._safe_str(self.detector, "Max"),
            "ref_wl":            self._safe_float(self.ref_wl, 1550.0),
            "threshold":         self._safe_float(self.threshold, -40.0),
            "secondary_wl":      self._safe_float(self.secondary_wl, 1540.0),
            "secondary_loss":    self._safe_float(self.secondary_loss, -50.0),
        }

        file = File("shared_memory", "FineA", value)
        file.save()
        print("Confirm Fine Align Setting")

        import webview
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )

    # ---------------- Commands (unchanged) ----------------

    def execute_command(self, path=command_path):
        fa = 0
        record = 0
        new_command = {}

        try:
            data = read_command_file()
            command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key.startswith("fa_set") and record == 0:
                fa = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
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

            elif key == "fa_window_size":
                self.window_size.set_value(val)
            elif key == "fa_step_size":
                self.step_size.set_value(val)
            elif key == "fa_max_iters":
                self.max_iters.set_value(val)
            elif key == "fa_min_gradient_ss":
                self.min_grad_ss.set_value(val)
            elif key == "fa_detector":
                self.detector.set_value(str(val))
            elif key == "fa_ref_wl":
                self.ref_wl.set_value(float(val))
            elif key == "fa_confirm":
                self.onclick_confirm()

        if fa == 1:
            print("fa record")
            file = File("command", "command", new_command)
            file.save()


if __name__ == "__main__":
    configuration = {
        "config_project_name": "fine_align",
        "config_address": "0.0.0.0",
        "config_port": 7003,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(
        fine_align,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"]
    )
