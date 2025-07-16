import sys

if sys.platform == "win32":
    from .win32 import Win32Memory as PlatformMemoryManager
else:
    from .posix import PosixMemory as PlatformMemoryManager

os_manager = PlatformMemoryManager()

get_memory = os_manager.get
release_memory = os_manager.release

__all__ = ["get_memory", "release_memory", "os_manager", "PlatformMemoryManager"]
