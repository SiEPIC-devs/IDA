from lab_gui import *
from remi import start, App
import threading
import webview
import signal


class stage_control(App):
    def __init__(self, *args, **kwargs):
        self.command_input = None
        self.confirm_btn = None
        if "editing_mode" not in kwargs:
            super(stage_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        pass

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        command_container = StyledContainer(
            container=None, variable_name="command_container", left=0, top=0, height=50, width=400
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

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm_btn))

        self.command_container = command_container
        return command_container

    def onclick_confirm_btn(self):
        command_text = self.command_input.get_value().strip()
        if not command_text:
            print("Empty command ignored")
            return

        command_data = {}
        try:
            parts = [p.strip() for p in command_text.split(",")]
            for part in parts:
                if "_" not in part:
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
                elif val.replace(".", "", 1).isdigit():
                    val = float(val) if "." in val else int(val)
                else:
                    val = val
                command_data[key] = val
        except Exception as e:
            print(f"[Error] Invalid command format: {e}")
            return

        file = File("shared_memory", "command", command_data)
        file.save()

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
            document.documentElement.style.overflow = 'hidden';
            document.body.style.overflow = 'hidden';
        """)
    except Exception as e:
        print("JS Wrong", e)


if __name__ == '__main__':
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    local_ip = get_local_ip()
    webview.create_window(
        'TEC Control',
        f'http://{local_ip}:8003',
        width=422, height=107,
        x=800, y=100,
        resizable=True
    )
    webview.start(func=disable_scroll)
