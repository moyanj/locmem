from typing import Dict, List, Optional, Set, Tuple  # 导入 Set 类型

from locmem.core import Pointer
from locmem.os_mem import get_memory, release_memory

from .base import BaseAllocator

# --- 配置常量 ---
BIN_SIZES = (8, 16, 32, 64, 128, 256, 512)
PAGE_SIZE = 4096  # 通常是操作系统内存页的大小
MAX_BIN_SIZE = BIN_SIZES[-1]


class BinPage:
    """
    封装一个由操作系统分配的内存页，并管理其内部小块（chunks）的分配状态。
    """

    def __init__(
        self, base_address: int, page_size: int, bin_size: int, executable: bool
    ):
        """
        初始化一个内存页。
        :param base_address: 该内存页的起始地址。
        :param page_size: 页的总大小（通常是PAGE_SIZE）。
        :param bin_size: 该页将被切割成的小块大小。
        :param executable: 该页是否可执行。
        """
        self.base_address: int = base_address
        self.page_size: int = page_size
        self.bin_size: int = bin_size
        self.executable: bool = executable  # 新增：记录页的可执行状态
        self.total_chunks: int = page_size // bin_size
        self.allocated_chunks: int = 0  # 记录当前页中已分配的块数

        if self.total_chunks == 0:
            raise ValueError(
                f"Page size {page_size} is too small for bin size {bin_size}."
            )

    def mark_allocated(self):
        """标记页中的一个块已被分配。"""
        if self.allocated_chunks >= self.total_chunks:
            raise RuntimeError("Attempted to allocate from a full page.")
        self.allocated_chunks += 1

    def mark_freed(self):
        """标记页中的一个块已被释放。"""
        if self.allocated_chunks <= 0:
            raise RuntimeError("Attempted to free from an empty page.")
        self.allocated_chunks -= 1

    def is_fully_free(self) -> bool:
        """检查该页是否所有块都已释放。"""
        return self.allocated_chunks == 0

    def get_base_pointer(self) -> Pointer:
        """获取页的起始指针。"""
        return Pointer(self.base_address)

    def __repr__(self):
        return (
            f"BinPage(addr={hex(self.base_address)}, bin_size={self.bin_size}, "
            f"allocated={self.allocated_chunks}/{self.total_chunks}, "
            f"exec={self.executable})"
        )

    def __hash__(self):
        return hash(self.base_address)

    def __eq__(self, other):
        if not isinstance(other, BinPage):
            return NotImplemented
        return self.base_address == other.base_address


class BinnedAllocator(BaseAllocator):
    """
    一个高效的分箱内存分配器，支持内存回收。
    """

    BIN_SIZES = BIN_SIZES

    def __init__(self):
        super().__init__()
        self._allocated_blocks = {}
        self.bins: Dict[Tuple[int, bool], Set[Pointer]] = {}
        for size in BIN_SIZES:
            self.bins[(size, False)] = set()  # 不可执行内存的 bin
            self.bins[(size, True)] = set()  # 可执行内存的 bin

        # 此映射关系在页被释放前应保持不变
        self.chunk_to_page_map: Dict[Pointer, BinPage] = {}

        # 当前正在使用的 BinPage 对象
        self.active_pages: Dict[Tuple[int, bool], List[BinPage]] = {}
        for size in BIN_SIZES:
            self.active_pages[(size, False)] = []
            self.active_pages[(size, True)] = []

    def _find_bin(self, size: int) -> Optional[int]:
        """为指定的 size 找到最合适的 bin size。"""
        if size > MAX_BIN_SIZE:
            return None
        for bin_size in BIN_SIZES:
            if size <= bin_size:
                return bin_size
        return None

    def _grow_bin(self, bin_size: int, executable: bool):
        """
        为指定 bin size 扩展内存。
        从OS申请一个内存页，并将其切割成多个小块，放入空闲链表。
        同时创建并管理 BinPage 对象。
        """
        # 向OS申请一个大内存页，并传入 executable 状态
        page_address = get_memory(PAGE_SIZE, executable=executable)

        new_page = BinPage(page_address, PAGE_SIZE, bin_size, executable)
        self.active_pages[(bin_size, executable)].append(new_page)

        # 3. 将大内存页切割成小块，并放入空闲集合
        for i in range(new_page.total_chunks):
            chunk_addr = page_address + i * bin_size
            ptr = Pointer(chunk_addr)
            ptr._set_hook(self.free)
            self.bins[(bin_size, executable)].add(ptr)
            self.chunk_to_page_map[ptr] = new_page  # 映射 chunk 到其所属的 BinPage

    def alloc(self, size: int, executable: bool = False) -> Pointer:
        """
        分配内存。优先从 bin 分配，否则直接向OS分配。
        """
        if size <= 0:
            raise ValueError("Allocation size must be positive.")
        with self._lock:
            bin_size = self._find_bin(size)

            if bin_size is not None:
                # --- 处理小内存请求 (来自 bin) ---
                bin_key = (bin_size, executable)

                if not self.bins[bin_key]:
                    # 如果箱子是空的，则扩充它
                    self._grow_bin(bin_size, executable)

                if not self.bins[bin_key]:
                    raise RuntimeError(f"Failed to grow bin {bin_key} or bin is empty.")
                ptr = self.bins[bin_key].pop()
                ptr.freed = False

                # 标记所属 BinPage 中的 chunk 为已分配
                parent_page = self.chunk_to_page_map[ptr]
                parent_page.mark_allocated()

                return ptr
            else:
                # --- 处理大内存请求 (直接向OS申请) ---
                address = get_memory(size, executable)
                ptr = Pointer(address)
                ptr._set_hook(self.free)
                self._allocated_blocks[ptr] = size
                return ptr

    def free(self, ptr: Pointer):
        """
        释放内存。如果来自 bin，则归还到空闲链表，并更新 BinPage 状态；
        如果是大内存块，则归还给操作系统。
        """
        if not isinstance(ptr, Pointer):
            raise TypeError("Argument to free must be a Pointer object.")
        with self._lock:
            if ptr.freed:
                # 允许重复释放，不抛出异常
                return

            # 检查是否是来自 bin 的小内存块
            if ptr in self.chunk_to_page_map:
                parent_page = self.chunk_to_page_map[ptr]
                bin_size = parent_page.bin_size
                executable = parent_page.executable

                bin_key = (bin_size, executable)

                # 将指针归还到对应的空闲集合
                self.bins[bin_key].add(ptr)
                ptr.freed = True

                parent_page.mark_freed()

                # 检查该页是否已完全空闲，如果是则归还给OS
                if parent_page.is_fully_free():
                    # 从对应的活跃页列表中移除该页
                    self.active_pages[bin_key].remove(parent_page)
                    release_memory(parent_page.base_address, parent_page.page_size)

                    # 这些指针现在指向无效内存，必须清除
                    for i in range(parent_page.total_chunks):
                        chunk_addr = parent_page.base_address + i * bin_size
                        chunk_ptr = Pointer(chunk_addr)
                        # 从 chunk_to_page_map 中移除映射
                        if chunk_ptr in self.chunk_to_page_map:
                            del self.chunk_to_page_map[chunk_ptr]
                        # 从 bins 中移除，因为现在它们是无效指针
                        if chunk_ptr in self.bins[bin_key]:
                            self.bins[bin_key].remove(chunk_ptr)
            # 检查是否是直接分配的大内存块
            elif ptr in self._allocated_blocks:
                mem_size = self._allocated_blocks.pop(ptr)
                release_memory(ptr.value, mem_size)
                ptr.freed = True
            else:
                raise ValueError(
                    f"Invalid pointer: {ptr} was not managed by this allocator."
                )

    def gc(self):
        """
        确保在分配器对象销毁时，所有未释放的内存块（包括所有活跃的BinPage）都被归还给OS。
        """
        with self._lock:
            # 释放所有大块内存
            for ptr, size in list(self._allocated_blocks.items()):
                try:
                    release_memory(ptr.value, size)
                    ptr.freed = True
                except Exception as e:
                    print(f"  Error releasing large block {hex(ptr.value)}: {e}")
            self._allocated_blocks.clear()

            # 释放所有 BinPage 管理的内存
            for bin_key, pages_list in list(self.active_pages.items()):
                for page in list(pages_list):  # 迭代副本
                    try:
                        release_memory(page.base_address, page.page_size)
                    except Exception as e:
                        print(
                            f"  Error releasing BinPage {hex(page.base_address)}: {e}"
                        )
                self.active_pages[bin_key].clear()  # 清空列表

            # 清空所有 bins 和 chunk_to_page_map
            self.bins.clear()
            self.chunk_to_page_map.clear()

    def __del__(self):
        self.gc()
