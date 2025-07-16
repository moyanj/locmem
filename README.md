# `locmem` - Low-Level Memory Management for Python

[![PyPI version](https://img.shields.io/pypi/v/locmem.svg)](https://pypi.org/project/locmem/)
[![Build Status](https://img.shields.io/travis/com/your-username/locmem.svg)](https://travis-ci.com/your-username/locmem)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**`locmem`** is a Python library that provides a powerful toolkit for direct, low-level memory management. It allows you to bypass Python's standard memory allocation and interact with memory at a level similar to C.


## Key Features

*   **Direct Memory Control**: Allocate and free raw memory blocks on demand.
*   **Smart `Pointer` Class**: A robust wrapper around memory addresses with support for arithmetic, context management (`with` statement), and automatic garbage collection.
*   **C-Style Memory Operations**: A suite of familiar functions including `memread`, `memwrite`, `memcpy`, and `memset`.
*   **High-Level Data Types**: Work with `Int`, `Float` and other C-like types that live directly in the memory you manage.
*   **Executable Memory**: Allocate memory with execute permissions and run machine code directly using `memexec`.
*   **Cross-Platform**: Works seamlessly on Windows and POSIX-compliant systems (Linux, macOS).

## Installation

```bash
pip install locmem
```

## Quick Start

The easiest way to use `locmem` is with the `with` statement, which ensures that memory is automatically freed when you're done.

```python
from locmem import alloc, memwrite, Int

# The `with` block ensures the pointer `p` is automatically freed upon exit.
with alloc(16) as p:
    print(f"Allocated 16 bytes at address: {p}")

    # Write a 32-bit integer (value 12345) to the start of the memory block
    value_to_write = 12345
    memwrite(p, value_to_write.to_bytes(4, 'little'))
    print(f"Wrote the value {value_to_write} to memory.")

    # Create a locmem.Int object that is mapped to that memory location.
    # It reads and interprets the bytes at that address.
    my_int = Int.from_ptr(p)

    print(f"Value read via Int object: {my_int.value}")
    assert my_int.value == value_to_write

    # You can also modify the underlying memory through the object.
    my_int.value = 54321
    print(f"Changed value to: {my_int.value}")

    # The memory is automatically freed here.
print("Memory has been freed.")
```

## Core Concepts

### 1. Allocation & Pointers

The library revolves around the `Pointer` object, which is returned by the `alloc` function.

```python
from locmem import alloc, free

# Manual allocation
ptr = alloc(32)

# Pointers support arithmetic
ptr2 = ptr + 16
print(f"Original: {ptr}, Offset: {ptr2}")

# Manually free the memory when done
free(ptr)
# Or, even better, call the method on the pointer itself
# ptr.free()
```

The `Pointer` object's `__del__` method will automatically call `free`, but relying on Python's garbage collector for timely memory release is not recommended. **Always use the `with` statement or call `free()` explicitly.**

### 2. High-Level Data Types

`locmem` provides classes that mirror C data types. These objects manage their own memory and handle the packing/unpacking of data for you. They also support standard arithmetic and comparison operations.

```python
from locmem import Int, Double, Char

# These objects allocate their own memory upon creation.
a = Int(100)
b = Int(50)

c = a + b  # c is a new Int object with value 150
c -= 20    # c.value is now 130

print(f"Result: {c.value}")

# Perform float arithmetic
d = Double(1.25)
e = Double(4.0)
f = d * e  # f is a new Double object with value 5.0
print(f"Float result: {f.value}")

# These objects will free their memory when they go out of scope.
```

### 3. Executable Memory

A powerful feature of `locmem` is the ability to allocate executable memory. This allows you to write machine code into memory and then call it like a regular Python function.

```python
from locmem import alloc, memwrite, memexec
import ctypes

# x86-64 machine code for a function that returns 42:
# mov eax, 42   ; b8 2a 00 00 00
# ret           ; c3
shellcode = b'\xb8\x2a\x00\x00\x00\xc3'

# Allocate memory with executable permissions
with alloc(len(shellcode), executable=True) as p:
    # Write the machine code to the allocated block
    memwrite(p, shellcode)
  
    # Create a callable Python function from the memory address.
    # Specify that it takes no arguments and returns a C integer.
    func = memexec(p, restype=ctypes.c_int)

    # Call the function!
    result = func()
    print(f"Executed code from memory, result: {result}")
    assert result == 42
```

## Advanced Usage

### Choosing an Allocator

`locmem` ships with two main allocator types. The `BinnedAllocator` is the default because it's highly efficient for programs that make many small allocations. However, you can switch to the simpler `HeapAllocator` if you prefer.

The global allocator can be changed at runtime.

```python
from locmem import alloc, set_global_allocator, HeapAllocator, BinnedAllocator

# The default is BinnedAllocator
ptr1 = alloc(16)
print(f"Allocated with: {type(ptr1._deref.__self__)}")
# > Allocated with: <class 'locmem.allocator.binned.BinnedAllocator'>
ptr1.free()


# Switch to the HeapAllocator for all subsequent allocations
set_global_allocator(HeapAllocator())

ptr2 = alloc(16)
print(f"Allocated with: {type(ptr2._deref.__self__)}")
# > Allocated with: <class 'locmem.allocator.heap.HeapAllocator'>
ptr2.free()
```

## Project Architecture

`locmem` is built on a layered architecture:

1.  **OS Memory Layer (`locmem.os_mem`)**: The lowest level. It contains platform-specific code (`mmap` for POSIX, `VirtualAlloc` for Windows) to request memory directly from the operating system.
2.  **Allocator Layer (`locmem.allocator`)**: This layer sits on top of the OS layer. It implements allocation strategies (`BinnedAllocator`, `HeapAllocator`) to manage the raw memory obtained from the OS efficiently.
3.  **Core API (`locmem.core`, `locmem.datatype`)**: The highest level. It provides the user-facing `Pointer` object, memory manipulation functions (`memread`, `memwrite`, etc.), and the high-level `Int`, `Float` data types.

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the documentation, please open an issue or submit a pull request on our GitHub repository.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.