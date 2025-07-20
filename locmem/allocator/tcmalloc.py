from typing import Optional
from locmem.allocator.base import BaseAllocator
import ctypes
import sys
from locmem.core import Pointer


class TcMallocAllocator(BaseAllocator):
    """
    基于TcMalloc的内存分配器
    """

    def __init__(self, path: Optional[str] = None):
        if path is not None:
            self._tcmalloc = ctypes.CDLL(path)
        else:
            self._tcmalloc = ctypes.CDLL(
                "tcmalloc.dll" if sys.platform == "win32" else "libtcmalloc.so"
            )
        self._tc_alloc = self._tcmalloc.tc_malloc
        self._tc_alloc.restype = ctypes.c_void_p
        self._tc_alloc.argtypes = [ctypes.c_size_t]
        self._tc_free = self._tcmalloc.tc_free
        self._tc_free.argtypes = [ctypes.c_void_p]
        self._tc_free.restype = None

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        if executable:
            raise MemoryError("TcMalloc does not support executable memory")
        addr = self._tc_alloc(size)
        if addr == 0:
            raise MemoryError("Failed to allocate memory")
        ptr = Pointer(addr)
        ptr._set_hook(self.free)
        return ptr

    def free(self, ptr: Pointer):
        if ptr.freed:
            return
        self._tc_free(ptr.value)
        ptr.freed = True
