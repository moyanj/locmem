from __future__ import annotations

import struct
from typing import Any, Generic, Optional, TypeVar, Union

from locmem.allocator import alloc, free
from locmem.core import Pointer, memread, memwrite

DataType = TypeVar("DataType")
NumberType = TypeVar("NumberType", int, float, str, bool, bytes)
Numeric = Union[int, float]

__all__ = [
    "BaseType",
    "StructBaseType",
    "Short",
    "UShort",
    "Int",
    "UInt",
    "Long",
    "ULong",
    "LongLong",
    "ULongLong",
    "Float",
    "Double",
    "Char",
    "Bool",
    "VoidPtr",
]


class ComparableMixin:
    """
    为子类提供比较、字符串和布尔转换能力的 Mixin。
    要求宿主类必须实现 `value` 属性。
    """

    value: Any

    def _resolve(self, other: Any) -> Any:
        if isinstance(other, BaseType):
            return other.value
        return other

    def __eq__(self, other: Any) -> bool:
        try:
            return self.value == self._resolve(other)
        except (TypeError, ValueError):
            # 如果类型不兼容导致比较失败，应返回 False
            return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        return self.value < self._resolve(other)

    def __le__(self, other: Any) -> bool:
        return self.value <= self._resolve(other)

    def __gt__(self, other: Any) -> bool:
        return self.value > self._resolve(other)

    def __ge__(self, other: Any) -> bool:
        return self.value >= self._resolve(other)

    def __str__(self) -> str:
        return str(self.value)

    def __bool__(self) -> bool:
        return bool(self.value)


class ArithmeticMixin(ComparableMixin):
    """
    为子类提供完整的算术运算能力的 Mixin。
    继承自 ComparableMixin 以获得所有比较能力。
    """

    def _resolve(self, other: Any) -> Numeric:
        if isinstance(other, Char):
            return ord(other.value)  # b'A' -> 65
        if isinstance(other, BaseType):
            # 包括 Bool, 其 .value (True/False) 会被自动转为 1/0
            return int(other.value)
        if isinstance(other, (int, float, bool)):
            return other
        raise TypeError(
            f"Unsupported operand type(s) for arithmetic: '{type(other).__name__}'"
        )

    # --- 算术运算符 ---
    def __add__(self, other: Any):
        return self.__class__(self._resolve(self.value) + self._resolve(other))  # type: ignore

    def __sub__(self, other: Any):
        return self.__class__(self._resolve(self.value) - self._resolve(other))  # type: ignore

    def __mul__(self, other: Any):
        return self.__class__(self._resolve(self.value) * self._resolve(other))  # type: ignore

    def __truediv__(self, other: Any) -> Double:
        # 除法总是返回 Double 以保证精度
        return Double(self._resolve(self.value) / self._resolve(other))

    def __floordiv__(self, other: Any):
        return self.__class__(self._resolve(self.value) // self._resolve(other))  # type: ignore

    def __mod__(self, other: Any):
        return self.__class__(self._resolve(self.value) % self._resolve(other))  # type: ignore

    def __pow__(self, other: Any):
        return self.__class__(self._resolve(self.value) ** self._resolve(other))  # type: ignore

    # --- 反向算术运算符 ---
    def __radd__(self, other: Any):
        return self.__class__(self._resolve(other) + self._resolve(self.value))  # type: ignore

    def __rsub__(self, other: Any):
        return self.__class__(self._resolve(other) - self._resolve(self.value))  # type: ignore

    def __rmul__(self, other: Any):
        return self.__class__(self._resolve(other) * self._resolve(self.value))  # type: ignore

    def __rtruediv__(self, other: Any) -> Double:
        return Double(self._resolve(other) / self._resolve(self.value))

    def __rfloordiv__(self, other: Any):
        return self.__class__(self._resolve(other) // self._resolve(self.value))  # type: ignore

    def __rmod__(self, other: Any):
        return self.__class__(self._resolve(other) % self._resolve(self.value))  # type: ignore

    # --- 赋值运算符 ---
    def __iadd__(self, other: Any):
        self.value += self._resolve(other)
        return self

    def __isub__(self, other: Any):
        self.value -= self._resolve(other)
        return self

    # --- 数值类型转换 ---
    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)


class BaseType(Generic[DataType]):
    """
    泛型基类，管理内存指针和大小。
    """

    size: int = 0

    def __init__(self, size: int):
        self.ptr: Pointer = alloc(size)
        self.size: int = size

    @property
    def value(self) -> DataType:
        """获取存储的值"""
        return self.get()

    @value.setter
    def value(self, value: DataType) -> None:
        """设置存储的值"""
        self.set(value)

    def get(self) -> DataType:
        """获取存储的值"""
        raise NotImplementedError

    def set(self, value: DataType) -> None:
        """设置存储的值"""
        raise NotImplementedError

    def __del__(self):
        """对象销毁时自动释放内存。"""
        self.free()

    def free(self) -> None:
        """手动释放内存。"""
        free(self.ptr)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.free()

    @classmethod
    def from_ptr(cls, ptr: Pointer):  # 返回类型使用 Self
        """从内存指针创建对象。"""
        if cls.size <= 0:
            raise NotImplementedError(
                f"Class {cls.__name__} must define a positive 'size' class attribute to use from_ptr."
            )
        byte_data = memread(ptr, cls.size)
        # from_bytes 会创建一个新的对象，并为其分配独立的内存
        return cls.from_bytes(byte_data)

    @classmethod
    def from_bytes(cls, data: bytes):  # 返回类型使用 Self
        """从字节序列创建对象。"""
        raise NotImplementedError(
            f"Method 'from_bytes' not implemented for {cls.__name__}."
        )

    def __str__(self):
        return str(self.value)

    def __int__(self):
        return int(self.value)  # type: ignore

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"


class StructBaseType(BaseType[DataType], ArithmeticMixin):
    """
    使用 `struct` 模块进行序列化/反序列化的泛型基类。
    """

    _fmt: str = ""

    def __init__(self, initial_value: DataType):
        if not hasattr(self.__class__, "size") or self.__class__.size <= 0:
            raise ValueError(
                "Concrete subclass of StructBaseType must define a positive 'size' class attribute."
            )
        if not hasattr(self.__class__, "_fmt") or not self.__class__._fmt:
            raise ValueError(
                "Concrete subclass of StructBaseType must define a non-empty '_fmt' class attribute."
            )
        super().__init__(self.__class__.size)
        self._fmt = self.__class__._fmt
        # 初始值在子类中提供，这里直接设置
        self.set(initial_value)

    def get(self) -> DataType:
        """从内存中读取并解包数据。"""
        # struct.unpack 返回一个元组，我们取第一个元素
        return struct.unpack(self._fmt, memread(self.ptr, self.size))[0]

    def set(self, value: DataType) -> None:
        """将数据打包并写入内存。"""
        memwrite(self.ptr, struct.pack(self._fmt, value))

    @classmethod
    def from_bytes(cls, data: bytes):  # 为 StructBaseType 实现 from_bytes
        """从字节序列创建对象。"""
        if not hasattr(cls, "size") or cls.size <= 0:
            raise ValueError(
                f"Class {cls.__name__} must define a positive 'size' class attribute."
            )
        if not hasattr(cls, "_fmt") or not cls._fmt:
            raise ValueError(
                f"Class {cls.__name__} must define a non-empty '_fmt' class attribute."
            )

        if len(data) != cls.size:
            raise ValueError(
                f"Data length ({len(data)}) does not match expected size for {cls.__name__} ({cls.size})."
            )

        # 使用类的格式字符串解包数据
        value = struct.unpack(cls._fmt, data)[0]

        # 用解包后的值创建一个新的实例
        return cls(value)


class Int(StructBaseType[int]):
    size = 4
    _fmt = "<i"


class UInt(StructBaseType[int]):
    size = 4
    _fmt = "<I"


class Long(StructBaseType[int]):
    size = 8
    _fmt = "<l"


class ULong(StructBaseType[int]):
    size = 8
    _fmt = "<L"


class LongLong(StructBaseType[int]):
    size = 16
    _fmt = "<q"


class ULongLong(StructBaseType[int]):
    size = 16
    _fmt = "<Q"


class Short(StructBaseType[int]):
    size = 2
    _fmt = "<h"


class UShort(StructBaseType[int]):
    size = 2
    _fmt = "<H"


class Float(StructBaseType[float]):
    size = 4
    _fmt = "<f"


class Double(StructBaseType[float]):
    size = 8
    _fmt = "<d"


class Char(StructBaseType[bytes]):
    size = 1
    _fmt = "<c"

    def __init__(self, initial_value: Union[bytes, str] = b"\x00"):
        if isinstance(initial_value, str):
            initial_value = initial_value.encode("utf-8")
        if not isinstance(initial_value, bytes) or len(initial_value) != 1:
            raise TypeError("Char initial_value must be a single byte or string.")
        super().__init__(initial_value)


class VoidPtr(BaseType[Pointer]):
    def __init__(self, initial_value: Optional[Pointer] = None):
        super().__init__(8)
        if initial_value is None:
            initial_value = Pointer(0)
        self.set(initial_value)

    def set(self, value: Pointer):
        memwrite(self.ptr, value.value.to_bytes(self.size, "little"))

    def get(self) -> Pointer:
        return Pointer(int.from_bytes(memread(self.ptr, self.size), "little"))

    @classmethod
    def from_bytes(cls, data: bytes) -> "VoidPtr":
        return cls(Pointer(int.from_bytes(data, "little")))


class Bool(BaseType[bool]):
    size = 1

    def __init__(self, initial_value: bool = False):
        super().__init__(self.__class__.size)
        self.set(initial_value)

    def set(self, value: bool):
        memwrite(self.ptr, bytes([1 if value else 0]))

    def get(self) -> bool:
        return memread(self.ptr, self.size)[0] != 0

    @classmethod
    def from_bytes(cls, data: bytes) -> "Bool":
        return cls(data[0] != 0)
