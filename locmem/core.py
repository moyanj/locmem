import ctypes
from typing import Any, Callable, Optional, Tuple, Type


class MemoryError(Exception):
    """Base class for all memory errors."""

    pass


class Pointer:
    """Pointer to a memory location. Dereference function is set by a memory allocator."""

    def __init__(self, value: int):
        if not isinstance(value, int):
            raise TypeError("Pointer value must be an integer.")
        self.value = value
        self._free_func = None  # 解引用函数由内存分配器设置
        self.freed = False

    def __repr__(self):
        return f"Pointer({hex(self.value)})"

    def __eq__(self, other):
        if isinstance(other, Pointer):
            return self.value == other.value
        elif isinstance(other, int):
            return self.value == other
        else:
            return False

    def __hash__(self):
        return hash(self.value)

    def __int__(self):
        return self.value

    def __add__(self, other):
        if isinstance(other, int):
            return Pointer(self.value + other)
        elif isinstance(other, Pointer):
            return Pointer(self.value + other.value)
        else:
            raise TypeError("Cannot add non-integer or non-Pointer to a Pointer.")

    def __sub__(self, other):
        if isinstance(other, int):
            return Pointer(self.value - other)
        elif isinstance(other, Pointer):
            return Pointer(self.value - other.value)
        else:
            raise TypeError(
                "Cannot subtract non-integer or non-Pointer from a Pointer."
            )

    def __radd__(self, other):
        if isinstance(other, int):
            return Pointer(other + self.value)
        else:
            raise TypeError("Cannot add non-integer to a Pointer.")

    def __rsub__(self, other):
        if isinstance(other, int):
            return Pointer(other - self.value)
        else:
            raise TypeError("Cannot subtract a Pointer from non-integer.")

    def __iadd__(self, other):
        if isinstance(other, int):
            self.value += other
            return self
        else:
            raise TypeError("Cannot add non-integer to a Pointer.")

    def __isub__(self, other):
        if isinstance(other, int):
            self.value -= other
            return self
        else:
            raise TypeError("Cannot subtract non-integer from a Pointer.")

    def __str__(self):
        return hex(self.value)

    def free(self):
        """Dereference the pointer using the function set by the memory allocator."""
        if self._free_func is not None:
            self._free_func(self)
            self.freed = True

    def _set_hook(self, func: Callable):
        """Internal method to set the dereference function (intended for memory allocators)."""
        if not callable(func):
            raise TypeError("Function must be callable.")
        self._free_func = func

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.free()

    def __del__(self):
        self.free()


def memread(address: Pointer, size: int) -> bytes:
    """从指定内存地址读取字节数据"""
    if address.freed:
        raise ValueError("Cannot read from freed memory")
    buffer = (ctypes.c_byte * size)()
    ctypes.memmove(buffer, address.value, size)
    return bytes(buffer)


def memwrite(address: Pointer, data: bytes):
    """向指定内存地址写入字节数据。"""
    if address.freed:
        raise ValueError("Cannot write to freed memory")
    ctypes.memmove(address.value, data, len(data))


def memcpy(dest: Pointer, src: Pointer, size: int):
    """
    将指定大小的字节数据从源内存地址复制到目标内存地址。
    """
    if not isinstance(dest, Pointer):
        raise TypeError("dest must be a Pointer object.")
    if not isinstance(src, Pointer):
        raise TypeError("src must be a Pointer object.")
    if not isinstance(size, int) or size < 0:
        raise ValueError("size must be a non-negative integer.")
    if dest.freed:
        raise MemoryError(f"Cannot copy to freed memory (destination: {dest}).")
    if src.freed:
        raise MemoryError(f"Cannot copy from freed memory (source: {src}).")

    # ctypes.memmove 能够处理源和目标重叠的情况，因此直接用它即可
    ctypes.memmove(dest.value, src.value, size)


def memset(address: Pointer, value: int, size: int):
    """
    使用指定的字节值填充指定内存区域。
    """
    if not isinstance(address, Pointer):
        raise TypeError("address must be a Pointer object.")
    if not isinstance(value, int):
        raise TypeError("value must be an integer.")
    if not (0 <= value <= 255):
        raise ValueError("value must be an integer between 0 and 255.")
    if not isinstance(size, int) or size < 0:
        raise ValueError("size must be a non-negative integer.")

    if address.freed:
        raise ValueError(f"Cannot write to freed memory (address: {address}).")

    # 使用 ctypes.memset 进行内存填充
    ctypes.memset(address.value, value, size)


def memexec(
    address: Pointer,
    argtypes: Optional[Tuple[Any, ...]] = None,
    restype: Optional[Type[Any]] = None,
) -> Callable:
    if address.freed:
        raise ValueError("Cannot execute from freed memory")
    if not isinstance(argtypes, tuple):
        argtypes = (argtypes,)

    argtypes_tuple: Tuple[Type[Any], ...] = argtypes if argtypes is not None else ()

    func_type = ctypes.CFUNCTYPE(restype, *argtypes_tuple)

    func_ptr = func_type(address.value)

    return func_ptr
