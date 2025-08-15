from remi import start, App
import os, lab_coordinates, threading, glob
from lab_gui import *

class registration(App):
    def __init__(self, *args, **kwargs):
        self.first_mark_set = 0
        self.second_mark_set = 0
        self.third_mark_set = 0
        self.number_1 = 1
        self.number_2 = 1
        self.number_3 = 1
        self.first_mark_position = [-100,-100,0]
        self.second_mark_position = [100, -100,0]
        self.third_mark_position = [100, 100,0]
        self.memory = Memory()

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

        """StyledLabel(container=file_container, text="Stage:", variable_name="label_stage",
                    left=130, top=13, width=150, height=20, font_size=100, color="#444", align="right")
        StyledDropDown(container=file_container, text=["Fiber Stage", "Chip Stage"], variable_name="choose_stage",
                       left=290, top=8, width=220, height=30)
        StyledButton(container=file_container, text="Setting", variable_name="setting",
                     left=515, top=8, font_size=90, normal_color="#007BFF", press_color="#0056B3")"""

        # ---------------- Coordinate Table Section ----------------
        coordinate_container = StyledContainer(
            container=registration_container, variable_name="coordinate_container",
            left=10, top=80, height=188, width=625, border=True
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

        # ---------------- Terminal Display ----------------
        terminal_container = StyledContainer(
            container=registration_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text", left=10, top=15, width=610, height=100
        )

        # ---------------- Event Bindings ----------------
        self.uploader.ondata.do(lambda emitter, filedata, filename: self.run_in_thread(self.ondata_uploader, emitter, filedata, filename))
        self.device_id_1.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_device_1, emitter, value))
        self.device_id_2.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_device_2, emitter, value))
        self.device_id_3.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_device_3, emitter, value))
        self.checkbox_1.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_checkbox_1, emitter, value))
        self.checkbox_2.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_checkbox_2, emitter, value))
        self.checkbox_3.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_checkbox_3, emitter, value))
        self.reset_button.do_onclick(lambda *_: self.run_in_thread(self.onclick_reset))
        self.transform_button.do_onclick(lambda *_: self.run_in_thread(self.onclick_transform))

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

        self.gds = lab_coordinates.coordinates(("./res/coordinates/" + filename), read_file=True,name="./database/coordinates.json")
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        self.devices = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]

        self.device_id_1.empty()
        self.device_id_2.empty()
        self.device_id_3.empty()
        self.device_id_1.append(self.devices)
        self.device_id_2.append(self.devices)
        self.device_id_3.append(self.devices)
        self.device_id_1.attributes["title"] = self.devices[0]
        self.device_id_2.attributes["title"] = self.devices[0]
        self.device_id_3.attributes["title"] = self.devices[0]
        self.gds_x_1.set_text(str(self.coordinate[0][0]))
        self.gds_y_1.set_text(str(self.coordinate[0][1]))
        self.gds_x_2.set_text(str(self.coordinate[0][0]))
        self.gds_y_2.set_text(str(self.coordinate[0][1]))
        self.gds_x_3.set_text(str(self.coordinate[0][0]))
        self.gds_y_3.set_text(str(self.coordinate[0][1]))

    def onchange_device_1(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_1 = int(number_str)
        x = self.coordinate[self.number_1-1][0]
        y = self.coordinate[self.number_1-1][1]
        self.gds_x_1.set_text(str(x))
        self.gds_y_1.set_text(str(y))
        self.device_id_1.attributes["title"] = new_value

    def onchange_device_2(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_2 = int(number_str)
        x = self.coordinate[self.number_2-1][0]
        y = self.coordinate[self.number_2-1][1]
        self.gds_x_2.set_text(str(x))
        self.gds_y_2.set_text(str(y))
        self.device_id_2.attributes["title"] = new_value

    def onchange_device_3(self, emitter, new_value):
        number_str = new_value.split("(")[-1].split(")")[0]
        self.number_3 = int(number_str)
        x = self.coordinate[self.number_3-1][0]
        y = self.coordinate[self.number_3-1][1]
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

    def onclick_reset(self):
        self.checkbox_1.set_value(False)
        self.checkbox_2.set_value(False)
        self.checkbox_3.set_value(False)

        self.onchange_checkbox_1(1,0)
        self.onchange_checkbox_2(1, 0)
        self.onchange_checkbox_3(1, 0)

    def onclick_transform(self):
        if self.first_mark_set == 1 and self.second_mark_set == 1 and self.third_mark_set == 1:
            return_value = self.gds.apply_transform([self.number_1, self.number_2, self.number_3],
                                                    self.first_mark_position, self.second_mark_position, self.third_mark_position)
            print(return_value)

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
        "config_port": 9002,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(registration,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
