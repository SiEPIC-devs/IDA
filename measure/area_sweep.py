import asyncio
import numpy as np
from typing import Dict, Any

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
        
        # Setup logger
        self.logger = setup_logger("AreaSweep", "SWEEP", debug_mode=debug)
        self._log("AreaSweep initialized")

    async def begin_sweep(self) -> np.ndarray:
        """
        Take an area sweep, entry point.
        cfg:
            - pattern[str]: "crosshair" or "spiral"
            - x_size: number of columns (cells)
            - y_size: number of rows (cells)
            - x_step: step for crosshair serpentine (stage units)
            - y_step: step for crosshair serpentine (stage units)
            - step_size: step per cell for spiral (stage units)

        Returns:
            np.ndarray: (y_size, x_size) with measurement data at position 
                        (DEPRACATED) [[x, y, loss], ...] alignment path data
        """
        # Confirm managers are functional
        ok = await self.stage_status()
        if not ok:
            self._log("Stage manager not ready", "error")
            raise Exception("Invalid stage manager status")
        ok = await self.nir_status()
        if not ok:
            self._log("NIR manager not ready", "error")
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
        Crosshair with serpentine pattern
        """
        try:
            cfg = self.config

            data = []
            x_data = []

            # Read current absolute position and keep as the origin 
            x_pos = (await self.stage_manager.get_position(AxisType.X)).actual
            y_pos = (await self.stage_manager.get_position(AxisType.Y)).actual
            initial_x, initial_y = x_pos, y_pos

            x_len, x_step = cfg.x_size, cfg.x_step
            y_len, y_step = cfg.y_size, cfg.y_step
            self._log(f"Starting area sweep: {x_len}x{y_len} with steps ({x_step}, {y_step})")

            # Initial measurement at the starting cell
            loss_master, loss_slave = self.nir_manager.read_power()
            initial_power = self._select_detector_channel(loss_master, loss_slave)
            x_data.append(initial_power)
            self._log(f"Starting position: ({x_pos:.3f}, {y_pos:.3f}) with power: {initial_power:.2f} dBm")

            # Helper to alternate X direction per row 
            parity = lambda step, n: step if (n % 2) != 0 else -step

            total_cols = int(x_len // x_step)
            total_rows = int(y_len // y_step)

            point_count = 1  # already sampled the first point

            for i in range(total_cols):
                if self._stop_requested:
                    self._log("Area sweep stopped by user request")
                    break

                # Walk across a row (in X)
                for _ in range(total_rows):
                    if self._stop_requested:
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

                # End of a row -> store and reset row accumulator
                data.append(x_data)
                x_data = []

                # Move one row in Y and sample the first point of the next row
                if not self._stop_requested and (i + 1) < total_cols:
                    await self.stage_manager.move_axis(
                        axis=AxisType.Y,
                        position=y_step,
                        relative=True,
                        wait_for_completion=True,
                    )
                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_power = self._select_detector_channel(loss_master, loss_slave)
                    x_data.append(current_power)
                    y_pos += y_step
                    point_count += 1

            # Return to starting absolute position
            await self.stage_manager.move_axis(
                axis=AxisType.X, position=initial_x, relative=False, wait_for_completion=True
            )
            await self.stage_manager.move_axis(
                axis=AxisType.Y, position=initial_y, relative=False, wait_for_completion=True
            )

            if self._stop_requested:
                self._log("Area sweep stopped early.")
            else:
                self._log(f"Area sweep completed. Total points: {point_count}")

            return np.array(data, dtype=float)

        except Exception as e:
            self._log(f"Area sweep (crosshair) error: {e}", "error")
            raise
    
    async def _begin_sweep_spiral_grid(self) -> np.ndarray:
        """
        Spiral search area sweep

        Returns:
            np.ndarray: shape (y_size, x_size) of measured values.
        """
        try:
            cfg = self.config

            #  window -> cell grid (um) 
            step = float(getattr(cfg, "step_size", getattr(cfg, "x_step", 1.0)))
            if step <= 0:
                raise ValueError("step_size must be > 0 µm")

            # inclusive endpoints => floor(extent/step) + 1
            def samples_along(extent_um: float, pitch_um: float) -> int:
                return max(1, int(extent_um // pitch_um) + 1)

            x_cells = samples_along(float(cfg.x_size), step)   # columns
            y_cells = samples_along(float(cfg.y_size), step)   # rows
            total_cells = x_cells * y_cells

            #  buffers 
            data = np.full((y_cells, x_cells), np.nan, dtype=float)
            visited = np.zeros((y_cells, x_cells), dtype=bool)

            #  anchor at current physical pose (this is the spiral center) 
            x0 = (await self.stage_manager.get_position(AxisType.X)).actual
            y0 = (await self.stage_manager.get_position(AxisType.Y)).actual
            # Clamp to exact current pose (no-op if already there)
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            # Logical center index (lower of the two middles if even-sized window)
            cx = (x_cells - 1) // 2
            cy = (y_cells - 1) // 2

            # Current accepted logical cell (maps to current physical pose)
            x_idx, y_idx = cx, cy

            def read_value() -> float:
                lm, ls = self.nir_manager.read_power()
                return float(self._select_detector_channel(lm, ls))

            # First sample: no motion
            visited[y_idx, x_idx] = True
            data[y_idx, x_idx] = read_value()
            covered = 1

            #  centered spiral driver (legs 1,1,2,2,3,3,...) 
            # directions in *cell units*: Right, Down, Left, Up
            dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            d = 0           # current dir index (start to the right)
            leg_len = 1     # how many virtual steps to take on this leg

            # virtual cursor walks the ideal spiral; we only move physically when the
            # next virtual cell is inside the grid and unvisited
            vx, vy = x_idx, y_idx

            while covered < total_cells and not self._stop_requested:
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

                            if covered >= total_cells or self._stop_requested:
                                break

                    if covered >= total_cells or self._stop_requested:
                        break
                    # 90deg right turn
                    d = (d + 1) % 4

                # next ring grows by one cell
                leg_len += 1

            #  return to where we started 
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            self._log(f"Centered spiral completed {x_cells}x{y_cells} at {step:g} µm pitch")
            return data

        except Exception as e:
            self._log(f"Spiral grid sweep error: {e}", "error")
            raise

    def _select_detector_channel(self, loss_master: float, loss_slave: float) -> float:
        """Select detector channel based on config"""
        if self.primary_detector == "ch1":
            return loss_master
        elif self.primary_detector == "ch2":
            return loss_slave
        else:
            # Default to best (highest power)
            return max(loss_master, loss_slave)

    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)

    def stop_sweep(self):
        """Request to stop the area sweep"""
        self._log("Area sweep stop requested")
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
        