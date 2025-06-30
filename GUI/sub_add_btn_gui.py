from lab_gui import *
from remi import start, App
import os
DEFAULT_DIR = ".\\UserData"
class add_btn(App):
    def __init__(self, *args, **kwargs):
        if "editing_mode" not in kwargs:
            super(add_btn, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        add_btn_container = StyledContainer(variable_name="add_btn_container", left=0, top=0, height=50, width=225)
        StyledLabel(container=add_btn_container, text="Name", variable_name="name",
                                 left=0, top=0, width=50, height=50, font_size=100, color="#222", flex=True, justify_content="right")
        self.name_input = StyledTextInput(container=add_btn_container, variable_name="name_input", left=60, top=12.5, height=25, width=70)
        self.add = StyledButton(container=add_btn_container, text="Add", variable_name="add",
                            left=160, top=12.5, height=25, width=50, normal_color="#007BFF", press_color="#0056B3")
        self.add.do_onclick(self.onclick_add)

        self.add_btn_container = add_btn_container
        return add_btn_container

    def onclick_add(self):
        folder_name = self.name_input.get_value().strip()
        if not folder_name:
            print("⚠️  Please enter a valid name.")  # Empty input
            return
        target_path = os.path.join(DEFAULT_DIR, folder_name)
        try:
            os.makedirs(DEFAULT_DIR, exist_ok=True)  # Ensure root exists
            os.makedirs(target_path, exist_ok=False)  # Create sub-folder
            print(f"✅ Folder created: {target_path}")
        except FileExistsError:
            print(f"⚠️  Folder already exists: {target_path}")
        except Exception as e:
            print(f"❌ Failed to create folder: {e}")

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
