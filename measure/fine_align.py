import asyncio
import numpy as np
from typing import Dict, Any, Optional, Callable, Any
import time

from motors.stage_manager import StageManager
from motors.hal.motors_hal import AxisType
from NIR.nir_manager import NIRManager

from utils.logging_helper import setup_logger

"""
Made by: Cameron Basara, 2025
Fine alignment module for optical coupling using spiral and gradient search.

Assited by ChatGPT 5 for integration help 
"""


class FineAlign:
    """
    Perform fine alignment by optimizing optical coupling using spiral, gradient
    """

    def __init__(
            self,
            config: Dict[str, Any],
            stage_manager: StageManager,
            nir_manager: NIRManager,
            progress: Optional[Callable[[float, str], None]] = None,
            cancel_event: Optional[Any] = None,
            debug: bool = False
        ):
        self.config = config
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.debug = debug

        # external progress + cancel
        self._progress = progress
        self._cancel_event = cancel_event
        self.is_running = False

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
        self.lowest_loss = -80

    def _report(self, percent: float, msg: str) -> None:
        """Report progress to GUI if a callback was provided."""
        if self._progress is not None:
            p = 0.0 if percent < 0.0 else (100.0 if percent > 100.0 else percent)
            self._progress(p, msg)

    def _cancelled(self) -> bool:
        """True if stop() was requested or the external cancel_event is set."""
        return self._stop_requested or (
            self._cancel_event is not None and getattr(self._cancel_event, "is_set", lambda: False)()
        )

    async def begin_fine_align(self) -> bool:
        """
        Gradient -> (optional) Spiral.
        """
        self.is_running = True
        try:
            self.log("Fine alignment starting…", "info")
            self._report(0.0, "Fine alignment: starting…")
            self.nir_manager.set_wavelength(self.ref_wl)
            self._start_time = time.monotonic()

            if self._cancelled():
                self._report(95.0, "Fine alignment: canceled")
                return False

            # Safety: seed best_position from current pose if not set
            if not self.best_position or len(self.best_position) != 2:
                x = await self.stage_manager.get_position(AxisType.X)
                y = await self.stage_manager.get_position(AxisType.Y)
                self.best_position = [x.actual, y.actual]

            # Spiral search first
            aok = await self.spiral_search(self.best_position[0], self.best_position[1])
            if not aok:
                if self._cancelled():
                    self._report(100.0, "Spiral: canceled")
                else:
                    self._report(100.0, "Spiral: failed")
                    self.log("Spiral search failed.", "error")
                return False

            if self.lowest_loss >= self.threshold:
                self._report(100.0, "Threshold met after spiral")
                self.log(f"Target met after spiral: {self.lowest_loss:.2f} dBm", "info")
                return True

            # Return to best before gradient
            await self.stage_manager.move_axis(AxisType.X, self.best_position[0], relative=False,
                                               wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, self.best_position[1], relative=False,
                                               wait_for_completion=True)

            # Gradient refinement
            bok = await self.gradient_search()
            if not bok:
                if self._cancelled():
                    self._report(100.0, "Gradient: canceled")
                else:
                    self._report(100.0, "Gradient: failed")
                    self.log("Gradient search failed; skipping spiral.", "error")
                return False

            # Return to best finally
            await self.stage_manager.move_axis(AxisType.X, self.best_position[0], relative=False,
                                               wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, self.best_position[1], relative=False,
                                               wait_for_completion=True)
            self._report(100.0, "Fine alignment: completed")
            return True

        except Exception as e:
            self.log(f"Fine alignment failed: {e}", "error")
            self._report(100.0, f"Fine alignment: error ({e})")
            return False

        finally:
            self.is_running = False

    async def spiral_search(self, x_pos: float, y_pos: float) -> bool:
        """
        Perform spiral search until threshold is met or limit reached.

            Args:
                x_pos[float]: initial x position
                y_pos[float]: initial y position
            Returns:
                bool: True if successful False if limit reached / canceled / error
        """
        try:
            # Ensure exact start
            await self.stage_manager.move_axis(AxisType.X, x_pos, relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, y_pos, relative=False, wait_for_completion=True)

            step = self.step_size
            limit = max(1, int(self.scan_window / max(1e-9, step)))  # segments per arm (radius in steps)
            total_moves = max(1, limit * (limit + 1))  # ~upper bound of micro-moves in centered spiral
            covered = 0
            self._report(1.0, "Spiral: initializing")
            direction = 1
            num_steps = 1

            # initial sample
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

            while num_steps <= limit and not self._cancelled():
                # X sweep
                for _ in range(num_steps):
                    if self._cancelled():
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
                            covered += 1
                            self._report(100.0 * covered / total_moves, f"Spiral: step {covered}/{total_moves}")
                            break

                    covered += 1
                    self._report(100.0 * covered / total_moves, f"Spiral: step {covered}/{total_moves}")

                if self._cancelled() or best_loss >= self.threshold:
                    break

                # Y sweep
                for _ in range(num_steps):
                    if self._cancelled():
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
                            covered += 1
                            self._report(100.0 * covered / total_moves, f"Spiral: step {covered}/{total_moves}")
                            break

                    covered += 1
                    self._report(100.0 * covered / total_moves, f"Spiral: step {covered}/{total_moves}")

                # Expand one ring and flip direction
                num_steps += 1
                direction *= -1

            # If canceled mid-loop
            if self._cancelled():
                # Snap to best found so far
                await self.stage_manager.move_axis(AxisType.X, best_pos[0], relative=False, wait_for_completion=True)
                await self.stage_manager.move_axis(AxisType.Y, best_pos[1], relative=False, wait_for_completion=True)
                self.best_position = best_pos
                self._report(min(99.0, 100.0 * covered / total_moves), "Spiral: canceled")
                return False

            # Snap to best
            await self.stage_manager.move_axis(AxisType.X, best_pos[0], relative=False, wait_for_completion=True)
            await self.stage_manager.move_axis(AxisType.Y, best_pos[1], relative=False, wait_for_completion=True)
            self.best_position = best_pos

            if best_loss >= self.threshold:
                self._report(100.0, f"Spiral: reached {best_loss:.2f} dBm")
                self.log(f"Spiral completed: reached {best_loss:.2f} dBm", "info")
            else:
                self.log(f"Spiral completed: best {best_loss:.2f} dBm (threshold {self.threshold:.2f} dBm not met)", "info")
                self._report(min(99.0, 100.0 * covered / total_moves),
                             f"Spiral: best {best_loss:.2f} dBm (threshold {self.threshold:.2f} dBm)")
            return True

        except Exception as e:
            self.log(f"Spiral search error: {e}", "error")
            self._report(100.0, f"Spiral: error ({e})")
            return False

    async def gradient_search(self) -> bool:
        try:
            self.log("Starting gradient search refinement", "info")
            self._report(20.0, "Gradient: starting")
            iters = max(1, int(self.max_gradient_iters))
            total_probes = 4 * iters + 1
            probes_done = 0

            if self.best_position is None:
                # Initial positions
                x = await self.stage_manager.get_position(AxisType.X)
                y = await self.stage_manager.get_position(AxisType.Y)
                self.best_position = [x.actual, y.actual]

            lm, ls = self.nir_manager.read_power()
            current = self._select_detector_channel(lm, ls)
            self.lowest_loss = current

            # Step schedule
            total_shrink = max(0.0, self.step_size - self.min_gradient_ss)
            grad_step = self.grad_step if self.grad_step > 0 else (total_shrink / iters)

            ss = self.step_size
            # Probe order: +/-X then +/-Y
            axes = [(AxisType.X, +1), (AxisType.X, -1), (AxisType.Y, +1), (AxisType.Y, -1)]
            tried_min_step = False

            while ss >= self.min_gradient_ss:
                if self._cancelled() or (time.monotonic() - self._start_time) > self.timeout_s:
                    self._report(min(99.0, 100.0 * probes_done / total_probes), "Gradient: canceled/timeout")
                    return False

                improved = False
                best_axis, best_dir, best_val = None, 0, self.lowest_loss

                # Probe each direction using the current step size
                for axis, direction in axes:
                    if self._cancelled():
                        self._report(min(99.0, 100.0 * probes_done / total_probes), "Gradient: canceled")
                        return False

                    await self.stage_manager.move_axis(axis, ss * direction, relative=True, wait_for_completion=True)
                    lm, ls = self.nir_manager.read_power()
                    val = self._select_detector_channel(lm, ls)

                    # Immediately move back
                    await self.stage_manager.move_axis(axis, -ss * direction, relative=True, wait_for_completion=True)

                    if val > best_val:
                        best_axis, best_dir, best_val = axis, direction, val
                        improved = True

                    probes_done += 1
                    self._report(min(99.0, 100.0 * probes_done / total_probes),
                                 f"Gradient(ss={ss:.3g}): probing…")

                if self._cancelled():
                    self._report(min(99.0, 100.0 * probes_done / total_probes), "Gradient: canceled")
                    return False

                if improved and best_axis is not None:
                    # Commit the best probing direction
                    await self.stage_manager.move_axis(best_axis, ss * best_dir, relative=True, wait_for_completion=True)

                    # Update from controller
                    x = await self.stage_manager.get_position(AxisType.X)
                    y = await self.stage_manager.get_position(AxisType.Y)
                    self.best_position = [x.actual, y.actual]

                    self.lowest_loss = best_val
                    current = best_val

                    self._report(min(99.0, 100.0 * probes_done / total_probes),
                                 f"Gradient: improved → {self.lowest_loss:.2f} dBm")

                    if self.lowest_loss >= self.threshold:
                        self.log(f"Gradient met threshold at {self.lowest_loss:.2f} dBm", "info")
                        self._report(100.0, f"Gradient: threshold {self.lowest_loss:.2f} dBm")
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
            self._report(100.0, f"Gradient: error ({e})")
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
