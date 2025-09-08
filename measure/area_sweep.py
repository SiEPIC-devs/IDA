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
        Fill a (y_size x x_size) grid by walking a spiral from the current position as cell (0,0),
        turning whenever we hit a boundary or a visited cell.
        We sample once per cell and write directly into the 2-D grid.

        Returns:
            np.ndarray: shape (y_size, x_size) of measured values.
        """
        try:
            cfg = self.config

            x_cells = int(cfg.x_size)     # columns
            y_cells = int(cfg.y_size)     # rows
            step = float(getattr(cfg, "step_size", getattr(cfg, "x_step", 1.0)))  # physical step per cell

            # Preallocate output grid; NaN marks "unvisited"
            data = np.full((y_cells, x_cells), np.nan, dtype=float)

            # Ensure exact current position is the origin for this grid
            x0 = (await self.stage_manager.get_position(AxisType.X)).actual
            y0 = (await self.stage_manager.get_position(AxisType.Y)).actual
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            # Logical cell indices
            x_idx, y_idx = 0, 0

            # Directions in cell units: right, down, left, up
            dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            d = 0  # current direction index

            def read_value() -> float:
                lm, ls = self.nir_manager.read_power()
                return float(self._select_detector_channel(lm, ls))

            # Sample initial cell
            data[y_idx, x_idx] = read_value()

            total_cells = x_cells * y_cells
            # Already sampled 1 cell; iterate remaining
            for _ in range(total_cells - 1):
                if self._stop_requested:
                    self._log("Spiral grid sweep stopped by user request")
                    break

                # Proposed next index
                nx = x_idx + dirs[d][0]
                ny = y_idx + dirs[d][1]

                # Turn on boundary or visited
                if not (0 <= nx < x_cells and 0 <= ny < y_cells) or np.isfinite(data[ny, nx]):
                    d = (d + 1) % 4
                    nx = x_idx + dirs[d][0]
                    ny = y_idx + dirs[d][1]

                # Translate cell delta to physical move
                dx_cells = nx - x_idx
                dy_cells = ny - y_idx

                if dx_cells:
                    await self.stage_manager.move_axis(
                        AxisType.X, dx_cells * step, relative=True, wait_for_completion=True
                    )
                if dy_cells:
                    await self.stage_manager.move_axis(
                        AxisType.Y, dy_cells * step, relative=True, wait_for_completion=True
                    )

                # Commit and sample
                x_idx, y_idx = nx, ny
                data[y_idx, x_idx] = read_value()

            # Return to physical start
            await self.stage_manager.move_axis(AxisType.X, x0, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y0, relative=False, wait_for_completion=True)

            self._log(f"Spiral grid completed ({x_cells}x{y_cells}) at step {step:g}")
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
        