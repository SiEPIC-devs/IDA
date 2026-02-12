from GUI.lib_gui import *
from remi import start, App
import serial.tools.list_ports
import webview
import threading
import os
import pyvisa
import re
import time

"""
Scan all visa resources and refresh the drop down.
This calls the ResourceManager so I've hosted the 
subprocess on the clicking of the button found in

"GUI\main_instruments_gui.py"

I was a little concerned about the case where Users
do not click confirm, so I've added that functionality
when a user e"x"its.

Cameron Basara, 2025
"""

command_path = os.path.join("database", "command.json")

class connect_config(App):
    def __init__(self, *args, **kwargs):
        self.stage_dd = None
        self.tec_dd = None
        self.smu_dd = None
        
        # NIR Configuration widgets
        self.laser_gpib_dd = None
        self.detector_gpib_dd = None  # Optional - None means single mainframe
        
        self.confirm_btn = None

        self._last_resources = []
        self._resource_map = {}   # display_label -> actual_resource_string
        
        # Performance optimization
        self._last_scan_time = 0
        self._scan_interval = 2.0  # Scan every 2 seconds instead of every idle call
        self._resource_manager = None  # Cached ResourceManager instance
        self._scanning_enabled = False  # Only scan when UI is visible
        
        # Load default port configuration
        self._default_ports = {
            "stage": "ASRL7::INSTR",
            "tec": "GPIB0::7::INSTR",
            "smu": "GPIB0::26::INSTR",
            "laser_gpib": "GPIB0::20::INSTR",
            "detector_gpib": ["USB0::0x0957::0x3718::MY48102149::INSTR"]
        }
        self._load_port_config()

        if "editing_mode" not in kwargs:
            super(connect_config, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ------------------ REMI lifecycle ------------------

    def main(self):
        # Do NOT auto-enable VISA scanning here — the hidden webview connects
        # at startup and would put GPIB instruments into REMOTE mode.
        # Scanning is enabled explicitly via enable_scanning() when the user
        # clicks "Configure VISA" in main_instruments_gui.
        return self.construct_ui()
    
    def enable_scanning(self):
        """Call this to start VISA resource scanning (e.g. when the user opens the config window)."""
        self._scanning_enabled = True
    
    def disable_scanning(self):
        """Stop VISA resource scanning and release the ResourceManager."""
        self._scanning_enabled = False
        if self._resource_manager:
            try:
                self._resource_manager.close()
            except Exception:
                pass
            self._resource_manager = None
    
    def _load_port_config(self):
        """Load port configuration from shared_memory.json"""
        data = SharedMemory.read({})
        port_config = data.get("Port", {})
        if port_config:
            self._default_ports.update(port_config)

    def idle(self):
        """Periodic hardware rescan (throttled for performance)."""
        try:
            # Only scan VISA resources when explicitly enabled (user opened the config window)
            if not self._scanning_enabled:
                return

            current_time = time.time()
            
            # Throttle scanning: only scan every _scan_interval seconds
            if current_time - self._last_scan_time < self._scan_interval:
                return
            
            self._last_scan_time = current_time
            
            resources, mapping = self._scan_resources()
            need_refresh = (
                resources != self._last_resources
                or self.stage_dd is None
                or self.tec_dd is None
                or self.smu_dd is None
                or self.laser_gpib_dd is None
                or self.detector_gpib_dd is None
            )

            if need_refresh:
                self._last_resources = resources
                self._resource_map = mapping

                if self.stage_dd:
                    self._refresh_dropdown(self.stage_dd, resources, self._default_ports.get("stage"))
                if self.tec_dd:
                    self._refresh_dropdown(self.tec_dd, resources, self._default_ports.get("tec"))
                if self.smu_dd:
                    self._refresh_dropdown(self.smu_dd, resources, self._default_ports.get("smu"))
                if self.laser_gpib_dd:
                    self._refresh_dropdown(self.laser_gpib_dd, resources, self._default_ports.get("laser_gpib"))
                if self.detector_gpib_dd:
                    self._refresh_detector_dropdown(self.detector_gpib_dd, resources, self._default_ports.get("detector_gpib"))

        except Exception as e:
            print("[Connect Config][idle] Error:", e)
    
    # ------------------ UI construction ------------------

    def construct_ui(self):
        container = StyledContainer(
            variable_name="connect_config_setting_container",
            left=0, top=0, height=280, width=200  # Increased height for SMU + NIR controls
        )

        # ---- Stage ----
        StyledLabel(
            container=container,
            text="Stage",
            variable_name="stage",
            left=0, top=10, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.stage_dd = StyledDropDown(
            container=container,
            variable_name="stage_dd",
            text="N/A",
            left=70, top=10, width=100, height=25,
            position="absolute",
        )


        # ---- TEC ----
        StyledLabel(
            container=container,
            text="TEC",
            variable_name="tec",
            left=0, top=45, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.tec_dd = StyledDropDown(
            container=container,
            variable_name="tec_dd",
            text="N/A",
            left=70, top=45, width=100, height=25,
            position="absolute",
        )

        # ---- SMU ----
        StyledLabel(
            container=container,
            text="SMU",
            variable_name="smu",
            left=0, top=80, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.smu_dd = StyledDropDown(
            container=container,
            variable_name="smu_dd",
            text="N/A",
            left=70, top=80, width=100, height=25,
            position="absolute",
        )

        # ---- Laser GPIB ----
        StyledLabel(
            container=container,
            text="Laser",
            variable_name="laser_gpib_label",
            left=0, top=115, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.laser_gpib_dd = StyledDropDown(
            container=container,
            variable_name="laser_gpib_dd",
            text="N/A",
            left=70, top=115, width=100, height=25,
            position="absolute",
        )

        # ---- Detector GPIB (Optional) ----
        StyledLabel(
            container=container,
            text="Detector",
            variable_name="detector_gpib_label",
            left=0, top=150, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.detector_gpib_dd = StyledDropDown(
            container=container,
            variable_name="detector_gpib_dd",
            text="None",
            left=70, top=150, width=100, height=25,
            position="absolute",
        )

        # ---- Confirm ----
        self.confirm_btn = StyledButton(
            container=container,
            text="Confirm",
            variable_name="confirm_btn",
            left=100, top=237, height=25, width=70,  # Moved down for SMU control
            font_size=90,
        )

        self.confirm_btn.do_onclick(
            lambda *_: self._run_in_thread(self.onclick_confirm)
        )

        # ---- Scan VISA button (user-initiated scan only) ----
        self.scan_btn = StyledButton(
            container=container,
            text="Scan VISA",
            variable_name="scan_btn",
            left=20, top=237, height=25, width=70,
            font_size=90,
        )
        self.scan_btn.do_onclick(
            lambda *_: self.enable_scanning()
        )

        return container

    # ------------------ Helpers ------------------

    def _run_in_thread(self, target, *args):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()

    def _scan_resources(self):
        resources = []
        mapping = {}

        try:
            # Reuse ResourceManager to avoid repeated initialization overhead
            if self._resource_manager is None:
                self._resource_manager = pyvisa.ResourceManager()
            
            visa_resources = self._resource_manager.list_resources()

            for r in visa_resources:
                if r not in mapping.values():
                    resources.append(r)
                    mapping[r] = r

        except Exception as e:
            print("[Connect Config][_scan_resources] VISA scan error:", e)
            # Reset resource manager on error
            if self._resource_manager:
                try:
                    self._resource_manager.close()
                except:
                    pass
                self._resource_manager = None

        # Remove duplicates
        resources = list(set(resources))

        if not resources:
            resources = ["N/A"]
            mapping["N/A"] = None

        return resources, mapping

    def _refresh_dropdown(self, dropdown, items, default_value=None):
        if dropdown is None:
            return

        dropdown.empty()

        if not items:
            dropdown.append("N/A")
            dropdown.set_value("N/A")
            return

        # Prioritize default value by putting it first if it exists
        sorted_items = []
        
        if default_value and default_value in items:
            # Put default value first
            sorted_items.append(default_value)
            # Add remaining items in sorted order
            remaining_items = [item for item in items if item != default_value]
            sorted_items.extend(self._smart_sort_resources(remaining_items))
        else:
            # No default or default not found, just sort normally
            sorted_items = self._smart_sort_resources(items)
        
        # Add all items to dropdown
        for item in sorted_items:
            dropdown.append(item)
        
        # Set the first item as selected (which will be default if it exists)
        dropdown.set_value(sorted_items[0])
    
    def _smart_sort_resources(self, resources):
        """Smart sort: numeric sort for ASRL/COM, alphabetic for others"""
        import re
        
        def resource_sort_key(resource):
            """Sort key that handles numeric values in resource names"""
            # Extract numbers from ASRL or COM resources
            match = re.match(r'(ASRL|COM)(\d+)', resource)
            if match:
                prefix = match.group(1)
                number = int(match.group(2))
                return (0, prefix, number, resource)  # ASRL/COM resources first, sorted by number
            return (1, resource, 0, resource)  # Other resources second, sorted alphabetically
        
        return sorted(resources, key=resource_sort_key)

    def _refresh_detector_dropdown(self, dropdown, items, default_value=None):
        """Special refresh for detector dropdown that includes 'None' option."""
        if dropdown is None:
            return

        dropdown.empty()
        dropdown.append("None")  # Option for single mainframe mode
        
        # Prioritize default value by putting it first after "None"
        sorted_items = []
        
        # Handle default_value which might be a list
        default_str = None
        if default_value:
            if isinstance(default_value, list) and len(default_value) > 0:
                default_str = default_value[0]
            elif isinstance(default_value, str):
                default_str = default_value
        
        if items:
            if default_str and default_str in items:
                # Put default value first
                sorted_items.append(default_str)
                # Add remaining items in sorted order
                remaining_items = [item for item in items if item != default_str and item != "N/A"]
                sorted_items.extend(self._smart_sort_resources(remaining_items))
            else:
                # No default or default not found, just sort normally
                sorted_items = self._smart_sort_resources([item for item in items if item != "N/A"])
        
        # Add sorted items to dropdown
        for item in sorted_items:
            dropdown.append(item)
        
        # Set default selection
        if default_str and default_str in sorted_items:
            dropdown.set_value(default_str)
        else:
            dropdown.set_value("None")  # Default to single mainframe

    # ------------------ Confirm logic ------------------

    def onclick_confirm(self):
        global SHOULD_EXIT

        try:
            # Stage resource - convert COM format to VISA format if needed
            stage_resource = self.stage_dd.get_value()
            if stage_resource == "N/A":
                stage_resource = None
            elif stage_resource and stage_resource.startswith("COM"):
                # Convert COM format to VISA format (COM7 -> ASRL7::INSTR)
                com_num = stage_resource.replace("COM", "")
                stage_resource = f"ASRL{com_num}::INSTR"
                print(f"[Connect Config] Converted stage port to VISA format: {stage_resource}")

            # TEC resource
            tec_resource = self.tec_dd.get_value()
            if tec_resource == "N/A":
                tec_resource = None

            # SMU resource
            smu_resource = self.smu_dd.get_value()
            if smu_resource == "N/A":
                smu_resource = None

            # Laser GPIB resource
            laser_resource = self.laser_gpib_dd.get_value()
            if laser_resource == "N/A":
                laser_resource = None

            # Detector GPIB resource (optional)
            detector_resource = self.detector_gpib_dd.get_value()
            if detector_resource == "None" or detector_resource == "N/A":
                detector_resource = None

            config = {
                "stage": stage_resource,
                "tec": tec_resource,
                "smu": smu_resource,
                "laser_gpib": laser_resource,
                "detector_gpib": [detector_resource] if detector_resource else [],
            }

            file = File("shared_memory", "Port", config)
            file.save()
            print("[Connect Config] Saved Port config:", config)

        except Exception as e:
            print("[Connect Config][onclick_confirm] Error:", e)


# =============================================================================
#                MAIN LAUNCHER (REMI + WEBVIEW)
# =============================================================================

def run_remi():
    start(
        connect_config,
        address='0.0.0.0',
        port=7005,
        multiple_instance=False,
        enable_file_cache=False,
        start_browser=False
    )

if __name__ == '__main__':
    # Start REMI server in background thread
    threading.Thread(target=run_remi, daemon=True).start()
    
    # Give server time to start
    time.sleep(0.5)
    
    # Create hidden window (will be shown when user clicks Configure VISA button)
    local_ip = "127.0.0.1"
    webview.create_window(
        "Connection Config",
        f"http://{local_ip}:7005",
        width=223 + web_w,
        height=336 + web_h,
        resizable=True,
        on_top=True,
        hidden=True
    )
    
    webview.start()