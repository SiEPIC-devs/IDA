import asyncio
import numpy as np
from typing import Dict, Any, Tuple
import time

from motors.stage_manager import StageManager
from motors.hal.motors_hal import AxisType
from NIR.nir_manager import NIRManager

from utils.logging_helper import setup_logger

"""
Made by: Cameron Basara, 2025
Fine alignment module for optical coupling using spiral and gradient search.
"""


class FineAlign:
    """
    Perform fine alignment by optimizing optical coupling using spiral, gradient
    """

    def __init__(self, config: Dict[str, Any], stage_manager: StageManager, nir_manager: NIRManager,
                 debug: bool = False):
        self.config = config
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.debug = debug

        # Setup logger
        self.logger = setup_logger("FineAlign", debug_mode=debug)

        # Extract config params
        self.step_size = config.get("step_size", 2.0)  # microns
        self.scan_window = config.get("scan_window", 50.0)
        self.threshold = config.get("threshold", -50.0)
        self.max_gradient_iters = max(1, config.get("gradient_iters", 50))
        self.min_gradient_ss = config.get("min_gradient_ss", 0.2)  # microns
        self.grad_step = (self.step_size - self.min_gradient_ss) / self.max_gradient_iters
        self.primary_detector = config.get("primary_detector", "ch1")
        self.ref_wl = config.get("ref_wl", 1550.0)
        self.timeout_s = float(config.get("timeout_s", 180.0))
        self._start_time = 0.0

        self.log(f"FineAlign initialized with detector: {self.primary_detector}", "info")
        self._stop_requested = False

        # Tracking
        self.best_position = None
        self.lowest_loss = -200

    async def begin_fine_align(self) -> bool:
        """
        Gradient -> (optional) Spiral.
        """
        try:
            self.nir_manager.set_wavelength(self.ref_wl)
            self._start_time = time.monotonic()

            # Safety
            if not self.best_position or len(self.best_position) != 2:
                x = await self.stage_manager.get_position(AxisType.X)
                y = await self.stage_manager.get_position(AxisType.Y)
                self.best_position = [x.actual, y.actual]

            aok = await self.spiral_search(self.best_position[0], self.best_position[1])
            if not aok:
                self.log("Spiral search failed.", "error")
                return False

            if self.lowest_loss >= self.threshold:
                self.log(f"Target met after gradient: {self.lowest_loss:.2f} dBm", "info")
                return True

            await self.stage_manager.move_axis(AxisType.X, self.best_position[0], relative=False,
                                               wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, self.best_position[1], relative=False,
                                               wait_for_completion=True)

            bok = await self.gradient_search()
            if not bok:
                self.log("Gradient search failed; skipping spiral.", "error")
                return False

            await self.stage_manager.move_axis(AxisType.X, self.best_position[0], relative=False,
                                               wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, self.best_position[1], relative=False,
                                               wait_for_completion=True)
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
            # Ensure exact start
            await self.stage_manager.move_axis(AxisType.X, x_pos, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y_pos, relative=False, wait_for_completion=True)

            step = self.step_size
            limit = max(1, int(self.scan_window / max(1e-9, step)))  # number of segments per arm
            direction = 1
            num_steps = 1

            lm, ls = self.nir_manager.read_power()
            best_loss = self._select_detector_channel(lm, ls)
            x = await self.stage_manager.get_position(AxisType.X)
            y = await self.stage_manager.get_position(AxisType.Y)
            best_pos = [x.actual, y.actual]
            self.lowest_loss = max(self.lowest_loss, best_loss)

            self.log(f"Starting spiral at ({best_pos[0]:.3f}, {best_pos[1]:.3f})", "info")
            if best_loss >= self.threshold:
                self.best_position = best_pos
                self.log("Spiral skipped: threshold already met.", "info")
                return True

            while num_steps <= limit and not self._stop_requested:
                # X sweep
                for _ in range(num_steps):
                    if self._stop_requested:
                        break
                    await self.stage_manager.move_axis(AxisType.X, step * direction, relative=True, wait_for_completion=True)
                    lm, ls = self.nir_manager.read_power()
                    val = self._select_detector_channel(lm, ls)
                    if val > best_loss:
                        best_loss = val
                        x = await self.stage_manager.get_position(AxisType.X)
                        y = await self.stage_manager.get_position(AxisType.Y)
                        best_pos = [x.actual, y.actual]
                        self.lowest_loss = best_loss
                        if best_loss >= self.threshold:
                            break

                if self._stop_requested or best_loss >= self.threshold:
                    break

                # Y sweep
                for _ in range(num_steps):
                    if self._stop_requested:
                        break
                    await self.stage_manager.move_axis(AxisType.Y, step * direction, relative=True, wait_for_completion=True)
                    lm, ls = self.nir_manager.read_power()
                    val = self._select_detector_channel(lm, ls)
                    if val > best_loss:
                        best_loss = val
                        x = await self.stage_manager.get_position(AxisType.X)
                        y = await self.stage_manager.get_position(AxisType.Y)
                        best_pos = [x.actual, y.actual]
                        self.lowest_loss = best_loss
                        if best_loss >= self.threshold:
                            break

                # Expand one ring and flip direction
                num_steps += 1
                direction *= -1

            # Snap to best
            await self.stage_manager.move_axis(AxisType.X, best_pos[0], relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, best_pos[1], relative=False, wait_for_completion=True)
            self.best_position = best_pos

            if best_loss >= self.threshold:
                self.log(f"Spiral completed: reached {best_loss:.2f} dBm", "info")
            else:
                self.log(f"Spiral completed: best {best_loss:.2f} dBm (threshold {self.threshold:.2f} dBm not met)", "info")
            return True

        except Exception as e:
            self.log(f"Spiral search error: {e}", "error")
            return False

    async def gradient_search(self) -> bool:
            try:
                self.log("Starting gradient search refinement", "info")

                if self.best_position is None:
                    # Initial positions
                    x = await self.stage_manager.get_position(AxisType.X)
                    y = await self.stage_manager.get_position(AxisType.Y)
                    self.best_position = [x.actual, y.actual]

                lm, ls = self.nir_manager.read_power()
                current = self._select_detector_channel(lm, ls)
                self.lowest_loss = current

                # Grad shrink
                iters = max(1, int(self.max_gradient_iters))
                total_shrink = max(0.0, self.step_size - self.min_gradient_ss)
                grad_step = total_shrink / iters  # step reduction

                ss = self.step_size
                # Probe order: +/-X then +/-Y
                axes = [(AxisType.X, +1), (AxisType.X, -1), (AxisType.Y, +1), (AxisType.Y, -1)]
                tried_min_step = False

                while ss >= self.min_gradient_ss:
                    if self._stop_requested or (time.monotonic() - self._start_time) > self.timeout_s:
                        self.log("Gradient search stop requested or timeout", "info")
                        break

                    improved = False
                    best_axis, best_dir, best_val = None, 0, self.lowest_loss

                    # Probe each direction using the current step size
                    for axis, direction in axes:
                        if self._stop_requested:
                            break

                        await self.stage_manager.move_axis(axis, ss * direction, relative=True, wait_for_completion=True)
                        lm, ls = self.nir_manager.read_power()
                        val = self._select_detector_channel(lm, ls)

                        # Immediately move back
                        await self.stage_manager.move_axis(axis, -ss * direction, relative=True, wait_for_completion=True)

                        if val > best_val:
                            best_axis, best_dir, best_val = axis, direction, val
                            improved = True

                    if self._stop_requested:
                        self.log("Gradient search stop requested", "info")
                        break

                    if improved and best_axis is not None:
                        # Commit the best probing direction
                        await self.stage_manager.move_axis(best_axis, ss * best_dir, relative=True, wait_for_completion=True)

                        # Update from controller
                        x = await self.stage_manager.get_position(AxisType.X)
                        y = await self.stage_manager.get_position(AxisType.Y)
                        self.best_position = [x.actual, y.actual]

                        self.lowest_loss = best_val
                        current = best_val
                        tried_min_step = False

                        if self.lowest_loss >= self.threshold:
                            self.log(f"Gradient met threshold at {self.lowest_loss:.2f} dBm", "info")
                            return True
                    else:
                        # No progress at this scale -> shrink step
                        if ss <= self.min_gradient_ss:
                            if tried_min_step:
                                break
                            tried_min_step = True
                        ss = max(self.min_gradient_ss, ss - grad_step)

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
