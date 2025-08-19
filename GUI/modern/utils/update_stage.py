import functools
import asyncio
from typing import Callable, TypeVar, Awaitable, Optional, Dict
from modern.modern_stage import AxisType

F = TypeVar("F", bound=Callable[..., Awaitable])

def update_stage_position(func: F) -> F:
    """
    Decorator for MotorStageManager methods.
    After the wrapped async method completes, calls:
        self.stage_pos.update(homed_axes=self._homed_axes)
    so that your StagePosition always reflects the latest self._last_positions.
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)
        
        # Only update if stage_pos is initialized
        if hasattr(self, "stage_pos") and self.stage_pos is not None:
            # Prepare position data if available
            new_positions: Optional[Dict[AxisType, float]] = None
            if hasattr(self, "_last_positions") and self._last_positions:
                new_positions = self._last_positions
            
            # Prepare homing data if available
            new_homed: Optional[Dict[AxisType, bool]] = None
            if hasattr(self, "_homed_axes") and self._homed_axes:
                # Only pass axes that are actually homed (True values)
                new_homed = {axis: status for axis, status in self._homed_axes.items() if status}
            
            # Update the stage position
            self.stage_pos.update(
                new_positions=new_positions,
                new_homed=new_homed
            )
        
        return result
    
    return wrapper  # type: ignore