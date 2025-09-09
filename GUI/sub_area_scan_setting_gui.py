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

    # ---------------- UI ----------------
    def construct_ui(self):
        # Layout constants for clean alignment
        BOX_W, BOX_H = 320, 360
        LBL_W, INP_W, UNIT_W = 120, 90, 50
        LBL_X, INP_X, UNIT_X = 10, 10 + LBL_W + 8, 10 + LBL_W + 8 + INP_W + 6

        y = 10
        ROW = 30

        area_scan_setting_container = StyledContainer(
            variable_name="area_scan_setting_container",
            left=0, top=0, width=BOX_W, height=BOX_H
        )
        # Make long content scroll instead of overflow-cut
        try:
            area_scan_setting_container.style['overflow'] = 'auto'
        except Exception:
            pass

        # Helper to attach a tooltip if supported
        def tooltip(widget, text: str):
            try:
                widget.attributes['title'] = text
            except Exception:
                pass

        # Title row
        StyledLabel(
            container=area_scan_setting_container, text="Area Scan Settings",
            variable_name="title_lb", left=10, top=y, width=BOX_W-20, height=24,
            font_size=110, flex=True, justify_content="left", color="#111"
        )
        y += ROW

        # Pattern
        StyledLabel(container=area_scan_setting_container, text="Pattern",
                    variable_name="pattern_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.pattern_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="pattern_dd",
            text=["Crosshair", "Spiral"], left=INP_X, top=y, width=INP_W+UNIT_W, height=24, position="absolute"
        )
        self.pattern_dd.set_value("Crosshair")
        y += ROW

        # Pattern hint line (updates when Pattern changes)
        self.pattern_hint = StyledLabel(
            container=area_scan_setting_container, text="Crosshair: uses X Step and Y Step.",
            variable_name="pattern_hint", left=LBL_X, top=y, width=BOX_W-2*LBL_X, height=22,
            font_size=90, flex=True, justify_content="left", color="#666"
        )
        y += ROW

        # X Size
        StyledLabel(container=area_scan_setting_container, text="X Size",
                    variable_name="x_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.x_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_size_in",
            left=INP_X, top=y, value=20, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(container=area_scan_setting_container, text="µm",  # nicer micro symbol
                    variable_name="x_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # Y Size
        StyledLabel(container=area_scan_setting_container, text="Y Size",
                    variable_name="y_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.y_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_size_in",
            left=INP_X, top=y, value=20, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="y_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # --- Crosshair controls ---
        StyledLabel(container=area_scan_setting_container, text="X Step (Crosshair)",
                    variable_name="x_step_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.x_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_step_in",
            left=INP_X, top=y, value=1, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        tooltip(self.x_step, "Used when Pattern = Crosshair. Saved as x_step.")
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="x_step_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        StyledLabel(container=area_scan_setting_container, text="Y Step (Crosshair)",
                    variable_name="y_step_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.y_step = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_step_in",
            left=INP_X, top=y, value=1, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=0.1, position="absolute"
        )
        tooltip(self.y_step, "Used when Pattern = Crosshair. Saved as y_step.")
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="y_step_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # --- Spiral control ---
        StyledLabel(container=area_scan_setting_container, text="Step Size (Spiral)",
                    variable_name="step_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.step_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="step_size_in",
            left=INP_X, top=y, value=1, width=INP_W, height=24,
            min_value=0.001, max_value=1000, step=0.1, position="absolute"
        )
        tooltip(self.step_size, "Used when Pattern = Spiral. Mirrored to both x_step and y_step on save.")
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="step_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # Plot selector
        StyledLabel(container=area_scan_setting_container, text="Plot",
                    variable_name="plot_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.plot_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="plot_dd",
            text=["New", "Previous"], left=INP_X, top=y, width=INP_W+UNIT_W, height=24, position="absolute"
        )
        y += ROW

        # Confirm button
        self.confirm_btn = StyledButton(
            container=area_scan_setting_container, text="Confirm",
            variable_name="confirm_btn", left=(BOX_W-80)//2, top=y+6, height=28, width=80, font_size=90
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        # Try to attach onchange for live hint updates (guarded)
        try:
            self.pattern_dd.do_onchange(lambda *_: self._update_pattern_hint())
        except Exception:
            pass

        # Initial hint
        self._update_pattern_hint()
        return area_scan_setting_container

    # Clarifies which fields apply in each mode (no enabling/hiding; pure text)
    def _update_pattern_hint(self):
        try:
            pat = self.pattern_dd.get_value()
            spiral = (isinstance(pat, str) and pat.lower() == "spiral")
        except Exception:
            spiral = False
        if spiral:
            text = "Spiral: uses Step Size (mirrored to X/Y Step on save)."
        else:
            text = "Crosshair: uses X Step and Y Step."
        try:
            self.pattern_hint.set_text(text)
        except Exception:
            # fallback: ignore if StyledLabel doesn't expose set_text
            pass

    # ---------------- Save (protocol unchanged) ----------------
    def onclick_confirm(self):
        """
        We still write ONLY: x_size, x_step, y_size, y_step, plot.
        If Pattern == 'Spiral', mirror step_size into x_step & y_step here.
        """
        try:
            pat = self.pattern_dd.get_value()
            spiral = (isinstance(pat, str) and pat.lower() == "spiral")
        except Exception:
            spiral = False

        if spiral:
            try:
                step_val = float(self.step_size.get_value())
            except Exception:
                step_val = 1.0
            x_step_out = step_val
            y_step_out = step_val
        else:
            x_step_out = float(self.x_step.get_value())
            y_step_out = float(self.y_step.get_value())

        value = {
            "x_size": float(self.x_size.get_value()),
            "x_step": float(x_step_out),
            "y_size": float(self.y_size.get_value()),
            "y_step": float(y_step_out),
            "plot": self.plot_dd.get_value(),
        }
        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting:", value)

    # ---------------- Commands (unchanged) ----------------
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
            if key.startswith("as_set") and record == 0:
                area = 1
            elif key.startswith(("stage_control", "tec_control", "sensor_control",
                                 "fa_set", "lim_set", "sweep_set",
                                 "devices_control", "testing_control")) or record == 1:
                record = 1
                new_command[key] = val

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
