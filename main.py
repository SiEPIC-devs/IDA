#!/usr/bin/env python3
"""
Launcher for the SiEPIC Probe Stage application.

When frozen by PyInstaller this becomes a standalone .exe.  Because
runner.py spawns each GUI module as a *subprocess* (needs a real Python
interpreter), the exe acts as a thin launcher that:

  1. Locates the project root (directory containing this exe / script).
  2. Finds a working Python interpreter (venv → pyenv-win → system PATH).
  3. Runs ``python GUI/runner.py`` in that project root.

Double-click the resulting .exe for the same effect as running runner.py.
"""

import sys
import os
import signal
import subprocess
import ctypes
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────

def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _project_root() -> Path:
    """Return the project root directory."""
    if _is_frozen():
        # When frozen, the exe sits *inside* the project root
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _find_python(project_root: Path) -> str:
    """
    Search for a working Python interpreter in order of preference:
      1. <project>/venv/Scripts/python.exe   or .venv
      2. Well-known install paths for Python 3.11
      3. Windows ``py -3.11`` launcher
      4. pyenv-win versions (3.11.x first)
      5. System PATH  (``python`` / ``python3``)
    Returns the path string or raises RuntimeError.
    """
    import shutil

    candidates: list[str] = []

    # 1. Virtual-env inside the project
    for venv in ("venv", ".venv"):
        py = project_root / venv / "Scripts" / "python.exe"
        if py.is_file():
            candidates.append(str(py))

    # 2. Well-known Windows install locations for Python 3.11
    for base in (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python311",
        Path("C:/Python311"),
        Path("C:/Program Files/Python311"),
    ):
        py = base / "python.exe"
        if py.is_file():
            candidates.append(str(py))

    # 3. Windows ``py`` launcher  (``py -3.11``)
    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            r = subprocess.run(
                [py_launcher, "-3.11", "-c",
                 "import sys; print(sys.executable)"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                candidates.append(r.stdout.strip())
        except Exception:
            pass

    # 4. pyenv-win versions (prefer 3.11.x)
    pyenv_root = Path.home() / ".pyenv" / "pyenv-win" / "versions"
    if pyenv_root.is_dir():
        for ver_dir in sorted(pyenv_root.iterdir(), reverse=True):
            py = ver_dir / "python.exe"
            if py.is_file():
                candidates.append(str(py))

    # 5. System PATH (fallback — might be a different minor version)
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        norm = os.path.normcase(os.path.abspath(c))
        if norm not in seen:
            seen.add(norm)
            unique.append(c)

    # Validate: pick the first one that actually executes
    for c in unique:
        try:
            r = subprocess.run(
                [c, "-c", "import sys; print(sys.version_info[:2])"],
                capture_output=True, timeout=10,
            )
            if r.returncode == 0:
                return c
        except Exception:
            continue

    raise RuntimeError(
        "Could not find a working Python interpreter.\n"
        "Please create a venv in the project root or ensure Python is on PATH."
    )


def _msgbox(title: str, text: str):
    """Show a Windows message-box (works even without a console)."""
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


def _log(project_root: Path, msg: str):
    """Append a line to launcher.log for debugging."""
    try:
        with open(project_root / "launcher.log", "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now():%H:%M:%S}] {msg}\n")
    except Exception:
        pass


# ── Main ─────────────────────────────────────────────────────────────

def main():
    project_root = _project_root()
    _log(project_root, f"Launcher started. frozen={_is_frozen()}, root={project_root}")
    runner_script = project_root / "GUI" / "runner.py"

    if not runner_script.is_file():
        _msgbox(
            "SiEPIC Probe Stage",
            f"Cannot find GUI/runner.py in:\n{project_root}\n\n"
            "Make sure the executable is placed at the project root.",
        )
        sys.exit(1)

    # --- non-frozen: just call runner.main() directly (original path) ---
    if not _is_frozen():
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        from GUI.runner import main as gui_main
        gui_main()
        return

    # --- frozen exe: find Python and launch runner.py as a subprocess ---
    try:
        python = _find_python(project_root)
    except RuntimeError as exc:
        _msgbox("SiEPIC Probe Stage – Python not found", str(exc))
        sys.exit(1)

    _log(project_root, f"Using Python: {python}")

    env = {**os.environ, "PYTHONPATH": str(project_root)}
    # runner.py needs a real console for SetConsoleCtrlHandler, log viewer, etc.
    proc = subprocess.Popen(
        [python, "-u", str(runner_script)],
        cwd=str(project_root),
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    _log(project_root, f"runner.py launched as PID {proc.pid}")

    try:
        rc = proc.wait()
        _log(project_root, f"runner.py exited with code {rc}")
        sys.exit(rc)
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=5)
        sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()