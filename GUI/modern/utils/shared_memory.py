import struct
import ctypes
import json
from multiprocessing import shared_memory, Process
from time import monotonic
from typing import Optional

from modern.config.stage_position import StagePosition, StagePositionStruct
from modern.config.stage_config import StageConfiguration

"""
Helper functions to share stage position memory w the manager
"""

def create_shared_stage_position() ->  tuple[shared_memory.SharedMemory, StagePositionStruct]:
    """
    Create shared-memory block

    TODO:
        Add functionality to support multiple stages "factory" style
    """
    # Create shared mem
    size = ctypes.sizeof(StagePositionStruct)
    shm = shared_memory.SharedMemory(name="stage_position",create=True,size=size)
    # Map shm to struct instance
    view = StagePositionStruct.from_buffer(shm.buf)
    view.__init__()
    return shm, view

def open_shared_stage_position(name: str = "stage_position") -> tuple[shared_memory.SharedMemory, StagePositionStruct]:
    """
    Attach to an existing shared mem block, to be used in child processes or GUI
    """
    shm = shared_memory.SharedMemory(name=name)
    view = StagePositionStruct.from_buffer(shm.buf)
    return shm, view

def safe_shm_shutdown(shm: shared_memory.SharedMemory, view: Optional[object] = None) -> None:
    if view is not None:
        # Delete any Structure that holds buffer refs
        del view
    
    # Just force garbage collection to clean up any remaining references
    import gc
    gc.collect()
    
    # Close the shared memory
    shm.close()
    
    # Unlink (only the creator should do this)
    try:
        shm.unlink()
    except FileNotFoundError:
        # Already unlinked, that's fine
        pass
    except Exception as e:
        # Other processes might still be using it
        print(f"Warning: Could not unlink shared memory: {e}")

"""
Helper functions to create shared memory ipc for json (serialization)
"""

# SHM and json framing consts
MAX_PAYLOAD = 2048
SHM_SIZE = 4 + MAX_PAYLOAD # 4 byte u_int32
_LEN_STRUCT = struct.Struct("<I") # 4 byte u_int32 length header 
SHM_NAME = "stage_config" # fixed shared mem name

def create_shared_stage_config(name: str = SHM_NAME) ->  shared_memory.SharedMemory:
    """
    Create shared-memory block for json serialization

    TODO:
        Add functionality to support multiple stages "factory" style
    """
    shm = shared_memory.SharedMemory(name=name, create=True, size=SHM_SIZE)

    # zero the block
    shm.buf[:] = b'\x00' * SHM_SIZE
    return shm

def open_shared_stage_config(name: str = SHM_NAME) -> shared_memory.SharedMemory:
    """
    Attach to an existing shared-memory block
    """
    return shared_memory.SharedMemory(name=name)

def read_shared_stage_config(shm: shared_memory.SharedMemory) -> StageConfiguration:
    """
    Read from shared-memory block 
    """ 
    # Unpacked serialized JSON buf 
    (length,) = _LEN_STRUCT.unpack_from(shm.buf, 0) 
    
    if length == 0 or length > MAX_PAYLOAD:
        raise BufferError(f"Invalid config length: {length}")
    
    # Convert serialized json to dict and into StageConfiguration format
    raw = bytes(shm.buf[4:4 + length])
    data = json.loads(raw.decode("utf-8"))
    return StageConfiguration.from_dict(data)

def write_shared_stage_config(shm: shared_memory.SharedMemory,
                              config: StageConfiguration) -> None:
    """
    Write serialize config to json into shared-memory buffer
    """
    # Serialize dictionary config
    payload = json.dumps(config.to_dict()).encode("utf-8")
    n = len(payload)
    if n > MAX_PAYLOAD:
        raise BufferError(f"Config too large / not formatted correctly ({n} > {MAX_PAYLOAD})")
    
    # Dump to shm (Header + payload)
    shm.buf[:4] = _LEN_STRUCT.pack(n)
    shm.buf[4:4+n] = payload

    shm.buf[4+n:SHM_SIZE] = b'\x00' * (SHM_SIZE - 4 - n) # zero tail



