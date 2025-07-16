from locmem import *

ptr = alloc(16)
memwrite(ptr, int(232).to_bytes(4, "little"))
memwrite(ptr + 2, int(233).to_bytes(4, "little"))
a = Int.from_ptr(ptr + 2)
print(ptr)
print(a.value)
