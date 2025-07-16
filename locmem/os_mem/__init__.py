import sys

if sys.platform == "win32":
    from .win32 import Win32Memory as PlatformMemoryManager
else:
    from .posix import PosixMemory as PlatformMemoryManager

# 创建一个全局的、平台特定的OS内存管理器实例
os_manager = PlatformMemoryManager()

# 导出核心功能函数，供分配器层调用
get_memory = os_manager.get
release_memory = os_manager.release

__all__ = ["get_memory", "release_memory", "os_manager", "PlatformMemoryManager"]
