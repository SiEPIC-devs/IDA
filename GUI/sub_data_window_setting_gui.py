from GUI.lib_gui import *
from remi import start, App
import json
import os
import threading

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


def update_detector_window_setting(mf, slot, setting_type, value):
    try:
        # Load existing detector window settings (thread-safe)
        data = SharedMemory.read({})

        # Get existing DetectorWindowSettings or initialize
        dws = data.get("DetectorWindowSettings", {})

        mf_key = f"mf{mf}"
        dws.setdefault(mf_key, {})
        dws[mf_key].setdefault(str(slot), {})

        # Update the specific setting
        dws[mf_key][str(slot)][setting_type] = value
        dws["Detector_Change"] = "1"

        # Use the File class like other modules for consistency
        file = File("shared_memory", "DetectorWindowSettings", dws)
        file.save()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


class data_window(App):
    def __init__(self, *args, **kwargs):
        try:
            self._cmd_mtime = None
            self._shared_mtime = None
            self._first_command_check = True
            self._first_shared_check = True

            if "editing_mode" not in kwargs:
                super(data_window, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def idle(self):
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

        # Only track mtime; do NOT reload user-editable fields.
        # Fields are loaded once in main() and after onclick_confirm().
        shared_mtime = get_shared_memory_mtime()

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        elif shared_mtime != self._shared_mtime:
            self._shared_mtime = shared_mtime

    def main(self):
        try:
            self.container = self.construct_ui()
            self._load_from_shared()
            return self.container
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def run_in_thread(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _set_spin(self, widget, value):
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            pass

    def _load_from_shared(self):
        data = SharedMemory.read({})
        if not data:
            return

        dws = data.get("DetectorWindowSettings", {})
        for mf in (0, 1):
            mf_data = dws.get(f"mf{mf}", {})
            for slot in range(1, 5):
                slot_data = mf_data.get(str(slot), {})
                self._set_spin(getattr(self, f"mf{mf}_ch{slot}_range", None),
                               slot_data.get("range", -10))
                self._set_spin(getattr(self, f"mf{mf}_ch{slot}_ref", None),
                               slot_data.get("ref", -30))

    def construct_ui(self):
        try:
            c = StyledContainer(
                variable_name="data_window_container",
                left=0,
                top=0,
                width=280,
                height=800
            )

            self._build_mainframe(c, mf=0, top_offset=5, header_color="#E8F4FD")
            self._build_mainframe(c, mf=1, top_offset=395, header_color="#FFF3E0")

            return c
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    def _build_mainframe(self, container, mf, top_offset, header_color):
        header = StyledLabel(
            text=f"MAINFRAME {mf}",
            variable_name=f"mf{mf}_header",
            left=10,
            top=top_offset,
            width=260,
            height=25,
            font_size=120,
            flex=True,
            justify_content="center",
            bold=True,
            container=container
        )
        header.style["background-color"] = header_color
        header.style["color"] = "#000"

        base = top_offset + 25
        for slot in range(1, 5):
            y = base + (slot - 1) * 90

            StyledLabel(
                text=f"Slot {slot}",
                variable_name=f"mf{mf}_slot{slot}_label",
                left=10,
                top=y,
                width=100,
                height=25,
                font_size=110,
                bold=True,
                container=container
            )

            StyledLabel(
                text="Range",
                variable_name=f"mf{mf}_slot{slot}_range_lb",
                left=10,
                top=y + 25,
                width=60,
                height=25,
                container=container
            )

            setattr(self, f"mf{mf}_ch{slot}_range", StyledSpinBox(
                container=container,
                variable_name=f"mf{mf}_ch{slot}_range",
                left=80,
                top=y + 25,
                width=60,
                height=24,
                value=-10,
                min_value=-70,
                max_value=10
            ))

            StyledLabel(
                text="Ref",
                variable_name=f"mf{mf}_slot{slot}_ref_lb",
                left=10,
                top=y + 50,
                width=60,
                height=25,
                container=container
            )

            setattr(self, f"mf{mf}_ch{slot}_ref", StyledSpinBox(
                container=container,
                variable_name=f"mf{mf}_ch{slot}_ref",
                left=80,
                top=y + 50,
                width=60,
                height=24,
                value=-30,
                min_value=-100,
                max_value=0
            ))

            btn_range = StyledButton(
                text="Range",
                variable_name=f"mf{mf}_apply_range_{slot}",
                left=190,
                top=y + 25,
                width=60,
                height=24,
                container=container
            )

            btn_ref = StyledButton(
                text="Ref",
                variable_name=f"mf{mf}_apply_ref_{slot}",
                left=190,
                top=y + 50,
                width=60,
                height=24,
                container=container
            )

            btn_auto = StyledButton(
                text="Auto",
                variable_name=f"mf{mf}_apply_auto_{slot}",
                left=190,
                top=y + 75,
                width=60,
                height=20,
                normal_color="#28A745",
                press_color="#1E7E34",
                container=container
            )

            btn_auto.do_onclick(lambda s=slot, m=mf: self.run_in_thread(self._apply_auto, m, s))
            btn_range.do_onclick(lambda s=slot, m=mf: self.run_in_thread(self._apply_range, m, s))
            btn_ref.do_onclick(lambda s=slot, m=mf: self.run_in_thread(self._apply_ref, m, s))

    def _apply_auto(self, mf, slot):
        update_detector_window_setting(mf, slot, "auto_range", True)
        update_detector_window_setting(mf, slot, "range", None)

    def _apply_range(self, mf, slot):
        val = float(getattr(self, f"mf{mf}_ch{slot}_range").get_value())
        update_detector_window_setting(mf, slot, "range", val)
        update_detector_window_setting(mf, slot, "auto_range", False)

    def _apply_ref(self, mf, slot):
        val = float(getattr(self, f"mf{mf}_ch{slot}_ref").get_value())
        update_detector_window_setting(mf, slot, "ref", val)

    def execute_command(self, path=command_path):
        try:
            data = read_command_file()
        except Exception:
            return

        command = data.get("command", {})
        new_command = {}
        record = False
        hit = False

        for k, v in command.items():
            if k.startswith("data_window") and not record:
                hit = True
            elif k.startswith(("stage_control", "tec_control", "sensor_control",
                                "as_set", "lim_set", "fa_set", "sweep_set",
                                "devices_control", "testing_control")):
                record = True
                new_command[k] = v

        if hit:
            File("command", "command", new_command).save()


if __name__ == "__main__":
    try:
        start(
            data_window,
            address="0.0.0.0",
            port=7006,
            multiple_instance=False,
            enable_file_cache=False,
            start_browser=False
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
