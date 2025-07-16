from locmem.core import Pointer
from .base import BaseAllocator
from .heap import HeapAllocator
from .binned import BinnedAllocator


# 默认的分配器类型
DefaultAllocator = BinnedAllocator

# 创建一个全局的分配器实例，供整个库使用
global_allocator = DefaultAllocator()


def set_global_allocator(allocator: BaseAllocator):
    """设置全局分配器。"""
    global global_allocator
    global_allocator = allocator


# 提供便捷的顶层函数，代理到全局分配器实例
def alloc(size: int, executable: bool = False) -> Pointer:
    """使用全局分配器分配内存。"""
    return global_allocator.alloc(size, executable)


def free(ptr: Pointer):
    """使用全局分配器释放内存。"""
    global_allocator.free(ptr)


# 定义此模块的公开API
__all__ = [
    "BaseAllocator",
    "DefaultAllocator",
    "global_allocator",
    "alloc",
    "free",
    "HeapAllocator",
    "BinnedAllocator",
    "set_global_allocator",
]
