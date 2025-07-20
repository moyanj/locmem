from typing import Optional
from locmem.allocator.base import BaseAllocator
import ctypes
import sys
from locmem.core import Pointer


class MiMallocAllocator(BaseAllocator):
    """
    基于MiMalloc的内存分配器
    """

    def __init__(self, path: Optional[str] = None):
        if path is not None:
            self._mimalloc = ctypes.CDLL(path)
        else:
            self._mimalloc = ctypes.CDLL(
                "mimalloc.dll" if sys.platform == "win32" else "libmimalloc.so"
            )
        self._mi_alloc = self._mimalloc.mi_malloc
        self._mi_alloc.restype = ctypes.c_void_p
        self._mi_alloc.argtypes = [ctypes.c_size_t]
        self._mi_free = self._mimalloc.mi_free
        self._mi_free.argtypes = [ctypes.c_void_p]
        self._mi_free.restype = None

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        if executable:
            raise MemoryError("MiMalloc does not support executable memory")
        addr = self._mi_alloc(size)
        if addr == 0:
            raise MemoryError("Failed to allocate memory")
        ptr = Pointer(addr)
        ptr._set_hook(self.free)
        return ptr

    def free(self, ptr: Pointer):
        if ptr.freed:
            return
        self._mi_free(ptr.value)
        ptr.freed = True
