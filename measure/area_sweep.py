import asyncio
import numpy as np
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

Assisted by ChatGPT 5 for some integration fixes.
"""
...
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
        self.primary_detector = None # Max is fine for area sweeps
        self.spiral = None
        self._stop_requested = False
        self._cancel_event = cancel_event  # external cancel (multiprocessing.Event)
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
        
    def _select_detector_channel(self, loss_master: float, loss_slave: float) -> float:
        """Select detector channel based on config"""
        # Select max by default (area sweep doesn't enforce a primary detector)
        return max(loss_master, loss_slave)

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
        pattern = getattr(cfg, "pattern", "crosshair")

        if pattern == "crosshair":
            return await self._begin_sweep_crosshair()
        elif pattern == "spiral":
            return await self._begin_sweep_spiral_grid()
        else:
            self._log(f"Unknown pattern '{pattern}', defaulting to crosshair.", "warning")
            return await self._begin_sweep_crosshair()


    async def _begin_sweep_crosshair(self) -> np.ndarray:
        """
        Sweep crosshair-like pattern using a serpentine approach
        """
        try:
            cfg = self.config
            # Cache config to keep inner loop tight
            x_len = float(cfg.x_size)   # total X length
            y_len = float(cfg.y_size)   # total Y length
            x_step = float(getattr(cfg, "x_step", getattr(cfg, "step_size", 1.0)))
            y_step = float(getattr(cfg, "y_step", getattr(cfg, "step_size", 1.0)))
            if x_step <= 0 or y_step <= 0:
                raise ValueError("x_step/y_step must be > 0 µm")

            # inclusive endpoints => floor(extent/step) + 1
            # (e.g., 0..100 step 50 => col indices 0,1,2 => 3 cols)
            total_cols = max(1, int(x_len // x_step))
            total_rows = max(1, int(y_len // y_step))
            total_points = total_cols * total_rows

            self._log(f"Crosshair sweep: cols={total_cols}, rows={total_rows}, step=({x_step},{y_step})")
            self._report(5.0, f"Area sweep: scanning {total_points} points...")

            # anchor origin pose
            x_pos = (await self.stage_manager.get_position(AxisType.X)).actual
            y_pos = (await self.stage_manager.get_position(AxisType.Y)).actual
            initial_x, initial_y = x_pos, y_pos

            # first sample at the center
            loss_master, loss_slave = self.nir_manager.read_power()
            first_val = self._select_detector_channel(loss_master, loss_slave)

            # allocate output (rows of x_data)
            data = []
            x_data = [first_val]

            # serpentine X across rows; move Y between rows
            # parity determines sign (+/-) of X stepping per col
            def parity(step, n):
                return step if (n % 2) != 0 else -step

            point_count = 1  # already sampled the first point

            for i in range(total_cols):
                if self._cancelled():
                    self._log("Area sweep canceled")
                    self._report(100.0, "Area sweep: canceled")
                    break

                # Walk across a row (in X)
                for _ in range(total_rows):
                    if self._cancelled():
                        self._report(100.0, "Area sweep: canceled")
                        break

                    step = parity(x_step, i)
                    await self.stage_manager.move_axis(
                        axis=AxisType.X,
                        position=step,
                        relative=True,
                        wait_for_completion=True,
                    )

                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_power = self._select_detector_channel(loss_master, loss_slave)
                    x_data.append(current_power)
                    x_pos += step
                    point_count += 1
                    
                    # Report progress
                    progress = min(95.0, 10.0 + (point_count / total_points) * 85.0)
                    self._report(progress, f"Area sweep: point {point_count}/{total_points}")

                # End of a row -> store and reset row accumulator
                data.append(x_data)
                x_data = []

                # Move to the next row in Y (except after the last)
                if not self._cancelled() and (i + 1) < total_cols:
                    await self.stage_manager.move_axis(
                        axis=AxisType.Y,
                        position=y_step,
                        relative=True,
                        wait_for_completion=True,
                    )
                    loss_master, loss_slave = self.nir_manager.read_power()
                    x_data.append(self._select_detector_channel(loss_master, loss_slave))
                    y_pos += y_step

            # Return to origin pose
            self._report(98.0, "Area sweep: returning to start position...")
            await self.stage_manager.move_axis(AxisType.X, initial_x, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, initial_y, relative=False, wait_for_completion=True)

            self._report(100.0, "Area sweep: completed")
            self._log(f"Crosshair sweep completed. Total rows stored: {len(data)}")
            return np.array(data, dtype=float)

        except Exception as e:
            self._log(f"Area sweep (crosshair) error: {e}", "error")
            raise

    async def _begin_sweep_spiral_grid(self) -> np.ndarray:
        """
        Spiral search on a discrete grid centered at the current pose.
        """
        try:
            cfg = self.config

            # The "step" is the pitch between samples in both axes
            step = float(getattr(cfg, "step_size", getattr(cfg, "x_step", 1.0)))
            if step <= 0:
                raise ValueError("step_size must be > 0 µm")

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
            def read_value() -> float:
                lm, ls = self.nir_manager.read_power()
                return float(self._select_detector_channel(lm, ls))

            visited[y_idx, x_idx] = True
            data[y_idx, x_idx] = read_value()
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
                            data[y_idx, x_idx] = read_value()
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
            self._log(f"Centered spiral completed {x_cells}x{y_cells} at {step:g} µm pitch")
            return data

        except Exception as e:
            self._log(f"Spiral grid sweep error: {e}", "error")
            raise

    def _cancelled(self) -> bool:
        """True if a stop was requested or the external Cancel button was pressed."""
        return self._stop_requested or (self._cancel_event is not None and getattr(self._cancel_event, "is_set", lambda: False)())

    def _select_detector_channel(self, loss_master: float, loss_slave: float) -> float:
        """Select detector channel based on config"""
        if loss_master is None or loss_slave is None:
            self._log("Warning: non-numeric detector values; returning 0.0", "error")
            return 0.0
        # Max power (area sweep)
        return max(loss_master, loss_slave)

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
