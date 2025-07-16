from .base import BaseMemory
import ctypes
import sys

if "linux" not in sys.platform and "darwin" not in sys.platform:
    raise ImportError("This module only supports POSIX-compliant.")


class PosixMemory(BaseMemory):
    def __init__(self):
        super().__init__()
        # 在Linux上是libc.so.6, 在macOS上是libSystem.B.dylib
        lib_name = "libc.so.6" if "linux" in sys.platform else "libSystem.B.dylib"
        self.libc = ctypes.CDLL(lib_name)
        self.libc.mmap.restype = ctypes.c_void_p
        self.libc.mmap.argtypes = (
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_long,
        )
        self.libc.munmap.restype = ctypes.c_int
        self.libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)

    def get(self, size: int, executable: bool = False) -> int:
        # 内存保护标志
        PROT_READ = 0x01
        PROT_WRITE = 0x02
        PROT_EXEC = 0x04
        prot = PROT_READ | PROT_WRITE
        if executable:
            prot |= PROT_EXEC

        # 映射标志
        MAP_PRIVATE = 0x0002
        MAP_ANONYMOUS = 0x1000  # 在macOS上是0x1000，在Linux上通常是0x20
        # 为了跨平台兼容，需要检查
        if "linux" in sys.platform:
            MAP_ANONYMOUS = 0x20

        flags = MAP_PRIVATE | MAP_ANONYMOUS

        address = self.libc.mmap(0, size, prot, flags, -1, 0)
        if address == -1:
            raise MemoryError(f"mmap failed to allocate {size}")

        return address

    def release(self, address: int, size: int):
        if self.libc.munmap(address, size) == -1:
            raise MemoryError(f"munmap failed to free memory at {hex(address)}")
