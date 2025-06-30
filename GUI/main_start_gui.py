"""
Remi GUI — User/Mode selector with dynamic dropdown + JSON sync
--------------------------------------------------------------
* Keeps user list in ROOT_DIR
* Writes currently selected user to JSON_PATH whenever it changes
* No functional change versus the original script — only formatting / layout tidy-up
"""

import json
import os
import shutil
import threading
from typing import List, Union

import webview
from remi.gui import *
from remi import App, start

# NOTE: external helper modules (keep as-is)
from lab_gui import *

# ──────────────────────────────────────────
ROOT_DIR = ".\\UserData"
JSON_PATH = ".\\database\\current_user.json"


class Starts(App):
    """Main application class (unchanged behaviour, cleaner layout)."""

    # ──────────────────────────────── INIT & REMI HOOKS

    def __init__(self, *args, **kwargs):
        # runtime flags
        self._last_saved_user: str = ""
        if "editing_mode" not in kwargs:
            super().__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self) -> None:
        """Refresh terminal & sync dropdown/JSON when things change."""
        self.terminal.terminal_refresh()

        # 1) folder list changed → refresh dropdown
        now = tuple(self.list_user_folders())
        if getattr(self, "_last_folders", None) != now:
            self.refresh()
            self._last_folders = now

        # 2) current dropdown selection changed → write JSON
        current_user = self.user_dd.get_value()
        if current_user != self._last_saved_user:
            try:
                with open(JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump({"user": current_user}, f)
            except Exception as exc:
                print(f"❌ Failed to write JSON: {exc}")
            self._last_saved_user = current_user

    def main(self):
        return self.construct_ui()

    # ──────────────────────────────── HELPERS

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
        if len(names) == 1:
            return names[0]
        return names

    # ──────────────────────────────── UI

    def construct_ui(self):
        """Build and return the root container."""
        starts_container = StyledContainer(
            variable_name="starts_container", left=0, top=0
        )

        # ── dropdowns
        user_folders = self.list_user_folders()
        self.user_dd = StyledDropDown(
            container=starts_container,
            text=user_folders,
            variable_name="set_user",
            left=260,
            top=100,
            width=220,
            height=30,
        )
        self.mode_dd = StyledDropDown(
            container=starts_container,
            text=["TE mode", "TM mode"],
            variable_name="set_mode",
            left=260,
            top=140,
            width=220,
            height=30,
        )

        StyledLabel(
            container=starts_container,
            text="User:",
            variable_name="label_user",
            left=100,
            top=105,
            width=150,
            height=20,
            font_size=100,
            color="#444",
            align="right",
        )
        StyledLabel(
            container=starts_container,
            text="Operating Mode:",
            variable_name="label_mode",
            left=100,
            top=145,
            width=150,
            height=20,
            font_size=100,
            color="#444",
            align="right",
        )

        StyledLabel(
            container=starts_container,
            text="Welcome to 347 Probe Stage",
            variable_name="label_configuration",
            left=180,
            top=20,
            width=300,
            height=20,
            font_size=150,
            color="#222",
            align="left",
        )

        # ── buttons
        self.add_btn = StyledButton(
            container=starts_container,
            text="Add",
            variable_name="add",
            left=260,
            top=180,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        self.remove_btn = StyledButton(
            container=starts_container,
            text="Remove",
            variable_name="remove",
            left=380,
            top=180,
            normal_color="#dc3545",
            press_color="#c82333",
        )

        # ── terminal
        terminal_container = StyledContainer(
            container=starts_container,
            variable_name="terminal_container",
            left=0,
            top=500,
            height=150,
            width=650,
            bg_color=True,
        )
        self.terminal = Terminal(
            container=terminal_container,
            variable_name="terminal_text",
            left=10,
            top=15,
            width=610,
            height=100,
        )

        # ── event bindings
        self.add_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_add))
        self.remove_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_remove))

        self.starts_container = starts_container
        return starts_container

    # ──────────────────────────────── CALLBACKS

    def onclick_add(self):
        local_ip = get_local_ip()
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7000",
            width=247,
            height=105,
            resizable=True,
            on_top=True,
        )

    def onclick_remove(self):
        folder = self.user_dd.get_value().replace(" ", "")
        path = os.path.join(ROOT_DIR, folder)
        if not os.path.isdir(path):
            print(f"⚠️ No such folder: {path}")
            return
        try:
            shutil.rmtree(path)
            print(f"🗑️ Removed {path}")
        except Exception as exc:
            print(f"❌ Failed to remove: {exc}")

    # ──────────────────────────────── DROPDOWN REFRESH

    def refresh(self):
        self.user_dd.empty()
        self.user_dd.append(self.list_user_folders())


# ────────────────────────────────────────── RUN


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
