from locmem.core import Pointer
from locmem.os_mem import get_memory, release_memory  # 从OS层导入接口

from .base import BaseAllocator


class HeapAllocator(BaseAllocator):
    """
    一个简单的堆分配器
    """

    def __init__(self):
        super().__init__()
        # 存储对底层OS内存操作函数的引用，以便调用
        self._allocated_blocks = {}
        self._get_raw_memory = get_memory
        self._release_raw_memory = release_memory

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        """
        分配一块内存。
        """
        if size <= 0:
            raise ValueError("Allocation size must be a positive integer.")
        address = self._get_raw_memory(size, executable)

        ptr = Pointer(address)

        self._allocated_blocks[ptr] = size

        # 4. 设置钩子，让指针知道如何通过这个分配器来释放自己
        ptr._set_hook(self.free)

        return ptr

    def free(self, ptr: Pointer):
        """
        释放由该分配器分配的内存。
        """
        if not isinstance(ptr, Pointer):
            raise TypeError("Argument to free must be a Pointer object.")

        if ptr.freed:
            return

        if ptr not in self._allocated_blocks:
            raise ValueError(
                f"Invalid pointer: {ptr} was not allocated by this allocator."
            )

        size = self._allocated_blocks.pop(ptr)
        self._release_raw_memory(ptr.value, size)
        ptr.freed = True
