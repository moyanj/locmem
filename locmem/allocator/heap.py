from .base import BaseAllocator
from locmem.core import Pointer
from locmem.os_mem import get_memory, release_memory  # 从OS层导入接口


class HeapAllocator(BaseAllocator):
    """
    一个简单的堆分配器
    """

    def __init__(self):
        super().__init__()
        # 存储对底层OS内存操作函数的引用，以便调用
        self._get_raw_memory = get_memory
        self._release_raw_memory = release_memory

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        """
        分配一块内存。

        1. 调用OS内存管理器获取原始内存地址。
        2. 创建一个Pointer对象来包装该地址。
        3. 记录这次分配（指针和大小）。
        4. 为Pointer对象设置回收钩子。
        5. 返回Pointer对象。
        """
        if size <= 0:
            raise ValueError("Allocation size must be a positive integer.")

        # 1. 从OS层获取内存
        address = self._get_raw_memory(size, executable)

        # 2. 创建指针
        ptr = Pointer(address)

        # 3. 记账：记录指针和它对应的大小
        self._allocated_blocks[ptr] = size

        # 4. 设置钩子，让指针知道如何通过这个分配器来释放自己
        ptr._set_hook(self.free)

        # 5. 返回指针
        return ptr

    def free(self, ptr: Pointer):
        """
        释放由该分配器分配的内存。

        1. 验证指针的有效性。
        2. 从记录中查找并移除该指针，获取其大小。
        3. 调用OS内存管理器归还内存。
        4. 将指针标记为“已释放”。
        """
        if not isinstance(ptr, Pointer):
            raise TypeError("Argument to free must be a Pointer object.")

        if ptr.freed:
            # 允许重复释放，不抛出异常，行为更像标准的free
            return

        if ptr not in self._allocated_blocks:
            raise ValueError(
                f"Invalid pointer: {ptr} was not allocated by this allocator."
            )

        # 2. 从记录中弹出指针，同时获得其大小
        size = self._allocated_blocks.pop(ptr)

        # 3. 调用OS层归还内存
        self._release_raw_memory(ptr.value, size)

        # 4. 标记指针状态
        ptr.freed = True
