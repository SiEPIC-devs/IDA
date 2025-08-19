import asyncio
import numpy as np
from typing import Dict, Any

from motors.stage_manager import *
from motors.hal.motors_hal import AxisType, Position
from NIR.nir_manager import *

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

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
                 stage_manager: StageManager, nir_manager: NIRManager):
        self.stage_manager = stage_manager
        self.nir_manager = nir_manager
        self.config = area_sweep_config

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
                raise Exception("Invalid stage manager status")
            ok = await self.nir_status()
            if not ok:
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

            # Initial measurement
            loss_master, loss_slave = self.nir_manager.read_power() 
            x_data.append(loss_master)
            
            
            parity = lambda step, n: step if (n%2) == 0 else -step  # helper for parity switchin

            for i in range(y_len // y_step):
                for j in range(x_len // x_step):
                    step = parity(x_step, i)
                    await self.stage_manager.move_axis(
                        axis = AxisType.X,
                        position = step,
                        relative = True,
                        wait_for_completion = True)
                    
                    loss_master, loss_slave = self.nir_manager.read_power() 
                    x_data.append(loss_master)
                    x_pos += step
                data.append(x_data)
                x_data = []
                
                # After a row has been measured, move y axis take the initial measurement
                await self.stage_manager.move_axis(
                        axis = AxisType.Y,
                        position = y_step,
                        relative = True,
                        wait_for_completion = True)
                loss_master, loss_slave = self.nir_manager.read_power() # some params
                x_data.append(loss_master)
                y_pos += y_step
            
            # Once area sweep is complete, return the data as np.array
            return np.array(data)

        except Exception as e:
            logger.error(f"[AREA_SWEEP] Exception found: {e}")
            raise            

    async def stage_status(self):
        """Ensure stage manager instance is alive"""
        return True
    
    async def nir_status(self):
        """Ensure NIR manager instance is alive"""
        return True
        