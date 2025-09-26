#!/usr/bin/env python3
"""
Main entry point for the Probe_Stage Probe application.
This file serves as the entry point for PyInstaller.
"""

import sys
import os
import threading
import signal
from pathlib import Path

def main():
    """Main application entry point"""
    print("Starting Probe_Stage Probe Application...")
    
    # Import the main GUI launcher
    from GUI.runner import main as gui_main
    
    try:
        # Run the GUI launcher (starts all GUI components)
        gui_main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()