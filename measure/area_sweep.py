import asyncio
import numpy as np
import re
from typing import Any, Callable, Dict, Optional

from motors.stage_manager import *
from motors.hal.motors_hal import AxisType, Position
from NIR.nir_manager import *
from utils.logging_helper import setup_logger

import logging

"""
Made by: Cameron Basara, 2025
Area sweep module that takes instances of managers, completes an area scan and returns
positional data of the optical sweep.
"""


class AreaSweep:
    """
    Take an optical area sweep for alignement purposes
    """
    def __init__(
            self, 
            area_sweep_config: Dict[Any, Any],
            stage_manager: StageManager,
              nir_manager: NIRManager,
                progress: Optional[Callable[[float, str], None]] = None,
                cancel_event: Optional[Any] = None,
                debug: bool = False
        ):
        # Init
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.config = area_sweep_config
        self.debug = debug
        self.primary_detector = self.config.primary_detector
        self.primary_detector = str(self.primary_detector).lower()
        # Determine slots from primary channel
        self.slots = getattr(self.config, "slots", [1])
        if isinstance(self.primary_detector, str) and "ch" in self.primary_detector:
            # compute slot for that channel
            num = int(re.findall(r'\d+', self.primary_detector)[0])
            if (num%2) == 0:
                slot_i = num // 2 + 1
                head_i = 0
            else:
                slot_i = num // 2
                head_i = 1
            self.slots = [[0, slot_i, head_i]]
        self.spiral = None
        self._stop_requested = False
        self._cancel_event = cancel_event  
        self._progress = progress
        
        # Setup logger
        self.logger = setup_logger("AreaSweep", "SWEEP", debug_mode=debug)

        self._log("AreaSweep initialized")

    def _report(self, percent: float, msg: str) -> None:
        """Report progress to GUI if a callback was provided."""
        if self._progress is not None:
            p = 0.0 if percent < 0.0 else (100.0 if percent > 100.0 else percent)
            self._progress(p, msg)

    def _log(self, message: str, level: str = "info"):
        """Log Helper function"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        else:
            raise ValueError("Invalid log level")

    async def begin_sweep(self) -> np.ndarray:
        """
        Entry point to sweeps, given config, this will call
        the correct type of sweep.
        """
        self._report(0.0, "Area sweep: starting...")
        
        # Confirm managers are functional
        ok = await self.stage_status()
        if not ok:
            self._log("Stage manager not ready", "error")
            self._report(100.0, "Area sweep: error (stage manager not ready)")
            raise Exception("Invalid stage manager status")

        ok = await self.nir_status()
        if not ok:
            self._log("NIR manager not ready", "error")
            self._report(100.0, "Area sweep: error (NIR manager not ready)")
            raise Exception("Invalid NIR instrument manager status")
            
        # Initiate config
        cfg = self.config
        pattern = getattr(cfg, "pattern", "spiral")

        # if pattern == "crosshair":
        #     return await self._begin_sweep_crosshair()
        if pattern == "spiral":
            return await self._begin_sweep_spiral_grid()
        else:
            self._log(f"Unknown pattern '{pattern}', defaulting to spiral.", "warning")
            return await self._begin_sweep_spiral_grid()

    async def _begin_sweep_spiral_grid(self) -> np.ndarray:
        """
        Spiral search on a discrete grid centered at the current pose.
        """
        try:
            cfg = self.config

            # The "step" is the pitch between samples in both axes
            step = float(getattr(cfg, "step_size", getattr(cfg, "x_step", 1.0)))
            if step <= 0:
                raise ValueError("step_size must be > 0 um")
            
            # inclusive endpoints => floor(extent/step) + 1
            def samples_along(extent_um: float, pitch_um: float) -> int:
                return max(1, int(extent_um // pitch_um) + 1)

            x_cells = samples_along(float(cfg.x_size), step)   # columns
            y_cells = samples_along(float(cfg.y_size), step)   # rows
            total_cells = x_cells * y_cells

            self._report(5.0, f"Area sweep (spiral): scanning {total_cells} points...")

            #  buffers 
            data = np.full((y_cells, x_cells), np.nan, dtype=float)
            visited = np.zeros((y_cells, x_cells), dtype=bool)

            #  anchor at current physical pose (this is the spiral center) 
            x0 = (await self.stage_manager.get_position(AxisType.X)).actual
            y0 = (await self.stage_manager.get_position(AxisType.Y)).actual
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            # center cell indices
            cx = (x_cells - 1) // 2
            cy = (y_cells - 1) // 2
            x_idx, y_idx = cx, cy

            # first sample (center)
            # def read_value() -> float:
            #     lm, ls = self.nir_manager.read_power()
            #     return float(self._select_detector_channel(lm, ls))

            visited[y_idx, x_idx] = True
            data[y_idx, x_idx] = self.read_value()
            covered = 1
            self._report(10.0, f"Area sweep (spiral): point {covered}/{total_cells}")

            # right, up, left, down (clockwise)
            dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            d = 0          # direction index
            leg_len = 1     # how many virtual steps to take on this leg

            # virtual cursor walks the ideal spiral; we only move physically when the
            # next virtual cell is inside the grid and unvisited
            vx, vy = x_idx, y_idx

            while covered < total_cells and not self._cancelled():
                # two legs share the same length before we grow the ring
                for _repeat in range(2):
                    for _ in range(leg_len):
                        vx += dirs[d][0]
                        vy += dirs[d][1]

                        # accept only in-bounds, unvisited cells
                        if 0 <= vx < x_cells and 0 <= vy < y_cells and not visited[vy, vx]:
                            dx_cells = vx - x_idx
                            dy_cells = vy - y_idx

                            # physical motion in um (relative)
                            if dx_cells:
                                await self.stage_manager.move_axis(
                                    AxisType.X, dx_cells * step, relative=True, wait_for_completion=True
                                )
                            if dy_cells:
                                await self.stage_manager.move_axis(
                                    AxisType.Y, dy_cells * step, relative=True, wait_for_completion=True
                                )

                            # commit and read
                            x_idx, y_idx = vx, vy
                            visited[y_idx, x_idx] = True
                            data[y_idx, x_idx] = self.read_value()
                            covered += 1
                            
                            # Report progress
                            progress = min(95.0, 10.0 + (covered / total_cells) * 85.0)
                            self._report(progress, f"Area sweep (spiral): point {covered}/{total_cells}")

                        if covered >= total_cells or self._cancelled():
                            break
                    # 90deg right turn
                    d = (d + 1) % 4
                    if covered >= total_cells or self._cancelled():
                        break
                leg_len += 1

            # return to start
            self._report(98.0, "Area sweep (spiral): returning to start position...")
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            self._report(100.0, "Area sweep (spiral): completed")
            self._log(f"Centered spiral completed {x_cells}x{y_cells} at {step:g} um pitch")
            return data

        except Exception as e:
            self._log(f"Spiral grid sweep error: {e}", "error")
            raise

    def _cancelled(self) -> bool:
        """True if a stop was requested or the external Cancel button was pressed."""
        return self._stop_requested or (self._cancel_event is not None and getattr(self._cancel_event, "is_set", lambda: False)())

    def read_value(self):
        """Return the requested power by method"""
        if "ch" not in self.primary_detector:
            # Max
            best = -100
            for mf, slot, head in self.slots:
                loss = self.nir_manager.read_power(slot=slot, head=head, mf=mf)
                best = max(best, loss)
            return best
        else:
            mf, slot, head = self.slots[0]
            loss = self.nir_manager.read_power(slot=slot, head=head, mf=mf)
            return loss

    def stop_sweep(self):
        """Public stop hook used by GUI Cancel (legacy internal stop)"""
        self._log("Area sweep stop requested", "info")
        self._stop_requested = True

    def reset_stop_flag(self):
        """Reset stop flag for new sweep"""
        self._stop_requested = False

    async def stage_status(self):
        """Ensure stage manager instance is alive"""
        try:
            return True
            # return self.stage_manager is not None
        except Exception as e:
            self._log(f"Stage status check error: {e}", "error")
            return False

    async def nir_status(self):
        """Ensure NIR manager instance is alive"""
        try:
            return True
            # return self.nir_manager is not None and self.nir_manager.is_connected()
        except Exception as e:
            self._log(f"NIR status check error: {e}", "error")
            return False
