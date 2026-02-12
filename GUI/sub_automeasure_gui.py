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

        # Widgets
        self.power = None
        self.step_size = None
        self.start_wvl = None
        self.stop_wvl = None
        self.range_mode_dd = None
        self.manual_range = None
        self.ref_value = None
        self.detector = None
        self.confirm_btn = None
        self.detector_window_btn = None
        self.fine_align_btn = None  # NEW

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
        """Reload when shared_memory.json changes on disk."""
        stime = get_shared_memory_mtime()

        if self._first_check:
            self._user_stime = stime
            self._first_check = False
            return

        if stime != self._user_stime:
            self._user_stime = stime
            self._load_from_shared()

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
            width=280,
            height=260,
        )

        y = 10
        row_h = 28

        # Detector window launch settings
        self.detector_window_btn = StyledButton(
            container=root,
            text="Detector Window",
            variable_name="detector_window_btn",
            left=105,
            top=y,
            width=100,
            height=24,
            font_size=90,
        )
        self.detector_window_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_detector_window)
        )

        # Fine Align button (directly below Detector Window)  # NEW
        y += row_h
        self.fine_align_btn = StyledButton(
            container=root,
            text="Fine Align",
            variable_name="fine_align_btn",
            left=105,
            top=y,
            width=100,
            height=24,
            font_size=90,
        )
        self.fine_align_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_fine_align)
        )
        # Power
        y += row_h

        StyledLabel(
            container=root,
            text="Power",
            variable_name="power_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.power = StyledSpinBox(
            container=root,
            variable_name="power_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=0.0,
            min_value=-110,
            max_value=30,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="power_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Step size
        y += row_h
        StyledLabel(
            container=root,
            text="Step",
            variable_name="step_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.step_size = StyledSpinBox(
            container=root,
            variable_name="step_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=0.001,
            min_value=0,
            max_value=1000,
            step=0.001,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="step_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Start wavelength
        y += row_h
        StyledLabel(
            container=root,
            text="Start Wvl",
            variable_name="start_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.start_wvl = StyledSpinBox(
            container=root,
            variable_name="start_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=1500.0,
            min_value=1456,
            max_value=1583,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="start_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Stop wavelength
        y += row_h
        StyledLabel(
            container=root,
            text="Stop Wvl",
            variable_name="stop_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stop_wvl = StyledSpinBox(
            container=root,
            variable_name="stop_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=1580.0,
            min_value=1456,
            max_value=1583,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="stop_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )


        # FA detector selection (FineA.detector)
        # y += row_h
        # StyledLabel(
        #     container=root,
        #     text="FA Detector",
        #     variable_name="detector_lb",
        #     left=5,
        #     top=y,
        #     width=95,
        #     height=25,
        #     font_size=100,
        #     flex=True,
        #     justify_content="right",
        #     color="#222",
        # )

        # self.detector = StyledDropDown(
        #     container=root,
        #     variable_name="detector",
        #     text=["ch1", "ch2", "Max"],
        #     left=105,
        #     top=y,
        #     width=70,
        #     height=25,
        #     position="absolute",
        # )

        # Confirm button
        y += row_h
        self.confirm_btn = StyledButton(
            container=root,
            text="Confirm",
            variable_name="confirm_btn",
            left=105,
            top=y,
            width=80,
            height=24,
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

        # Sweep
        self.sweep = data.get("Sweep", {}) or {}
        self._set_spin_safely(self.power, self.sweep.get("power"))
        self._set_spin_safely(self.step_size, self.sweep.get("step"))
        self._set_spin_safely(self.start_wvl, self.sweep.get("start"))
        self._set_spin_safely(self.stop_wvl, self.sweep.get("end"))

        # # FineA.detector -> FA Detector dropdown (read-only / non-destructive)
        # finea = data.get("FineA")
        # if isinstance(finea, dict) and self.detector is not None:
        #     det = str(finea.get("detector", "")).lower()
        #     if det == "ch1":
        #         target = "ch1"
        #     elif det == "ch2":
        #         target = "ch2"
        #     elif det == "max":
        #         target = "Max"
        #     else:
        #         target = None

        #     if target:
        #         try:
        #             self.detector.set_value(target)
        #         except Exception:
        #             pass

    # ---------------- CONFIRM: WRITE BACK ----------------

    def onclick_confirm(self):
        # Load current shared_memory
        data = SharedMemory.read({})

        if not isinstance(data, dict):
            data = {}

        # ---- Sweep (merge) ----
        existing_sweep = data.get("Sweep", {})
        if not isinstance(existing_sweep, dict):
            existing_sweep = {}

        try:
            existing_sweep.update(
                {
                    "power": float(self.power.get_value()),
                    "step": float(self.step_size.get_value()),
                    "start": float(self.start_wvl.get_value()),
                    "end": float(self.stop_wvl.get_value()),
                }
            )
        except Exception as exc:
            print(f"[AutoSweepConfig] Invalid sweep input: {exc}")
            return

        File("shared_memory", "Sweep", existing_sweep).save()

        # ---- FineA.detector ----
        finea = data.get("FineA")
        if isinstance(finea, dict) and self.detector is not None:
            try:
                det_ui = str(self.detector.get_value())
            except Exception:
                det_ui = ""

            det_norm = det_ui.lower()
            if det_norm == "max":
                det_norm = "max"
            elif det_norm in ("ch1", "ch2"):
                pass
            else:
                # If invalid choice, keep existing detector
                current = str(finea.get("detector", "")).lower()
                if current in ("ch1", "ch2", "max"):
                    det_norm = current
                else:
                    det_norm = "max"

            finea["detector"] = det_norm
            File("shared_memory", "FineA", finea).save()

        print("[AutoSweepConfig] Updated Sweep and FineA.detector")
        # NOTE: removed the hidden webview.create_window here.
        # This app just writes config; windows are managed by pywebview main.

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

    def onclick_fine_align(self):  # NEW
        """Launch Fine Alignment window."""
        local_ip = "127.0.0.1"
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=262 + web_w,
            height=426 + web_h,
            resizable=True,
            on_top=True,
            hidden=False,   # set False so it actually shows when button is clicked
        )
        print("[AutoSweepConfig] Fine Align window requested")

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
        width=280 + web_w,
        height=260 + web_h,
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
