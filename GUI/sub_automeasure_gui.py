import datetime
import json
import os
import threading
import signal
import sys

from remi import App, start
from GUI.lib_gui import *
import webview  

SHARED_PATH = os.path.join("database", "shared_memory.json")


class AutoSweepConfig(App):
    """Auto sweep settings panel."""

    def __init__(self, *args, **kwargs):
        # Track shared_memory.json changes
        self._user_stime = None
        self._first_check = True

        # Cached sweep block
        self.sweep = {}

        # EO settings widgets
        self.eo_bias_voltage = None
        self.eo_step_down = None
        self.eo_force_contact = None
        self.eo_min_current = None
        self.eo_current_stable = None
        self.eo_stable_count = None
        self.eo_max_force = None
        self.eo_retract_step = None
        self.eo_retract_final = None
        self.eo_max_descent = None
        self.eo_max_retract = None

        # Button widgets
        self.detector_window_btn = None
        self.fine_align_btn = None
        self.laser_sweep_btn = None
        self.confirm_btn = None

        # REMI init (support editing_mode)
        editing_mode = kwargs.pop("editing_mode", False)
        super_kwargs = {}
        if not editing_mode:
            super_kwargs["static_file_path"] = {"my_res": "./res/"}
        super(AutoSweepConfig, self).__init__(*args, **super_kwargs)

    # ---------------- REMI HOOKS ----------------

    def main(self):
        ui = None
        try:
            ui = self.construct_ui()
            # print("[AutoSweepConfig] UI constructed:", ui)
            self._load_from_shared()
            # print("[AutoSweepConfig] _load_from_shared() completed")
        except Exception as e:
            import traceback
            print("[AutoSweepConfig] main() FAILED with:", repr(e))
            traceback.print_exc()
            # Fallback UI if something exploded so `ui` isn't None
            root = StyledContainer(
                variable_name="auto_sweep_container_error",
                left=0,
                top=0,
                width=280,
                height=260,
            )
            StyledLabel(
                container=root,
                text="AutoSweepConfig UI error",
                variable_name="error_lb",
                left=5,
                top=10,
                width=260,
                height=30,
                font_size=100,
                flex=True,
                justify_content="center",
                color="#b00",
            )
            ui = root
        return ui

    def idle(self):
        """Track shared_memory changes but do NOT reload user-editable fields.
        Fields are loaded once in main() and refreshed after onclick_confirm()."""
        stime = get_shared_memory_mtime()

        if self._first_check:
            self._user_stime = stime
            self._first_check = False
            return

        if stime != self._user_stime:
            self._user_stime = stime
            # Only track mtime; do not overwrite user edits

    # ---------------- UTIL ----------------

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """Set a spinbox if widget/value are valid."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    # ---------------- UI ----------------

    def construct_ui(self):
        root = StyledContainer(
            variable_name="auto_sweep_container",
            left=0,
            top=0,
            width=330,
            height=520,
        )

        btn_w = 120
        btn_h = 28
        btn_left = 105
        y = 10
        btn_row_h = 32
        row_h = 28

        # --- Buttons row ---
        # Detector Window button
        self.detector_window_btn = StyledButton(
            container=root,
            text="Detector Window",
            variable_name="detector_window_btn",
            left=btn_left,
            top=y,
            width=btn_w,
            height=btn_h,
            font_size=90,
        )
        self.detector_window_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_detector_window)
        )

        # Fine Align button
        y += btn_row_h
        self.fine_align_btn = StyledButton(
            container=root,
            text="Fine Align",
            variable_name="fine_align_btn",
            left=btn_left,
            top=y,
            width=btn_w,
            height=btn_h,
            font_size=90,
        )
        self.fine_align_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_fine_align)
        )

        # Laser Sweep button
        y += btn_row_h
        self.laser_sweep_btn = StyledButton(
            container=root,
            text="Laser Sweep",
            variable_name="laser_sweep_btn",
            left=btn_left,
            top=y,
            width=btn_w,
            height=btn_h,
            font_size=90,
        )
        self.laser_sweep_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_laser_sweep)
        )

        # --- Separator label ---
        y += btn_row_h + 4
        StyledLabel(
            container=root,
            text="─── EO Probe Settings ───",
            variable_name="eo_sep_lb",
            left=5, top=y, width=320, height=20,
            font_size=85, flex=True, justify_content="center", color="#555",
        )

        # --- EO parameter rows ---
        y += 24
        label_w = 140
        spin_w = 65
        unit_w = 50
        spin_left = 150
        unit_left = 238

        def _add_row(label_text, var_name, unit_text, value, min_v, max_v, step):
            nonlocal y
            StyledLabel(
                container=root, text=label_text, variable_name=f"{var_name}_lb",
                left=5, top=y, width=label_w, height=row_h,
                font_size=90, flex=True, justify_content="right", color="#222",
            )
            spin = StyledSpinBox(
                container=root, variable_name=f"{var_name}_in",
                left=spin_left, top=y, width=spin_w, height=24,
                value=value, min_value=min_v, max_value=max_v, step=step,
            )
            StyledLabel(
                container=root, text=unit_text, variable_name=f"{var_name}_unit",
                left=unit_left, top=y, width=unit_w, height=row_h,
                font_size=90, flex=True, justify_content="left", color="#222",
            )
            y += row_h
            return spin

        self.eo_bias_voltage   = _add_row("Bias Voltage",      "eo_bias",       "V",   0.8,   0, 10,    0.1)
        self.eo_step_down      = _add_row("Step Down",          "eo_step",       "µm",  10,    1, 500,   1)
        self.eo_force_contact  = _add_row("Force Contact",      "eo_fcontact",   "g",   0.5,   0.01, 10, 0.01)
        self.eo_min_current    = _add_row("Min Current",        "eo_mincur",     "µA",  10.0,  0, 1000,  1)
        self.eo_current_stable = _add_row("Current Stable",     "eo_curstable",  "µA",  3.0,   0, 100,   0.1)
        self.eo_stable_count   = _add_row("Stable Count",       "eo_stblcnt",    "",    3,     1, 20,    1)
        self.eo_max_force      = _add_row("Max Force",          "eo_maxforce",   "g",   50.0,  1, 500,   1)
        self.eo_retract_step   = _add_row("Retract Step",       "eo_retstep",    "µm",  50,    1, 1000,  10)
        self.eo_retract_final  = _add_row("Retract Final",      "eo_retfinal",   "µm",  200,   10, 5000, 10)
        self.eo_max_descent    = _add_row("Max Descent",        "eo_maxdesc",    "µm",  5000,  100, 50000, 100)
        self.eo_max_retract    = _add_row("Max Retract",        "eo_maxret",     "µm",  5000,  100, 50000, 100)

        # --- Confirm button ---
        y += 6
        self.confirm_btn = StyledButton(
            container=root,
            text="Confirm",
            variable_name="confirm_btn",
            left=btn_left,
            top=y,
            width=btn_w,
            height=btn_h,
            font_size=90,
        )
        self.confirm_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_confirm)
        )

        self.auto_sweep_container = root
        return root

    # --- LOAD EXISTING STATE ---

    def _load_from_shared(self):
        data = SharedMemory.read({})
        if not data:
            return
        self.sweep = data.get("Sweep", {}) or {}

        # Load EO settings
        eo = data.get("EO_Settings", {})
        if eo:
            self._set_spin_safely(self.eo_bias_voltage,   eo.get("bias_voltage"))
            self._set_spin_safely(self.eo_step_down,      eo.get("step_down_um"))
            self._set_spin_safely(self.eo_force_contact,  eo.get("force_contact_g"))
            self._set_spin_safely(self.eo_min_current,    eo.get("min_current_ua"))
            self._set_spin_safely(self.eo_current_stable, eo.get("current_stable_ua"))
            self._set_spin_safely(self.eo_stable_count,   eo.get("stable_count"))
            self._set_spin_safely(self.eo_max_force,      eo.get("max_force_g"))
            self._set_spin_safely(self.eo_retract_step,   eo.get("retract_step_um"))
            self._set_spin_safely(self.eo_retract_final,  eo.get("retract_final_um"))
            self._set_spin_safely(self.eo_max_descent,    eo.get("max_descent_um"))
            self._set_spin_safely(self.eo_max_retract,    eo.get("max_retract_um"))

    # ---------------- CONFIRM: WRITE BACK ----------------

    def onclick_confirm(self):
        """Save all EO settings to shared_memory."""
        try:
            eo_settings = {
                "bias_voltage":     float(self.eo_bias_voltage.get_value()),
                "step_down_um":     float(self.eo_step_down.get_value()),
                "force_contact_g":  float(self.eo_force_contact.get_value()),
                "min_current_ua":   float(self.eo_min_current.get_value()),
                "current_stable_ua":float(self.eo_current_stable.get_value()),
                "stable_count":     int(float(self.eo_stable_count.get_value())),
                "max_force_g":      float(self.eo_max_force.get_value()),
                "retract_step_um":  float(self.eo_retract_step.get_value()),
                "retract_final_um": float(self.eo_retract_final.get_value()),
                "max_descent_um":   float(self.eo_max_descent.get_value()),
                "max_retract_um":   float(self.eo_max_retract.get_value()),
            }
        except Exception as exc:
            print(f"[AutoSweepConfig] Invalid EO input: {exc}")
            return

        SharedMemory.update({"EO_Settings": eo_settings})
        print(f"[AutoSweepConfig] EO Settings saved: {eo_settings}")

    def onclick_detector_window(self):
        """Launch detector window settings."""
        # local_ip = get_local_ip()  
        local_ip = "127.0.0.1"
        webview.create_window(
            "Detector Window Settings",
            f"http://{local_ip}:7006",
            width=302 + web_w,
            height=856 + web_h,
            resizable=True,
            on_top=True,
            hidden=False,
        )
        print("[AutoSweepConfig] Detector Window Settings requested")

    def onclick_fine_align(self):
        """Launch Fine Alignment window."""
        local_ip = "127.0.0.1"
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=262 + web_w,
            height=426 + web_h,
            resizable=True,
            on_top=True,
            hidden=False,
        )
        print("[AutoSweepConfig] Fine Align window requested")

    def onclick_laser_sweep(self):
        """Launch Laser Sweep configure window (same as sensor Configure)."""
        local_ip = "127.0.0.1"
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7101",
            width=262 + web_w,
            height=416 + web_h,
            resizable=True,
            on_top=True,
            hidden=False,
        )
        print("[AutoSweepConfig] Laser Sweep config window requested")

def run_remi():
    start(
        AutoSweepConfig,
        address="0.0.0.0",
        port=7109,
        multiple_instance=False,
        enable_file_cache=False,
        start_browser=False,
    )


def disable_scroll():
    try:
        if webview.windows:
            webview.windows[0].evaluate_js(
                """
                document.documentElement.style.overflow = 'hidden';
                document.body.style.overflow = 'hidden';
                """
            )
    except Exception as e:
        print("JS Wrong", e)


if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    local_ip = "127.0.0.1"

    # Main window hosting this config panel
    webview.create_window(
        "Auto Sweep Config",
        f"http://{local_ip}:7109",
        width=340 + web_w,
        height=560 + web_h,
        resizable=True,
        hidden=True,
    )

    webview.create_window(
        "Detector Window Settings",
        f"http://{local_ip}:7006",
        width=302 + web_w,
        height=856 +web_h,
        resizable=True,
        on_top=True,
        hidden=True,
    )


    webview.create_window(
        "Fine Alignment Settings",
        f"http://{local_ip}:7003",
        width=240 + web_w,
        height=370 + web_h,
        resizable=True,
        on_top=True,
        hidden=True,
    )


    webview.start(func=disable_scroll)
    sys.exit(0)
