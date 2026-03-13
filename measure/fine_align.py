import asyncio
import numpy as np
from typing import Dict, Any, Optional, Callable, Any
import time
import re

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
        self.step_size = config.get("step_size", 5.0)  # microns
        self.scan_window = config.get("scan_window", 45.0)
        self.threshold = config.get("threshold", -45.0)
        self.max_gradient_iters = max(1, config.get("gradient_iters", 10))
        self.min_gradient_ss = config.get("min_gradient_ss", 0.2)  # microns
        self.grad_step = (self.step_size - self.min_gradient_ss) / self.max_gradient_iters
        # self.primary_detector = config.get("primary_detector", "Max")
        # self.slots = config.get("slot", [[0, 1, 0]])  # mf, slot, head
        # if "ch" in self.primary_detector and len(self.slots) > 1:
        #     # Edge case, if not using max, we only want 1 slot 
        #     num = int(re.findall(r'\d+', self.primary_detector)[0])
        #     # Assume mf = 0 for now
        #     if (num%2) == 0:
        #         # if even, then slot is the same
        #         slot_i = num // 2 + 1
        #         head_i = 0
        #     else:
        #         # if odd, then slot-=1
        #         slot_i = num // 2
        #         head_i = 1 
        #     self.slots = [[0, slot_i, head_i]]
        self.primary_detector = config.get("primary_detector", "Max")
        raw_slots = config.get("slots", config.get("slot", [[0, 1, 0]]))  # mf, slot, head

        if isinstance(raw_slots, int):
            slots = [[0, raw_slots, 0]]
        elif isinstance(raw_slots, (list, tuple)):
            if len(raw_slots) == 3 and all(isinstance(x, int) for x in raw_slots):
                slots = [list(raw_slots)]
            elif all(isinstance(row, (list, tuple)) and len(row) == 3 for row in raw_slots):
                slots = [list(row) for row in raw_slots]
            else:
                raise ValueError(f'config["slot"] must be [mf,slot,head] or [[mf,slot,head],...]; got {raw_slots!r}')
        else:
            raise TypeError(f'config["slot"] must be int/list/tuple; got {type(raw_slots).__name__}')

        self.slots = slots

        if "ch" in self.primary_detector.lower():
            m = re.findall(r"\d+", self.primary_detector)
            if not m:
                raise ValueError(f'primary_detector looks like "chX" but no number found: {self.primary_detector!r}')
            num = int(m[0])
            ch_index = num - 1  # Convert to 0-based index

            # Direct lookup from slot_info: CH1=slots[0], CH2=slots[1], etc.
            if ch_index < len(slots):
                self.slots = [slots[ch_index]]
            else:
                self.log(f"WARNING: ch{num} requested but only {len(slots)} slots available; "
                         f"using first slot", "error")
                self.slots = [slots[0]]

        self.ref_wl = config.get("ref_wl", 1550.0)
        self.secondary_wl = config.get("secondary_wl", 1540)
        self.secondary_loss = config.get("secondary_loss", -50.0)  # dBm 
        self.timeout_s = float(config.get("timeout_s", 180.0))
        self._start_time = 0.0

        self.log(f"FineAlign initialized with detector: {self.primary_detector}, slots: {self.slots}", "info")
        self._stop_requested = False

        # Tracking
        self.best_position = None
        self.lowest_loss = -80
        self.spiral_threshold_met = False

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
        Spiral => Gradient descent
        """
        self.is_running = True
        try:
            self.log("Fine alignment starting...", "info")
            self._report(0.0, "Fine alignment: starting...")
            self.nir_manager.enable_laser(True)  # Enforce laser on
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

            if self.lowest_loss <= self.secondary_loss:
                # dBm thresh not met, proceed with secondary wl
                self.log(f"Loss not met, changing to 2ndary wl {self.secondary_wl}.", "info")
                self.nir_manager.set_wavelength(self.secondary_wl)

                # Now, recompute spiral
                aok = await self.spiral_search(self.best_position[0], self.best_position[1])
                if not aok:
                    if self._cancelled():
                        self._report(100.0, "Spiral: canceled")
                    else:
                        self._report(100.0, "Spiral: failed")
                        self.log("Spiral search failed.", "error")
                    return False

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

            final_check = self.get_power()
            self.log(f"Fine align complete: {final_check:.2f} dBm at "
                     f"({self.best_position[0]:.3f}, {self.best_position[1]:.3f})", "info")

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
            # lm, ls = self.nir_manager.read_power(slot=self.slot)
            # best_loss = self._select_detector_channel(lm, ls)
            best_loss = self.get_power()
            x = await self.stage_manager.get_position(AxisType.X)
            y = await self.stage_manager.get_position(AxisType.Y)
            best_pos = [x.actual, y.actual]
            self.lowest_loss = max(self.lowest_loss, best_loss)

            self.log(f"Starting spiral at ({best_pos[0]:.3f}, {best_pos[1]:.3f})", "info")
            if best_loss >= self.threshold:
                self.best_position = best_pos
                self.log("Spiral skipped: threshold already met.", "info")
                self.spiral_threshold_met = True
                return True

            while num_steps <= limit and not self._cancelled():
                # X sweep
                for _ in range(num_steps):
                    if self._cancelled():
                        break
                    await self.stage_manager.move_axis(AxisType.X, step * direction, relative=True, wait_for_completion=True)
                    # lm, ls = self.nir_manager.read_power(slot=self.slot)
                    # val = self._select_detector_channel(lm, ls)
                    val = self.get_power()

                    if val > best_loss:
                        best_loss = val
                        x = await self.stage_manager.get_position(AxisType.X)
                        y = await self.stage_manager.get_position(AxisType.Y)
                        best_pos = [x.actual, y.actual]
                        self.lowest_loss = best_loss
                        if best_loss >= self.threshold:
                            self.log(f"Threshold {self.threshold} met, skipping spiral", "info")
                            self.best_position = best_pos
                            self.spiral_threshold_met = True
                            return True

                    covered += 1
                    self._report(100.0 * covered / total_moves, f"Spiral: step {covered}/{total_moves}")

                if self._cancelled():
                    break

                # Y sweep
                for _ in range(num_steps):
                    if self._cancelled():
                        break
                    await self.stage_manager.move_axis(AxisType.Y, step * direction, relative=True, wait_for_completion=True)
                    val = self.get_power()
                    if val > best_loss:
                        best_loss = val
                        x = await self.stage_manager.get_position(AxisType.X)
                        y = await self.stage_manager.get_position(AxisType.Y)
                        best_pos = [x.actual, y.actual]
                        self.lowest_loss = best_loss
                        if best_loss >= self.threshold:
                            self.log(f"Threshold {self.threshold} met, skipping spiral", "info")
                            self.best_position = best_pos
                            self.spiral_threshold_met = True
                            return True
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
                self.spiral_threshold_met = True
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

            current = self.get_power()
            # Preserve spiral's proven best — noise can make re-read worse
            self.lowest_loss = max(self.lowest_loss, current)

            # Step schedule
            total_shrink = max(0.0, self.step_size - self.min_gradient_ss)
            grad_step = self.grad_step if self.grad_step > 0 else (total_shrink / iters)

            if self.spiral_threshold_met:
                # Threshold met: spiral was close; start at half step for refinement
                ss = min(self.step_size, 3.0) / 2.0
            else:
                # Spiral already searched at full step; refine at half
                ss = self.step_size / 2.0

            # Recompute grad_step based on actual starting step size
            grad_step = max(0.01, (ss - self.min_gradient_ss) / max(1, iters))
            
            # Probe order: +/-X then +/-Y
            axes = [(AxisType.X, +1), (AxisType.X, -1), (AxisType.Y, +1), (AxisType.Y, -1)]
            tried_min_step = False

            # NOTE: threshold is intentionally *not* used as a stopping condition here.
            # Gradient is meant to refine to convergence based on step size / lack of improvement.
            while ss >= self.min_gradient_ss:
                improved = False
                best_axis, best_dir, best_val = None, 0, self.lowest_loss

                # Probe each direction using the current step size
                for axis, direction in axes:
                    if self._cancelled():
                        self._report(min(99.0, 100.0 * probes_done / total_probes), "Gradient: canceled")
                        print(f"GRADIENT: CANCELED")
                        return False

                    await self.stage_manager.move_axis(axis, ss * direction, relative=True, wait_for_completion=True)
                    val = self.get_power()

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
                    print(f"GRADIENT: CANCELED 2")
                    return False

                if improved and best_axis is not None:
                    # Commit the best probing direction
                    await self.stage_manager.move_axis(
                        best_axis, ss * best_dir, relative=True, wait_for_completion=True)

                    # Update from controller
                    x = await self.stage_manager.get_position(AxisType.X)
                    y = await self.stage_manager.get_position(AxisType.Y)
                    self.best_position = [x.actual, y.actual]

                    # Line search: continue in winning direction while improving
                    for _ls in range(3):
                        await self.stage_manager.move_axis(
                            best_axis, ss * best_dir, relative=True, wait_for_completion=True)
                        ls_val = self.get_power()
                        if ls_val > best_val:
                            best_val = ls_val
                            x = await self.stage_manager.get_position(AxisType.X)
                            y = await self.stage_manager.get_position(AxisType.Y)
                            self.best_position = [x.actual, y.actual]
                        else:
                            # Undo last step that didn't improve
                            await self.stage_manager.move_axis(
                                best_axis, -ss * best_dir, relative=True, wait_for_completion=True)
                            break

                    improvement = best_val - self.lowest_loss
                    self.lowest_loss = best_val
                    current = best_val

                    self._report(min(99.0, 100.0 * probes_done / total_probes),
                                 f"Gradient: improved -> {self.lowest_loss:.2f} dBm")

                    # Marginal improvement -> shrink step to probe finer, don't exit
                    if improvement <= 0.05:
                        self.log(f"Gradient: marginal gain ({improvement:.3f} dB) at ss={ss:.3f}, "
                                 f"shrinking step", "info")
                        if ss <= self.min_gradient_ss:
                            if tried_min_step:
                                break
                            tried_min_step = True
                        ss = max(self.min_gradient_ss, ss - grad_step)


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
    
    def get_power(self):
        """Return the requested power by method"""
        if "ch" not in self.primary_detector:
            # Max
            best = -100
            for mf,slot,head in self.slots:
                m = self.nir_manager.read_power(slot=slot, head=head, mf=mf)
                best = max(best, m)
            return best
        else:
            mf, slot, head = self.slots[0]
            loss = self.nir_manager.read_power(slot=slot, head=head, mf=mf)
            return loss

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
