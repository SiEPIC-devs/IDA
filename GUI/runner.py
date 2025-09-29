import sys, pathlib, subprocess, threading, os, time, platform, signal
import atexit

# # ────────── Configuration ───────────
# PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
# PY = sys.executable
# LOG_FILE = PROJECT_ROOT / "log.txt"
# OPEN_LOG_TERMINAL = True
# LOG_TAIL_LINES = 200
#
# KEEP_LINES = 500
# TRIM_THRESHOLD = 750
# # ───────────────────────────────────
def find_project_root(start: pathlib.Path) -> pathlib.Path:
    """
    Walk upward until we find a directory that contains 'GUI' and 'motors'.
    This works whether the runner is in GUI/ or elsewhere.
    """
    cur = start if start.is_dir() else start.parent
    for parent in [cur] + list(cur.parents):
        if (parent / "GUI").is_dir() and (parent / "motors").is_dir():
            return parent
    raise RuntimeError(
        f"Could not locate project root above {start}; "
        f"expected sibling folders 'GUI' and 'motors'."
    )

# ────────── Configuration ───────────
THIS_FILE = pathlib.Path(__file__).resolve()
PROJECT_ROOT = find_project_root(THIS_FILE)
GUI_DIR = PROJECT_ROOT / "GUI"
EXCLUDE_DIRS = {PROJECT_ROOT / "venv", PROJECT_ROOT / ".venv", PROJECT_ROOT / "build", PROJECT_ROOT / "dist"}
PY = sys.executable
LOG_FILE = PROJECT_ROOT / "GUI" / "log.txt"
OPEN_LOG_TERMINAL = True
LOG_TAIL_LINES = 200

KEEP_LINES = 500
TRIM_THRESHOLD = 750
# ───────────────────────────────────


assert (PROJECT_ROOT / "GUI").is_dir()
assert (PROJECT_ROOT / "motors").is_dir()

# import warnings
# warnings.filterwarnings(
#     "ignore",
#     category=UserWarning,
#     message=r"pkg_resources is deprecated as an API\.",
#     module=r"remi(\.|$)",
# )

def is_target(p: pathlib.Path) -> bool:
    if any(ex in p.parents for ex in EXCLUDE_DIRS):
        return False
    s = p.stem.lower()
    if s.endswith("gui"):
        return True
    return s in {
        "main_start_gui",
        "main_instruments_gui",
        "main_devices_gui",
        "main_registration_gui",
        "mainframe_command_gui",
        "mainframe_configuration_gui",
        "mainframe_sensor_control_gui",
        "mainframe_stage_control_gui",
        "mainframe_tec_control_gui",
        "sub_add_btn_gui",
        "sub_area_scan_setting_gui",
        "sub_connect_config_gui",
        "sub_data_window_setting_gui",
        "sub_fine_align_setting_gui",
        "sub_laser_sweep_setting_gui",
        "sub_limit_setting_gui",
    }

PROJECT_ROOT.mkdir(parents=True, exist_ok=True)

class LastNFileLogger:
    def __init__(self, path: pathlib.Path, keep_lines=500, threshold=750, encoding='utf-8'):
        self.path = pathlib.Path(path)
        self.keep = int(keep_lines)
        self.threshold = int(threshold)
        self.encoding = encoding
        self._lock = threading.Lock()
        self._fh = None
        self._open()
        self._line_count = self._count_lines()

    def _open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 行缓冲，文本模式
        self._fh = open(self.path, 'a', buffering=1, encoding=self.encoding, newline='')

    def _ensure_open(self):
        if self._fh is None or self._fh.closed:
            # 防御性重开
            self._open()

    def close(self):
        with self._lock:
            try:
                if self._fh and not self._fh.closed:
                    self._fh.flush()
                    self._fh.close()
            except Exception:
                pass

    def _count_lines(self) -> int:
        try:
            with open(self.path, 'rb') as f:
                return sum(1 for _ in f.read().splitlines())
        except FileNotFoundError:
            return 0

    def _decode_bytes(self, b: bytes) -> str:
        if not b:
            return ''
        if b.count(b'\x00') > max(8, len(b)//10):
            try:
                return b.decode('utf-16-le', errors='replace').replace('\x00', '')
            except Exception:
                pass
        return b.decode(self.encoding, errors='replace').replace('\x00', '')

    def write_line(self, s):
        if isinstance(s, (bytes, bytearray)):
            s = self._decode_bytes(bytes(s))
        if not s.endswith('\n'):
            s = s + '\n'
        with self._lock:
            self._ensure_open()
            try:
                self._fh.write(s)
            except ValueError:
                self._open()
                self._fh.write(s)
            self._fh.flush()
            self._line_count += 1
            if self._line_count >= self.threshold:
                self._compact_locked()

    def _read_last_lines(self, n: int) -> list[str]:
        n = max(0, n)
        lines: list[str] = []
        with open(self.path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            block = 64 * 1024
            buf = b''
            while pos > 0 and len(lines) < n:
                size = min(block, pos)
                pos -= size
                f.seek(pos, os.SEEK_SET)
                buf = f.read(size) + buf
                parts = buf.split(b'\n')
                buf = parts[0]
                for line in reversed(parts[1:]):
                    lines.append(self._decode_bytes(line))
                    if len(lines) >= n:
                        break
            if len(lines) < n and buf:
                lines.append(self._decode_bytes(buf))
        lines.reverse()
        return [ln.rstrip('\r\n') for ln in lines[-n:]]

    def _compact_locked(self):
        tail = self._read_last_lines(self.keep)

        try:
            if self._fh and not self._fh.closed:
                self._fh.flush()
                self._fh.close()
        except Exception:
            pass

        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        with open(tmp, 'w', encoding=self.encoding, newline='') as out:
            if tail:
                out.write('\n'.join(tail))
                out.write('\n')

        import time as _t
        for _ in range(10):
            try:
                os.replace(tmp, self.path)
                break
            except PermissionError:
                _t.sleep(0.05)
        else:
            # 替换始终失败：回退为追加模式避免卡死
            try:
                os.remove(tmp)
            except Exception:
                pass

        self._open()
        self._line_count = len(tail)

FILE_LOG = LastNFileLogger(LOG_FILE, keep_lines=KEEP_LINES, threshold=TRIM_THRESHOLD)

# Track subprocesses globally
processes = []

def _quote(p: pathlib.Path) -> str:
    s = str(p)
    return f'"{s}"' if any(ch in s for ch in (' ', '(', ')')) else s

def open_log_terminal_windows(log_path: pathlib.Path, tail_lines: int = 200):
    log_q = _quote(log_path)
    ps_cmd = (
        f"$host.ui.RawUI.WindowTitle='log viewer'; "
        f"Write-Host 'Viewing {log_path}'; "
        f"if (!(Test-Path {log_q})) {{ '' | Out-File -Encoding utf8 {log_q} }}; "
        f"Get-Content -Path {log_q} -Tail {tail_lines} -Wait"
    )
    subprocess.Popen(["start", "powershell", "-NoLogo", "-NoExit", "-Command", ps_cmd], shell=True)

def _pump_output(proc: subprocess.Popen):
    try:
        with proc.stdout:
            for raw in iter(proc.stdout.readline, b''):
                raw = raw.rstrip(b'\r\n')
                if not raw:
                    FILE_LOG.write_line('')
                else:
                    FILE_LOG.write_line(raw)
    except Exception as e:
        FILE_LOG.write_line(f"[launcher] output reader error: {e!r}")

def start_gui(path: pathlib.Path):
    # Esnure proj root is found as sys.path as child
    # Then make the child see its parent as top-folder package
    env = {**os.environ, "REM_MULTI_INST": "1", "PYTHONUNBUFFERED": "1"}
    env["PYTHONPATH"] = str(PROJECT_ROOT) + (os.pathsep + os.environ.get("PYTHONPATH", "")) if os.environ.get("PYTHONPATH") else str(PROJECT_ROOT)
    creation = subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
    proc = subprocess.Popen(
        [PY,"-u", str(path)],
        cwd=GUI_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=creation
    )
    processes.append(proc)
    FILE_LOG.write_line(f"▶ {path.name} started (pid={proc.pid})")

    reader = threading.Thread(target=_pump_output, args=(proc,), daemon=True)
    reader.start()

    rc = proc.wait()
    reader.join(timeout=1.0)
    FILE_LOG.write_line(f"⏹ {path.name} exited (rc={rc})")

def terminate_all():
    FILE_LOG.write_line("⏹ Terminating all subprocesses...")
    for proc in processes:
        try:
            print("Pre windows check")
            if platform.system() == "Windows":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                time.sleep(0.2)
            print("Pre termination:", proc.returncode)
            proc.terminate()
            print("Post termination:", proc.returncode if proc is not None else None)
            if proc.poll() is None:
                proc.kill()
            print("Post force:", proc.returncode if proc is not None else None)
            FILE_LOG.write_line(f"✔ Terminated PID {proc.pid}")
        except Exception as e:
            FILE_LOG.write_line(f"⚠️ Failed to terminate PID {proc.pid}: {e}")
        # Log file cleanup
        time.sleep(1)
        FILE_LOG.close()

def main():
    if platform.system() != "Windows":
        print("It's Windows Version")
    targets = sorted(p for p in GUI_DIR.rglob("*.py") if is_target(p))
    if not targets:
        print("⚠️  No *gui.py / *setup.py found"); return

    print(f"Logging (tail={KEEP_LINES}, trim-threshold={TRIM_THRESHOLD}) → {LOG_FILE}\n")

    threads = []
    for mod in targets:
        th = threading.Thread(target=start_gui, args=(mod,), daemon=True)
        th.start()
        threads.append(th)
        time.sleep(0.3)

    if OPEN_LOG_TERMINAL and platform.system() == "Windows":
        open_log_terminal_windows(LOG_FILE, LOG_TAIL_LINES)

    print("All GUIs started. Press Ctrl-C to exit.")
    try:
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        print("DEBUG: THIS IS A INTERRUPT")
        terminate_all()
    except Exception as e:
        print(f"DEBUG: EXCPETION: {e!r}")
        terminate_all()

if __name__ == "__main__":
    # atexit.register(terminate_all)
    # signal.signal(signal.SIGTERM, lambda sig, frame: terminate_all())
    main()
