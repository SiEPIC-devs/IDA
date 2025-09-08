from lib_gui import *
from remi import start, App
import os, json, threading  # keep imports aligned with original file

command_path = os.path.join("database", "command.json")

class area_scan(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        # unchanged behavior: watch command.json and react
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

    # ---------- UI ----------
    def construct_ui(self):
        # Bigger box to fit pattern toggle + step size
        area_scan_setting_container = StyledContainer(
            variable_name="area_scan_setting_container", left=0, top=0, height=300, width=240
        )

        # X Size
        StyledLabel(
            container=area_scan_setting_container, text="X Size", variable_name="x_size_lb",
            left=0, top=10, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.x_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_size_in",
            left=90, top=10, value=20, width=70, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="x_size_um",
            left=170, top=10, width=40, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # X Step (Crosshair only)
        StyledLabel(
            container=area_scan_setting_container, text="X Step", variable_name="x_step_lb",
            left=0, top=42, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.x_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_step_in",
            left=90, top=42, value=1, width=70, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="x_step_um",
            left=170, top=42, width=40, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Y Size
        StyledLabel(
            container=area_scan_setting_container, text="Y Size", variable_name="y_size_lb",
            left=0, top=74, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.y_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_size_in",
            left=90, top=74, value=20, width=70, height=24, min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="y_size_um",
            left=170, top=74, width=40, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Y Step (Crosshair only)
        StyledLabel(
            container=area_scan_setting_container, text="Y Step", variable_name="y_step_lb",
            left=0, top=106, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.y_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_step_in",
            left=90, top=106, value=1, width=70, height=24, min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="y_step_um",
            left=170, top=106, width=40, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Step Size (Spiral only; we map it to x_step/y_step on Confirm)
        StyledLabel(
            container=area_scan_setting_container, text="Step Size", variable_name="step_size_lb",
            left=0, top=138, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.step_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="step_size_in",
            left=90, top=138, value=1, width=70, height=24, min_value=0.001, max_value=1000, step=0.1, position="absolute"
        )
        StyledLabel(
            container=area_scan_setting_container, text="um", variable_name="step_size_um",
            left=170, top=138, width=40, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        # Pattern selector
        StyledLabel(
            container=area_scan_setting_container, text="Pattern", variable_name="pattern_lb",
            left=0, top=170, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.pattern_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="pattern_dd",
            text=["Crosshair", "Spiral"], left=90, top=170, width=120, height=24, position="absolute"
        )
        self.pattern_dd.set_value("Crosshair")  # default matches legacy behavior
        self.pattern_dd.do_onchange(lambda *_: self._on_pattern_change())

        # Plot
        StyledLabel(
            container=area_scan_setting_container, text="Plot", variable_name="plot_lb",
            left=0, top=202, width=80, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )
        self.plot_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="plot_dd",
            text=["New", "Previous"], left=90, top=202, width=120, height=24, position="absolute"
        )

        # Confirm
        self.confirm_btn = StyledButton(
            container=area_scan_setting_container, text="Confirm", variable_name="confirm_btn",
            left=85, top=236, height=28, width=80, font_size=90
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.area_scan_setting_container = area_scan_setting_container

        # First-time toggle to reflect default pattern
        self._on_pattern_change()
        return area_scan_setting_container

    # ---- UI helpers ----
    def _show(self, widget, visible: bool):
        """Best-effort show/hide that works with our Styled widgets."""
        try:
            widget.set_visibility(visible)
            return
        except Exception:
            pass
        try:
            widget.style['display'] = 'block' if visible else 'none'
            return
        except Exception:
            pass
        try:
            if visible:
                widget.attributes.pop('hidden', None)
            else:
                widget.attributes['hidden'] = 'true'
        except Exception:
            pass

    def _on_pattern_change(self):
        """Switch visible inputs based on selected pattern."""
        pat = self.pattern_dd.get_value()
        spiral = (isinstance(pat, str) and pat.lower() == "spiral")

        # Crosshair controls
        self._show(self.x_step, not spiral)
        self._show(self.y_step, not spiral)
        self._show(self.x_step_lb, not spiral)
        self._show(self.y_step_lb, not spiral)
        self._show(self.x_step_um, not spiral)
        self._show(self.y_step_um, not spiral)

        # Spiral control
        self._show(self.step_size, spiral)
        self._show(self.step_size_lb, spiral)
        self._show(self.step_size_um, spiral)

    # ---- Confirm/save (wire protocol unchanged) ----
    def onclick_confirm(self):
        """
        We still write ONLY: x_size, x_step, y_size, y_step, plot.
        If Pattern == 'Spiral', we map step_size -> x_step AND y_step.
        """
        pat = self.pattern_dd.get_value()
        spiral = (isinstance(pat, str) and pat.lower() == "spiral")

        if spiral:
            x_step_out = float(self.step_size.get_value())
            y_step_out = float(self.step_size.get_value())
        else:
            x_step_out = float(self.x_step.get_value())
            y_step_out = float(self.y_step.get_value())

        value = {
            "x_size": float(self.x_size.get_value()),
            "x_step": float(x_step_out),   # Spiral: uses step_size as x_step (and y_step)
            "y_size": float(self.y_size.get_value()),
            "y_step": float(y_step_out),
            "plot": self.plot_dd.get_value(),
        }
        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting")

    # ---- Command ingestion (identical protocol) ----
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

            # GUI-bound keys (unchanged)
            elif key == "as_x_size":
                self.x_size.set_value(val)
            elif key == "as_x_step":
                self.x_step.set_value(val)
            elif key == "as_y_size":
                self.y_size.set_value(val)
            elif key == "as_y_step":
                self.y_step.set_value(val)
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

# ---- App entry (unchanged) ----
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
