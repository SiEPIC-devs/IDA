from lib_gui import *
from remi import start, App
import os, json, threading

command_path = os.path.join("database", "command.json")

class area_scan(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        # Watch command.json for changes so we can update UI or execute commands
        try:
            mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            mtime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    # ---- UI ----
    def construct_ui(self):
        # Taller container to fit new controls (Step Size + Pattern)
        area_scan_setting_container = StyledContainer(
            variable_name="area_scan_setting_container", left=0, top=0, height=270, width=200
        )

        # X Size
        StyledLabel(
            container=area_scan_setting_container, text="X Size", variable_name="x_size_lb", left=0,
            top=10, width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.x_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_size_in", left=80, top=10, value=20,
            width=50, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="x_size_um", left=150, top=10,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # X Step (crosshair serpentine only; left enabled for back-compat)
        StyledLabel(
            container=area_scan_setting_container, text="X Step", variable_name="x_step_lb", left=0, top=42,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.x_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_step_in", left=80, top=42, value=1,
            width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="x_step_um", left=150, top=42,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Y Size
        StyledLabel(
            container=area_scan_setting_container, text="Y Size", variable_name="y_size_lb", left=0,
            top=74, width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.y_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_size_in", left=80, top=74, value=20,
            width=50, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="y_size_um", left=150, top=74,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Y Step (crosshair serpentine only)
        StyledLabel(
            container=area_scan_setting_container, text="Y Step", variable_name="y_step_lb", left=0, top=106,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.y_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_step_in", left=80, top=106, value=1,
            width=50, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="y_step_um", left=150, top=106,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Step Size (spiral grid uses one unified step per cell; we keep it visible for clarity)
        StyledLabel(
            container=area_scan_setting_container, text="Step Size", variable_name="step_size_lb", left=0, top=138,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.step_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="step_size_in", left=80, top=138, value=1,
            width=50, height=24, min_value=0.001, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="step_size_um", left=150, top=138,
            width=20, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Pattern selector (Crosshair / Spiral)
        StyledLabel(
            container=area_scan_setting_container, text="Pattern", variable_name="pattern_lb", left=0, top=170,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.pattern_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="pattern_dd",
            text=["Crosshair", "Spiral"], left=80, top=170, width=90, height=24, position="absolute"
        )
        # Default to Spiral to match your current defaults; change to "Crosshair" if you prefer
        self.pattern_dd.set_value("Spiral")
        self.pattern_dd.do_onchange(lambda *_: self._on_pattern_change())

        # Plot behavior (unchanged)
        StyledLabel(
            container=area_scan_setting_container, text="Plot", variable_name="plot_lb", left=0, top=202,
            width=70, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.plot_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="plot_dd", text=["New", "Previous"],
            left=80, top=202, width=90, height=24, position="absolute"
        )

        # Confirm
        self.confirm_btn = StyledButton(
            container=area_scan_setting_container, text="Confirm", variable_name="confirm_btn",
            left=68, top=236, height=25, width=70, font_size=90
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.area_scan_setting_container = area_scan_setting_container
        # Initialize field enabling/visibility based on default pattern
        self._on_pattern_change()
        return area_scan_setting_container

    # ---- Events & helpers ----
    def _on_pattern_change(self):
        """Toggle hinting/enabling for step fields based on pattern."""
        pat = self._get_pattern_text()
        spiral = (pat == "Spiral")

        # We keep all fields visible for clarity/back-compat; just hint by enabling preferred ones.
        self._set_enabled(self.step_size, spiral)   # spiral prefers step_size
        self._set_enabled(self.x_step, not spiral)  # crosshair prefers x_step/y_step
        self._set_enabled(self.y_step, not spiral)

    def _set_enabled(self, widget, enabled: bool):
        """Best-effort enabling/readonly helper for Styled widgets."""
        try:
            widget.set_enabled(enabled)  # if provided by your StyledSpinBox
        except Exception:
            try:
                widget.set_readonly(not enabled)
            except Exception:
                # Last resort: set the 'disabled' HTML attribute
                try:
                    if enabled:
                        widget.attributes.pop('disabled', None)
                    else:
                        widget.attributes['disabled'] = 'true'
                except Exception:
                    pass

    def _get_pattern_text(self) -> str:
        return self.pattern_dd.get_value()

    def _get_pattern_keypair(self):
        """Returns ('pattern', 'use_spiral') coherent with backend."""
        pat = self._get_pattern_text()
        if isinstance(pat, str):
            p = pat.strip().lower()
        else:
            p = "crosshair"
        if p not in ("crosshair", "spiral"):
            p = "crosshair"
        return p, (p == "spiral")

    # ---- Confirm/save ----
    def onclick_confirm(self):
        # Resolve pattern & boolean for back-compat with cfg.use_spiral
        pattern, use_spiral = self._get_pattern_keypair()

        # Always emit both the new fields and the legacy ones.
        # - For spiral, back-fill x_step/y_step with step_size (keeps legacy consumers happy).
        # - For crosshair, still write step_size (some backends expect it).
        step_size_val = float(self.step_size.get_value())
        x_step_val = float(self.x_step.get_value())
        y_step_val = float(self.y_step.get_value())

        if use_spiral:
            x_step_out = step_size_val
            y_step_out = step_size_val
        else:
            x_step_out = x_step_val
            y_step_out = y_step_val

        value = {
            # extents
            "x_size": float(self.x_size.get_value()),
            "y_size": float(self.y_size.get_value()),
            # per-axis steps for crosshair / back-compat
            "x_step": float(x_step_out),
            "y_step": float(y_step_out),
            # unified step for spiral (and new configs)
            "step_size": float(step_size_val),
            # pattern selection (both string and bool for cfg compatibility)
            "pattern": pattern,
            "use_spiral": bool(use_spiral),
            # plotting
            "plot": self.plot_dd.get_value(),
        }

        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting:", value)

    # ---- Command ingestion ----
    def execute_command(self, path=command_path):
        area = 0
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
            # pass-through keys to next stage
            if key.startswith("as_set") and record == 0:
                area = 1
            elif key.startswith(("stage_control", "tec_control", "sensor_control",
                                 "fa_set", "lim_set", "sweep_set",
                                 "devices_control", "testing_control")) or record == 1:
                record = 1
                new_command[key] = val

            # UI-bound keys
            elif key == "as_x_size":
                self.x_size.set_value(val)
            elif key == "as_x_step":
                self.x_step.set_value(val)
            elif key == "as_y_size":
                self.y_size.set_value(val)
            elif key == "as_y_step":
                self.y_step.set_value(val)
            elif key == "as_step_size":
                self.step_size.set_value(val)
            elif key in ("as_pattern", "as_use_spiral"):
                # Normalize either form into the dropdown value
                if key == "as_pattern":
                    p = str(val).strip().lower()
                    ui_val = "Spiral" if p == "spiral" else "Crosshair"
                else:
                    ui_val = "Spiral" if bool(val) else "Crosshair"
                self.pattern_dd.set_value(ui_val)
                self._on_pattern_change()
            elif key == "as_plot":
                if isinstance(val, str):
                    low = val.lower()
                    if low == "new":
                        val = "New"
                    elif low == "previous":
                        val = "Previous"
                    else:
                        val = "New"
                self.plot_dd.set_value(val)
            elif key == "as" and val == "confirm":
                self.onclick_confirm()

        if area == 1:
            print("as record")
            file = File("command", "command", new_command)
            file.save()

# ---- App entry ----
if __name__ == "__main__":
    configuration = {
        "config_project_name": "area_scan",
        "config_address": "0.0.0.0",
        "config_port": 7004,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(area_scan,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
