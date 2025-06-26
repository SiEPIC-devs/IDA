import functools
import asyncio
from typing import Callable, TypeVar, Awaitable
from modern_stage import AxisType

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
        # only update if you’ve initialized stage_pos
        if hasattr(self, "stage_pos"):
            # assume your manager tracks which axes have been homed in self._homed_axes
            self.stage_pos.update(homed_axes=self._homed_axes)
        return result
    return wrapper  # type: ignore