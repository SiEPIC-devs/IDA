# common_struct.py
import ctypes

class StagePositionStruct(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_double),
        ("is_homed", ctypes.c_bool),
    ]
