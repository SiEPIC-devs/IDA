import threading
import asyncio
import signal
import webview 
import time
import datetime

from remi.gui import *
from remi import start, App

from GUI import lib_coordinates
from GUI.lib_gui import *
from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration
from measure.area_sweep import AreaSweep
from measure.fine_align import FineAlign
from measure.config.area_sweep_config import AreaSweepConfiguration
from measure.config.fine_align_config import FineAlignConfiguration
from utils.progress_write_helpers import write_progress_file
from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration

# Global Vars
FILENAME = "coordinates.json"
COMMAND_PATH = os.path.join("database", "command.json")
SHARED_PATH = os.path.join("database", "shared_memory.json")


class stage_control(App):
    """
    Primary control method for state machine involving movements
    and operations
    """

    def __init__(self, *args, **kwargs):
        # Mixed Label + (high level) State vars
        self.memory = None
        self.configure = None
        self.stage_manager = None
        self.x_position_lb = None
        self.y_position_lb = None
        self.z_position_lb = None
        self.chip_position_lb = None
        self.fiber_position_lb = None
        self._user_mtime = None
        self._first_command_check = True
        self._user_stime = None
        
        # Config vars
        self.user = "Guest"
        self.limit = {}
        self.area_s = {}
        self.fine_a = {}
        self.count = 0
        self.filter = {}
        self.configuration = {}
        self.configuration_check = {}
        self.port = {}  # For VISA addr
        self.data_window = {}

        # State vars
        self.auto_sweep = 0
        self.configuration_stage = 0
        self.configuration_sensor = 0
        self.project = None
        self.scanpos = {}
        self.stagepos = {}
        self.zero_state = {}
        self.stage_x_pos = 0
        self.stage_y_pos = 0
        self.sweep = {}
        self.name = None
        self.sweep_count = 0
        self.pre_x = None
        self.pre_y = None
        self.stage_window = None
        self.sensor_window = None
        self.devices = None
        self.web = None
        self.file_format = {}
        self.use_destination_dir = {}  # For auto file pathing
        self.file_path = None
        self.slot_info = None
        self.slot_info_flag = False
        self.detector_window_settings = {}
        self.meta_data = {}

        # Misc vars, managers, progress bar and locks
        self.nir_configure = None
        self.nir_manager = None

        self.past_laser_on = 0
        self.past_wvl = None
        self.past_power = None

        self.data = None
        self._scan_done = Value(c_int, 0)
        self.ch_count = 0
        self.ch_last_time = 0
        self.ch_current_time = 0
        self.task_start = 0
        self._win_lock = threading.Lock()
        self.axis_locked = {"x": False, "y": False, "z": False, "chip": False, "fiber": False}
        self.use_relative_movement = True  # For absolute movements
        self._absolute_locked_axes = {"z": False, "chip": False}  # For tracking of abs mvnts
        self.area_sweep = None
        self.fine_align = None
        self.task_laser = 0
        self._progress_lock = threading.Lock()  # For progress.json 'w'
        self.pause_power_reading = False  # Pause update_ch during fine_align/sweep
        self._bias_sweep_active = False     # True while _do_bias_sweep is running
        self._sweep_locked = False              # True when external SweepLock detected
        self._self_locking = False              # True when this GUI wrote SweepLock

        # User config settings 
        self.load_user_settings = False  # False until loaded
        self.apply_initial_positions = True
        self.initial_positions = {}
        
        if "editing_mode" not in kwargs:
            super(stage_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            mtime = os.path.getmtime(COMMAND_PATH)
            stime = os.path.getmtime(SHARED_PATH)
        except FileNotFoundError:
            mtime = None
            stime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.run_in_thread(self.execute_command)

        if stime != self._user_stime:
            self._user_stime = stime
            # Use thread-safe SharedMemory utility
            data = SharedMemory.read({})
            if data:
                self.user = data.get("User", "")
                self.project = data.get("Project", "")
                self.limit = data.get("Limit", {})
                self.area_s = data.get("AreaS", {})
                self.fine_a = data.get("FineA", {})
                self.auto_sweep = data.get("AutoSweep", 0)
                self.auto_sweep_type = data.get("AutoSweepType", "Laser Sweep")
                self.filter = data.get("Filtered", {})
                # Guard: never overwrite with empty — protects against partial reads
                cfg = data.get("Configuration")
                if isinstance(cfg, dict) and cfg:
                    self.configuration = cfg
                cfg_chk = data.get("Configuration_check")
                if isinstance(cfg_chk, dict) and cfg_chk:
                    self.configuration_check = cfg_chk
                self.scanpos = data.get("ScanPos", {})
                self.sweep = data.get("Sweep", {})
                self.name = data.get("DeviceName", "")
                self.data_window = data.get("DataWindow", {})
                self.port = data.get("Port", {})
                self.web = data.get("Web", "")
                self.file_format = data.get("FileFormat", {})
                self.file_path = data.get("FilePath", "")
                self.use_destination_dir = data.get("ExportRequest", {})
                self.load_user_settings = data.get("LoadConfig", False)
                
                # Mainframe slot info
                self.slot_info = data.get("SlotInfo", None)

                # Read detector range and reference settings
                self.detector_window_settings = data.get("DetectorWindowSettings", {})

                # Meta data for auto sweeps
                self.meta_data = {
                    'user': self.user,
                    'project': self.project,
                    'device_name': self.name,
                    'fine_a': self.fine_a,
                    'area_s': self.area_s,
                    'detector_window': self.detector_window_settings,
                    'slot_info': self.slot_info,
                    'configuration': self.configuration,
                    # Add more as you feel necessary
                    # Used for passing information 
                    # During automated measurements
                    # For mata data context
                }

            
                if self.detector_window_settings.get("Detector_Change") == "1":
                    if self.slot_info is not None:
                        # If we've enumerated slot info, proceed as is
                        for mf, slot, head in self.slot_info:
                            self.apply_detector_window(slot, mf)
                    
                        data["DetectorWindowSettings"]["Detector_Change"] = "0"   # reset flag
                        SharedMemory.update({"DetectorWindowSettings": data["DetectorWindowSettings"]})
                    
                    else:
                        # Otw, wait until enumeration
                        pass
                
                if self.load_user_settings:
                    # Load user settings on initial boot up 
                    self.load_user_settings = False  # Do this only once

                    # Import the class
                    from GUI.lib_gui import UserConfigManager

                    # Load hierarchical config
                    config_manager = UserConfigManager(self.user, self.project)
                    user_settings = config_manager.load_config()

                    # Load sweep settings
                    self.sweep = user_settings.get("Sweep", {})
                    self.detector_window_settings = user_settings.get("DetectorWindowSettings")

                    # Load FA / Area Scan settings
                    self.area_s = user_settings.get("AreaS", {})
                    self.fine_a = user_settings.get("FineA", {})

                    # Load instrument connections and factory
                    # Only restore non-connection settings from saved config;
                    # skip "sensor", "tec", "smu" so devices don't auto-connect.
                    saved_cfg = user_settings.get("Configuration", {})
                    for k, v in saved_cfg.items():
                        if k not in ("sensor", "tec", "smu"):
                            self.configuration[k] = v

                    self.initial_positions = user_settings.get("InitialPositions", {})
                    if self.initial_positions == {}:
                        # If there is no preference to initial positions
                        # Do not apply anything
                        self.apply_initial_positions = False
                    else:
                        self.apply_initial_positions = True  # Should reapply on a new config

                    data["LoadConfig"] = False   # reset flag
                    SharedMemory.update({"LoadConfig": False})

                # ---------------- SweepLock from external (elec_probe) ----------------
                sweep_lock_val = data.get("SweepLock", 0)
                if sweep_lock_val and not self._sweep_locked and not self._self_locking:
                    self._sweep_locked = True
                    self.lock_all(sweep_lock_val, write_shared=False)
                    print("[StageControl] Locked by external SweepLock")
                elif not sweep_lock_val and self._sweep_locked:
                    self._sweep_locked = False
                    self._self_locking = False
                    self.lock_all(0, write_shared=False)
                    print("[StageControl] Unlocked (external SweepLock cleared)")

        # For slot enum
        if self.nir_manager is not None and not self.slot_info_flag:
            self.slot_info = self.nir_manager.get_mainframe_slot_info()
            self.slot_info_flag = True
            SharedMemory.update({"SlotInfo": self.slot_info})

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def set_power(self):
        self.nir_manager.set_power(self.sweep["power"])
        self.sweep_count = 0

    def set_wvl(self):
        self.nir_manager.set_wavelength(self.sweep["wvl"])
        self.sweep_count = 0

    def laser_on(self):
        self.nir_manager.enable_laser(self.sweep["on"])
        self.sweep_count = 0
    
    def apply_detector_auto_range(self, channel, mf=0):
        success = self.nir_manager.set_power_range_auto(channel, mf=mf)
        return success

    def apply_detector_range(self, range_dbm, channel, mf=0):
        success = self.nir_manager.set_power_range(range_dbm, channel, mf=mf)
        return success
    
    def apply_detector_reference(self, ref_dbm, channel, mf=0):
        success = self.nir_manager.set_power_reference(ref_dbm, channel, mf=mf)
        return success
    
    def apply_detector_window(self, channel, mf=0):
        try:
            # Get detector window data from new compact structure
            detector_window_data = getattr(self, 'detector_window_settings', {})
            mf_data = detector_window_data.get(f'mf{mf}', {})
            slot_data = mf_data.get(str(channel), {})
            
            # Extract settings from compact structure
            auto_range = slot_data.get('auto_range', True)    # Default to auto
            manual_range = slot_data.get('range', -10)        # Default -10 dBm
            ref_value = slot_data.get('ref', -30)             # Default -30 dBm
            
            # Apply range settings
            if auto_range:
                self.apply_detector_auto_range(
                    channel=channel,
                    mf=mf
                )
            else:
                self.apply_detector_range(
                    manual_range,
                    channel=channel,
                    mf=mf
                )

            # Apply reference setting
            self.apply_detector_reference(
                ref_dbm=ref_value,
                channel=channel,
                mf=mf
            )
            
            return True
        
        except Exception as e:
            print(f'Detector window error: {e}')
            return False

    def laser_sweep(self, name=None):
        print("Sweep Start")
        auto = 0
        if name is None:
            session_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # Check if bias sweep is enabled
            bias_cfg = self.sweep.get("bias_voltage", {})
            bias_enabled = bias_cfg.get("enabled", False)

            if bias_enabled:
                session_name = f"spectral_sweep_EO_{session_time}"
                name = f"Manual_Sweep_EO/{session_name}"
            else:
                session_name = f"spectral_sweep_Optical_{session_time}"
                name = f"Manual_Sweep_Optical/{session_name}"

            self.busy_dialog()
            self.task_start = 1
            self.task_laser = 1
            self.lock_all(1)
        else:
            self.task_start = 1
            auto = 1
            bias_cfg = self.sweep.get("bias_voltage", {})
            bias_enabled = bias_cfg.get("enabled", False)

        if bias_enabled:
            self._do_bias_sweep(name, auto, bias_cfg)
        else:
            self._do_single_sweep(name, auto, filename_prefix="spectral_sweep_Optical")

        if auto == 0:
            if self.sweep.get("done", "Laser On") == "Laser On":
                self.nir_manager.enable_laser(True)
            else:
                self.nir_manager.enable_laser(False)

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0
                self.task_laser = 0
                self.lock_all(0)

            self.sweep_count = 0
            self.sweep["sweep"] = 0
            file = File("shared_memory", "Sweep", self.sweep)
            file.save()
        if auto == 1:
            # Always have the laser on during an auto 
            self.nir_manager.enable_laser(True)
            
        print("Sweep Done")

    # ------------------------------------------------------------------
    # Bias sweep via shared_memory (stage <-> elec_probe)
    # ------------------------------------------------------------------
    def _send_bias_command(self, action, mode="V", value=0.0):
        """
        Write a BiasCommand to shared_memory.json for elec_probe to execute.
        action: 'set' | 'off' | 'init'
        Waits until elec_probe sets action='done' (with timeout).
        """
        try:
            # Clear any stale 'done' from previous command
            SharedMemory.update({"BiasCommand": {"action": ""}})
            time.sleep(0.05)

            cmd = {"action": action, "mode": mode, "value": value}
            SharedMemory.update({"BiasCommand": cmd})
            print(f"[Bias] Sent command: {cmd}")

            # Poll for completion
            timeout = 10.0  # seconds
            poll_interval = 0.05
            elapsed = 0.0
            while elapsed < timeout:
                time.sleep(poll_interval)
                elapsed += poll_interval
                data = SharedMemory.read({})
                bc = data.get("BiasCommand", {})
                if bc.get("action") == "done":
                    print(f"[Bias] Command completed: {action} {value}{mode}")
                    return True
            print(f"[Bias] Timeout waiting for elec_probe to execute: {action}")
            return False
        except Exception as e:
            print(f"[Bias] Error sending bias command: {e}")
            return False

    def _turn_off_bias(self):
        """Send bias off command via shared_memory."""
        self._send_bias_command("off")

    # ------------------------------------------------------------------
    # MotorCommand IPC: move BSC203 axis via elec_probe
    # ------------------------------------------------------------------
    def _send_motor_command(self, axis, distance_um):
        """
        Ask elec_probe to move BSC203 'axis' by 'distance_um' micrometres.
        Clears previous result, writes MotorCommand, waits for action='done'.
        Returns True on success, False on timeout/error.
        """
        # Clear any stale 'done' from previous command before sending new one
        SharedMemory.update({"MotorCommand": {"action": ""}})
        time.sleep(0.05)  # Let elec_probe idle() see the clear

        cmd = {"action": "move", "axis": axis, "distance_um": distance_um}
        SharedMemory.update({"MotorCommand": cmd})
        print(f"[Motor] Sent: move {axis} {distance_um} um")

        timeout, poll = 65.0, 0.05
        elapsed = 0.0
        while elapsed < timeout:
            time.sleep(poll)
            elapsed += poll
            data = SharedMemory.read({})
            mc = data.get("MotorCommand", {})
            if mc.get("action") == "done":
                err = mc.get("error")
                if err:
                    print(f"[Motor] Error: {err}")
                    return False
                print(f"[Motor] Move complete: {axis} {distance_um} um")
                return True
        print(f"[Motor] Timeout moving {axis}")
        return False

    # ------------------------------------------------------------------
    # CurrentRead IPC: read SMU current via elec_probe
    # ------------------------------------------------------------------
    def _request_current_read(self, channel="A"):
        """
        Ask elec_probe to measure current on SMU channel.
        Returns current in Amps (float), or None on failure.
        """
        cmd = {"action": "read", "channel": channel}
        SharedMemory.update({"CurrentRead": cmd})

        timeout, poll = 10.0, 0.05
        elapsed = 0.0
        while elapsed < timeout:
            time.sleep(poll)
            elapsed += poll
            data = SharedMemory.read({})
            cr = data.get("CurrentRead", {})
            if cr.get("action") == "done":
                err = cr.get("error")
                if err:
                    print(f"[CurrentRead] Error: {err}")
                    return None
                val = cr.get("value")
                if val is not None:
                    return float(val)
                return None
        print("[CurrentRead] Timeout")
        return None

    def _read_force_weight(self, max_age_s=5.0):
        """
        Read total force weight from shared_memory (written by zns_v6_plot_cal.py).
        Returns (total_g, is_fresh).  is_fresh=False if data is stale or missing.
        """
        data = SharedMemory.read({})
        fw = data.get("ForceWeight", {})
        total = fw.get("total", 0.0)
        ts = fw.get("timestamp")
        is_fresh = False
        if ts:
            try:
                import datetime
                age = (datetime.datetime.now() - datetime.datetime.fromisoformat(ts)).total_seconds()
                is_fresh = age <= max_age_s
            except Exception:
                pass
        return total, is_fresh

    def _average_force(self, duration=5.0, interval=1.0):
        """Read force weight repeatedly over 'duration' seconds, return average."""
        readings = []
        t0 = time.time()
        while time.time() - t0 < duration:
            val, fresh = self._read_force_weight()
            if fresh:
                readings.append(val)
            time.sleep(interval)
        if readings:
            return sum(readings) / len(readings)
        return 0.0

    def _do_bias_sweep(self, name, auto, bias_cfg):
        """Loop over bias values: send bias command -> sweep -> save with bias-aware name."""
        mode = bias_cfg.get("mode", "V")
        b_start = float(bias_cfg.get("start", 0.0))
        b_stop = float(bias_cfg.get("stop", 1.0))
        b_step = float(bias_cfg.get("step", 0.1))

        if b_step <= 0:
            print("[Bias] Invalid step size, skipping bias sweep")
            self._do_single_sweep(name, auto)
            return

        import numpy as np
        bias_values = np.arange(b_start, b_stop + b_step / 2, b_step)
        unit = "V" if mode == "V" else "uA"

        # Ask elec_probe to init SMU source mode and output on
        if not self._send_bias_command("init", mode=mode, value=b_start):
            print("[Bias] Elec probe did not respond, falling back to single sweep")
            self._do_single_sweep(name, auto, filename_prefix="spectral_sweep_EO")
            return

        print(f"[Bias] Starting bias sweep: {b_start}{unit} -> {b_stop}{unit}, step {b_step}{unit} ({len(bias_values)} points)")

        # Pause power reading for the entire bias sweep
        self.pause_power_reading = True
        self._bias_sweep_active = True

        cancel_flag = getattr(self, "_scan_cancel", None)
        total_points = len(bias_values)

        try:
            for idx, bias_val in enumerate(bias_values):
                # Check for cancel
                if cancel_flag and cancel_flag.is_set():
                    print("[Bias] Sweep cancelled by user")
                    break

                bias_val_rounded = round(bias_val, 6)
                print(f"[Bias] Point {idx+1}/{total_points}: {bias_val_rounded} {unit}")

                # Update progress
                pct = (idx / total_points) * 100.0
                write_progress_file(
                    activity=f"Bias {bias_val_rounded} {unit} ({idx+1}/{total_points})",
                    percent=pct,
                    n=idx+1, total=total_points
                )

                if not self._send_bias_command("set", mode=mode, value=bias_val_rounded):
                    print(f"[Bias] Failed to set bias {bias_val_rounded} {unit}, skipping")
                    continue

                # Settle time
                time.sleep(0.2)

                bias_label = f"{bias_val_rounded}{unit}"
                sweep_subdir = f"{name}/{bias_label}"

                self._do_single_sweep(
                    sweep_subdir, auto,
                    skip_webview=True,
                    filename_prefix=f"spectral_sweep_EO_{bias_label}"
                )
        finally:
            self._turn_off_bias()
            self._bias_sweep_active = False
            self.pause_power_reading = False

        print("[Bias] Bias sweep completed")

    # ------------------------------------------------------------------
    # Single sweep (original logic, extracted)
    # ------------------------------------------------------------------
    def _do_single_sweep(self, name, auto, skip_webview=False,
                          filename_prefix="spectral_sweep"):

        saved_pause = self.pause_power_reading

        # Update progress for manual single sweep (non-bias)
        if not self._bias_sweep_active:
            write_progress_file(activity="Laser sweep in progress...", percent=10.0)

        try:
            # Pause power reading to avoid GPIB conflicts
            self.pause_power_reading = True
            time.sleep(0.5)  # Wait for update_ch to finish current GPIB cycle

            # --- LUNA CONTROLLER PATH ---
            if self.configuration.get("sensor") == "luna_controller":
                print("[Stage Control] Using Luna OVA sweep")
                
                # Luna returns full data matrix from output.txt
                data_matrix = self.nir_manager.sweep(
                    start_nm=self.sweep["start"],
                    stop_nm=self.sweep["end"],
                    step_nm=self.sweep["step"],
                    laser_power_dbm=self.sweep["power"]
                )
                
                # Extract wavelength for compatibility
                wl = data_matrix[0]
                detectors = None  # Luna doesn't use detector format
                luna_data = data_matrix  # Keep full matrix for saving
                
                print("[Stage Control] Luna Sweep completed Successfully")
            
            # --- NIR CONTROLLER PATH  ---
            else:
                # Get slot info
                if self.slot_info is None:
                    slot_info = self.nir_manager.get_mainframe_slot_info()
                    self.slot_info = slot_info
                else:
                    slot_info = self.slot_info
                
                if slot_info is None:
                    raise RuntimeError("No slots found in the instrument")
                
                # Apply detector window to connected slots
                args_list = []

                for mf, slot, head in slot_info:
                    # Get data for this MF/slot combination
                    detector_window_data = getattr(self, 'detector_window_settings', {})
                    
                    # Data window structure: mf -> slot -> settings
                    mf_data = detector_window_data.get(f'mf{mf}', {})
                    slot_data = mf_data.get(str(slot), {})
                    
                    # Extract settings 
                    auto_range = slot_data.get('auto_range', True) # Default to auto (consistent with apply_detector_window)
                    manual_range = slot_data.get('range', -10.0)      # Default -10 dBm
                    ref_value = slot_data.get('ref', -30.0)           # Default -30 dBm
                    
                    # Determine final range and ref values
                    if auto_range:
                        ch_range = None  # None indicates auto ranging
                    else:
                        ch_range = manual_range
                    ch_ref = ref_value
                    
                    # Args format: (slot, mf, ref, range)
                    args_list.append((slot, mf, ch_ref, ch_range))
                    
                
                if len(args_list) == 0:
                    raise Exception("No args found")
                
                wl, detectors = self.nir_manager.sweep(
                    start_nm=self.sweep["start"],
                    stop_nm=self.sweep["end"],
                    step_nm=self.sweep["step"],
                    laser_power_dbm=self.sweep["power"],
                    args=args_list
                )
                
                luna_data = None  # No Luna data in NIR mode
                
                print("[Stage Control] Laser Sweep completed Successfully")

                # Apply detector window settings once again 
                for mf, slot, head in self.slot_info:
                    self.apply_detector_window(slot, mf)
            
        except Exception as e:
            print(f"[Error] Sweep failed: {e}")
            wl, detectors, luna_data = [], [], None
        finally:
            # Restore previous pause state (important for bias sweep)
            self.pause_power_reading = saved_pause

        # Update progress for manual single sweep (non-bias)
        if not self._bias_sweep_active:
            write_progress_file(activity="Saving data...", percent=80.0)
        
        # Plotting the data
        x = wl
        active_detectors = []
        cancel_flag = getattr(self, "_scan_cancel", None)
        was_cancelled = bool(cancel_flag and cancel_flag.is_set())
        
        if was_cancelled:
            print("[Plot] Sweep flag is 0  cancelled; skipping plot & webview.")
        else:
            try:
                fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                
                # Choose plotter based on sensor type
                if self.configuration.get("sensor") == "luna_controller":
                    if luna_data is None or len(luna_data) == 0:
                        raise ValueError("No Luna data to plot.")
                    
                    luna_fname = filename_prefix.replace("spectral_sweep", "ova_sweep")
                    diagram = plot_luna(
                        luna_data, luna_fname, fileTime,
                        self.user, name, self.project,
                        auto, self.file_format,
                        destination_dir=self.file_path,
                        meta_data=self.meta_data
                    )
                else:
                    # If detectors is None, treat as empty
                    if not detectors:
                        raise ValueError("No detectors data to plot.")

                    for d in detectors:
                        active_detectors.append(d)

                    if not active_detectors:
                        raise ValueError("Detector list empty after sweep.")

                    y = np.vstack(active_detectors)

                    diagram = plot(
                        x, y, filename_prefix, fileTime, 
                        self.user, name, self.project,
                        auto, self.file_format, self.slot_info,
                        destination_dir=self.file_path,
                        meta_data=self.meta_data
                    )
                
                p = Process(target=diagram.generate_plots)
                p.start()
                p.join(timeout=60)  # 60s max for plot generation
                if p.is_alive():
                    print("[Plot] Plot process timed out after 60s, terminating")
                    p.terminate()
                    p.join(timeout=5)

                if self.web != "" and auto == 0 and not skip_webview:
                    file_uri = Path(self.web).resolve().as_uri()
                    webview.create_window(
                        'Stage Control',
                        file_uri,
                        width=700, height=500,
                        resizable=True,
                        hidden=False
                    )

            except Exception as e:
                print(f"[Plot] Skipping plot due to error: {e}")

    def scan_move(self):
        import asyncio

        sp = self.scanpos
        x_step = float(self.area_s["x_step"])
        y_step = float(self.area_s["y_step"])

        use_rel = ("x_rel" in sp) and ("y_rel" in sp)

        if use_rel:
            xr = float(sp["x_rel"])
            yr = float(sp["y_rel"])

            # You must set these once at spiral start; see below.
            x_anchor = float(getattr(self, "stage_x_center", self.stage_x_pos))
            y_anchor = float(getattr(self, "stage_y_center", self.stage_y_pos))
            x_pos = x_anchor + xr
            y_pos = y_anchor + yr
        else:
            # Legacy path: BL indices
            j = int(sp["x"])
            i = int(sp["y"])
            x_pos = float(self.stage_x_pos) + j * x_step
            y_pos = float(self.stage_y_pos) + i * y_step

        # Respect per-axis locks
        if not self.axis_locked.get("x", False):
            asyncio.run(self.stage_manager.move_axis(AxisType.X, x_pos, False))
        if not self.axis_locked.get("y", False):
            asyncio.run(self.stage_manager.move_axis(AxisType.Y, y_pos, False))

        print(f"Move to: {x_pos:.3f}, {y_pos:.3f}")
        sp["move"] = 0
        File("shared_memory", "ScanPos", sp).save()
    
    def after_configuration(self):
        # Connect stage control instance
        if (self.configuration["stage"] != "" and self.configuration_stage == 0 and 
            self.configuration_check["stage"] == 0 and 
            (not hasattr(self, 'stage_manager') or self.stage_manager is None or 
             getattr(self, '_stage_disconnected', False))):
            
            # If reconnecting, clean up old manager first
            if hasattr(self, 'stage_manager') and self.stage_manager is not None and getattr(self, '_stage_disconnected', False):
                print("[Stage] Cleaning up old manager before reconnection")
                try:
                    future = asyncio.run_coroutine_threadsafe(self.stage_manager.disconnect_all(), main_loop)
                    future.result(timeout=5)
                except Exception as e:
                    print(f"[Stage] Old manager cleanup error: {e}")
            
            # Clear disconnected flag and create new manager
            self._stage_disconnected = False
            # Initialize automeasurement params
            self.gds = lib_coordinates.coordinates(("./res/" + FILENAME), read_file=False,
                                                   name="./database/coordinates.json")
            self.number = self.gds.listdeviceparam("number")
            self.coordinate = self.gds.listdeviceparam("coordinate")
            self.polarization = self.gds.listdeviceparam("polarization")
            self.wavelength = self.gds.listdeviceparam("wavelength")
            self.type = self.gds.listdeviceparam("type")
            self.devices = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]
            self.memory = Memory()

            # Initialize Stage configuration, startup stage manager
            self.configure = StageConfiguration()
            
            # Read Port configuration from shared_memory
            port_config = SharedMemory.get("Port", {})
            stage_port = port_config.get("stage", "ASRL7::INSTR")
            self.configure.visa_addr = stage_port
            print(f"[Stage Control] Using port: {stage_port}")
            
            self.configure.driver_types[AxisType.X] = self.configuration["stage"]
            self.configure.driver_types[AxisType.Y] = self.configuration["stage"]
            self.configure.driver_types[AxisType.Z] = self.configuration["stage"]
            self.configure.driver_types[AxisType.ROTATION_CHIP] = self.configuration["stage"]
            self.configure.driver_types[AxisType.ROTATION_FIBER] = self.configuration["stage"]
            self.stage_manager = StageManager(self.configure, create_shm=True)
            
            # Run both startup and initialization in the same event loop
            async def init_stage_manager():
                await self.stage_manager.startup()
                success = await self.stage_manager.initialize_all(
                    [AxisType.X, AxisType.Y, AxisType.Z, AxisType.ROTATION_CHIP, AxisType.ROTATION_FIBER]
                )
                return success
            
            future = asyncio.run_coroutine_threadsafe(init_stage_manager(), main_loop)
            success_stage = future.result(timeout=30)  # Wait up to 30 seconds
            if success_stage:
                stage_d = self.stage_manager.config.driver_types[AxisType.X]
                if (stage_d == "Corvus_controller") or (stage_d == "scylla_controller"):
                    self.onclick_home()  # Run "fake" home to get lims
                
                # Setup state machine
                self.configuration_stage = 1
                self.configuration_check["stage"] = 2
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()
                self.stage_window = webview.create_window(
                    'Stage Control',
                    f'http://{local_ip}:8000',
                    width=903 + web_w, height=437 + web_h,
                    x=800, y=465,
                    resizable=True,
                    hidden=False
                )
            else:
                # Connection failed - clean up the manager
                self.configuration_stage = 0
                self.configuration_check["stage"] = 1
                if self.stage_manager:
                    try:
                        future = asyncio.run_coroutine_threadsafe(self.stage_manager.shutdown(), main_loop)
                        future.result(timeout=10)
                    except Exception as e:
                        print(f"[Stage] Cleanup error: {e}")
                    self.stage_manager = None
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()

        elif self.configuration["stage"] == "" and self.configuration_stage == 1:
            # Disconnect instance
            self.configuration_stage = 0
            if self.stage_window:
                self.stage_window.destroy()
                self.stage_window = None
            if self.stage_manager:
                # Use the same event loop as connection
                future = asyncio.run_coroutine_threadsafe(self.stage_manager.shutdown(), main_loop)
                try:
                    future.result(timeout=10)  # Wait up to 10 seconds
                except Exception as e:
                    print(f"[Stage] Shutdown error: {e}")
                # Don't set to None to avoid triggering Python GC and shm.close()
                # Just mark as disconnected
                self._stage_disconnected = True
            self.configuration_check["stage"] = 0
            File("shared_memory", "Configuration_check", self.configuration_check).save()
            print("Stage Disconnected")

        if self.configuration.get("sensor", "") != "" and self.configuration_sensor == 0 and self.configuration_check.get(
            "sensor", -1) == 0 and (not hasattr(self, 'nir_manager') or self.nir_manager is None):
            # Connect sensor instance
            self.nir_configure = NIRConfiguration()
            self.nir_configure.driver_types = self.configuration["sensor"]
            laser = self.port.get("laser_gpib")
            detector = self.port.get("detector_gpib")
            
            # Handle detector configuration
            # detector_gpib should be a list or None
            if detector is None or detector == []:
                # Single mainframe mode (no separate detector)
                self.nir_configure.laser_slot = laser if laser else "GPIB0::20::INSTR"
                self.nir_configure.detector_slots = []
            elif isinstance(detector, list):
                # Filter out None values from detector list
                valid_detectors = [d for d in detector if d is not None and d != "None"]
                if len(valid_detectors) == 0:
                    # Empty list after filtering
                    self.nir_configure.laser_slot = laser if laser else "GPIB0::20::INSTR"
                    self.nir_configure.detector_slots = []
                else:
                    # Multi-mainframe mode
                    self.nir_configure.laser_slot = laser if laser else "GPIB0::20::INSTR"
                    self.nir_configure.detector_slots = valid_detectors
            else:
                # Old format compatibility
                self.nir_configure.laser_slot = laser if laser else "GPIB0::20::INSTR"
                self.nir_configure.detector_slots = []
            
            print(f'[NIR Config] LASER: {self.nir_configure.laser_slot} | DETECTOR: {self.nir_configure.detector_slots}')
            self.nir_manager = NIRManager(self.nir_configure)
            success_sensor = self.nir_manager.initialize()
            if success_sensor:
                self.configuration_sensor = 1
                self.configuration_check["sensor"] = 2
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()
                self.sensor_window = webview.create_window(
                    'Sensor Control',
                    f'http://{local_ip}:8001',
                    width=672 + web_w,
                    height=197 + web_h,
                    x=800, y=255,
                    resizable=True,
                    hidden=False
                )
            else:
                self.configuration_sensor = 0
                self.configuration_check["sensor"] = 1
                file = File(
                    "shared_memory", "Configuration_check", self.configuration_check
                )
                file.save()

        elif self.configuration["sensor"] == "" and self.configuration_sensor == 1:
            # Disconnect sensor constrol instance
            self.configuration_sensor = 0
            if self.sensor_window:
                self.sensor_window.destroy()
                self.sensor_window = None
            if self.nir_manager:
                self.nir_manager.disconnect()
                self.nir_manager = None
            self.configuration_check["sensor"] = 0
            File("shared_memory", "Configuration_check", self.configuration_check).save()
            print("Sensor Disconnected")

        if self.configuration_stage == 1:
            # Change positions using shared mem, if changed
            self.memory.reader_pos()
            if self.memory.x_pos != float(self.x_position_lb.get_text()):
                x_zero = self.zero_state.get("x")
                if x_zero is None:
                    x_zero = 0.0
                self.x_position_lb.set_text(str(round((self.memory.x_pos- x_zero), 3)))
            if self.memory.y_pos != float(self.y_position_lb.get_text()):
                y_zero = self.zero_state.get("y")
                if y_zero is None:
                    y_zero = 0.0
                self.y_position_lb.set_text(str(round((self.memory.y_pos - y_zero), 3)))
            if self.memory.z_pos != float(self.z_position_lb.get_text()):
                z_zero = self.zero_state.get("z")
                if z_zero is None:
                    z_zero = 0.0
                self.z_position_lb.set_text(str(round((self.memory.z_pos - z_zero), 3)))
            if self.memory.cp_pos != float(self.chip_position_lb.get_text()):
                self.chip_position_lb.set_text(str(self.memory.cp_pos))
            if self.memory.fr_pos != float(self.fiber_position_lb.get_text()):
                self.fiber_position_lb.set_text(str(45 - self.memory.fr_pos))

        if self.configuration_sensor == 1:
            # Use .get() so config-only dicts don't crash us
            sweep_flag = self.sweep.get("sweep", 0)
            if sweep_flag == 1 and self.sweep_count == 0:
                self.sweep_count = 1
                self.run_in_thread(self.laser_sweep)

            on_flag = self.sweep.get("on", self.past_laser_on)
            if on_flag != self.past_laser_on and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_laser_on = on_flag
                self.run_in_thread(self.laser_on)

            wvl_val = self.sweep.get("wvl", self.past_wvl)
            if wvl_val != self.past_wvl and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_wvl = wvl_val
                self.run_in_thread(self.set_wvl)

            power_val = self.sweep.get("power", self.past_power)
            if power_val != self.past_power and self.sweep_count == 0:
                self.sweep_count = 1
                self.past_power = power_val
                self.run_in_thread(self.set_power)


        if self.configuration_stage == 1 and self.configuration_sensor == 1:
            if self.auto_sweep == 1 and self.count == 0:
                self.lock_all(1)
                self.count = 1

                # Calculate progress config for auto sweep
                device_count = len(self.filter) if hasattr(self, 'filter') and self.filter else 0
                if device_count > 0:
                    estimated_total = self._estimate_total_time(device_count)
                    estimated_per_device = estimated_total / device_count
                    progress_config = {
                        'total_devices': device_count,
                        'estimated_total_time': estimated_total,
                        'estimated_per_device': estimated_per_device
                    }
                    self.busy_dialog(progress_config)
                else:
                    self.busy_dialog()

                self.task_start = 1
                if getattr(self, 'auto_sweep_type', 'Laser Sweep') == 'EO':
                    self.run_in_thread(self._safe_do_auto_eo_sweep)
                else:
                    self.run_in_thread(self.do_auto_sweep)

            elif self.auto_sweep == 0 and self.count == 1:
                self.lock_all(0)
                self.count = 0
                self.nir_manager.cancel_sweep()
                if self.fine_align != None:
                    self.fine_align.stop_alignment()

            # Safely handle ScanPos; it may be {} right after loading config
            move_flag = self.scanpos.get("move", 0)
            if move_flag == 1:
                x_val = self.scanpos.get("x")
                y_val = self.scanpos.get("y")
                if x_val != self.pre_x or y_val != self.pre_y:
                    self.run_in_thread(self.scan_move)
                    self.pre_x = x_val
                    self.pre_y = y_val

            if self.ch_count == 0:
                self.ch_count = 1
                if self.configuration.get("sensor") == "luna_controller":
                    pass
                else:
                    self.run_in_thread(self.update_ch)

            self.stop_task()

    def stop_task(self):
        # Called from idle() every loop
        if self._scan_done.value == -1:
            # Reset our internal flags
            self._scan_done.value = 0
            self.task_start = 0

            # Stop any area scan / fine align
            if self.area_sweep is not None:
                self.area_sweep.stop_sweep()
                self.area_sweep = None

            if self.fine_align is not None:
                self.fine_align.stop_alignment()
                self.fine_align = None

            # -------- MANUAL LASER SWEEP CANCEL --------
            if self.task_laser == 1:
                self.task_laser = 0
                try:
                    if self.nir_manager:
                        self.nir_manager.cancel_sweep()
                except Exception as e:
                    print(f"[StopTask] Error cancelling laser sweep: {e}")

                # Turn off bias SMU if it was active
                if self._bias_sweep_active:
                    try:
                        self._turn_off_bias()
                    except Exception as e:
                        print(f"[StopTask] Error turning off bias: {e}")

                try:
                    self.sweep["sweep"] = 0
                    file = File("shared_memory", "Sweep", self.sweep)
                    file.save()
                except Exception as e:
                    print(f"[StopTask] Error resetting Sweep flag: {e}")

            # -------- AUTO SWEEP CANCEL --------
            if self.auto_sweep == 1 and self.count == 1:
                self.auto_sweep = 0
                self.count = 0
                try:
                    file = File("shared_memory", "AutoSweep", 0)
                    file.save()
                    print("[StopTask] Reset AutoSweep flag -> 0")
                except Exception as e:
                    print(f"[StopTask] Error resetting AutoSweep flag: {e}")

                try:
                    if self.nir_manager:
                        self.nir_manager.cancel_sweep()
                except Exception as e:
                    print(f"[StopTask] Error cancelling auto sweep: {e}")

            # -------- UNLOCK STAGE UI --------
            self.lock_all(0)
            print("[StopTask] Cancel completed, UI unlocked")


    def update_ch(self):
        while True:
            try:
                if self.configuration.get("sensor") == "luna_controller":
                    time.sleep(10.0)
                    continue

                # Skip power reading if paused during fine_align/sweep
                if getattr(self, 'pause_power_reading', False):
                    time.sleep(1.0)
                    continue

                if self.configuration_sensor == 1 and self.slot_info is not None and self.nir_manager is not None:
                    # Batch read all channels first, then update UI together for sync display
                    readings = []
                    for idx, (mf, slot, head) in enumerate(self.slot_info):
                        try:
                            power = self.nir_manager.read_power(slot=slot, head=head, mf=mf)
                            readings.append((idx, str(round(power, 3))))
                        except Exception:
                            readings.append((idx, "N/A"))

                    # Update all channel labels at once
                    for i, text in readings:
                        if i < len(self.ch_vals):
                            self.ch_vals[i].set_text(text)
                else:
                    if getattr(self, "ch_vals", None):
                        for v in self.ch_vals:
                            v.set_text("N/A")

                time.sleep(0.3)

            except Exception as e:
                print(f"[UpdateCH] Error: {e}")
                time.sleep(0.3)

    def do_auto_sweep(self):
        device_count = len(self.filter)
        estimated_total_time = self._estimate_total_time(device_count)
        device_start_times = []

        print(f"Starting auto sweep of {device_count} devices (estimated {estimated_total_time:.0f}s total)")

        i = 0
        while i < device_count:
            print("It's " + str(i))
            if self.auto_sweep == 0:
                break

            device_start_time = time.time()
            device_start_times.append(device_start_time)
            device_num = i + 1

            key = list(self.filter.keys())
            x = float(self.filter[key[i]][0])
            y = float(self.filter[key[i]][1])

            # Update progress: Moving to device
            progress_percent = (i / device_count) * 100
            activity = f"Moving to Device {device_num}/{device_count}"
            self._write_progress_file(device_num, activity, progress_percent)
            print(f"Move to Device {device_num} [{x}, {y}]")

            # Respect per-axis locks for XY moves
            if not self.axis_locked["x"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            if not self.axis_locked["y"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))
            if self.auto_sweep == 0:
                break

            # Update progress: Fine alignment
            progress_percent = (i / device_count) * 100 + (20 / device_count)  # Add 20% for alignment
            activity = f"Device {device_num}/{device_count}: Fine alignment"
            self._write_progress_file(device_num, activity, progress_percent)

            self.onclick_fine_align()
            if self.auto_sweep == 0:
                break

            # Update progress: Spectral sweep
            progress_percent = (i / device_count) * 100 + (70 / device_count)  # Add 70% for sweep
            activity = f"Device {device_num}/{device_count}: Spectral sweep"
            self._write_progress_file(device_num, activity, progress_percent)

            device_name = self.devices[int(key[i])-1]
            session_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.laser_sweep(name=f"Auto_Sweep_Optical/{device_name}/spectral_sweep_Optical_{session_time}")

            # Update progress: Device completed
            progress_percent = ((i + 1) / device_count) * 100
            activity = f"Device {device_num}/{device_count}: Completed"
            self._write_progress_file(device_num, activity, progress_percent)

            file = File("shared_memory", "DeviceName", self.devices[int(key[i])-1], "DeviceNum", int(key[i]))  # potential index error
            file.save()

            # Calculate actual device time for learning
            device_time = time.time() - device_start_time
            print(f"Device {device_num} completed in {device_time:.1f}s")

            i += 1

        # Final completion
        self._write_progress_file(device_count, "All measurements completed", 100)

        with self._scan_done.get_lock():
            self._scan_done.value = 1
            self.task_start = 0

        # Destroy destination dir var after auto measuremenet is complete
        self.use_destination_dir = {}
        SharedMemory.update({"ExportRequest": {}})
        
        
        self.nir_manager.enable_laser(False)
        print("The Auto Sweep Is Finished")
        time.sleep(1)
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    # ------------------------------------------------------------------
    # EO Auto Sweep: fine align -> probe down -> EO sweep -> retract
    # ------------------------------------------------------------------
    # Default EO parameters (overridden by EO_Settings in shared_memory)
    EO_BIAS_VOLTAGE       = 0.8    # V – SMU bias voltage
    EO_STEP_DOWN_UM       = -10    # um – each descent step (negative = down)
    EO_FORCE_CONTACT_G    = 0.5    # g  – force change threshold to detect contact
    EO_MIN_CURRENT_UA     = 10.0   # uA – minimum current to consider "in contact"
    EO_CURRENT_STABLE_UA  = 3.0    # uA – current-change threshold for stability
    EO_STABLE_COUNT       = 3      # consecutive stable readings to stop
    EO_MAX_FORCE_G        = 50.0   # g  – absolute max force change safety limit
    EO_RETRACT_STEP_UM    = 50     # um – retract step size
    EO_RETRACT_FINAL_UM   = 200    # um – final extra retract after force returns to baseline
    EO_MAX_DESCENT_UM     = 5000   # um – max total descent before aborting (safety)
    EO_MAX_RETRACT_UM     = 5000   # um – max total retract distance (safety)

    def _load_eo_settings(self):
        """Load EO parameters from shared_memory, falling back to class defaults."""
        def _safe_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return float(default)

        def _safe_int(value, default):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return int(default)

        eo = SharedMemory.get("EO_Settings", {})
        if not isinstance(eo, dict):
            eo = {}
        self.EO_BIAS_VOLTAGE      = _safe_float(eo.get("bias_voltage"), self.__class__.EO_BIAS_VOLTAGE)
        self.EO_STEP_DOWN_UM      = -abs(_safe_float(eo.get("step_down_um"), abs(self.__class__.EO_STEP_DOWN_UM)))
        self.EO_FORCE_CONTACT_G   = _safe_float(eo.get("force_contact_g"), self.__class__.EO_FORCE_CONTACT_G)
        self.EO_MIN_CURRENT_UA    = _safe_float(eo.get("min_current_ua"), self.__class__.EO_MIN_CURRENT_UA)
        self.EO_CURRENT_STABLE_UA = _safe_float(eo.get("current_stable_ua"), self.__class__.EO_CURRENT_STABLE_UA)
        self.EO_STABLE_COUNT      = max(1, _safe_int(eo.get("stable_count"), self.__class__.EO_STABLE_COUNT))
        self.EO_MAX_FORCE_G       = _safe_float(eo.get("max_force_g"), self.__class__.EO_MAX_FORCE_G)
        self.EO_RETRACT_STEP_UM   = abs(_safe_float(eo.get("retract_step_um"), self.__class__.EO_RETRACT_STEP_UM))
        self.EO_RETRACT_FINAL_UM  = abs(_safe_float(eo.get("retract_final_um"), self.__class__.EO_RETRACT_FINAL_UM))
        self.EO_MAX_DESCENT_UM    = abs(_safe_float(eo.get("max_descent_um"), self.__class__.EO_MAX_DESCENT_UM))
        self.EO_MAX_RETRACT_UM    = abs(_safe_float(eo.get("max_retract_um"), self.__class__.EO_MAX_RETRACT_UM))
        print(f"[EO] Settings loaded: bias={self.EO_BIAS_VOLTAGE}V, step={self.EO_STEP_DOWN_UM}um, "
              f"force_contact={self.EO_FORCE_CONTACT_G}g, min_current={self.EO_MIN_CURRENT_UA}uA, "
              f"current_stable={self.EO_CURRENT_STABLE_UA}uA, stable_count={self.EO_STABLE_COUNT}, "
              f"max_force={self.EO_MAX_FORCE_G}g, retract_step={self.EO_RETRACT_STEP_UM}um, "
              f"retract_final={self.EO_RETRACT_FINAL_UM}um, max_descent={self.EO_MAX_DESCENT_UM}um, "
              f"max_retract={self.EO_MAX_RETRACT_UM}um")

    def _safe_do_auto_eo_sweep(self):
        """Run EO autosweep with top-level exception guard and cleanup."""
        try:
            self.do_auto_eo_sweep()
        except Exception as e:
            print(f"[EO] FATAL: Unhandled exception in EO auto sweep: {e}")
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass

            # Best-effort cleanup so UI does not remain stuck in running state.
            try:
                self._send_bias_command("off")
            except Exception:
                pass
            # Best-effort probe retract so probe is not left in contact
            try:
                print("[EO] FATAL cleanup: attempting emergency probe retract...")
                ok = self._send_motor_command("Z", self.EO_RETRACT_FINAL_UM)
                if ok:
                    print("[EO] FATAL cleanup: emergency retract succeeded")
                else:
                    print("[EO] FATAL cleanup: emergency retract failed — probe may still be in contact!")
            except Exception:
                print("[EO] FATAL cleanup: emergency retract exception — probe may still be in contact!")
            try:
                self._write_progress_file(0, f"ABORTED: EO exception ({e})", 0)
            except Exception:
                pass
            try:
                with self._scan_done.get_lock():
                    self._scan_done.value = 1
                    self.task_start = 0
            except Exception:
                pass
            try:
                self.use_destination_dir = {}
                SharedMemory.update({"ExportRequest": {}})
                self.nir_manager.enable_laser(False)
            except Exception:
                pass
            try:
                file = File("shared_memory", "AutoSweep", 0)
                file.save()
            except Exception:
                pass

    def do_auto_eo_sweep(self):
        """
        EO automated measurement per device:
        1. Fine align (optical)
        2. Turn on SMU voltage (0.8 V)
        3. Record baseline force (5 s average)
        4. Lower BSC203-Z in 10 um steps:
           - Once |force change| > 0.5g, check current (>10 uA)
           - Track current change; if < 3 uA for 3 consecutive readings -> stop
           - Safety: stop if |force change| > 50g
        5. Perform EO laser sweep (bias enabled)
        6. Turn off voltage
        7. Retract 50 um steps until |force change| < 0.5g of baseline
        8. Extra retract
        """
        # ---- Load EO settings from shared_memory ----
        self._load_eo_settings()

        # ---- Pre-flight check: Force sensor must be running ----
        data = SharedMemory.read({})
        fw = data.get("ForceWeight")
        if not fw or not isinstance(fw, dict):
            print("[EO] ERROR: Force sensor is not running! Please start Force before running EO Auto Sweep.")
            self._write_progress_file(0, "ABORTED: Force sensor not running", 0)
            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0
            file = File("shared_memory", "AutoSweep", 0)
            file.save()
            return

        device_count = len(self.filter)
        print(f"[EO Auto] Starting EO sweep of {device_count} devices")

        i = 0
        while i < device_count:
            if self.auto_sweep == 0:
                break

            device_num = i + 1
            device_start = time.time()
            key = list(self.filter.keys())
            x = float(self.filter[key[i]][0])
            y = float(self.filter[key[i]][1])
            device_name = self.devices[int(key[i]) - 1]

            # ---- 1. Move to device ----
            pct = (i / device_count) * 100
            self._write_progress_file(device_num, f"Moving to Device {device_num}/{device_count}", pct)
            print(f"[EO] Move to Device {device_num} [{x}, {y}]")
            if not self.axis_locked["x"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            if not self.axis_locked["y"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))
            if self.auto_sweep == 0:
                break

            # ---- 2. Fine alignment ----
            pct = (i / device_count) * 100 + (10 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: Fine alignment", pct)
            self.onclick_fine_align()
            if self.auto_sweep == 0:
                break

            # ---- 3. Turn on SMU voltage ----
            pct = (i / device_count) * 100 + (20 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: Setting bias {self.EO_BIAS_VOLTAGE}V", pct)
            bias_ok = self._send_bias_command("init", mode="V", value=self.EO_BIAS_VOLTAGE)
            if not bias_ok:
                print("[EO] ERROR: SMU bias command failed/timeout — skipping device")
                self._send_bias_command("off")
                pct = ((i + 1) / device_count) * 100
                self._write_progress_file(device_num, f"Device {device_num}: SKIPPED (SMU timeout)", pct)
                file = File("shared_memory", "DeviceName", device_name, "DeviceNum", int(key[i]))
                file.save()
                i += 1
                continue
            if self.auto_sweep == 0:
                self._send_bias_command("off")
                break

            # ---- 4. Record baseline force (5 s average) ----
            pct = (i / device_count) * 100 + (22 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: Recording baseline force", pct)
            print("[EO] Recording baseline force (5 s)...")
            time.sleep(1)  # Let force sensor settle
            baseline_force = self._average_force(duration=5.0)
            print(f"[EO] Baseline force: {baseline_force:.1f} g")

            # ---- 5. Descent loop ----
            prev_current_ua = None
            stable_count = 0
            contact_detected = False
            force_exceeded = False
            motor_failed = False
            total_descent_um = 0
            step_num = 0

            while self.auto_sweep != 0:
                step_num += 1
                pct = (i / device_count) * 100 + (25 / device_count)
                self._write_progress_file(
                    device_num,
                    f"Device {device_num}: Lowering probe (step {step_num}, {abs(total_descent_um)} um)",
                    pct
                )

                # Move Z down 10 um
                ok = self._send_motor_command("Z", self.EO_STEP_DOWN_UM)
                if not ok:
                    print("[EO] Motor move failed, aborting descent")
                    motor_failed = True
                    break
                total_descent_um += abs(self.EO_STEP_DOWN_UM)
                time.sleep(1.2)  # Wait >1s so force sensor (1 Hz) has fresh data

                # Safety: max descent distance
                if total_descent_um >= self.EO_MAX_DESCENT_UM:
                    print(f"[EO] SAFETY: Max descent {self.EO_MAX_DESCENT_UM} um reached without stable contact!")
                    force_exceeded = True
                    break

                # Check force (with freshness)
                current_force, force_fresh = self._read_force_weight()
                if not force_fresh:
                    print("[EO] WARNING: Force sensor data is stale — sensor may have crashed!")
                    force_exceeded = True  # Treat as safety event
                    break
                force_delta = current_force - baseline_force
                abs_delta = abs(force_delta)
                print(f"[EO] Step {step_num}: force={current_force:.1f}g (delta={force_delta:+.1f}g, |delta|={abs_delta:.1f}g)")

                # Safety: max force exceeded (either direction)
                if abs_delta > self.EO_MAX_FORCE_G:
                    print(f"[EO] SAFETY: |Force delta| {abs_delta:.1f}g > {self.EO_MAX_FORCE_G}g limit, stopping!")
                    force_exceeded = True
                    break

                # Check if we have contact (force change > threshold in either direction)
                if abs_delta >= self.EO_FORCE_CONTACT_G:
                    if not contact_detected:
                        print(f"[EO] Contact detected at step {step_num} (force delta={force_delta:.1f}g)")
                        contact_detected = True

                    # Read current
                    current_a = self._request_current_read("A")
                    if current_a is None:
                        print("[EO] Current read failed, retrying next step")
                        continue
                    current_ua = abs(current_a) * 1e6
                    print(f"[EO] Current: {current_ua:.2f} uA")

                    # Need minimum 10 uA
                    if current_ua < self.EO_MIN_CURRENT_UA:
                        print(f"[EO] Current {current_ua:.2f} uA < {self.EO_MIN_CURRENT_UA} uA, continuing descent")
                        prev_current_ua = current_ua
                        continue

                    # Check current stability
                    if prev_current_ua is not None:
                        current_change = abs(current_ua - prev_current_ua)
                        print(f"[EO] Current change: {current_change:.2f} uA (threshold={self.EO_CURRENT_STABLE_UA})")
                        if current_change < self.EO_CURRENT_STABLE_UA:
                            stable_count += 1
                            print(f"[EO] Stable count: {stable_count}/{self.EO_STABLE_COUNT}")
                            if stable_count >= self.EO_STABLE_COUNT:
                                print(f"[EO] Current stable for {self.EO_STABLE_COUNT} consecutive readings, stopping descent")
                                break
                        else:
                            stable_count = 0  # Reset if current changed significantly

                    prev_current_ua = current_ua

            if self.auto_sweep == 0:
                self._send_bias_command("off")
                break

            # Safety: if force exceeded limit, retract immediately and skip sweep
            if force_exceeded or motor_failed:
                reason = "force safety" if force_exceeded else "motor failure"
                print(f"[EO] SAFETY: {reason} — skipping sweep, retracting")
                self._send_bias_command("off")

                if motor_failed:
                    # BSC203 already dead — retract attempts would each timeout 65s
                    print("[EO] SAFETY: Motor already failed — skipping retract (probe may still be in contact!)")
                else:
                    retract_total = 0
                    consecutive_failures = 0
                    while self.auto_sweep != 0:
                        ok = self._send_motor_command("Z", self.EO_RETRACT_STEP_UM)
                        if not ok:
                            consecutive_failures += 1
                            print(f"[EO] Safety retract motor failure #{consecutive_failures}")
                            if consecutive_failures >= 2:
                                print("[EO] SAFETY: 2 consecutive motor failures during retract — giving up")
                                break
                            continue
                        consecutive_failures = 0
                        retract_total += self.EO_RETRACT_STEP_UM
                        if retract_total >= self.EO_MAX_RETRACT_UM:
                            print(f"[EO] Max retract {self.EO_MAX_RETRACT_UM} um reached")
                            break
                        time.sleep(1.2)  # Wait >1s so force sensor (1 Hz) has fresh data
                        current_force, _ = self._read_force_weight()
                        force_delta = current_force - baseline_force
                        if abs(force_delta) < self.EO_FORCE_CONTACT_G:
                            break
                    if self.auto_sweep != 0 and consecutive_failures < 2:
                        self._send_motor_command("Z", self.EO_RETRACT_FINAL_UM)

                pct = ((i + 1) / device_count) * 100
                self._write_progress_file(device_num, f"Device {device_num}: SKIPPED ({reason})", pct)
                file = File("shared_memory", "DeviceName", device_name, "DeviceNum", int(key[i]))
                file.save()
                i += 1
                continue

            # ---- 6. EO laser sweep (bias-enabled) ----
            pct = (i / device_count) * 100 + (50 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: EO spectral sweep", pct)
            print("[EO] Starting EO laser sweep...")

            session_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            sweep_name = f"Auto_Sweep_EO/{device_name}/spectral_sweep_EO_{session_time}"

            # Perform bias sweep using existing machinery
            bias_cfg = self.sweep.get("bias_voltage", {})
            bias_enabled = bias_cfg.get("enabled", False)
            if bias_enabled:
                self._do_bias_sweep(sweep_name, auto=1, bias_cfg=bias_cfg)
            else:
                # Even without explicit bias config, do a single sweep since SMU is already on
                self._do_single_sweep(sweep_name, auto=1, filename_prefix=f"spectral_sweep_EO")

            if self.auto_sweep == 0:
                self._send_bias_command("off")
                break

            # ---- 7. Turn off voltage ----
            pct = (i / device_count) * 100 + (80 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: Turning off bias", pct)
            self._send_bias_command("off")

            # ---- 8. Retract probe ----
            pct = (i / device_count) * 100 + (85 / device_count)
            self._write_progress_file(device_num, f"Device {device_num}: Retracting probe", pct)
            print("[EO] Retracting probe...")

            retract_total = 0
            consecutive_failures = 0
            while self.auto_sweep != 0:
                ok = self._send_motor_command("Z", self.EO_RETRACT_STEP_UM)
                if not ok:
                    consecutive_failures += 1
                    print(f"[EO] Retract motor failure #{consecutive_failures}")
                    if consecutive_failures >= 2:
                        print("[EO] 2 consecutive motor failures during retract — giving up")
                        break
                    continue
                consecutive_failures = 0
                retract_total += self.EO_RETRACT_STEP_UM
                if retract_total >= self.EO_MAX_RETRACT_UM:
                    print(f"[EO] Max retract {self.EO_MAX_RETRACT_UM} um reached, forcing final retract")
                    break
                time.sleep(1.2)  # Wait >1s so force sensor (1 Hz) has fresh data

                current_force, _ = self._read_force_weight()
                force_delta = current_force - baseline_force
                print(f"[EO] Retracting: force delta={force_delta:.1f}g (retracted {retract_total} um)")

                if abs(force_delta) < self.EO_FORCE_CONTACT_G:
                    print("[EO] Force returned to baseline range")
                    break

            # Final extra retract 200 um
            if self.auto_sweep != 0 and consecutive_failures < 2:
                print(f"[EO] Final retract {self.EO_RETRACT_FINAL_UM} um")
                self._send_motor_command("Z", self.EO_RETRACT_FINAL_UM)

            # ---- Done with this device ----
            pct = ((i + 1) / device_count) * 100
            self._write_progress_file(device_num, f"Device {device_num}/{device_count}: Completed", pct)

            file = File("shared_memory", "DeviceName", device_name, "DeviceNum", int(key[i]))
            file.save()

            device_time = time.time() - device_start
            print(f"[EO] Device {device_num} completed in {device_time:.1f}s")

            i += 1

        # ---- Finalize ----
        self._write_progress_file(device_count, "All EO measurements completed", 100)
        with self._scan_done.get_lock():
            self._scan_done.value = 1
            self.task_start = 0
        self.use_destination_dir = {}
        SharedMemory.update({"ExportRequest": {}})
        self.nir_manager.enable_laser(False)
        print("[EO] Auto EO Sweep Finished")
        time.sleep(1)
        file = File("shared_memory", "AutoSweep", 0)
        file.save()

    def set_axis_enabled(self, prefix: str, enabled: bool):
        getattr(self, f"{prefix}_left_btn").set_enabled(enabled)
        getattr(self, f"{prefix}_right_btn").set_enabled(enabled)
        getattr(self, f"{prefix}_input").set_enabled(enabled)

    def onchange_axis_lock(self, prefix: str, value):
        # remi CheckBox sends 1 for checked, 0 for unchecked
        self.axis_locked[prefix] = bool(value)
        self.set_axis_enabled(prefix, not self.axis_locked[prefix])
        print(f"[Axis Lock] {prefix} -> {'LOCKED' if self.axis_locked[prefix] else 'UNLOCKED'}")

    def lock_all(self, value, write_shared=True):
        enabled = value == 0

        # Mark that we are the source of this lock
        if write_shared:
            self._self_locking = (value != 0)
            # Notify other GUIs via shared_memory
            SharedMemory.update({"SweepLock": value})

        widgets_to_check = [self.stage_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()
            
            # keep global lock and per-axis lock checkboxes enabled
            if hasattr(widget, "variable_name"):
                vn = widget.variable_name
                if vn in ("lock_box", "stop_button") or (isinstance(vn, str) and vn.endswith("_lock")):
                    widget.set_enabled(True)
                    continue
                elif isinstance(widget, (Button, SpinBox, CheckBox, DropDown)):
                    widget.set_enabled(enabled)
            if isinstance(widget, (Button, SpinBox, CheckBox, DropDown)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

        # after UNLOCK, reapply per-axis lock disables
        if enabled:
            for pfx, is_locked in self.axis_locked.items():
                self.set_axis_enabled(pfx, not is_locked)

    def construct_ui(self):
        # -------- layout constants (positions/sizes only) --------
        LEFT_PANEL_W = 490  # wider left box so rows + Zero buttons fit cleanly
        LOCK_COL_LEFT = 18  # per-axis lock column (aligns with top lock icon)
        ICON_LEFT = 21      # big lock icon
        LABEL_LEFT = 42     # axis text column (left of readouts)
        POS_LEFT = 35       # position numeric readout (limit label uses this too)
        UNIT_LEFT = 150     # unit next to readout
        BTN_L_LEFT = 185    # left jog button
        SPIN_LEFT = 245     # step spinbox
        BTN_R_LEFT = 345    # right jog button
        ZERO_LEFT = 415     # Zero button
        # slightly larger vertical spacing so rows + "lim" line don't overlap
        ROW_TOPS = [75, 120, 165, 210, 255]
        ROW_H = 30

        RIGHT_START = LEFT_PANEL_W + 20  # right-hand panels start after wider box
        # ---------------------------------------------------------

        stage_control_container = StyledContainer(
            container=None, variable_name="stage_control_container",
            left=0, top=0, height=380, width=880  # bigger so nothing clips
        )

        xyz_container = StyledContainer(
            container=stage_control_container, variable_name="xyz_container",
            left=0, top=20, height=300, width=LEFT_PANEL_W
        )

        self.stop_btn = StyledButton(
            container=xyz_container, text="Stop", variable_name="stop_button", font_size=100,
            left=POS_LEFT, top=10, width=90, height=30,
            normal_color="#dc3545", press_color="#c82333"
        )

        self.lock_box = StyledCheckBox(
            container=xyz_container, variable_name="lock_box",
            left=POS_LEFT + 100, top=10, width=10, height=10, position="absolute"
        )

        StyledLabel(
            container=xyz_container, text="Lock", variable_name="lock_label",
            left=POS_LEFT + 130, top=17, width=80, height=50, font_size=100, color="#222"
        )

        # Big lock icon aligned with per-axis lock column
        StyledLabel(
            container=xyz_container, text="🔒", variable_name="per_axis_lock_icon",
            left=ICON_LEFT, top=48, width=5, height=5, font_size=130, color="#444"
        )

        self.absolute_movement_cb = StyledCheckBox(
            container=xyz_container,
            variable_name="absolute_movement_cb",
            left=POS_LEFT + 165,
            top=10, width=10, height=10, position="absolute"
        )
        StyledLabel(
            container=xyz_container,
            text="Absolute movement",
            variable_name="absolute_movement_label",
            left=POS_LEFT + 195,
            top=17, width=180, height=50, font_size=100, color="#222"
        )

        labels = ["X", "Y", "Z", "Chip", "Fiber"]
        left_arrows = ["⮜", "⮟", "Down", "⭮", "⭮"]
        right_arrows = ["⮞", "⮝", "Up", "⭯", "⭯"]
        var_prefixes = ["x", "y", "z", "chip", "fiber"]
        position_texts = ["0", "0", "0", "0", "0"]
        position_unit = ["um", "um", "um", "deg", "deg"]
        init_value = ["10.0", "10.0", "10.0", "0.1", "0.1"]

        for i in range(5):
            prefix = var_prefixes[i]
            top = ROW_TOPS[i]

            # per-axis lock checkbox (aligned with header icon)
            setattr(self, f"{prefix}_lock", StyledCheckBox(
                container=xyz_container, variable_name=f"{prefix}_lock",
                left=LOCK_COL_LEFT, top=top, width=12, height=12
            ))

            # axis label (left column)
            StyledLabel(
                container=xyz_container, text=labels[i], variable_name=f"{prefix}_label",
                left=LABEL_LEFT, top=top, width=51, height=ROW_H,
                font_size=100, color="#222", flex=True, bold=True,
                justify_content="center"
            )

            # position readout + unit (next column)
            setattr(self, f"{prefix}_position_lb", StyledLabel(
                container=xyz_container, text=position_texts[i], variable_name=f"{prefix}_position_lb",
                left=POS_LEFT + 50, top=top, width=70, height=ROW_H,
                font_size=100, color="#222", flex=True, bold=True,
                justify_content="left"
            ))
            # limit line, smaller and a bit higher so it doesn't collide with next row
            setattr(self, f"{prefix}_limit_lb", StyledLabel(
                container=xyz_container, text="lim: N/A", variable_name=f"{prefix}_limit_lb",
                left=POS_LEFT, top=top + 22, width=100, height=16,
                font_size=70, color="#666", flex=True, justify_content="right"
            ))
            setattr(self, f"{prefix}_position_unit", StyledLabel(
                container=xyz_container, text=position_unit[i], variable_name=f"{prefix}_position_unit",
                left=UNIT_LEFT, top=top, width=40, height=ROW_H,
                font_size=100, color="#222", flex=True, bold=True,
                justify_content="left"
            ))

            # per-axis buttons / spinbox
            if prefix in ["x", "y"]:
                max_val = 30000
            elif prefix == "z":
                max_val = 1000
            elif prefix == "chip":
                max_val = 360
            else:  # fiber tilt
                max_val = 45

            setattr(self, f"{prefix}_left_btn", StyledButton(
                container=xyz_container, text=left_arrows[i],
                variable_name=f"{prefix}_left_button", font_size=100,
                left=BTN_L_LEFT, top=top, width=50, height=ROW_H,
                normal_color="#007BFF", press_color="#0056B3"
            ))
            setattr(self, f"{prefix}_input", StyledSpinBox(
                container=xyz_container, variable_name=f"{prefix}_step",
                min_value=0, max_value=max_val, value=init_value[i], step=0.1,
                left=SPIN_LEFT, top=top, width=73, height=ROW_H, position="absolute"
            ))
            setattr(self, f"{prefix}_right_btn", StyledButton(
                container=xyz_container, text=right_arrows[i],
                variable_name=f"{prefix}_right_button", font_size=100,
                left=BTN_R_LEFT, top=top, width=50, height=ROW_H,
                normal_color="#007BFF", press_color="#0056B3"
            ))

            # Zero button
            if prefix in ["x", "y", "z"]:
                setattr(self, f"{prefix}_zero_btn", StyledButton(
                    container=xyz_container, text="Zero", variable_name=f"{prefix}_zero_button",
                    font_size=100, left=ZERO_LEFT, top=top, width=55, height=ROW_H,
                    normal_color="#6c757d", press_color="#5a6268"
                ))

        # ---- Right-hand panels ----
        limits_container = StyledContainer(
            container=stage_control_container, variable_name="limits_container",
            left=RIGHT_START, top=12, height=90, width=90, border=True
        )
        StyledLabel(
            container=limits_container, text="Home Lim", variable_name="limits_label",
            left=12, top=-12, width=66, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.limit_setting_btn = StyledButton(
            container=limits_container, text="Setting", variable_name="limit_setting_btn",
            font_size=100, left=5, top=10, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )
        self.home_btn = StyledButton(
            container=limits_container, text="Home", variable_name="home_btn",
            font_size=100, left=5, top=50, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )

        fine_align_container = StyledContainer(
            container=stage_control_container, variable_name="fine_align_container",
            left=RIGHT_START + 100, top=12, height=90, width=90, border=True
        )
        StyledLabel(
            container=fine_align_container, text="Fine Align", variable_name="fine_align_label",
            left=12.5, top=-12, width=65, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.fine_align_setting_btn = StyledButton(
            container=fine_align_container, text="Setting", variable_name="fine_align_setting_btn",
            font_size=100, left=5, top=10, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )
        self.start_btn = StyledButton(
            container=fine_align_container, text="Start", variable_name="start_button",
            font_size=100, left=5, top=50, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )

        area_scan_container = StyledContainer(
            container=stage_control_container, variable_name="area_scan_container",
            left=RIGHT_START + 200, top=12, height=90, width=90, border=True
        )
        StyledLabel(
            container=area_scan_container, text="Area Scan", variable_name="area_scan_label",
            left=13, top=-12, width=65, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        self.scan_setting_btn = StyledButton(
            container=area_scan_container, text="Setting", variable_name="area_scan_setting_btn",
            font_size=100, left=5, top=10, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )
        self.scan_btn = StyledButton(
            container=area_scan_container, text="Scan", variable_name="scan_button",
            font_size=100, left=5, top=50, width=80, height=30,
            normal_color="#007BFF", press_color="#0056B3"
        )

        move_container = StyledContainer(
            container=stage_control_container, variable_name="move_container",
            left=RIGHT_START, top=122, height=88, width=200, border=True
        )
        StyledLabel(
            container=move_container, text="Move To Device", variable_name="move_label",
            left=50, top=-12, width=100, height=20, font_size=100, color="#444",
            position="absolute", flex=True, on_line=True, justify_content="center"
        )
        StyledLabel(
            container=move_container, text="Move to", variable_name="move_to_label",
            left=0, top=15, width=60, height=28, font_size=100, color="#222",
            position="absolute", flex=True, justify_content="right"
        )
        self.move_dd = StyledDropDown(
            container=move_container, variable_name="move_to_dd", text="N/A",
            left=75, top=15, height=28, width=115
        )
        self.move_dd.attributes["title"] = "N/A"
        self.load_btn = StyledButton(
            container=move_container, text="Load", variable_name="load_button",
            font_size=100, left=10, top=50, width=85, height=28,
            normal_color="#007BFF", press_color="#0056B3"
        )
        self.move_btn = StyledButton(
            container=move_container, text="Move", variable_name="move_button",
            font_size=100, left=105, top=50, width=85, height=28,
            normal_color="#007BFF", press_color="#0056B3"
        )

        # ---- Stacked channel tables (CH1–CH4 on first row, CH5–CH8 on second row) ----
        # ---- 2×4 channel grid (CH1–CH8), each with header + value ----
        TABLE_W = 360
        COLS = 4
        COL_W = TABLE_W // COLS

        HEADER_H = 22   # height of "CHx" header row
        DATA_H   = 22   # height of value row
        V_PAD    = 4    # vertical gap between channels

        # total height = 2 rows of (header+data+gap)
        TABLE_H = 2 * (HEADER_H + DATA_H + V_PAD)

        table_container = StyledContainer(
            container=stage_control_container,
            variable_name="coordinate_container",
            left=RIGHT_START,
            top=232,
            height=TABLE_H + 4,  # a little padding
            width=TABLE_W,
            border=True
        )

        self.ch_vals = []  # flat list: index 0 -> CH1, 1 -> CH2, ... 7 -> CH8

        for ch_idx in range(1, 9):
            # row: 0 for CH1–CH4, 1 for CH5–CH8
            row = 0 if ch_idx <= 4 else 1
            # col: 0..3
            col = (ch_idx - 1) % 4

            left = col * COL_W

            # vertical block for this channel (header + value)
            header_top = row * (HEADER_H + DATA_H + V_PAD)
            data_top   = header_top + HEADER_H

            # ---- header label: "CH1", "CH2", ... ----
            hdr = StyledLabel(
                container=table_container,
                text=f"CH{ch_idx}",
                variable_name=f"ch{ch_idx}_header",
                left=left,
                top=header_top,
                width=COL_W-1,
                height=HEADER_H,
                font_size=100,
                color="#222",
                flex=True,
                bold=True,
                justify_content="center"
            )
            # light header background so it still looks like a table
            hdr.style["background-color"] = "#eae8df"
            hdr.style["border-right"] = "1px solid #d0cec4"
            hdr.style["border-bottom"] = "1px solid #d0cec4"

            # ---- value label: "N/A" (this is what you'll update later) ----
            val = StyledLabel(
                container=table_container,
                text="N/A",
                variable_name=f"ch{ch_idx}_val",
                left=left,
                top=data_top,
                width=COL_W-1,
                height=DATA_H,
                font_size=100,
                color="#222",
                flex=True,
                justify_content="center"
            )
            val.style["border-right"] = "1px solid #d0cec4"

            self.ch_vals.append(val)


        # --------------------------------------------- #

        # ---- wire-ups (unchanged from your code) ----
        self.stop_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_stop))
        self.home_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_home))
        self.start_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fine_align))
        self.scan_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_area_scan))
        self.x_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_x_left))
        self.x_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_x_right))
        self.y_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_y_left))
        self.y_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_y_right))
        self.z_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_z_left))
        self.z_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_z_right))
        self.chip_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_chip_left))
        self.chip_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_chip_right))
        self.fiber_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fiber_left))
        self.fiber_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fiber_right))
        self.x_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "x"))
        self.y_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "y"))
        self.z_zero_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_zero, "z"))
        self.load_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_load))
        self.move_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move))
        self.limit_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_limit_setting_btn))
        self.fine_align_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_fine_align_setting_btn))
        self.scan_setting_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_area_scan_setting_btn))
        self.lock_box.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_lock_box, emitter, value))
        self.move_dd.onchange.do(lambda emitter, value: self.run_in_thread(self.onchange_move_dd, emitter, value))
        self.x_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "x", v))
        self.y_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "y", v))
        self.z_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "z", v))
        self.chip_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "chip", v))
        self.fiber_lock.onchange.do(lambda e, v: self.run_in_thread(self.onchange_axis_lock, "fiber", v))
        self.absolute_movement_cb.onchange.do(
            lambda emitter, value: self.run_in_thread(
                self.onclick_change_absolute_movement, emitter, value
            )
        )
        self.move_btn.set_enabled(False)
        self.stage_control_container = stage_control_container
        return stage_control_container



    def onclick_stop(self):
        print("Stopping stage control")

        asyncio.run(self.stage_manager.emergency_stop())
        
        # Cancel any active movements like area scan
        if hasattr(self, "_scan_cancel") and self._scan_cancel:
            self._scan_cancel.set()
        for _, motor_class in self.stage_manager.motors.items():
            motor_class._stop_requested = True
        if self.nir_manager and self.task_laser:
            self.nir_manager.cancel_sweep()
        if self.area_sweep:
            self.area_sweep.stop_sweep()
        if self.fine_align:
            self.fine_align.stop_alignment()    
        
        # Reset state
        with self._scan_done.get_lock():
            self._scan_done.value = -1
        self.task_start = 0
        self.lock_all(0)
        self.lock_box.set_value(0)
        print("Stop")

    def onclick_home(self):
        # Non homable case
        stage_d = self.stage_manager.config.driver_types[AxisType.X] 
        if (stage_d == "Corvus_controller"):
            pslims = self.stage_manager.config.position_limits
            self.x_limit_lb.set_text(
                f"lim: {round(pslims[AxisType.X][0], 2)}~{round(pslims[AxisType.X][1], 2)}"
                )
            self.y_limit_lb.set_text(
                f"lim: {round(pslims[AxisType.Y][0], 2)}~{round(pslims[AxisType.Y][1], 2)}"
                )
            self.z_limit_lb.set_text(
                f"lim: {round(pslims[AxisType.Z][0], 2)}~{round(pslims[AxisType.Z][1], 2)}"
                )
            return None
        elif (stage_d == "scylla_controller"):
            """
            # Axis 1 [50000.000, -50000.000] 
            # Axis 2 [24000.000, -24000.000] 
            # Axis 3 [12000.000, -12000.000] 
            # Axis 4 [56.577, -56.577]  fa
            # Axis 5 [360.000, -360.000] CR   
            """
            self.x_limit_lb.set_text(
                f"lim: {round(-50000.000, 2)}~{round(50000.000, 2)}"
                )
            self.y_limit_lb.set_text(
                f"lim: {round(-24000.000, 2)}~{round(24000.000, 2)}"
                )
            self.z_limit_lb.set_text(
                f"lim: {round(-12000.000, 2)}~{round(12000.000, 2)}"
                )
            self.chip_limit_lb.set_text(
                f"lim: {round(-360.000, 2)}~{round(360.000, 2)}"
                )
            self.fiber_limit_lb.set_text(
                f"lim: {round(-56.577, 2)}~{round(56.577, 2)}"
                )
        print("Start Home")
        self.busy_dialog()
        self.lock_all(1)
        self.stop_btn.set_enabled(True)
        self.task_start = 1
        home = self.limit
        x = home["x"]
        y = home["y"]
        z = home["z"]
        chip = home["chip"]
        fiber = home["fiber"]

        for _, motor_class in self.stage_manager.motors.items():
            motor_class._stop_requested = False
        
        # Progress bar update
        p_bar = [val for val in [x, y, z, chip, fiber] if val == "Yes"]
        total_steps = len(p_bar)
        current_step = 0
        
        def update_progress(activity):
            percent = (current_step / total_steps) * 100.0 if total_steps > 0 else 0.0
            write_progress_file(
                activity=activity,
                percent=percent,
                n=current_step,
                total=total_steps
            )

        if x == "Yes":
            update_progress("Homing X axis")
            xok, xlim = asyncio.run(self.stage_manager.home_limits(AxisType.X))
            if xok:
                self.x_limit_lb.set_text(f"lim: {round(xlim[0], 2)}~{round(xlim[1], 2)}")
            current_step += 1
            update_progress("Homed X axis")
        if y == "Yes":
            update_progress("Homing Y axis")
            yok, ylim = asyncio.run(self.stage_manager.home_limits(AxisType.Y))
            if yok:
                self.y_limit_lb.set_text(f"lim: {round(ylim[0], 2)}~{round(ylim[1], 2)}")
            current_step += 1
            update_progress("Homed Y axis")
        if z == "Yes":
            update_progress("Homing Z axis")
            zok, zlim = asyncio.run(self.stage_manager.home_limits(AxisType.Z))
            if zok:
                self.z_limit_lb.set_text(f"lim: {round(zlim[0], 2)}~{round(zlim[1], 2)}")
            current_step += 1
            update_progress("Homed Z axis")
        if chip == "Yes":
            update_progress("Homing Chip Rotation axis")
            cok, clim = asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_CHIP))
            if cok:
                self.chip_limit_lb.set_text(f"lim: {round(clim[0], 2)}~{3.6}")
            current_step += 1
            update_progress("Homed Chip Rotation axis")
        if fiber == "Yes":
            update_progress("Homing Fiber Rotation axis")
            fok, flim = asyncio.run(self.stage_manager.home_limits(AxisType.ROTATION_FIBER))
            if fok:
                self.fiber_limit_lb.set_text(f"lim: 0~45")
            current_step += 1
            update_progress("Homed Fiber Rotation axis")

        with self._scan_done.get_lock():
            self._scan_done.value = 1
            self.task_start = 0
            self.lock_all(0)
        print("Home Finished")

        # Apply initial position settings
        if self.apply_initial_positions:
            init_fa = self.initial_positions.get("fa", None)
            if init_fa is not None:
                _ = asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, init_fa, False))
            self.apply_initial_positions = False  # Apply only once

    def onclick_fine_align(self):
        print("Start Fine Align")
        manual = (self.auto_sweep == 0)

        try:
            # Pause power reading to avoid GPIB conflicts
            self.pause_power_reading = True
            # Wait for update_ch to finish its current GPIB read cycle
            time.sleep(0.5)
            
            if manual:
                # Show dialog
                self.busy_dialog()
                self.task_start = 1
                self.lock_all(1)
                t0 = time.time()
                
                print("[Info] Starting fine alignment process...")

            # Build config
            config = FineAlignConfiguration()
            config.scan_window = self.fine_a.get("window_size", 10.0) or 10.0
            config.step_size = self.fine_a.get("step_size", 1.0) or 1.0
            config.min_gradient_ss = self.fine_a.get("min_gradient_ss", 0.1) or 0.1
            config.gradient_iters = self.fine_a.get("max_iters", 10) or 10.0
            config.primary_detector = self.fine_a.get("detector", "ch1") or "ch1"
            config.ref_wl = self.fine_a.get("ref_wl", 1550.0) or 1550.0
            config.threshold = self.fine_a.get("threshold", -10.0)
            config.secondary_wl = self.fine_a.get("secondary_wl", 1540.0)
            config.secondary_loss = self.fine_a.get("secondary_loss", -50.0)
            if self.slot_info is not None:
                s_temp = self.slot_info
            else:
                s_temp = [[0, 1, 0]]  # Assume only primary slot
            config.slots = s_temp

            # Create aligner
            self.fine_align = FineAlign(
                config.to_dict(),
                self.stage_manager,
                self.nir_manager,
                progress=self._fa_progress,
                cancel_event=self._scan_cancel,
                debug=getattr(self,"debug",False),
                )

            # (Optional) tell the dialog we started
            try:
                self._write_progress_file(0, "Fine alignment: starting…", 1.0)
            except Exception:
                pass

            # Wait until FA finishes
            asyncio.run(self.fine_align.begin_fine_align())

            # (Optional) final update
            try:
                self._write_progress_file(0, "Fine alignment: completed", 100.0)
            except Exception:
                pass

        except Exception as e:
            print(f"[FineAlign] Error: {e}")
            # show error state to the dialog
            try:
                self._write_progress_file(0, f"Fine alignment: error ({e})", 100.0)
            except Exception:
                pass
        finally:
            # Resume power reading
            self.pause_power_reading = False
            
            if manual:
                # Prevent instant flicker: ensure the dialog stayed visible a moment
                min_visible = 1.5  # seconds (increased from 0.8)
                try:
                    elapsed = time.time() - t0
                except Exception:
                    elapsed = min_visible
                if elapsed < min_visible:
                    time.sleep(min_visible - elapsed)

                # now mark done and unlock UI
                with self._scan_done.get_lock():
                    self._scan_done.value = 1
                    self.task_start = 0
                self.lock_all(0)

            self.fine_align = None
            print("Fine Align Finished")

    def _calculate_sweep_time(self):
        """Calculate estimated sweep time based on configuration"""
        try:
            start_nm = self.sweep.get("start", 1500.0)
            end_nm = self.sweep.get("end", 1580.0)
            step_nm = self.sweep.get("step", 0.001)

            # Calculate number of data points
            data_points = abs(end_nm - start_nm) / step_nm

            # Use provided formula: 11 seconds per 20k data points
            sweep_time = (data_points / 20000) * 11
            return max(sweep_time, 5)  # Minimum 5 seconds
        except:
            return 30  # Default fallback

    def _calculate_area_sweep_time(self):
        """Calculate estimated area sweep time based on configuration"""
        try:
            x_size = self.area_s.get("x_size", 20.0)
            x_step = self.area_s.get("x_step", 1.0)
            y_size = self.area_s.get("y_size", 20.0)
            y_step = self.area_s.get("y_step", 1.0)

            # Calculate grid points
            x_points = int(x_size / x_step)
            y_points = int(y_size / y_step)
            total_points = x_points * y_points

            # Estimate ~0.5 seconds per point
            return max(total_points * 0.5, 10)  # Minimum 10 seconds
        except:
            return 30  # Default fallback

    def _calculate_fine_align_time(self):
        """Calculate estimated fine alignment time based on configuration"""
        try:
            timeout = self.fine_a.get("timeout_s", 30)
            return min(timeout, 180)  # Cap at 3 minutes
        except:
            return 45  # Default fallback

    def _estimate_total_time(self, device_count):
        """Estimate total time for all devices"""
        sweep_time = self._calculate_sweep_time()
        area_time = self._calculate_area_sweep_time()
        align_time = self._calculate_fine_align_time()
        overhead_time = 10  # Movement and overhead per device

        time_per_device = sweep_time + area_time + align_time + overhead_time
        return device_count * time_per_device
    
    def _write_progress_file(self, current_device, activity, progress_percent):
        """Atomically write progress for the PyQt dialog to read (thread-safe on Windows)."""
        from pathlib import Path
        import os, json, time

        try:
            # Import the same path and lock the dialog reads
            from lib_gui import PROGRESS_PATH, _progress_lock
        except Exception:
            # Fallback to a sane default if import fails
            PROGRESS_PATH = Path(__file__).resolve().parent / "database" / "progress.json"
            _progress_lock = threading.Lock()

        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)

        progress_data = {
            "current_device": int(current_device),
            "activity": str(activity),
            "progress_percent": float(progress_percent),
            "timestamp": time.time(),
        }

        tmp_path = PROGRESS_PATH.with_suffix(PROGRESS_PATH.suffix + ".tmp")

        # Use the shared global lock for consistency with readers
        with _progress_lock:
            # Small retry loop in case another PROCESS has the file open
            for attempt in range(5):
                try:
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(progress_data, f)
                        f.flush()
                        os.fsync(f.fileno())  # ensure contents hit disk where possible

                    os.replace(tmp_path, PROGRESS_PATH)  # atomic swap (if allowed by OS)
                    break
                except PermissionError as e:
                    # If some other process (e.g., the PyQt dialog) briefly locks the file,
                    # wait a bit and retry instead of crashing the autosweep thread.
                    if attempt == 4:
                        print(f"[Progress] Failed to update progress file after retries: {e}")
                    else:
                        time.sleep(0.05)  # 50 ms backoff and try again
                except Exception as e:
                    # Any other I/O error, just log and bail out of the loop
                    print(f"[Progress] Unexpected error writing progress file: {e}")
                    break

    def _fa_progress(self, percent: float, msg: str):
        """Write fine alignment progress helper"""
        try:
            self._write_progress_file(0, msg, float(percent))
        except Exception as e:
            print(f"[FA Progress] Error writing progress: {e}")
            pass
            
    def _as_progress(self, percent: float, msg: str):
        """Write Area scan progress helper"""
        try:
            self._write_progress_file(0, msg, float(percent))
        except Exception:
            pass
        
    def busy_dialog(self, progress_config=None):
        self._scan_done = Value(c_int, 0)
        self._scan_cancel = Event()
        
        from lib_gui import run_busy_dialog
        
        self._busy_proc = Process(
            target=run_busy_dialog,
            args=(self._scan_done, self._scan_cancel, progress_config),
            daemon=True
        )
        self._busy_proc.start()

    def onclick_area_scan(self):
        print("Start Scan")
        self.busy_dialog()
        self.task_start = 1
        self.lock_all(1)
        if self.area_s["plot"] == "New":
            self.stage_x_pos = self.memory.x_pos
            self.stage_y_pos = self.memory.y_pos
            config = AreaSweepConfiguration()
            config.x_size = int(self.area_s.get("x_size", "x_size") or "x_size")
            config.x_step = int(self.area_s.get("x_step", "x_step") or "x_step")
            config.y_size = int(self.area_s.get("y_size", "y_size") or "y_size")
            config.y_step = int(self.area_s.get("y_step", "y_step") or "y_step")
            config.primary_detector = str(self.area_s.get("primary_detector", "ch1") or "ch1")
            if self.slot_info is not None:
                s_temp = self.slot_info
            else:
                s_temp = [[0, 1, 0]]  # Assume only primary slot
            config.slots = s_temp

            self.area_sweep = AreaSweep(
                config, self.stage_manager, self.nir_manager,
                progress=self._as_progress,
                cancel_event=self._scan_cancel
            )
            self.data = asyncio.run(self.area_sweep.begin_sweep())
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            
            # Create window for plotting
            diagram = plot(
                filename="heat_map",
                fileTime=fileTime,
                user=self.user,
                project=self.project,
                data=self.data,
                xticks=int(self.area_s["x_step"]),
                yticks=None,
                pos_i = [self.stage_x_pos, self.stage_y_pos]
            )

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0
                self.lock_all(0)

            p = Process(target=diagram.heat_map)
            p.start()
            p.join()
            self.area_sweep = None
            print("Done Scan")

        elif self.area_s["plot"] == "Previous":
            fileTime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            diagram = plot(
                filename="heat_map",
                fileTime=fileTime,
                user=self.user,
                project=self.project,
                data=self.data)

            with self._scan_done.get_lock():
                self._scan_done.value = 1
                self.task_start = 0

            p = Process(target=diagram.heat_map)
            p.start()
            p.join()

        print("Done Scan")

    def onclick_change_absolute_movement(self, emitter=None, value=None):
        """
        Change between relative and absolute movement.
        """
        is_absolute_mode = bool(value)
        self.use_relative_movement = not is_absolute_mode

        # Handle locking of Z, CHIP, and FIBER axes
        for axis in ("z", "chip", "fiber"):
            lock_widget = getattr(self, f"{axis}_lock", None)

            if is_absolute_mode:
                # lock if not already locked
                if not self.axis_locked.get(axis, False):
                    self.axis_locked[axis] = True
                    self._absolute_locked_axes[axis] = True
                    if lock_widget is not None:
                        lock_widget.set_value(1)
                    self.set_axis_enabled(axis, False)
            else:
                # only unlock what we locked ourselves
                if self._absolute_locked_axes.get(axis, False):
                    self.axis_locked[axis] = False
                    self._absolute_locked_axes[axis] = False
                    if lock_widget is not None:
                        lock_widget.set_value(0)
                    self.set_axis_enabled(axis, True)


    def onclick_x_left(self):
        if self.axis_locked["x"]:
            print("[Axis Locked] X move ignored");
            return
        value = float(self.x_input.get_value())
        print(f"X Left {value} um")
        if not self.use_relative_movement:
            # Absolute mode: left goes to negative position
            value = -abs(value)
        else:
            # Relative mode: left moves negative
            value = -value
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.X, value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_x_right(self):
        if self.axis_locked["x"]:
            print("[Axis Locked] X move ignored");
            return
        value = float(self.x_input.get_value())
        print(f"X Right {value} um")
        if not self.use_relative_movement:
            # Absolute mode: right goes to positive position
            value = abs(value)
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.X, value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_y_left(self):
        if self.axis_locked["y"]:
            print("[Axis Locked] Y move ignored");
            return
        value = float(self.y_input.get_value())
        print(f"Y Left {value} um")
        if not self.use_relative_movement:
            # Absolute mode: left goes to negative position
            value = -abs(value)
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_y_right(self):
        if self.axis_locked["y"]:
            print("[Axis Locked] Y move ignored");
            return
        value = float(self.y_input.get_value())
        print(f"Y Right {value} um")
        if not self.use_relative_movement:
            # Absolute mode: right goes to positive position
            value = abs(value)
        else:
            # Relative mode: right moves negative (direction reversed)
            value = -value
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.Y, value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_z_left(self):
        if self.axis_locked["z"]:
            print("[Axis Locked] Z move ignored");
            return
        value = float(self.z_input.get_value())
        print(f"Z Down {value} um")
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, -value, True))
        self.lock_all(0, write_shared=False)

    def onclick_z_right(self):
        if self.axis_locked["z"]:
            print("[Axis Locked] Z move ignored");
            return
        value = float(self.z_input.get_value())
        print(f"Z Up {value} um")
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.Z, value, True))
        self.lock_all(0, write_shared=False)

    def onclick_chip_left(self):
        if self.axis_locked["chip"]:
            print("[Axis Locked] Chip move ignored");
            return
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CW {value} deg")
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, -value, True))
        self.lock_all(0, write_shared=False)

    def onclick_chip_right(self):
        if self.axis_locked["chip"]:
            print("[Axis Locked] Chip move ignored");
            return
        value = float(self.chip_input.get_value())
        print(f"Chip Turn CCW {value} deg")
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_CHIP, value, True))
        self.lock_all(0, write_shared=False)

    def onclick_fiber_left(self):
        if self.axis_locked["fiber"]:
            print("[Axis Locked] Fiber move ignored");
            return
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CW {value} deg")
        if not self.use_relative_movement:
            value = -value  # Fixes (-)abs movement issue
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, -value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_fiber_right(self):
        if self.axis_locked["fiber"]:
            print("[Axis Locked] Fiber move ignored");
            return
        value = float(self.fiber_input.get_value())
        print(f"Fiber Turn CCW {value} deg")
        self.lock_all(1, write_shared=False)
        asyncio.run(self.stage_manager.move_axis(AxisType.ROTATION_FIBER, value, self.use_relative_movement))
        self.lock_all(0, write_shared=False)

    def onclick_load(self):
        self.gds = lib_coordinates.coordinates(("./res/" + FILENAME), read_file=False,
                                               name="./database/coordinates.json")
        self.number = self.gds.listdeviceparam("number")
        self.coordinate = self.gds.listdeviceparam("coordinate")
        self.polarization = self.gds.listdeviceparam("polarization")
        self.wavelength = self.gds.listdeviceparam("wavelength")
        self.type = self.gds.listdeviceparam("type")
        self.devices = [f"{name} ({num})" for name, num in zip(self.gds.listdeviceparam("devicename"), self.number)]

        self.move_dd.empty()
        self.move_dd.append(self.devices)
        self.move_dd.attributes["title"] = self.devices[0]
        file = File("shared_memory", "DeviceName", self.devices[0])
        file.save()
        print(self.devices)
        if not self.move_dd.get_value() == "N/A":
            self.move_btn.set_enabled(True)

    def onclick_zero(self, prefix: str):
        try:
            if getattr(self, "axis_locked", {}).get(prefix, False) or prefix in ["chip", "fiber"]:
                # print(f"[Zero] Axis '{prefix}' is locked; ignoring zero request.")
                return

            # Optional: briefly lock the UI so users don't double-click
            self.lock_all(1)

            # Map UI prefix -> StageManager axis enum
            memory_map = {
                "x": self.memory.x_pos,
                "y": self.memory.y_pos,
                "z": self.memory.z_pos,
            }
            lims_map = {
                "x": self.configure.position_limits[AxisType.X],
                "y": self.configure.position_limits[AxisType.Y],
                "z": self.configure.position_limits[AxisType.Z]
            }
            pos = memory_map.get(prefix)
            if self.zero_state.get(prefix) is None:
                self.zero_state[prefix] = pos

                # Alter text box
                box_widg = getattr(self, f'{prefix}_zero_btn')
                box_widg.normal_color = "#942eb4"
                
                # Alter position label
                pos_attr = f'{prefix}_position_lb'
                pos_widg = getattr(self, pos_attr)
                pos_widg.set_text(str(0))

                # If on zero, retrieve and alter ficticous limits
                lim = lims_map.get(prefix)
                if lim is None:
                    return
                label_attr = f'{prefix}_limit_lb'
                label_widg = getattr(self, label_attr)
                txt = f"lim: {round((lim[0] - pos), 2)}~{round((lim[1] - pos), 2)}"
                label_widg.set_text(txt)

            else:
                self.zero_state[prefix] = None
                
                # Alter text box
                box_widg = getattr(self, f'{prefix}_zero_btn')
                box_widg.normal_color = "#6c757d"
 
                # Reassign actual position to label
                pos_attr = f'{prefix}_position_lb'
                pos_widg = getattr(self, pos_attr)
                pos_widg.set_text(f'{round(pos, 3)}')

                # If not on zero, retrieve and alter ficticous limits
                lim = lims_map.get(prefix)
                if lim is None:
                    return
                label_attr = f'{prefix}_limit_lb'
                label_widg = getattr(self, label_attr)
                txt = f"lim: {round((lim[0]), 2)}~{round((lim[1]), 2)}"
                label_widg.set_text(txt)


        except Exception as e:
            print(f"[Zero] Error handling zero for '{prefix}': {e}")
        
        finally:
            # Always re-enable the UI
            with self._scan_done.get_lock():
                self._scan_done.value = 1       # only after begin_fine_align() returns
                self.task_start = 0
            self.lock_all(0)

    def onclick_move(self):
        selected_device = self.move_dd.get_value()
        print(f"Selected device: {selected_device}")

        try:
            index = self.devices.index(selected_device)
        except ValueError:
            print(f"[Error] Device '{selected_device}' not found in device list.")
            return

        try:
            device_coord = self.coordinate[index]
            x = float(device_coord[0])
            y = float(device_coord[1])
            print(f"Moving to coordinate: X={x}, Y={y}")

            if not self.axis_locked["x"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.X, x, False))
            if not self.axis_locked["y"]:
                asyncio.run(self.stage_manager.move_axis(AxisType.Y, y, False))

            file = File("shared_memory", "DeviceName", selected_device, "DeviceNum", index + 1)
            file.save()

            print(f"Successfully moved to device {selected_device}")
        except Exception as e:
            print(f"[Error] Failed to move to device {selected_device}: {e}")

    def onchange_lock_box(self, emitter, value):
        # Locking applications except stop button
        enabled = value == 0
        widgets_to_check = [self.stage_control_container]
        while widgets_to_check:
            widget = widgets_to_check.pop()

            if hasattr(widget, "variable_name"):
                vn = widget.variable_name
                case1 = vn in ("lock_box", "stop_button")
                case2 = (isinstance(vn, str) and vn.endswith("_lock"))
                if case1 or case2:
                    widget.set_enabled(True)
                    continue
            
            if isinstance(widget, (Button, DropDown, SpinBox)):
                widget.set_enabled(enabled)

            if hasattr(widget, "children"):
                widgets_to_check.extend(widget.children.values())

            if self.move_dd.get_value() != "N/A" and enabled is True:
                self.move_btn.set_enabled(True)
            else:
                self.move_btn.set_enabled(False)

        # after UNLOCK, reapply per-axis lock disables
        if enabled:
            for pfx, is_locked in self.axis_locked.items():
                self.set_axis_enabled(pfx, not is_locked)

        print("Unlocked" if enabled else "Locked")

    def onchange_move_dd(self, emitter, value):
        self.move_dd.attributes["title"] = value

    def onclick_limit_setting_btn(self):
        # local_ip = get_local_ip()
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7002",
            width=222 + web_w,
            height=266 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_fine_align_setting_btn(self):
        # local_ip = get_local_ip()
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=262 + web_w,
            height=426 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def onclick_area_scan_setting_btn(self):
        # local_ip = get_local_ip()
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7004",
            width=352 + web_w,
            height=316 + web_h,
            resizable=True,
            on_top=True,
            hidden=False
        )

    def execute_command(self, path=COMMAND_PATH):
        stage = 0
        record = 0
        new_command = {}

        try:
            data = read_command_file()
            command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
            return

        for key, val in command.items():
            if key.startswith("stage_control") and record == 0:
                stage = 1
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("fa_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "stage_x_step":
                self.x_input.set_value(str(val))
            elif key == "stage_y_step":
                self.y_input.set_value(str(val))
            elif key == "stage_z_step":
                self.z_input.set_value(str(val))
            elif key == "stage_chip_step":
                self.chip_input.set_value(str(val))
            elif key == "stage_fiber_step":
                self.fiber_input.set_value(str(val))

            elif key == "stage_x" and val == "left":
                self.onclick_x_left()
            elif key == "stage_y" and val == "left":
                self.onclick_y_left()
            elif key == "stage_z" and val == "left":
                self.onclick_z_left()
            elif key == "stage_chip" and val == "left":
                self.onclick_chip_left()
            elif key == "stage_fiber" and val == "left":
                self.onclick_fiber_left()

            elif key == "stage_x" and val == "right":
                self.onclick_x_right()
            elif key == "stage_y" and val == "right":
                self.onclick_y_right()
            elif key == "stage_z" and val == "right":
                self.onclick_z_right()
            elif key == "stage_chip" and val == "right":
                self.onclick_chip_right()
            elif key == "stage_fiber" and val == "right":
                self.onclick_fiber_right()

            elif key == "stage_x_left":
                self.x_input.set_value(str(val))
                self.onclick_x_left()
            elif key == "stage_y_left":
                self.y_input.set_value(str(val))
                self.onclick_y_left()
            elif key == "stage_z_left":
                self.z_input.set_value(str(val))
                self.onclick_z_left()
            elif key == "stage_chip_left":
                self.chip_input.set_value(str(val))
                self.onclick_chip_left()
            elif key == "stage_fiber_left":
                self.fiber_input.set_value(str(val))
                self.onclick_fiber_left()

            elif key == "stage_stop":
                self.onclick_stop()
            elif key == "stage_load":
                self.onclick_load()
            elif key == "stage_home":
                self.onclick_home()
            elif key == "stage_start":
                self.onclick_fine_align()
            elif key == "stage_scan":
                self.onclick_area_scan()
            elif key == "stage_move":
                self.onclick_move()
            elif key == "stage_lock":
                self.lock_box.set_value(1)
                self.onchange_lock_box(val, 1)
            elif key == "stage_unlock":
                self.lock_box.set_value(0)
                self.onchange_lock_box(val, 0)
            elif key == "stage_device":
                length = len(self.devices)
                if val > length:
                    val = length
                elif val < 1:
                    val = 1
                device = self.devices[int(val - 1)]
                self.move_dd.set_value(device)

        if stage == 1:
            file = File("command", "command", new_command)
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
    start(stage_control,
          address='0.0.0.0', port=8000,
          start_browser=False,
          multiple_instance=False)


def disable_scroll():
    try:
        webview.windows[0].evaluate_js("""
            document.documentElement.style.overflow = 'hidden';
            document.body.style.overflow = 'hidden';
        """)
    except Exception as e:
        print("JS Wrong", e)


if __name__ == '__main__':
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    threading.Thread(target=main_loop.run_forever, daemon=True).start()

    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # local_ip = get_local_ip()
    local_ip = '127.0.0.1'

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7002",
        width=222,
        height=266,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7003",
        width=222,
        height=236,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        "Setting",
        f"http://{local_ip}:7004",
        width=222,
        height=266,
        resizable=True,
        on_top=True,
        hidden=True
    )

    webview.create_window(
        'Stage Control',
        f'http://{local_ip}:8000',
        width=1302 + web_w, height=537 + web_h,
        x=700, y=465,
        resizable=True,
        hidden=True
    )
    webview.start(func=disable_scroll)
