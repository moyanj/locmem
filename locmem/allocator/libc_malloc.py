from typing import Optional
from locmem.allocator.base import BaseAllocator
import ctypes
from locmem.core import Pointer


class LibcAllocator(BaseAllocator):
    """
    LibC中内存分配器包装
    """

    def __init__(self, path: Optional[str] = None):
        self.libc = ctypes.CDLL(path)
        self._alloc = self.libc.malloc
        self._alloc.restype = ctypes.c_void_p
        self._alloc.argtypes = [ctypes.c_size_t]
        self._free = self.libc.free
        self._free.argtypes = [ctypes.c_void_p]
        self._free.restype = None

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        if executable:
            raise MemoryError("LibcMalloc does not support executable memory")
        addr = self._alloc(size)
        if addr == 0:
            raise MemoryError("Failed to allocate memory")
        ptr = Pointer(addr)
        ptr._set_hook(self.free)
        return ptr

    def free(self, ptr: Pointer):
        if ptr.freed:
            return
        self._free(ptr.value)
        ptr.freed = True
