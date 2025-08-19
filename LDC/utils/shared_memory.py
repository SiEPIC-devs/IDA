import struct
import json
from multiprocessing import shared_memory, Process
from time import monotonic
from typing import Optional

from LDC.config.ldc_config import LDCConfiguration

"""
Helper functions to create shared memory ipc for json (serialization)
"""

# SHM and json framing consts
MAX_PAYLOAD = 2048
SHM_SIZE = 4 + MAX_PAYLOAD # 4 byte u_int32
_LEN_STRUCT = struct.Struct("<I") # 4 byte u_int32 length header 
SHM_NAME = "ldc_config" # fixed shared mem name

def create_shared_ldc_config(name: str = SHM_NAME) ->  shared_memory.SharedMemory:
    """
    Create shared-memory block for json serialization

    """
    shm = shared_memory.SharedMemory(name=name, create=True, size=SHM_SIZE)

    # zero the block
    shm.buf[:] = b'\x00' * SHM_SIZE
    return shm

def open_shared_ldc_config(name: str = SHM_NAME) -> shared_memory.SharedMemory:
    """
    Attach to an existing shared-memory block
    """
    return shared_memory.SharedMemory(name=name)

def read_shared_ldc_config(shm: shared_memory.SharedMemory) -> LDCConfiguration:
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
    return LDCConfiguration.from_dict(data)

def write_shared_ldc_config(shm: shared_memory.SharedMemory,
                              config: LDCConfiguration) -> None:
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



