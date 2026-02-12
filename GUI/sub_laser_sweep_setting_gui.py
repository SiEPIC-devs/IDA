from GUI.lib_gui import *
from remi import start, App
import os
import json
import threading

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


class add_btn(App):
    def __init__(self, *args, **kwargs):
        # Track modification times
        self._cmd_mtime = None
        self._shared_mtime = None
        self._first_command_check = True
        self._first_shared_check = True

        # Local cache of Sweep block from shared_memory.json
        self.sweep = {}

        if "editing_mode" not in kwargs:
            super(add_btn, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _set_spin_safely(widget, value):
        """Safely set SpinBox value with float fallback."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    # ------------------------------------------------------------------
    # REMI hooks
    # ------------------------------------------------------------------
    def idle(self):
        # ---------------- command.json watcher ----------------
        try:
            cmd_mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            cmd_mtime = None

        if self._first_command_check:
            self._cmd_mtime = cmd_mtime
            self._first_command_check = False
        elif cmd_mtime != self._cmd_mtime:
            self._cmd_mtime = cmd_mtime
            self.execute_command()

        # ---------------- shared_memory.json watcher ----------------
        shared_mtime = get_shared_memory_mtime()

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        elif shared_mtime != self._shared_mtime:
            self._shared_mtime = shared_mtime
            self._load_from_shared()

    def main(self):
        ui = self.construct_ui()
        # Load Sweep settings from shared_memory.json on startup
        self._load_from_shared()
        return ui

    # ------------------------------------------------------------------
    # Load from shared_memory.json → Sweep block
    # ------------------------------------------------------------------
    def _load_from_shared(self):
        """
        Populate laser sweep UI from shared_memory.json::Sweep.

        Expected structure (example):
        {
          "Sweep": {
            "wvl": 1550.0,
            "power": 0.0,
            "step": 0.001,
            "start": 1540.0,
            "end": 1580.0,
            "done": "Laser On" | "Laser Off" | "on" | "off",
            "sweep": 0 or 1,
            "on": 0 or 1
          }
        }
        """
        data = SharedMemory.read({})

        sweep = data.get("Sweep", {})
        if not isinstance(sweep, dict):
            sweep = {}

        self.sweep = sweep

        # Power
        self._set_spin_safely(self.power, sweep.get("power", 0.0))

        # Step size (was not previously pulled from shared; now mirrored from Sweep.step)
        self._set_spin_safely(self.step_size, sweep.get("step", 0.001))

        # Start / Stop wavelength
        self._set_spin_safely(self.start_wvl, sweep.get("start", 1500.0))
        self._set_spin_safely(self.stop_wvl, sweep.get("end", 1580.0))

        # When Done (Laser On / Laser Off)
        done = sweep.get("done")
        if isinstance(done, str):
            d = done.strip().lower()
            if d in ("laser on", "on"):
                try:
                    self.on_off.set_value("Laser On")
                except Exception:
                    pass
            elif d in ("laser off", "off"):
                try:
                    self.on_off.set_value("Laser Off")
                except Exception:
                    pass
        # If done is missing, keep whatever the UI default currently is

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def construct_ui(self):
        laser_sweep_container = StyledContainer(
            variable_name="laser_sweep_container", left=0, top=0, height=224, width=240
        )

        StyledLabel(
            container=laser_sweep_container, text="Power", variable_name="laser_power_lb", left=0, top=12,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.power = StyledSpinBox(
            container=laser_sweep_container, variable_name="power_in", left=95, top=12, value=1.0,
            width=65, height=24, min_value=-110, max_value=30, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="dBm", variable_name="laser_power_unit", left=185, top=12,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Step Size", variable_name="step_size_lb", left=0, top=44,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.step_size = StyledSpinBox(
            container=laser_sweep_container, variable_name="step_size_in", left=95, top=44, value=0.001,
            width=65, height=24, min_value=0, max_value=1000, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="step_size_unit", left=185, top=44,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Start Wvl", variable_name="start_wvl_lb", left=0, top=76,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.start_wvl = StyledSpinBox(
            container=laser_sweep_container, variable_name="start_wvl_in", left=95, top=76, value=1500.0,
            width=65, height=24, min_value=1456, max_value=1583, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="start_wvl_unit", left=185, top=76,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="Stop Wvl", variable_name="stop_wvl_lb", left=0, top=108,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.stop_wvl = StyledSpinBox(
            container=laser_sweep_container, variable_name="stop_wvl_in", left=95, top=108, value=1580.0,
            width=65, height=24, min_value=1456, max_value=1583, step=0.1, position="absolute"
        )

        StyledLabel(
            container=laser_sweep_container, text="nm", variable_name="stop_wvl_unit", left=185, top=108,
            width=55, height=25, font_size=100, flex=True, justify_content="left", color="#222"
        )

        StyledLabel(
            container=laser_sweep_container, text="When Done", variable_name="when_done_lb", left=0, top=140,
            width=85, height=25, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.on_off = StyledDropDown(
            container=laser_sweep_container, variable_name="when_done_dd", text=["Laser On", "Laser Off"],
            left=95, top=140, width=110, height=24, position="absolute"
        )

        self.confirm_btn = StyledButton(
            container=laser_sweep_container, text="Confirm", variable_name="confirm_btn",
            left=88, top=180, height=25, width=70, font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.laser_sweep_container = laser_sweep_container
        return laser_sweep_container

    # ------------------------------------------------------------------
    # Save to shared_memory.json (Sweep block)
    # ------------------------------------------------------------------
    def onclick_confirm(self):
        # Use cached sweep values for fields we don't edit directly
        mem = {
            "wvl": self.sweep.get("wvl", 1550),
            "power": float(self.power.get_value()),
            "step": float(self.step_size.get_value()),
            "start": float(self.start_wvl.get_value()),
            "end": float(self.stop_wvl.get_value()),
            "done": self.on_off.get_value(),                  # "Laser On" or "Laser Off"
            "sweep": self.sweep.get("sweep", 0),              # keep sweep status
            "on": self.sweep.get("on", 1)                     # keep on/off status
        }
        file = File("shared_memory", "Sweep", mem)
        file.save()

        print("Confirm Sweep Setting")

        import webview
        # Set to a hidden window
        local_ip = "127.0.0.1"
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7101",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )

    # ------------------------------------------------------------------
    # Command JSON integration
    # ------------------------------------------------------------------
    def execute_command(self, path=command_path):
        sweep = 0
        record = 0
        new_command = {}

        try:
            data = read_command_file()
            command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key.startswith("sweep_set") and record == 0:
                sweep = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            # Direct control commands → UI
            elif key == "sweep_power":
                self.power.set_value(val)
            elif key == "sweep_step_size":
                self.step_size.set_value(val)
            elif key == "sweep_start_wvl":
                self.start_wvl.set_value(val)
            elif key == "sweep_stop_wvl":
                self.stop_wvl.set_value(val)
            elif key == "sweep_done":
                if str(val).lower() == "on":
                    self.on_off.set_value("Laser On")
                elif str(val).lower() == "off":
                    self.on_off.set_value("Laser Off")
            elif key == "sweep_confirm":
                self.onclick_confirm()

        if sweep == 1:
            print("sweep record")
            file = File("command", "command", new_command)
            file.save()


if __name__ == "__main__":
    configuration = {
        "config_project_name": "add_btn",
        "config_address": "0.0.0.0",
        "config_port": 7101,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(
        add_btn,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"]
    )
