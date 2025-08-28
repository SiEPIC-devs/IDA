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
        
        # Setup logger
        self.logger = setup_logger("AreaSweep", "SWEEP", debug_mode=debug)
        self._log("AreaSweep initialized")
        self._stop_requested = False

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
            
            self._log(f"Starting area sweep: {x_len}x{y_len} with steps ({x_step}, {y_step})")
            
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

            # Initial measurement
            loss_master, loss_slave = self.nir_manager.read_power() 
            initial_power = max(loss_master, loss_slave)
            x_data.append(initial_power)
            self._log(f"Starting position: ({x_pos:.2f}, {y_pos:.2f}) with power: {initial_power:.2f}dBm")
            
            
            parity = lambda step, n: step if (n%2) != 0 else -step  # helper for parity switchin

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
                        axis = AxisType.X,
                        position = step,
                        relative = True,
                        wait_for_completion = True)
                    
                    loss_master, loss_slave = self.nir_manager.read_power() 
                    current_power = max(loss_master, loss_slave)
                    x_data.append(current_power)
                    x_pos += step
                
                data.append(x_data)
                x_data = []
                
                # After a row has been measured, move y axis take the initial measurement
                if not self._stop_requested:
                    await self.stage_manager.move_axis(
                            axis = AxisType.Y,
                            position = y_step,
                            relative = True,
                            wait_for_completion = True)
                    loss_master, loss_slave = self.nir_manager.read_power() # some params
                    current_power = max(loss_master,loss_slave)
                    x_data.append(current_power)
                    y_pos += y_step
                    point_count += 1
            
            # Once area sweep is complete, return the data as np.array
            if self._stop_requested:
                self._log(f"Area sweep stopped early.")
            else:
                self._log(f"Area sweep completed. Total points: {point_count}")
            return np.array(data)

        except Exception as e:
            self._log(f"Area sweep error: {e}", "error")
            raise            

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
            return self.stage_manager is not None
        except Exception as e:
            self._log(f"Stage status check error: {e}", "error")
            return False
    
    async def nir_status(self):
        """Ensure NIR manager instance is alive"""
        try:
            return self.nir_manager is not None and self.nir_manager.is_connected()
        except Exception as e:
            self._log(f"NIR status check error: {e}", "error")
            return False
        