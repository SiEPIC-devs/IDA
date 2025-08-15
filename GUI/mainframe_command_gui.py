from lab_gui import *
from remi import start, App
import threading
import webview
import signal
w = 6
h = 17
shared_path = os.path.join("database", "shared_memory.json")

class stage_control(App):
    def __init__(self, *args, **kwargs):
        self._user_stime = None
        self.command_input = None
        self.confirm_btn = None
        self.uploaded_filename = None
        self.configuration = {}
        self.configuration_count = 0
        if "editing_mode" not in kwargs:
            super(stage_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

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
                    self.configuration = data.get("Configuration", {})
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def after_configuration(self):
        if all(v != "" for v in self.configuration.values()) and self.configuration_count == 0:
            self.configuration_count = 1
            webview.create_window(
                "TEC Control",
                f"http://{local_ip}:8003",
                width=422-w, height=137-h,
                x=1150, y=100,
                resizable=True,
                hidden=False
            )


    def construct_ui(self):
        command_container = StyledContainer(
            container=None, variable_name="command_container", left=0, top=0, height=80, width=400
        )

        StyledLabel(
            container=command_container, text="Command", variable_name="on_label", left=0, top=10,
            width=70, height=30, font_size=100, flex=True, justify_content="right", color="#222"
        )

        self.command_input = StyledTextInput(
            container=command_container, variable_name="command", left=80, top=10, height=25, width=200
        )

        self.confirm_btn = StyledButton(
            container=command_container, variable_name="confirm", text="Confirm", left=310, top=10, height=27, width=80
        )

        self.uploader = StyledFileUploader(
            container=command_container, variable_name="uploader", left=10, top=45, width=220, height=30
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm_btn))
        self.uploader.ondata.do(lambda emitter, filedata, filename: self.run_in_thread(self.ondata_uploader, emitter, filedata, filename))

        self.command_container = command_container
        return command_container

    def onclick_confirm_btn(self):
        command_text = self.command_input.get_value().strip()
        command_data = {}

        if command_text:
            parts = [p.strip() for p in command_text.split(",")]
        elif self.uploaded_filename:
            try:
                filepath = os.path.join("./res", self.uploaded_filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                    parts = [p.strip() for p in text.split(",")]
            except Exception as e:
                print(f"[Error] Failed to load uploaded .txt file: {e}")
                return
        else:
            print("⚠️ No input or uploaded file to use")
            return

        try:
            for part in parts:
                if "_" not in part:
                    continue

                if part.count("_") == 1:
                    command_data[part] = True
                    continue

                key_parts = part.rsplit("_", 1)
                if len(key_parts) != 2:
                    continue
                key, val = key_parts
                val_lower = val.lower()
                if val_lower == "true":
                    val = True
                elif val_lower == "false":
                    val = False
                elif "/" in val:
                    val_list = val.split("/")
                    val = []
                    for v in val_list:
                        if v.replace(".", "", 1).isdigit():
                            v = float(v) if "." in v else int(v)
                        val.append(v)
                elif val.replace(".", "", 1).isdigit():
                    val = float(val) if "." in val else int(val)
                command_data[key] = val

        except Exception as e:
            print(f"[Error] Failed to parse command text: {e}")
            return

        file = File("command", "command", command_data)
        file.save()

    def ondata_uploader(self, emitter, filedata: bytes, filename: str):
        try:
            os.makedirs("./res", exist_ok=True)
            filepath = os.path.join("./res", filename)
            with open(filepath, "wb") as f:
                f.write(filedata)
            self.uploaded_filename = filename
            print(f"✅ File '{filename}' saved to ./res/")
        except Exception as e:
            print(f"[Error] Failed to save file: {e}")

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


def run_remi():
    start(
        stage_control,
        address="0.0.0.0", port=8003,
        start_browser=False, multiple_instance=False
    )


def disable_scroll():
    try:
        webview.windows[0].evaluate_js("""
            document.documentElement.style.overflow = "hidden";
            document.body.style.overflow = "hidden";
        """)
    except Exception as e:
        print("JS Wrong", e)


if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    local_ip = get_local_ip()
    webview.create_window(
        "TEC Control",
        f"http://{local_ip}:8003",
        width=422, height=137,
        x=1150, y=100,
        resizable=True,
        hidden=True
    )
    webview.start(func=disable_scroll)
