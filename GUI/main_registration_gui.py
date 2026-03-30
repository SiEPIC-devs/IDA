from remi import start, App
import os, json, lib_coordinates, threading, glob
from GUI.lib_gui import *

class registration(App):
    def __init__(self, *args, **kwargs):
        self.first_mark_set = 0
        self.second_mark_set = 0
        self.third_mark_set = 0
        self.number_1 = 1
        self.number_2 = 1
        self.number_3 = 1
        self.first_mark_position = [-100, -100, 0]
        self.second_mark_position = [100, -100, 0]
        self.third_mark_position = [100, 100, 0]
        self.memory = Memory()
        self.pad_device_number = 1
        self.pad_pad_number = 1
        self.transformed = False

        if "editing_mode" not in kwargs:
            super(registration, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        self.terminal.terminal_refresh()

    def main(self):
        return self.construct_ui()

    # Utility method to run any target in a background thread
    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    # ------- helper to notify devices UI to reload -------
    def send_devices_load_command(self):
        """
        Write a 'devices_load' command into command.json.

        The devices app watches this file and will call its
        onclick_load() when it sees 'devices_load'.
        """
        cmd = {"devices_load": 1}
        file = File("command", "command", cmd)
        file.save()

    def construct_ui(self):
        registration_container = StyledContainer(
            container=None, variable_name="registration_container", left=0, top=0
        )

        # ---------------- File Upload Section ----------------
        file_container = StyledContainer(
            container=registration_container, variable_name="file_container",
            left=10, top=10, height=45, width=265, border=True
        )

        self.uploader = StyledFileUploader(
            container=file_container, variable_name="uploader", savepath="./res/coordinates/",
            left=10, top=10, width=220, height=30
        )

        # ---------------- Coordinate Table Section ----------------
        coordinate_container = StyledContainer(
            container=registration_container, variable_name="coordinate_container",
            left=10, top=80, height=187, width=625, border=True
        )

        StyledLabel(
            container=coordinate_container, text="Coordinate System Parameters", variable_name=f"dev_sel_lb",
            left=360, top=-12, width=235, height=20, font_size=120, color="#222", position="absolute",
            flex=True, on_line=True
        )

        self.reset_button = StyledButton(
            container=coordinate_container, text="Reset", variable_name="reset",
            left=10, top=10, font_size=90, normal_color="#007BFF", press_color="#0056B3"
        )

        self.transform_button = StyledButton(
            container=coordinate_container, text="Transform", variable_name="transform",
            left=120, top=10, font_size=90, normal_color="#007BFF", press_color="#0056B3"
        )

        headers = ["Device ID", "GDS x", "GDS y", "Stage x", "Stage y", "Set"]
        widths = [150, 80, 80, 80, 80, 40]

        StyledTable(
            container=coordinate_container, variable_name="device_table",
            left=0, top=50, height=30, table_width=625, headers=headers, widths=widths, row=4
        )

        # Initialize each row of the coordinate table with UI elements
        for row_index in range(1, 4):
            table = registration_container.children["coordinate_container"].children["device_table"]
            row = list(table.children.values())[row_index]
            cell0, cell1, cell2, cell3, cell4, cell5 = [list(row.children.values())[i] for i in range(6)]
            cell5.style["text-align"] = "center"

            setattr(self, f"device_id_{row_index}", StyledDropDown(
                container=None, text="N/A", variable_name=f"device_id_{row_index}",
                bg_color="#ffffff" if row_index % 2 != 0 else "#f6f7f9",
                border="0px", border_radius="0px", left=0, top=0,
                width=100, height=100, position="inherit", percent=True))

            setattr(self, f"gds_x_{row_index}", StyledLabel(
                container=None, text="N/A", variable_name=f"gds_x_{row_index}", left=0, top=0,
                width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
                percent=True, flex=True))

            setattr(self, f"gds_y_{row_index}", StyledLabel(
                container=None, text="N/A", variable_name=f"gds_y_{row_index}", left=0, top=0,
                width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
                percent=True, flex=True))

            setattr(self, f"stage_x_{row_index}", StyledLabel(
                container=None, text="N/A", variable_name=f"stage_x_{row_index}", left=0, top=0,
                width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
                percent=True, flex=True))

            setattr(self, f"stage_y_{row_index}", StyledLabel(
                container=None, text="N/A", variable_name=f"stage_y_{row_index}", left=0, top=0,
                width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
                percent=True, flex=True))

            setattr(self, f"checkbox_{row_index}", StyledCheckBox(
                container=None, variable_name=f"checkbox_{row_index}", left=0, top=0,
                width=10, height=10, position="inherit"))

            # Append widgets to the corresponding cells
            cell0.append(getattr(self, f"device_id_{row_index}"))
            cell1.append(getattr(self, f"gds_x_{row_index}"))
            cell2.append(getattr(self, f"gds_y_{row_index}"))
            cell3.append(getattr(self, f"stage_x_{row_index}"))
            cell4.append(getattr(self, f"stage_y_{row_index}"))
            cell5.append(getattr(self, f"checkbox_{row_index}"))

        # ---------------- Pad Coordinate Section ----------------
        pad_container = StyledContainer(
            container=registration_container, variable_name="pad_container",
            left=10, top=293, height=118, width=625, border=True
        )

        StyledLabel(
            container=pad_container, text="Pad Coordinate", variable_name="pad_coord_lb",
            left=475, top=-12, width=120, height=20, font_size=120, color="#222", position="absolute",
            flex=True, on_line=True
        )

        self.set_as_ref_button = StyledButton(
            container=pad_container, text="Set as Ref", variable_name="set_as_ref",
            left=10, top=10, font_size=90, normal_color="#007BFF", press_color="#0056B3"
        )

        pad_headers = ["Device ID", "Pad ID", "Relative X", "Relative Y"]
        pad_widths = [150, 150, 105, 105]

        StyledTable(
            container=pad_container, variable_name="pad_table",
            left=0, top=50, height=30, table_width=625, headers=pad_headers, widths=pad_widths, row=2
        )

        pad_table = registration_container.children["pad_container"].children["pad_table"]
        pad_row = list(pad_table.children.values())[1]
        pad_cell0, pad_cell1, pad_cell2, pad_cell3 = [list(pad_row.children.values())[i] for i in range(4)]

        self.pad_device_id = StyledDropDown(
            container=None, text="N/A", variable_name="pad_device_id",
            bg_color="#ffffff", border="0px", border_radius="0px", left=0, top=0,
            width=100, height=100, position="inherit", percent=True)

        self.pad_pad_id = StyledDropDown(
            container=None, text="N/A", variable_name="pad_pad_id",
            bg_color="#ffffff", border="0px", border_radius="0px", left=0, top=0,
            width=100, height=100, position="inherit", percent=True)

        self.pad_relative_x = StyledLabel(
            container=None, text="N/A", variable_name="pad_relative_x", left=0, top=0,
            width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
            percent=True, flex=True)

        self.pad_relative_y = StyledLabel(
            container=None, text="N/A", variable_name="pad_relative_y", left=0, top=0,
            width=100, height=100, font_size=100, color="#222", align="right", position="inherit",
            percent=True, flex=True)

        pad_cell0.append(self.pad_device_id)
        pad_cell1.append(self.pad_pad_id)
        pad_cell2.append(self.pad_relative_x)
        pad_cell3.append(self.pad_relative_y)

        # ---------------- Terminal Display ----------------
        terminal_container = StyledContainer(
            container=registration_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text", left=10, top=15, width=610, height=100
        )

        # ---------------- Event Bindings ----------------
        self.uploader.ondata.do(
            lambda emitter, filedata, filename: self.run_in_thread(self.ondata_uploader, emitter, filedata, filename)
        )
        self.device_id_1.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_device_1, emitter, value)
        )
        self.device_id_2.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_device_2, emitter, value)
        )
        self.device_id_3.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_device_3, emitter, value)
        )
        self.checkbox_1.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_checkbox_1, emitter, value)
        )
        self.checkbox_2.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_checkbox_2, emitter, value)
        )
        self.checkbox_3.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_checkbox_3, emitter, value)
        )
        self.reset_button.do_onclick(lambda *_: self.run_in_thread(self.onclick_reset))
        self.transform_button.do_onclick(lambda *_: self.run_in_thread(self.onclick_transform))
        self.pad_device_id.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_pad_device, emitter, value)
        )
        self.pad_pad_id.onchange.do(
            lambda emitter, value: self.run_in_thread(self.onchange_pad_pad, emitter, value)
        )
        self.set_as_ref_button.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_as_ref))

        self.registration_container = registration_container
        return registration_container

    def ondata_uploader(self, emitter, filedata: bytes, filename: str):
        cleanupFiles = glob.glob("./res/coordinates/*")
        target = os.path.join(".", "res", "coordinates", filename)
        if target in cleanupFiles:
            cleanupFiles.remove(target)

        print("./res/coordinates" + filename)
        try:
            os.remove("./database/coordinates.json")
        except:
            pass

        self.gds = lib_coordinates.coordinates(
            ("./res/coordinates/" + filename),
            read_file=True,
            name="./database/coordinates.json"
        )
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.original_coordinate = [coord[:] for coord in self.coordinate]
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        devicenames = self.gds.listdeviceparam("devicename")
        self.devices = [f"{name} ({num})" for name, num in zip(devicenames, self.number)]

        # Build filtered lists by type
        PAD_TYPES = {"pad", "pada", "padb", "padab"}
        self.non_pad_devices = []
        self.pad_only_devices = []
        for i, t in enumerate(self.type):
            label = self.devices[i]
            if t.lower() in PAD_TYPES:
                self.pad_only_devices.append(label)
            else:
                self.non_pad_devices.append(label)

        # Populate coordinate table dropdowns with non-pad devices
        self.device_id_1.empty()
        self.device_id_2.empty()
        self.device_id_3.empty()
        self.device_id_1.append(self.non_pad_devices)
        self.device_id_2.append(self.non_pad_devices)
        self.device_id_3.append(self.non_pad_devices)
        self.device_id_1.attributes["title"] = self.non_pad_devices[0]
        self.device_id_2.attributes["title"] = self.non_pad_devices[0]
        self.device_id_3.attributes["title"] = self.non_pad_devices[0]
        first_non_pad_num = int(self.non_pad_devices[0].split("(")[-1].split(")")[0])
        self.number_1 = first_non_pad_num
        self.number_2 = first_non_pad_num
        self.number_3 = first_non_pad_num
        self.gds_x_1.set_text(str(self.coordinate[first_non_pad_num - 1][0]))
        self.gds_y_1.set_text(str(self.coordinate[first_non_pad_num - 1][1]))
        self.gds_x_2.set_text(str(self.coordinate[first_non_pad_num - 1][0]))
        self.gds_y_2.set_text(str(self.coordinate[first_non_pad_num - 1][1]))
        self.gds_x_3.set_text(str(self.coordinate[first_non_pad_num - 1][0]))
        self.gds_y_3.set_text(str(self.coordinate[first_non_pad_num - 1][1]))

        # Populate pad coordinate dropdowns
        self.pad_device_id.empty()
        self.pad_pad_id.empty()
        self.pad_device_id.append(self.non_pad_devices)
        self.pad_pad_id.append(self.pad_only_devices)
        self.pad_device_id.attributes["title"] = self.non_pad_devices[0]
        self.pad_pad_id.attributes["title"] = self.pad_only_devices[0]
        self.pad_device_number = first_non_pad_num
        first_pad_num = int(self.pad_only_devices[0].split("(")[-1].split(")")[0])
        self.pad_pad_number = first_pad_num
        self.update_pad_relative()

        # ----- condition 1: file upload triggers devices reload -----
        self.send_devices_load_command()

    def onchange_device_1(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_1 = int(number_str)
        x = self.original_coordinate[self.number_1 - 1][0]
        y = self.original_coordinate[self.number_1 - 1][1]
        self.gds_x_1.set_text(str(x))
        self.gds_y_1.set_text(str(y))
        self.device_id_1.attributes["title"] = new_value

    def onchange_device_2(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_2 = int(number_str)
        x = self.original_coordinate[self.number_2 - 1][0]
        y = self.original_coordinate[self.number_2 - 1][1]
        self.gds_x_2.set_text(str(x))
        self.gds_y_2.set_text(str(y))
        self.device_id_2.attributes["title"] = new_value

    def onchange_device_3(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_3 = int(number_str)
        x = self.original_coordinate[self.number_3 - 1][0]
        y = self.original_coordinate[self.number_3 - 1][1]
        self.gds_x_3.set_text(str(x))
        self.gds_y_3.set_text(str(y))
        self.device_id_3.attributes["title"] = new_value

    def onchange_checkbox_1(self, emitter, value):
        self.memory.reader_pos()
        self.first_mark_position[0] = self.memory.x_pos
        self.first_mark_position[1] = self.memory.y_pos
        if int(value) == 1:
            self.first_mark_set = 1
            self.stage_x_1.set_text(str(self.first_mark_position[0]))
            self.stage_y_1.set_text(str(self.first_mark_position[1]))
        else:
            self.first_mark_set = 0
            self.stage_x_1.set_text("N/A")
            self.stage_y_1.set_text("N/A")

    def onchange_checkbox_2(self, emitter, value):
        self.memory.reader_pos()
        self.second_mark_position[0] = self.memory.x_pos
        self.second_mark_position[1] = self.memory.y_pos
        if int(value) == 1:
            self.second_mark_set = 1
            self.stage_x_2.set_text(str(self.second_mark_position[0]))
            self.stage_y_2.set_text(str(self.second_mark_position[1]))
        else:
            self.second_mark_set = 0
            self.stage_x_2.set_text("N/A")
            self.stage_y_2.set_text("N/A")

    def onchange_checkbox_3(self, emitter, value):
        self.memory.reader_pos()
        self.third_mark_position[0] = self.memory.x_pos
        self.third_mark_position[1] = self.memory.y_pos
        if int(value) == 1:
            self.third_mark_set = 1
            self.stage_x_3.set_text(str(self.third_mark_position[0]))
            self.stage_y_3.set_text(str(self.third_mark_position[1]))
        else:
            self.third_mark_set = 0
            self.stage_x_3.set_text("N/A")
            self.stage_y_3.set_text("N/A")

    def onchange_pad_device(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.pad_device_number = int(number_str)
        self.pad_device_id.attributes["title"] = new_value
        self.update_pad_relative()

    def onchange_pad_pad(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.pad_pad_number = int(number_str)
        self.pad_pad_id.attributes["title"] = new_value
        self.update_pad_relative()

    def update_pad_relative(self):
        try:
            dev_coord = self.coordinate[self.pad_device_number - 1]
            pad_coord = self.coordinate[self.pad_pad_number - 1]
            rel_x = dev_coord[0] - pad_coord[0]
            rel_y = dev_coord[1] - pad_coord[1]
            self.pad_relative_x.set_text(f"{rel_x:.2f}")
            self.pad_relative_y.set_text(f"{rel_y:.2f}")
        except Exception:
            self.pad_relative_x.set_text("N/A")
            self.pad_relative_y.set_text("N/A")

    def onclick_set_as_ref(self):
        try:
            if not self.transformed:
                print("Please transform coordinates first")
                return

            all_entries = self.gds.device_db.all()

            # Look up the selected device and pad entries
            ref_dev = None
            ref_pad = None
            for entry in all_entries:
                if entry["number"] == self.pad_device_number:
                    ref_dev = entry
                if entry["number"] == self.pad_pad_number:
                    ref_pad = entry

            if ref_dev is None or ref_pad is None:
                print("Reference device or pad not found")
                return

            # Validate: must match on devicename, polarization, wavelength
            if (ref_dev["devicename"] != ref_pad["devicename"] or
                    ref_dev["polarization"] != ref_pad["polarization"] or
                    ref_dev["wavelength"] != ref_pad["wavelength"]):
                print("Device and Pad do not match (devicename/polarization/wavelength differ)")
                return

            # Build lookups to check one-to-one mapping
            # key = (devicename, polarization, wavelength)
            PAD_TYPES = {"pad", "pada", "padb", "padab"}
            PAD_CHANNEL_MAP = {"pad": "A", "pada": "A", "padb": "B", "padab": "AB"}
            pad_by_key = {}   # key -> list of pad entries
            dev_by_key = {}   # key -> list of non-pad device entries
            for entry in all_entries:
                key = (entry["devicename"], entry["polarization"], entry["wavelength"])
                if entry["type"].lower() in PAD_TYPES:
                    pad_by_key.setdefault(key, []).append(entry)
                else:
                    dev_by_key.setdefault(key, []).append(entry)

            # Validate reference pair is one-to-one
            ref_key = (ref_dev["devicename"], ref_dev["polarization"], ref_dev["wavelength"])
            if len(dev_by_key.get(ref_key, [])) != 1 or len(pad_by_key.get(ref_key, [])) != 1:
                print("Reference device/pad key is not a one-to-one mapping. Aborted.")
                return

            # Reference offset = ref_device_coord - ref_pad_coord
            ref_dev_coord = ref_dev["coordinate"]
            ref_pad_coord = ref_pad["coordinate"]
            ref_offset = [
                ref_dev_coord[0] - ref_pad_coord[0],
                ref_dev_coord[1] - ref_pad_coord[1],
                ref_dev_coord[2] - ref_pad_coord[2] if len(ref_dev_coord) > 2 else 0
            ]

            # Build output: only one-to-one matched pairs with coordinates in valid range
            output = {"_default": {}}
            skipped_multi = 0
            skipped_range = 0
            for entry in all_entries:
                if entry["type"].lower() in PAD_TYPES:
                    continue
                key = (entry["devicename"], entry["polarization"], entry["wavelength"])
                # Skip if no matching pad
                if key not in pad_by_key:
                    continue
                # Skip if not one-to-one (multiple devices or multiple pads for this key)
                if len(dev_by_key.get(key, [])) != 1 or len(pad_by_key[key]) != 1:
                    skipped_multi += 1
                    continue
                dev_coord = entry["coordinate"]
                matched_pad_coord = pad_by_key[key][0]["coordinate"]
                raw_dx = dev_coord[0] - matched_pad_coord[0]
                raw_dy = dev_coord[1] - matched_pad_coord[1]
                # Validate range on raw device-pad difference: X must be in [150, 1000], Y must be in [-750, 750]
                if not (150 <= raw_dx <= 1000) or not (-750 <= raw_dy <= 750):
                    skipped_range += 1
                    print(f"Skipped {entry['devicename']} ({entry['number']}): dx={raw_dx:.2f}, dy={raw_dy:.2f} out of range")
                    continue
                rel_x = raw_dx - ref_offset[0]
                rel_y = raw_dy - ref_offset[1]
                rel_z = (dev_coord[2] - matched_pad_coord[2] if len(dev_coord) > 2 else 0) - ref_offset[2]
                matched_pad_type = pad_by_key[key][0]["type"].lower()
                channel = PAD_CHANNEL_MAP.get(matched_pad_type, "A")
                new_entry = {
                    "number": entry["number"],
                    "coordinate": [rel_x, rel_y, rel_z],
                    "polarization": entry["polarization"],
                    "wavelength": entry["wavelength"],
                    "type": entry["type"],
                    "devicename": entry["devicename"],
                    "channel": channel
                }
                output["_default"][str(entry["number"])] = new_entry

            output_path = "./database/coordinates_relative.json"
            with open(output_path, "w") as f:
                json.dump(output, f, indent=2)

            saved_count = len(output['_default'])
            print(f"coordinates_relative.json saved with {saved_count} devices")
            if skipped_multi > 0:
                print(f"Skipped {skipped_multi} device(s) due to non-one-to-one mapping")
            if skipped_range > 0:
                print(f"Skipped {skipped_range} device(s) due to coordinates out of range")
        except Exception as e:
            print(f"Set as Ref failed: {e}")

    def onclick_reset(self):
        self.checkbox_1.set_value(False)
        self.checkbox_2.set_value(False)
        self.checkbox_3.set_value(False)

        self.onchange_checkbox_1(1, 0)
        self.onchange_checkbox_2(1, 0)
        self.onchange_checkbox_3(1, 0)

    def onclick_transform(self):
        if self.first_mark_set == 1 and self.second_mark_set == 1 and self.third_mark_set == 1:
            return_value = self.gds.apply_transform(
                [self.number_1, self.number_2, self.number_3],
                self.first_mark_position,
                self.second_mark_position,
                self.third_mark_position
            )

            if return_value == 1:
                print("WARNING: Transform completed with large error. Consider re-checking alignment marks.")

            # Refresh coordinates from the transformed data
            self.coordinate = self.gds.listdeviceparam("coordinate")
            self.transformed = True
            self.update_pad_relative()

            # ----- condition 2: successful transform triggers devices reload -----
            self.send_devices_load_command()

        else:
            print("Not all marks have been found")
            if self.first_mark_set != 1:
                print("First mark not found!")
            if self.second_mark_set != 1:
                print("Second mark not found!")
            if self.third_mark_set != 1:
                print("Third mark not found!")


if __name__ == "__main__":
    configuration = {
        "config_project_name": "registration",
        "config_address": "0.0.0.0",
        "config_port": 9102,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(
        registration,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"]
    )
