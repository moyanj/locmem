from abc import ABC, abstractmethod

from locmem.core import Pointer


class BaseMemory(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get(self, size: int, executable: bool = False) -> int:
        raise NotImplementedError

    @abstractmethod
    def release(self, address: int, size: int):
        raise NotImplementedError
