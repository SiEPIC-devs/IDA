import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from pymodbus.client import ModbusSerialClient


# ---------------------------
# Device register map (based on your module)
# ---------------------------
REG = {
    "CH1_WEIGHT_32": 0x0000,  # 0/1
    "CH2_WEIGHT_32": 0x0002,  # 2/3

    "CH1_ZERO_CAL":  40,      # write 1
    "CH2_ZERO_CAL":  50,      # write 1

    "CH1_ZERO_EN":   44,
    "CH1_FILT":      45,
    "CH1_CREEP":     46,
    "CH1_DYN":       47,

    "CH2_ZERO_EN":   54,
    "CH2_FILT":      55,
    "CH2_CREEP":     56,
    "CH2_DYN":       57,

    # 10-point calibration
    "CH1_NPT_COUNT": 182,     # write N (10)
    "CH1_P1":        183,     # p1..p10 = 183..192
    "CH2_NPT_COUNT": 193,     # write N (10)
    "CH2_P1":        194,     # p1..p10 = 194..203
}

def u16_to_s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v

def combine_u32_from_regs(hi: int, lo: int) -> int:
    return ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)

def combine_s32_from_regs(hi: int, lo: int) -> int:
    u = combine_u32_from_regs(hi, lo)
    return u - 0x100000000 if (u & 0x80000000) else u

def safe_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except Exception:
        return default

def safe_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s)
    except Exception:
        return default


class CalGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RS485 Multi-Point Calibration GUI")
        self.geometry("980x640")

        self.client: ModbusSerialClient | None = None
        self.polling = False
        self.poll_thread = None
        self.calib_point_count = 10  # Default to 10 points

        style = ttk.Style()
        style.theme_use("clam")

        default_font = ("TkDefaultFont", 12)
        text_font = ("TkDefaultFont", 12)
        
        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("TEntry", font=default_font)
        style.configure("TCombobox", font=default_font)
        style.configure("TSpinbox", font=default_font)
        style.configure("TLabelframe", font=default_font)
        style.configure("TLabelframe.Label", font=default_font)

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = 8

        # Top: connection
        frm_conn = ttk.LabelFrame(self, text="Connection")
        frm_conn.pack(fill="x", padx=pad, pady=pad)

        self.port_var = tk.StringVar(value="COM4")
        self.baud_var = tk.StringVar(value="115200")
        self.parity_var = tk.StringVar(value="N")
        self.stopbits_var = tk.StringVar(value="1")
        self.bytesize_var = tk.StringVar(value="8")
        self.timeout_var = tk.StringVar(value="0.3")

        row = 0
        ttk.Label(frm_conn, text="COM Port").grid(row=row, column=0, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.port_var, width=12).grid(row=row, column=1, padx=pad, pady=pad)
        ttk.Label(frm_conn, text="Baud").grid(row=row, column=2, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.baud_var, width=10).grid(row=row, column=3, padx=pad, pady=pad)

        ttk.Label(frm_conn, text="Parity (N/E/O)").grid(row=row, column=4, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.parity_var, width=5).grid(row=row, column=5, padx=pad, pady=pad)

        ttk.Label(frm_conn, text="Stopbits").grid(row=row, column=6, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.stopbits_var, width=5).grid(row=row, column=7, padx=pad, pady=pad)

        row = 1
        ttk.Label(frm_conn, text="Bytesize").grid(row=row, column=0, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.bytesize_var, width=12).grid(row=row, column=1, padx=pad, pady=pad)
        ttk.Label(frm_conn, text="Timeout(s)").grid(row=row, column=2, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_conn, textvariable=self.timeout_var, width=10).grid(row=row, column=3, padx=pad, pady=pad)

        self.btn_connect = ttk.Button(frm_conn, text="Connect", command=self.on_connect)
        self.btn_connect.grid(row=0, column=8, rowspan=2, padx=pad, pady=pad, sticky="ns")

        self.conn_status = tk.StringVar(value="Disconnected")
        ttk.Label(frm_conn, textvariable=self.conn_status).grid(row=0, column=9, rowspan=2, padx=pad, pady=pad, sticky="w")

        # Middle: device and live read
        frm_live = ttk.LabelFrame(self, text="Device / Live Read")
        frm_live.pack(fill="x", padx=pad, pady=pad)

        self.device_id_var = tk.StringVar(value="1")
        self.channel_var = tk.StringVar(value="CH1")

        # scale: how you encode weight for calibration registers
        # recommend 0.1g => multiply grams by 10
        self.unit_scale_var = tk.StringVar(value="10")  # grams -> raw integer
        self.point_count_var = tk.StringVar(value="10")  # Number of calibration points

        ttk.Label(frm_live, text="Device ID").grid(row=0, column=0, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_live, textvariable=self.device_id_var, width=8).grid(row=0, column=1, padx=pad, pady=pad)

        ttk.Label(frm_live, text="Channel").grid(row=0, column=2, padx=pad, pady=pad, sticky="w")
        ttk.Combobox(frm_live, textvariable=self.channel_var, values=["CH1", "CH2"], width=8, state="readonly")\
            .grid(row=0, column=3, padx=pad, pady=pad)

        ttk.Label(frm_live, text="Cal weight scale (grams * scale -> int)").grid(row=0, column=4, padx=pad, pady=pad, sticky="w")
        ttk.Entry(frm_live, textvariable=self.unit_scale_var, width=10).grid(row=0, column=5, padx=pad, pady=pad)

        ttk.Label(frm_live, text="Point count").grid(row=0, column=6, padx=pad, pady=pad, sticky="w")
        frm_point = ttk.Frame(frm_live)
        frm_point.grid(row=0, column=7, padx=pad, pady=pad)
        ttk.Spinbox(frm_point, from_=3, to=10, textvariable=self.point_count_var, width=5, 
                    command=self._on_point_count_changed).pack(side="left")
        ttk.Button(frm_point, text="Apply", command=self._on_point_count_changed).pack(side="left", padx=2)

        self.live_ch1 = tk.StringVar(value="CH1: --")
        self.live_ch2 = tk.StringVar(value="CH2: --")
        ttk.Label(frm_live, textvariable=self.live_ch1, font=("Consolas", 16)).grid(row=1, column=0, columnspan=3, padx=pad, pady=pad, sticky="w")
        ttk.Label(frm_live, textvariable=self.live_ch2, font=("Consolas", 16)).grid(row=1, column=3, columnspan=3, padx=pad, pady=pad, sticky="w")

        self.btn_poll = ttk.Button(frm_live, text="Start Live Poll", command=self.toggle_poll)
        self.btn_poll.grid(row=0, column=6, rowspan=2, padx=pad, pady=pad, sticky="ns")

        # Calibration controls
        frm_cal = ttk.LabelFrame(self, text="Calibration Controls")
        frm_cal.pack(fill="both", expand=True, padx=pad, pady=pad)

        # left: actions
        frm_actions = ttk.Frame(frm_cal)
        frm_actions.pack(side="left", fill="y", padx=pad, pady=pad)

        ttk.Button(frm_actions, text="(Optional) Disable auto adjust for selected CH",
                   command=self.disable_auto_adjust).pack(fill="x", pady=4)

        ttk.Button(frm_actions, text="Zero Cal (selected CH)",
                   command=self.zero_cal_selected).pack(fill="x", pady=4)

        ttk.Separator(frm_actions, orient="horizontal").pack(fill="x", pady=8)

        ttk.Button(frm_actions, text="Set N-point mode (write N)",
                   command=self.set_npt_mode).pack(fill="x", pady=4)

        ttk.Button(frm_actions, text="Write Point i (selected row)",
                   command=self.write_selected_point).pack(fill="x", pady=4)

        ttk.Button(frm_actions, text="Write ALL points (top->bottom)",
                   command=self.write_all_points).pack(fill="x", pady=4)

        ttk.Separator(frm_actions, orient="horizontal").pack(fill="x", pady=8)

        ttk.Button(frm_actions, text="Quick Fill (focus 600g)",
                   command=self.quick_fill_600g).pack(fill="x", pady=4)

        ttk.Button(frm_actions, text="Clear points",
                   command=self.clear_points).pack(fill="x", pady=4)

        ttk.Label(frm_actions, text="How to use:\n1) Empty load -> Zero Cal\n2) Set N-point mode\n3) For each point: place weight, wait stable, write point\n4) Verify around 600g",
                  justify="left").pack(fill="x", pady=10)

        # right: table of points
        frm_table = ttk.Frame(frm_cal)
        frm_table.pack(side="left", fill="both", expand=True, padx=pad, pady=pad)

        cols = ("idx", "grams", "raw_to_write", "status")
        self.tree = ttk.Treeview(frm_table, columns=cols, show="headings", height=18)
        for c, w in [("idx", 60), ("grams", 140), ("raw_to_write", 160), ("status", 420)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)

        self._refresh_tree_rows()

        # Setup editing
        self.tree.bind("<Double-1>", self._on_treeview_double_click)
        self.edit_entry = None
        self.edit_item = None
        self.edit_col = None

        # bottom log
        frm_log = ttk.LabelFrame(self, text="Log")
        frm_log.pack(fill="both", expand=False, padx=pad, pady=pad)
        self.log = tk.Text(frm_log, height=8)
        self.log.pack(fill="both", expand=True)

    # ---------------- Modbus helpers ----------------
    def logln(self, s: str):
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def _on_treeview_double_click(self, event):
        """Handle double-click on Treeview to edit grams column"""
        item = self.tree.selection()
        if not item:
            return
        
        item = item[0]
        col = self.tree.identify_column(event.x)
        
        # Only allow editing "grams" column (column 2, index 1)
        if col != "#2":
            return
        
        # Get cell value and position
        vals = self.tree.item(item, "values")
        cell_value = str(vals[1])
        
        # Get cell bounding box
        bbox = self.tree.bbox(item, col)
        if not bbox:
            return
        
        # Close any existing edit
        self._close_edit_entry()
        
        # Create Entry widget
        self.edit_entry = tk.Entry(self.tree, justify="left")
        self.edit_entry.insert(0, cell_value)
        self.edit_entry.select_range(0, tk.END)
        
        # Place Entry on top of cell
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        self.edit_entry.focus()
        
        self.edit_item = item
        self.edit_col = col
        
        # Bind keys
        self.edit_entry.bind("<Return>", lambda e: self._save_edit_entry())
        self.edit_entry.bind("<Escape>", lambda e: self._close_edit_entry())
        self.edit_entry.bind("<FocusOut>", lambda e: self._save_edit_entry())

    def _save_edit_entry(self):
        """Save edited value back to Treeview"""
        if self.edit_entry is None or self.edit_item is None:
            return
        
        new_value = self.edit_entry.get().strip()
        vals = list(self.tree.item(self.edit_item, "values"))
        
        # Update grams column (index 1)
        vals[1] = new_value
        vals[3] = "Not set"  # Reset status
        
        self.tree.item(self.edit_item, values=tuple(vals))
        self._close_edit_entry()

    def _close_edit_entry(self):
        """Close and destroy edit Entry widget"""
        if self.edit_entry is not None:
            self.edit_entry.destroy()
            self.edit_entry = None
            self.edit_item = None
            self.edit_col = None

    def ensure_client(self) -> bool:
        if self.client is None:
            messagebox.showerror("Error", "Not connected")
            return False
        return True

    def dev_id(self) -> int:
        return safe_int(self.device_id_var.get().strip(), 1)

    def cal_scale(self) -> int:
        s = safe_int(self.unit_scale_var.get().strip(), 10)
        return max(1, s)

    def selected_channel(self) -> str:
        return self.channel_var.get().strip().upper()

    def get_point_count(self) -> int:
        n = safe_int(self.point_count_var.get().strip(), 10)
        return max(3, min(10, n))  # Limit to 3-10

    def _refresh_tree_rows(self):
        """Clear and rebuild tree rows based on current point count"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        count = self.get_point_count()
        for i in range(1, count + 1):
            self.tree.insert("", "end", values=(i, "", "", "Not set"))

    def _on_point_count_changed(self):
        """Handle point count change"""
        self.calib_point_count = self.get_point_count()
        self._refresh_tree_rows()
        self.logln(f"Calibration points changed to {self.calib_point_count}")

    def reg_write_u16(self, reg_addr: int, value: int) -> bool:
        rr = self.client.write_register(reg_addr, value & 0xFFFF, device_id=self.dev_id())
        if rr.isError():
            self.logln(f"WRITE FAIL: dev={self.dev_id()} reg={reg_addr} val={value}")
            return False
        return True

    def reg_read_u16s(self, reg_addr: int, count: int):
        rr = self.client.read_holding_registers(reg_addr,count=4,device_id=1)
        if rr.isError():
            return None
        return rr.registers

    # ---------------- UI actions ----------------
    def on_connect(self):
        if self.client is not None:
            # disconnect
            self.stop_poll()
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
            self.conn_status.set("Disconnected")
            self.btn_connect.config(text="Connect")
            self.logln("Disconnected.")
            return

        port = self.port_var.get().strip()
        baud = safe_int(self.baud_var.get().strip(), 9600)
        parity = self.parity_var.get().strip().upper() or "N"
        stopbits = safe_int(self.stopbits_var.get().strip(), 1)
        bytesize = safe_int(self.bytesize_var.get().strip(), 8)
        timeout = safe_float(self.timeout_var.get().strip(), 0.3)

        self.client = ModbusSerialClient(
            port=port,
            baudrate=baud,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout,
        )
        ok = self.client.connect()
        if not ok:
            self.client = None
            messagebox.showerror("Connect failed", f"Cannot open {port}")
            return

        self.conn_status.set(f"Connected: {port} @ {baud} {parity}{stopbits}")
        self.btn_connect.config(text="Disconnect")
        self.logln(f"Connected: {port} @ {baud} {parity}{stopbits}")

    def toggle_poll(self):
        if not self.ensure_client():
            return
        if self.polling:
            self.stop_poll()
        else:
            self.start_poll()

    def start_poll(self):
        self.polling = True
        self.btn_poll.config(text="Stop Live Poll")
        self.poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.poll_thread.start()
        self.logln("Live polling started.")

    def stop_poll(self):
        self.polling = False
        self.btn_poll.config(text="Start Live Poll")
        self.logln("Live polling stopped.")

    def _poll_loop(self):
        while self.polling and self.client is not None:
            regs = self.reg_read_u16s(REG["CH1_WEIGHT_32"], 4)
            if regs is None:
                self.live_ch1.set("CH1: -- (read error)")
                self.live_ch2.set("CH2: -- (read error)")
            else:
                # Assumption: device stores signed 32-bit in two 16-bit regs (hi, lo)
                ch1 = combine_s32_from_regs(regs[0], regs[1])
                ch2 = combine_s32_from_regs(regs[2], regs[3])
                self.live_ch1.set(f"CH1: {ch1}")
                self.live_ch2.set(f"CH2: {ch2}")
            time.sleep(0.25)

    def disable_auto_adjust(self):
        if not self.ensure_client():
            return
        ch = self.selected_channel()
        # Disable zero enable + dynamic tracking; keep filter moderate (3)
        if ch == "CH1":
            ok = True
            ok &= self.reg_write_u16(REG["CH1_ZERO_EN"], 0)
            ok &= self.reg_write_u16(REG["CH1_DYN"], 0)
            ok &= self.reg_write_u16(REG["CH1_FILT"], 3)
            if ok:
                self.logln("CH1: disabled zero_en & dyn, filt=3 for calibration.")
        else:
            ok = True
            ok &= self.reg_write_u16(REG["CH2_ZERO_EN"], 0)
            ok &= self.reg_write_u16(REG["CH2_DYN"], 0)
            ok &= self.reg_write_u16(REG["CH2_FILT"], 3)
            if ok:
                self.logln("CH2: disabled zero_en & dyn, filt=3 for calibration.")

    def zero_cal_selected(self):
        if not self.ensure_client():
            return
        ch = self.selected_channel()
        if not messagebox.askyesno("Zero Cal", f"Make sure {ch} is EMPTY and stable.\nProceed?"):
            return
        if ch == "CH1":
            ok = self.reg_write_u16(REG["CH1_ZERO_CAL"], 1)
        else:
            ok = self.reg_write_u16(REG["CH2_ZERO_CAL"], 1)
        if ok:
            self.logln(f"{ch}: zero calibration triggered (write 1).")

    def set_10pt_mode(self):
        if not self.ensure_client():
            return
        ch = self.selected_channel()
        if ch == "CH1":
            ok = self.reg_write_u16(REG["CH1_NPT_COUNT"], 10)
        else:
            ok = self.reg_write_u16(REG["CH2_NPT_COUNT"], 10)
        if ok:
            self.logln(f"{ch}: set N-point mode to 10 (write 10).")

    def set_npt_mode(self):
        if not self.ensure_client():
            return
        ch = self.selected_channel()
        n = self.get_point_count()
        if ch == "CH1":
            ok = self.reg_write_u16(REG["CH1_NPT_COUNT"], n)
        else:
            ok = self.reg_write_u16(REG["CH2_NPT_COUNT"], n)
        if ok:
            self.logln(f"{ch}: set N-point mode to {n} (write {n}).")

    def _get_tree_selection_index(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return None
        return safe_int(str(vals[0]), 0)

    def _get_point_grams(self, idx: int) -> float | None:
        # idx: 1..10
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if safe_int(str(vals[0]), 0) == idx:
                g = safe_float(str(vals[1]).strip(), None)
                return g
        return None

    def _set_point_row(self, idx: int, grams: float, raw: int, status: str):
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if safe_int(str(vals[0]), 0) == idx:
                self.tree.item(item, values=(idx, f"{grams}", f"{raw}", status))
                return

    def _set_row_status(self, idx: int, status: str):
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if safe_int(str(vals[0]), 0) == idx:
                self.tree.item(item, values=(vals[0], vals[1], vals[2], status))
                return

    def write_selected_point(self):
        if not self.ensure_client():
            return

        idx = self._get_tree_selection_index()
        if idx is None or not (1 <= idx <= 10):
            messagebox.showwarning("Select row", "Select a point row (1..10) first.")
            return

        grams = self._get_point_grams(idx)
        if grams is None:
            messagebox.showwarning("Missing value", "Enter grams for this point.")
            return

        ch = self.selected_channel()
        scale = self.cal_scale()
        raw = int(round(grams * scale))

        if raw < 20 or raw > 65535:
            messagebox.showerror("Out of range",
                                 f"Raw value {raw} out of allowed 16-bit range.\n"
                                 f"Try smaller scale or different units.")
            return

        if not messagebox.askyesno("Write point",
                                   f"{ch} Point {idx}\n"
                                   f"Place {grams} g and wait stable.\n"
                                   f"Write raw={raw} to device now?"):
            return

        if ch == "CH1":
            reg_addr = REG["CH1_P1"] + (idx - 1)
        else:
            reg_addr = REG["CH2_P1"] + (idx - 1)

        ok = self.reg_write_u16(reg_addr, raw)
        if ok:
            self._set_point_row(idx, grams, raw, f"Wrote to reg {reg_addr}")
            self.logln(f"{ch}: wrote point {idx}: grams={grams} raw={raw} -> reg={reg_addr}")

    def write_all_points(self):
        if not self.ensure_client():
            return
        ch = self.selected_channel()
        scale = self.cal_scale()
        n = self.get_point_count()

        # Validate all points
        points = []
        for i in range(1, n + 1):
            g = self._get_point_grams(i)
            if g is None:
                messagebox.showerror("Missing", f"Point {i} grams is empty.")
                return
            raw = int(round(g * scale))
            if raw < 20 or raw > 65535:
                messagebox.showerror("Out of range",
                                     f"Point {i} raw={raw} out of range.\nTry scale={scale} -> adjust.")
                return
            points.append((i, g, raw))

        if not messagebox.askyesno("Write ALL",
                                   f"This will write {n} points for {ch}.\n"
                                   f"You must place each weight and keep it stable.\n\n"
                                   f"Proceed and you will be prompted point-by-point."):
            return

        for (i, g, raw) in points:
            if not messagebox.askyesno("Next point",
                                       f"{ch} Point {i}\n"
                                       f"Now place {g} g, wait stable.\n"
                                       f"Click Yes to write raw={raw}."):
                self._set_row_status(i, "Skipped by user")
                continue
            reg_addr = (REG["CH1_P1"] if ch == "CH1" else REG["CH2_P1"]) + (i - 1)
            ok = self.reg_write_u16(reg_addr, raw)
            if ok:
                self._set_point_row(i, g, raw, f"Wrote to reg {reg_addr}")
                self.logln(f"{ch}: wrote point {i}: grams={g} raw={raw} -> reg={reg_addr}")
            else:
                self._set_row_status(i, "WRITE FAIL")
                messagebox.showerror("Write failed", f"Failed at point {i}. Stop.")
                return

        messagebox.showinfo("Done", f"{ch} {n}-point write completed.")

    def quick_fill_600g(self):
        n = self.get_point_count()
        # Generate evenly distributed points focusing around 600g
        if n <= 3:
            pts = [100, 600, 1000][:n]
        else:
            # Create more dense around 600g
            start = 100
            end = 1000
            mid = 600
            
            # Split into two halves with denser spacing around mid
            low_pts = [start + (mid - start) * i / (n // 2) for i in range(n // 2)]
            high_pts = [mid + (end - mid) * i / (n - n // 2) for i in range(1, n - n // 2 + 1)]
            pts = low_pts + high_pts
            pts = sorted(list(set(int(p) for p in pts)))[:n]

        for i in range(1, n + 1):
            g = pts[i-1] if i <= len(pts) else 100 * i
            for item in self.tree.get_children():
                vals = self.tree.item(item, "values")
                if safe_int(str(vals[0]), 0) == i:
                    self.tree.item(item, values=(i, f"{g}", "", "Not set"))
                    break

        self.logln(f"Quick fill loaded ({n}-point template, dense around 600g). Adjust grams as needed.")
        messagebox.showinfo("Quick Fill",
                            f"Loaded a {n}-point template focusing around 600g.\n"
                            "Edit the grams column if your actual weights differ.\n")

    def clear_points(self):
        n = self.get_point_count()
        for i in range(1, n + 1):
            self._set_point_row(i, "", "", "Not set")
        self.logln("Cleared points table.")


if __name__ == "__main__":
    app = CalGUI()
    app.mainloop()
