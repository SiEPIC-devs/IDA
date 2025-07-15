import sys, pathlib, subprocess, threading, os, time
from lab_gui import *

# ────────── Configuration ───────────
BASE_DIR = pathlib.Path(__file__).resolve().parent
PY = sys.executable
LOG_FILE = BASE_DIR / "log.txt"
# ───────────────────────────────────

def is_target(p: pathlib.Path) -> bool:
    """Check if a file should be launched based on its name"""
    s = p.stem.lower()
    return s.endswith("gui") or s.endswith("setup") or s.endswith("init")

# Aggregate log file (line-buffered)
log_fh = open(LOG_FILE, "w", buffering=1, encoding="utf-8")

# Track subprocesses globally
processes = []

def start_gui(path: pathlib.Path):
    """Thread target: start a GUI subprocess and wait for it to exit"""
    proc = subprocess.Popen(
        [PY, str(path)],
        cwd=path.parent,
        stdout=log_fh,
        #stderr=subprocess.STDOUT,
        env={**os.environ, "REM_MULTI_INST": "1"}
    )
    processes.append(proc)
    print(f"▶ {path.name} started (pid={proc.pid})")
    proc.wait()
    print(f"⏹ {path.name} exited (rc={proc.returncode})")

def terminate_all():
    """Terminate all started subprocesses"""
    print("\n⏹ Terminating all subprocesses...")
    for proc in processes:
        try:
            proc.terminate()
            print(f"✔ Terminated PID {proc.pid}")
        except Exception as e:
            print(f"⚠️ Failed to terminate PID {proc.pid}: {e}")

def main():
    targets = sorted(p for p in BASE_DIR.rglob("*.py") if is_target(p))
    if not targets:
        print("⚠️  No *gui.py / *setup.py found"); return

    print(f"Logging all output to: {LOG_FILE}\n")

    threads = []
    for mod in targets:
        th = threading.Thread(target=start_gui, args=(mod,))
        th.start()
        threads.append(th)
        time.sleep(0.3)

    print("All GUIs started. Press Ctrl‑C to exit.")

    try:
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        terminate_all()

if __name__ == "__main__":

    main()
