from lab_gui import *
from remi import start, App
import os

DEFAULT_DIR = ".\\UserData"
shared_path = os.path.join("database", "shared_memory.json")

class add_btn(App):
    def __init__(self, *args, **kwargs):
        self._user_stime = None
        self.user = None
        if "editing_mode" not in kwargs:
            super(add_btn, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            stime = None

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user = data.get("User_add", "")
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

            self.user_input.set_value(self.user)

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        add_btn_container = StyledContainer(
            variable_name="add_btn_container", left=0, top=0, height=130, width=190
        )

        StyledLabel(
            container=add_btn_container, text="User", variable_name="user",
            left=5, top=0, width=50, height=50, font_size=100, color="#222", flex=True, justify_content="right"
        )

        self.user_input = StyledTextInput(
            container=add_btn_container, variable_name="user_input", left=65, top=12.5, height=25, width=90
        )

        StyledLabel(
            container=add_btn_container, text="Project", variable_name="project",
            left=5, top=35, width=50, height=50, font_size=100, color="#222", flex=True, justify_content="right"
        )

        self.project_input = StyledTextInput(
            container=add_btn_container, variable_name="project_input", left=65, top=47.5, height=25, width=90
        )

        self.add = StyledButton(
            container=add_btn_container, text="Add", variable_name="add",
            left=70, top=85, height=25, width=50, normal_color="#007BFF", press_color="#0056B3"
        )

        self.add.do_onclick(self.onclick_add)

        self.add_btn_container = add_btn_container
        return add_btn_container

    def onclick_add(self):
        user_name = self.user_input.get_value().strip()
        project_name = self.project_input.get_value().strip()
        file = File("shared_memory", "User_add", user_name)
        file.save()
        if not user_name:
            print("Please enter a valid user name.")  # Empty input
            return
        elif not project_name:
            print("Please enter a valid project name.")
            return
        target_path = os.path.join(DEFAULT_DIR, user_name, project_name)

        try:
            os.makedirs(DEFAULT_DIR, exist_ok=True)  # Ensure root exists
            os.makedirs(target_path, exist_ok=False)  # Create sub-folder
            os.makedirs(os.path.join(target_path, "Spectrum"), exist_ok=True)
            os.makedirs(os.path.join(target_path, "HeatMap"), exist_ok=True)
            print(f"Folder created: {target_path}")
        except FileExistsError:
            print(f"Folder already exists: {target_path}")
        except Exception as e:
            print(f"Failed to create folder: {e}")

if __name__ == "__main__":
    configuration = {
        "config_project_name": "add_btn",
        "config_address": "0.0.0.0",
        "config_port": 7000,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(add_btn,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
