import asyncio
import numpy as np
from typing import Dict, Any, Tuple

from motors.stage_manager import StageManager
from motors.hal.motors_hal import AxisType
from NIR.nir_manager import NIRManager
from utils.logging_helper import setup_logger

import logging

"""
Made by: Cameron Basara, 2025
Fine alignment module for optical coupling using spiral and gradient search.
"""

class FineAlign:
    """
    Perform fine alignment by optimizing optical coupling using spiral, gradient, and optional crosshair search.
    """

    def __init__(self, config: Dict[str, Any], stage_manager: StageManager, nir_manager: NIRManager, debug: bool = False):
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
        self.use_crosshair = config.get("use_crosshair", False)
        self.primary_detector = config.get("primary_detector", "ch1")
        
        self._log(f"FineAlign initialized with detector: {self.primary_detector}")
        self._stop_requested = False

    async def begin_fine_align(self) -> bool:
        """
        Run the fine alignment process: spiral → gradient → optional crosshair.
        """
        try:
            ok_stage = await self.stage_status()
            if not ok_stage:
                raise Exception("Stage manager not ready")
            ok_nir = await self.nir_status()
            if not ok_nir:
                raise Exception("NIR instrument manager not ready") 

            x_pos = await self.stage_manager.get_position(AxisType.X)
            x_pos = x_pos.actual
            y_pos = await self.stage_manager.get_position(AxisType.Y)
            y_pos = y_pos.actual
            
            # Start spiral search
            result = await self.spiral_search(x_pos, y_pos) 
            if result: 
                self._log("Spiral search completed successfully, proceeding with gradient search", "info")

            # Gradient refinement
            await self.gradient_search()  

            # Optional crosshair, probably never going to be used
            if self.use_crosshair:
                await self.crosshair_search()
            return True

        except Exception as e:
            self._log(f"Fine alignment failed: {e}", "error")
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
            
            self._log(f"Starting spiral search from ({x_pos:.2f}, {y_pos:.2f}) with detector: {self.primary_detector}")
            
            best = {"loss": detect, "position": (x_pos, y_pos)}

            while num_steps < limit and not self._stop_requested:
                # X movement
                for _ in range(num_steps):
                    await self.stage_manager.move_axis(AxisType.X, step * direction, relative=True, wait_for_completion=True)
                    x_pos += step * direction
                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_loss = self._select_detector_channel(loss_master, loss_slave)
                    if current_loss > best["loss"]:
                        best["loss"] = current_loss
                        best["position"] = (x_pos, y_pos)
                        self._log(f"New best position: ({x_pos:.2f}, {y_pos:.2f}) with power: {current_loss:.2f}dBm", "debug")

                # Y movement
                for _ in range(num_steps):
                    await self.stage_manager.move_axis(AxisType.Y, step * direction, relative=True, wait_for_completion=True)
                    y_pos += step * direction
                    loss_master, loss_slave = self.nir_manager.read_power()
                    current_loss = self._select_detector_channel(loss_master, loss_slave)
                    if current_loss > best["loss"]:
                        best["loss"] = current_loss
                        best["position"] = (x_pos, y_pos)
                        self._log(f"New best position: ({x_pos:.2f}, {y_pos:.2f}) with power: {current_loss:.2f}dBm", "debug")

                # Increase step count and flip direction
                num_steps += 1
                direction *= -1

            # Go to best position
            self._log(f"Moving to best position: ({best['position'][0]:.2f}, {best['position'][1]:.2f}) with power: {best['loss']:.2f}dBm")
            xok = await self.stage_manager.move_axis(AxisType.X, best["position"][0], relative=False, wait_for_completion=True)
            yok = await self.stage_manager.move_axis(AxisType.Y, best["position"][1], relative=False, wait_for_completion=True)

            if (xok and yok):
                self._log("Spiral search completed successfully")
                return True 
            else:
                self._log("Failed to move to best position", "error")
                return False
        
        except Exception as e:
            self._log(f"Spiral search error: {e}", "error")
            return False

    async def gradient_search(self):
        """Perform gradient-based fine alignment refinement."""
        try:
            self._log("Starting gradient search refinement")
            for iteration in range(self.max_gradient_iters):
                if self._stop_requested:
                    self._log("Gradient search stopped by user request")
                    break
                loss_master, loss_slave = self.nir_manager.read_power()
                current_detect = self._select_detector_channel(loss_master, loss_slave)
                
                best_loss = current_detect
                best_axis, best_dir = None, 0
                self._log(f"Gradient iteration {iteration+1}/{self.max_gradient_iters}, current power: {current_detect:.2f}dBm", "debug")

                # Test X+
                await self.stage_manager.move_axis(AxisType.X, self.step_size, relative=True, wait_for_completion=True)
                loss_xp_m, loss_xp_s = self.nir_manager.read_power()
                loss_xp = self._select_detector_channel(loss_xp_m, loss_xp_s)
                if loss_xp > best_loss:
                    best_loss, best_axis, best_dir = loss_xp, AxisType.X, +1
                await self.stage_manager.move_axis(AxisType.X, -self.step_size, relative=True, wait_for_completion=True)

                # Test X-
                await self.stage_manager.move_axis(AxisType.X, -self.step_size, relative=True, wait_for_completion=True)
                loss_xn_m, loss_xn_s = self.nir_manager.read_power()
                loss_xn = self._select_detector_channel(loss_xn_m, loss_xn_s)
                if loss_xn > best_loss:
                    best_loss, best_axis, best_dir = loss_xn, AxisType.X, -1
                await self.stage_manager.move_axis(AxisType.X, self.step_size, relative=True, wait_for_completion=True)

                # Test Y+
                await self.stage_manager.move_axis(AxisType.Y, self.step_size, relative=True, wait_for_completion=True)
                loss_yp_m, loss_yp_s = self.nir_manager.read_power()
                loss_yp = self._select_detector_channel(loss_yp_m, loss_yp_s)
                if loss_yp > best_loss:
                    best_loss, best_axis, best_dir = loss_yp, AxisType.Y, +1
                await self.stage_manager.move_axis(AxisType.Y, -self.step_size, relative=True, wait_for_completion=True)

                # Test Y-
                await self.stage_manager.move_axis(AxisType.Y, -self.step_size, relative=True, wait_for_completion=True)
                loss_yn_m, loss_yn_s = self.nir_manager.read_power()
                loss_yn = self._select_detector_channel(loss_yn_m, loss_yn_s)
                if loss_yn > best_loss:
                    best_loss, best_axis, best_dir = loss_yn, AxisType.Y, -1
                await self.stage_manager.move_axis(AxisType.Y, self.step_size, relative=True, wait_for_completion=True)

                if best_axis:
                    await self.stage_manager.move_axis(best_axis, self.step_size * best_dir, relative=True, wait_for_completion=True)
                else:
                    self._log("Gradient search converged")
                    break  # No improvement
            return True
        except Exception as e:
            self._log(f"Gradient search error: {e}", "error")
            return False

    async def crosshair_search(self):
        """
        Sweep full X then Y, move to positions with max loss.
        """
        # later
        raise NotImplementedError
    
        try:
            # Sweep X
            half_range = self.scan_window / 2.0
            await self.stage_manager.move_axis(AxisType.X, -half_range, relative=True, wait_for_completion=True)
            positions_x, losses_x = [], []
            steps = int(self.scan_window / self.step_size)

            for _ in range(steps):
                loss = await self.nir_manager.sweep()
                pos = (await self.stage_manager.get_position(AxisType.X)).actual
                positions_x.append(pos)
                losses_x.append(loss)
                await self.stage_manager.move_axis(AxisType.X, self.step_size, relative=True, wait_for_completion=True)

            best_x = positions_x[np.argmax(losses_x)]
            await self.stage_manager.move_axis(AxisType.X, best_x, relative=False, wait_for_completion=True)

            # Sweep Y
            await self.stage_manager.move_axis(AxisType.Y, -half_range, relative=True, wait_for_completion=True)
            positions_y, losses_y = [], []
            for _ in range(steps):
                loss = await self.nir_manager.sweep()
                pos = (await self.stage_manager.get_position(AxisType.Y)).actual
                positions_y.append(pos)
                losses_y.append(loss)
                await self.stage_manager.move_axis(AxisType.Y, self.step_size, relative=True, wait_for_completion=True)

            best_y = positions_y[np.argmax(losses_y)]
            await self.stage_manager.move_axis(AxisType.Y, best_y, relative=False, wait_for_completion=True)

            return True
        except Exception as e:
            self._log(f"Crosshair search error: {e}", "error")
            return False
    
    def _log(self, message: str, level: str = "info"):
        """Simple logging that respects debug flag"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
    
    def _select_detector_channel(self, loss_master: float, loss_slave: float) -> float:
        """Select detector channel based on config"""
        if self.primary_detector == "ch1":
            return loss_master
        elif self.primary_detector == "ch2":
            return loss_slave
        else:
            # Default to best (highest power)
            return max(loss_master, loss_slave)

    async def stage_status(self):
        """Check stage manager status"""
        try:
            return self.stage_manager is not None
        except Exception as e:
            self._log(f"Stage status check error: {e}", "error")
            return False

    async def nir_status(self):
        """Check NIR manager status"""
        try:
            return self.nir_manager is not None and self.nir_manager.is_connected()
        except Exception as e:
            self._log(f"NIR status check error: {e}", "error")
            return False
    
    def stop_alignment(self):
        """Request to stop the fine alignment process"""
        self._log("Fine alignment stop requested")
        self._stop_requested = True
        
    def reset_stop_flag(self):
        """Reset stop flag for new alignment"""
        self._stop_requested = False
