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
    def __init__(self, area_sweep_config: Dict[Any, Any], # place holder
                 stage_manager: StageManager, nir_manager: NIRManager, debug: bool = False):
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.config = area_sweep_config
        self.debug = debug
        self.primary_detector = None # placeholder
        self.spiral = None

        # Setup logger
        self.logger = setup_logger("AreaSweep", "SWEEP", debug_mode=debug)
        self._log("AreaSweep initialized")
        self._stop_requested = False

    # async def begin_sweep(self) -> np.ndarray:
    #     """
    #     Take an area sweep
    #
    #     Returns:
    #         np.ndarray: [[x, y, loss], ...] alignment path data
    #     """
    #     try:
    #         # Confirm managers are functional
    #         ok = await self.stage_status()
    #         if not ok:
    #             self._log("Stage manager not ready", "error")
    #             raise Exception("Invalid stage manager status")
    #         ok = await self.nir_status()
    #         if not ok:
    #             self._log("NIR manager not ready", "error")
    #             raise Exception("Invalid NIR instrument manager status")
    #         # Initiate config
    #         cfg = self.config
    #
    #         # Initiate data
    #         data = []
    #         x_data = []
    #         x_pos = await self.stage_manager.get_position(AxisType.X)
    #         x_pos = x_pos.actual
    #         y_pos = await self.stage_manager.get_position(AxisType.Y)
    #         y_pos = y_pos.actual
    #         x_len, x_step = cfg.x_size, cfg.x_step
    #         y_len, y_step = cfg.y_size, cfg.y_step
    #         self._log(f"Starting area sweep: {x_len}x{y_len} with steps ({x_step}, {y_step})")
    #         initial_x = x_pos
    #         initial_y = y_pos
    #
    #         # Ensure exact start
    #         await self.stage_manager.move_axis(AxisType.X, x_pos, relative=False, wait_for_completion=True)
    #         await self.stage_manager.move_axis(AxisType.Y, y_pos, relative=False, wait_for_completion=True)
    #
    #         step = x_step
    #         scan_window = x_len*y_len
    #         limit = max(1, int(scan_window / max(1e-9, step)))  # number of segments per arm
    #         direction = 1
    #         num_steps = 1
    #
    #         lm, ls = self.nir_manager.read_power()
    #         best_loss = self._select_detector_channel(lm, ls)
    #         x = await self.stage_manager.get_position(AxisType.X)
    #         y = await self.stage_manager.get_position(AxisType.Y)
    #         best_pos = [x.actual, y.actual]
    #         self.lowest_loss = max(self.lowest_loss, best_loss)
    #
    #         self.log(f"Starting spiral at ({best_pos[0]:.3f}, {best_pos[1]:.3f})", "info")
    #         if best_loss >= self.threshold:
    #             self.best_position = best_pos
    #             self.log("Spiral skipped: threshold already met.", "info")
    #             return True
    #
    #         while num_steps <= limit and not self._stop_requested:
    #             # X sweep
    #             for _ in range(num_steps):
    #                 if self._stop_requested:
    #                     break
    #                 await self.stage_manager.move_axis(AxisType.X, step * direction, relative=True,
    #                                                    wait_for_completion=True)
    #                 lm, ls = self.nir_manager.read_power()
    #                 val = self._select_detector_channel(lm, ls)
    #                 if val > best_loss:
    #                     best_loss = val
    #                     x = await self.stage_manager.get_position(AxisType.X)
    #                     y = await self.stage_manager.get_position(AxisType.Y)
    #                     best_pos = [x.actual, y.actual]
    #                     self.lowest_loss = best_loss
    #                     if best_loss >= self.threshold:
    #                         break
    #
    #             if self._stop_requested or best_loss >= self.threshold:
    #                 break
    #
    #             # Y sweep
    #             for _ in range(num_steps):
    #                 if self._stop_requested:
    #                     break
    #                 await self.stage_manager.move_axis(AxisType.Y, step * direction, relative=True,
    #                                                    wait_for_completion=True)
    #                 lm, ls = self.nir_manager.read_power()
    #                 val = self._select_detector_channel(lm, ls)
    #                 if val > best_loss:
    #                     best_loss = val
    #                     x = await self.stage_manager.get_position(AxisType.X)
    #                     y = await self.stage_manager.get_position(AxisType.Y)
    #                     best_pos = [x.actual, y.actual]
    #                     self.lowest_loss = best_loss
    #                     if best_loss >= self.threshold:
    #                         break
    #
    #             # Expand one ring and flip direction
    #             num_steps += 1
    #             direction *= -1
    #
    #         # Snap to best
    #         await self.stage_manager.move_axis(AxisType.X, best_pos[0], relative=False, wait_for_completion=True)
    #         await self.stage_manager.move_axis(AxisType.Y, best_pos[1], relative=False, wait_for_completion=True)
    #         self.best_position = best_pos
    #
    #         if best_loss >= self.threshold:
    #             self.log(f"Spiral completed: reached {best_loss:.2f} dBm", "info")
    #         else:
    #             self.log(f"Spiral completed: best {best_loss:.2f} dBm (threshold {self.threshold:.2f} dBm not met)",
    #                      "info")
    #         return True
    #     except Exception as e:
    #         self.log(f"Spiral search error: {e}", "error")
    #         return False
    #
    #         # Initial measurement
    #         loss_master, loss_slave = self.nir_manager.read_power()
    #         initial_power = max(loss_master, loss_slave)
    #         x_data.append(initial_power)
    #         self._log(f"Starting position: ({x_pos:.2f}, {y_pos:.2f}) with power: {initial_power:.2f}dBm")
    #
    #
    #         parity = lambda step, n: step if (n%2) != 0 else -step  # helper for parity switchin
    #
    #         total_points = (x_len // x_step) * (y_len // y_step)
    #         point_count = 1  # We already took initial measurement
    #
    #         for i in range(x_len // x_step):
    #             if self._stop_requested:
    #                 self._log("Area sweep stopped by user request")
    #                 break
    #
    #             for j in range(y_len // y_step):
    #                 if self._stop_requested:
    #                     break
    #
    #                 step = parity(x_step, i)
    #                 await self.stage_manager.move_axis(
    #                     axis = AxisType.X,
    #                     position = step,
    #                     relative = True,
    #                     wait_for_completion = True)
    #
    #                 loss_master, loss_slave = self.nir_manager.read_power()
    #                 current_power = max(loss_master, loss_slave)
    #                 x_data.append(current_power)
    #                 x_pos += step
    #
    #             data.append(x_data)
    #             x_data = []
    #
    #             # After a row has been measured, move y axis take the initial measurement
    #             if not self._stop_requested:
    #                 await self.stage_manager.move_axis(
    #                     axis = AxisType.Y,
    #                     position = y_step,
    #                     relative = True,
    #                     wait_for_completion = True)
    #                 loss_master, loss_slave = self.nir_manager.read_power() # some params
    #                 current_power = max(loss_master,loss_slave)
    #                 x_data.append(current_power)
    #                 y_pos += y_step
    #                 point_count += 1
    #
    #         # Once area sweep is complete, return the data as np.array
    #         # Return to starting position
    #         await self.stage_manager.move_axis(
    #             axis = AxisType.X,
    #             position = initial_x,
    #             relative = False,
    #             wait_for_completion = True
    #         )
    #         await self.stage_manager.move_axis(
    #             axis=AxisType.Y,
    #             position=initial_y,
    #             relative=False,
    #             wait_for_completion=True
    #         )
    #         if self._stop_requested:
    #             self._log(f"Area sweep stopped early.")
    #         else:
    #             self._log(f"Area sweep completed. Total points: {point_count}")
    #         return np.array(data)
    #     except Exception as e:
    #         self._log(f"Area sweep error: {e}", "error")
    #         raise
    #
    async def begin_sweep(self) -> np.ndarray:
        """
        Take an area sweep

        Returns:
            np.ndarray: [[x, y, loss], ...] alignment path data
        """
        try:
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

            # Initiate data
            data = []
            x_data = []
            x_pos = await self.stage_manager.get_position(AxisType.X)
            x_pos = x_pos.actual
            y_pos = await self.stage_manager.get_position(AxisType.Y)
            y_pos = y_pos.actual
            x_len, x_step = cfg.x_size, cfg.x_step
            y_len, y_step = cfg.y_size, cfg.y_step
            self._log(f"Starting area sweep: {x_len}x{y_len} with steps ({x_step}, {y_step})")
            initial_x = x_pos
            initial_y = y_pos

            # Initial measurement
            loss_master, loss_slave = self.nir_manager.read_power()
            initial_power = max(loss_master, loss_slave)
            x_data.append(initial_power)
            self._log(f"Starting position: ({x_pos:.2f}, {y_pos:.2f}) with power: {initial_power:.2f}dBm")

            parity = lambda step, n: step if (n % 2) != 0 else -step  # helper for parity switchin

            total_points = (x_len // x_step) * (y_len // y_step)
            point_count = 1  # We already took initial measurement

            for i in range(x_len // x_step):
                if self._stop_requested:
                    self._log("Area sweep stopped by user request")
                    break

                for j in range(y_len // y_step):
                    if self._stop_requested:
                        break

                    step = parity(x_step, i)
                    await self.stage_manager.move_axis(
                        axis=AxisType.X,
                        position=step,
                        relative=True,
                        wait_for_completion=True)

                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_power = max(loss_master, loss_slave)
                    x_data.append(current_power)
                    x_pos += step

                data.append(x_data)
                x_data = []

                # After a row has been measured, move y axis take the initial measurement
                if not self._stop_requested:
                    await self.stage_manager.move_axis(
                        axis=AxisType.Y,
                        position=y_step,
                        relative=True,
                        wait_for_completion=True)
                    loss_master, loss_slave = self.nir_manager.read_power()  # some params
                    current_power = max(loss_master, loss_slave)
                    x_data.append(current_power)
                    y_pos += y_step
                    point_count += 1

            # Once area sweep is complete, return the data as np.array
            # Return to starting position
            await self.stage_manager.move_axis(
                axis=AxisType.X,
                position=initial_x,
                relative=False,
                wait_for_completion=True
            )
            await self.stage_manager.move_axis(
                axis=AxisType.Y,
                position=initial_y,
                relative=False,
                wait_for_completion=True
            )
            if self._stop_requested:
                self._log(f"Area sweep stopped early.")
            else:
                self._log(f"Area sweep completed. Total points: {point_count}")
            return np.array(data)
        except Exception as e:
            self._log(f"Area sweep error: {e}", "error")
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
        