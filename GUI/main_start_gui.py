"""
Remi GUI — User/Mode selector with dynamic dropdown + JSON sync
--------------------------------------------------------------
* Keeps user list in ROOT_DIR
* Writes currently selected user to JSON_PATH whenever it changes
* No functional change versus the original script — only formatting / layout tidy-up
"""

import json, os, shutil, threading, webview
from typing import List, Union
from remi import App, start
from lab_gui import *

# ──────────────────────────────────────────
ROOT_DIR = "./UserData"
JSON_PATH = "database/shared_memory.json"


class Starts(App):
    """Main application class (unchanged behaviour, cleaner layout)."""

    # ──────────────────────────────── INIT & REMI HOOKS

    def __init__(self, *args, **kwargs):
        # runtime flags
        self._last_saved_user: str = ""
        self._last_saved_project: str = ""
        self._last_user: Union[str, List[str]] = ""
        self._last_project: Union[str, List[str]] = ""
        if "editing_mode" not in kwargs:
            super().__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self) -> None:
        """Refresh terminal & sync dropdown/JSON when things change."""
        self.terminal.terminal_refresh()

        now_user = tuple(self.list_user_folders())
        if getattr(self, "_last_user", None) != now_user:
            self.refresh_user()
            self.refresh_project()
            self._last_user = now_user

        now_project = tuple(self.list_project_folders())
        if getattr(self, "_last_project", None) != now_project:
            self.refresh_project()
            self._last_project = now_project

        current_user = self.user_dd.get_value()
        current_project = self.project_dd.get_value()
        if current_user != self._last_saved_user:
            file = File("shared_memory", "User", current_user)
            file.save()
            self._last_saved_user = current_user
            self.refresh_project()
        if current_project != self._last_saved_project:
            file = File("shared_memory", "Project", current_project)
            file.save()
            self._last_saved_project = current_project

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def list_user_folders(self) -> Union[str, List[str]]:
        """Return sub-folders of ROOT_DIR (same logic as original)."""
        names = [
            d for d in os.listdir(ROOT_DIR)
            if os.path.isdir(os.path.join(ROOT_DIR, d))
        ]
        if not names:
            return ""
        if "Guest" in names:
            names.remove("Guest")
            names = ["Guest"] + sorted(names)
        else:
            names = sorted(names)
        if len(names) == 1:
            return names[0]
        return names

    def list_project_folders(self) -> Union[str, List[str]]:
        """Return sub-folders of ROOT_DIR (same logic as original)."""
        path = os.path.join(ROOT_DIR, self.user_dd.get_value())
        names = [
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d))
        ]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        return names

    def construct_ui(self):
        """Build and return the root container."""
        starts_container = StyledContainer(
            variable_name="starts_container", left=0, top=0
        )

        user_folders = self.list_user_folders()
        self.user_dd = StyledDropDown(
            container=starts_container, text=user_folders, variable_name="set_user",
            left=210, top=100, width=220, height=30,
        )

        self.project_dd = StyledDropDown(
            container=starts_container, text="Project1", variable_name="set_mode",
            left=210, top=140, width=220, height=30,
        )

        StyledLabel(
            container=starts_container, text="User", variable_name="label_user",
            left=50, top=105, width=150, height=20, font_size=100, color="#444", align="right",
        )
        StyledLabel(
            container=starts_container, text="Project", variable_name="label_mode",
            left=50, top=145, width=150, height=20, font_size=100, color="#444", align="right",
        )

        StyledLabel(
            container=starts_container, text="Welcome to 347 Probe Stage", variable_name="label_configuration",
            left=180, top=20, width=300, height=20, font_size=150, color="#222", align="left",
        )

        self.add_btn = StyledButton(
            container=starts_container, text="Add", variable_name="add",
            left=270, top=180, normal_color="#007BFF", press_color="#0056B3",
        )

        self.user_btn = StyledButton(
            container=starts_container, text="Remove", variable_name="user_remove",
            left=440, top=100, width=60, height=30, normal_color="#dc3545", press_color="#c82333",
        )

        self.project_btn = StyledButton(
            container=starts_container, text="Remove", variable_name="project_remove",
            left=440, top=140, width=60, height=30, normal_color="#dc3545", press_color="#c82333",
        )

        terminal_container = StyledContainer(
            container=starts_container, variable_name="terminal_container",
            left=0, top=500, height=150, width=650, bg_color=True,
        )

        self.terminal = Terminal(
            container=terminal_container, variable_name="terminal_text",
            left=10, top=15, width=610, height=100,
        )

        # ── event bindings
        self.add_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_add))
        self.user_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_user_remove))
        self.project_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_project_remove))

        self.starts_container = starts_container
        return starts_container

    def onclick_add(self):
        file = File("shared_memory", "User_add", self.user_dd.get_value())
        file.save()
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7000",
            width=212,
            height=185,
            resizable=True,
            on_top=True
        )

    def onclick_user_remove(self):
        folder = self.user_dd.get_value().replace(" ", "")
        path = os.path.join(ROOT_DIR, folder)
        if not os.path.isdir(path):
            print(f"⚠️ No such folder: {folder}")
            return
        try:
            shutil.rmtree(path)
            print(f"🗑️ Removed {folder}")
        except Exception as exc:
            print(f"❌ Failed to remove: {exc}")

    def onclick_project_remove(self):
        user = self.user_dd.get_value().replace(" ", "")
        project = self.project_dd.get_value().replace(" ", "")
        path = os.path.join(ROOT_DIR, user, project)
        if not os.path.isdir(path):
            print(f"⚠️ No such project: {project}")
            return
        try:
            shutil.rmtree(path)
            print(f"🗑️ Removed {project}")
        except Exception as exc:
            print(f"❌ Failed to remove: {exc}")

    def refresh_user(self):
        self.user_dd.empty()
        self.user_dd.append(self.list_user_folders())

    def refresh_project(self):
        self.project_dd.empty()
        self.project_dd.append(self.list_project_folders())

def run_remi():
    start(
        Starts,
        address="0.0.0.0",
        port=9000,
        start_browser=False,
        multiple_instance=False,
        enable_file_cache=False,
    )

def get_local_ip():
    """Automatically detect local LAN IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Fake connect to get route IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # fallback

if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    local_ip = get_local_ip()
    webview.create_window(
        "Main Window",
        f"http://{local_ip}:9000",
        width=0,
        height=0,
        resizable=True,
        hidden=True,
    )
    webview.start()
