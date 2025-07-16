import ctypes
import sys

from .base import BaseMemory

if sys.platform != "win32":
    raise ImportError("This module only supports Windows.")


class Win32Memory(BaseMemory):
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        # ... VirtualAlloc setup ...
        self.kernel32.VirtualAlloc.restype = ctypes.c_void_p
        self.kernel32.VirtualAlloc.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        # ... VirtualFree setup ...
        self.kernel32.VirtualFree.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_ulong,
        ]

    def get(self, size: int, executable: bool = False) -> int:
        PAGE_EXECUTE_READWRITE = 0x40
        PAGE_READWRITE = 0x04
        protect = PAGE_EXECUTE_READWRITE if executable else PAGE_READWRITE

        MEM_COMMIT = 0x1000
        MEM_RESERVE = 0x2000
        allocation_type = MEM_COMMIT | MEM_RESERVE

        address = self.kernel32.VirtualAlloc(0, size, allocation_type, protect)
        if not address:
            raise MemoryError("VirtualAlloc failed to allocate memory")
        return address

    def release(self, address: int, size: int):
        MEM_RELEASE = 0x8000
        if self.kernel32.VirtualFree(address, 0, MEM_RELEASE) == 0:
            raise MemoryError(f"VirtualFree failed to free memory at {hex(address)}")
