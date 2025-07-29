from abc import ABC, abstractmethod

from locmem.core import Pointer
from threading import Lock


class BaseAllocator(ABC):
    """
    内存分配器接口的抽象基类。
    定义了分配和释放内存的基本操作。
    """

    def __init__(self):
        self._lock = Lock()
    @abstractmethod
    def alloc(self, size: int, executable: bool = False) -> Pointer:
        """分配一块指定大小的内存，返回一个指针。"""
        pass

    @abstractmethod
    def free(self, ptr: Pointer):
        """释放一个指针指向的内存块。"""
        pass
