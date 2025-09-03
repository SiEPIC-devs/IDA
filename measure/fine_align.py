import asyncio
import numpy as np
from typing import Dict, Any, Tuple

from motors.stage_manager import StageManager
from motors.hal.motors_hal import AxisType
from NIR.nir_manager import NIRManager

from utils.logging_helper import setup_logger

logger = setup_logger

"""
Made by: Cameron Basara, 2025
Fine alignment module for optical coupling using spiral and gradient search.
"""


class FineAlign:
    """
    Perform fine alignment by optimizing optical coupling using spiral, gradient, and optional crosshair search.
    """

    def __init__(self, config: Dict[str, Any], stage_manager: StageManager, nir_manager: NIRManager,
                 debug: bool = False):
        self.config = config
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.debug = debug

        # Setup logger
        self.logger = setup_logger("FineAlign", "ALIGN", debug_mode=debug)

        # Extract config params
        self.step_size = config.get("step_size", 2.0)  # microns
        self.scan_window = config.get("scan_window", 50.0)
        self.threshold = config.get("threshold", -50.0)
        self.max_gradient_iters = config.get("gradient_iters", 50)
        self.min_gradient_ss = config.get("min_gradient_ss", 0.2)  # microns
        self.grad_step = (self.step_size - self.min_gradient_ss) / self.max_gradient_iters
        self.use_crosshair = config.get("use_crosshair", False)
        self.primary_detector = config.get("primary_detector", "ch1")
        self.ref_wl = config.get("ref_wl", 1550.0)

        self.log(f"FineAlign initialized with detector: {self.primary_detector}", "info")
        self._stop_requested = False

        # Tracking
        self.best_position = None
        self.lowest_loss = -200

    async def begin_fine_align(self) -> bool:
        """
        Run the fine alignment process: spiral → gradient → optional crosshair.
        """
        try:
            # Set to ref wl
            self.nir_manager.set_wavelength(self.ref_wl)

            # Gradient refinement
            ok = await self.gradient_search()
            if ok:
                self.log(f"Gradient descent completed sucessfully {self.lowest_loss}", "info")

                # Start spiral search
            result = await self.spiral_search(self.best_position[0], self.best_position[1])
            if result:
                self.log(f"Spiral search completed successfully {self.lowest_loss}", "info")

            return True

        except Exception as e:
            self.log(f"Fine alignment failed: {e}", "error")
            return False

    async def spiral_search(self, x_pos: float, y_pos: float) -> bool:
        """
        Perform spiral search until threshold is met or limit reached.

        Args:
            x_pos[float]: initial x position
            y_pos[float]: initial y position
        Returns:
            bool: True if successful False if limit reached some error occured
        """
        try:
            # Start from current position
            step = self.step_size
            limit = int(self.scan_window / step)
            direction = 1
            num_steps = 1

            # Set primary detector
            loss_master, loss_slave = self.nir_manager.read_power()
            detect = self._select_detector_channel(loss_master, loss_slave)

            self.log(f"Starting spiral search from ({x_pos:.2f}, {y_pos:.2f}) with detector: {self.primary_detector}",
                     "info")

            best = {"loss": detect, "position": (x_pos, y_pos)}

            while num_steps < limit and not self._stop_requested:
                # X movement
                for _ in range(num_steps):
                    await self.stage_manager.move_axis(AxisType.X, step * direction, relative=True,
                                                       wait_for_completion=True)
                    x_pos += step * direction
                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_loss = self._select_detector_channel(loss_master, loss_slave)
                    if current_loss > best["loss"]:
                        best["loss"] = current_loss
                        best["position"] = (x_pos, y_pos)
                        self.log(f"New best position: ({x_pos:.2f}, {y_pos:.2f}) with power: {current_loss:.2f}dBm",
                                 "debug")

                # Y movement
                for _ in range(num_steps):
                    await self.stage_manager.move_axis(AxisType.Y, step * direction, relative=True,
                                                       wait_for_completion=True)
                    y_pos += step * direction
                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_loss = self._select_detector_channel(loss_master, loss_slave)
                    if current_loss > best["loss"]:
                        best["loss"] = current_loss
                        best["position"] = (x_pos, y_pos)
                        self.log(f"New best position: ({x_pos:.2f}, {y_pos:.2f}) with power: {current_loss:.2f}dBm",
                                 "debug")

                # Increase step count and flip direction
                num_steps += 1
                direction *= -1

            # Go to best position
            self.log(
                f"Moving to best position: ({best['position'][0]:.2f}, {best['position'][1]:.2f}) with power: {best['loss']:.2f}dBm",
                "info")
            xok = await self.stage_manager.move_axis(AxisType.X, best["position"][0], relative=False,
                                                     wait_for_completion=True)
            yok = await self.stage_manager.move_axis(AxisType.Y, best["position"][1], relative=False,
                                                     wait_for_completion=True)

            if (xok and yok):
                self.log("Spiral search completed successfully", "info")
                return True
            else:
                self.log("Failed to move to best position", "error")
                return False

        except Exception as e:
            self.log(f"Spiral search error: {e}", "error")
            return False

    async def gradient_search(self):
        """
        Perform gradient-based fine alignment refinement.

        Get power
        Take a step in each direction
        Go to lowest loss direction
        Take a step in each direction that is not the previous
        if no improvement
            decrease step size
            if step size threshold met
                break

        """

        async def _move_dir(axis, dir):
            await self.stage_manager.move_axis(axis, dir * self.step_size, relative=True, wait_for_completion=True)
            loss_m, loss_s = self.nir_manager.read_power()
            loss = self._select_detector_channel(loss_m, loss_s)
            await self.stage_manager.move_axis(axis, -dir * self.step_size, relative=True, wait_for_completion=True)
            if loss > self.lowest_loss:
                self.lowest_loss = loss
                if axis == AxisType.X:
                    self.best_position[0] = await self.stage_manager.get_position(axis) + dir * self.step_size
                else:  # AxisType.Y
                    self.best_position[1] = await self.stage_manager.get_position(axis) + dir * self.step_size
                return axis, dir
            else:
                return False, False

        try:
            self.log("Starting gradient search refinement", "info")
            loss_master, loss_slave = self.nir_manager.read_power()
            current_detect = self._select_detector_channel(loss_master, loss_slave)

            self.lowest_loss = current_detect
            x = await self.stage_manager.get_position(AxisType.X)
            y = await self.stage_manager.get_position(AxisType.Y)
            self.best_position = [x, y]
            axes = [(AxisType.X, +1), (AxisType.X, -1), (AxisType.Y, +1), (AxisType.Y, -1)]
            frozen = axes.copy()

            iteration = 0
            ss = self.step_size
            while ss >= self.min_gradient_ss:
                if self._stop_requested:
                    self.log("Gradient search stopped requested", "info")
                    break
                best_axis, best_dir = None, 0
                for axis, dir in axes:
                    ax, d = await _move_dir(axis, dir)
                    if ax:
                        best_axis, best_dir = ax, d
                if best_axis is None:
                    ss -= self.grad_step
                    continue
                await self.stage_manager.move_axis(best_axis, ss * best_dir, relative=True, wait_for_completion=True)
                axes = frozen.copy()
                axes.remove((best_axis, best_dir))
            self.log("Gradient descent converged", "info")
            return True
        except Exception as e:
            self.log(f"Gradient search error: {e}", "error")
            return False

    def _select_detector_channel(self, loss_master: float, loss_slave: float) -> float:
        """Select detector channel based on config"""
        if self.primary_detector == "ch1":
            return loss_master
        elif self.primary_detector == "ch2":
            return loss_slave
        else:
            # Default to best (highest power)
            return max(loss_master, loss_slave)

    def stop_alignment(self):
        self.log("Fine alignment stop requested", "info")
        self._stop_requested = True

    def reset_stop_flag(self):
        self._stop_requested = False

    def log(self, message, level):
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
