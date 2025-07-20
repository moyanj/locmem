from locmem.core import Pointer

from .base import BaseAllocator
from .binned import BinnedAllocator
from .heap import HeapAllocator
from .mimalloc import MiMallocAllocator
from .libc_malloc import LibcAllocator
from .tcmalloc import TcMallocAllocator

global_allocator = BinnedAllocator()


def set_global_allocator(allocator: BaseAllocator):
    """Set the global memory allocator."""
    global global_allocator
    global_allocator = allocator


def alloc(size: int, executable: bool = False) -> Pointer:
    """Use the global memory allocator to allocate memory."""
    return global_allocator.alloc(size, executable)


def free(ptr: Pointer):
    """Use the global memory allocator to free memory."""
    global_allocator.free(ptr)


__all__ = [
    "BaseAllocator",
    "global_allocator",
    "alloc",
    "free",
    "HeapAllocator",
    "BinnedAllocator",
    "MiMallocAllocator",
    "LibcAllocator",
    "TcMallocAllocator",
    "set_global_allocator",
]
