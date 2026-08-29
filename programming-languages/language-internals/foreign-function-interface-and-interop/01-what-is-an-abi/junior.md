# What Is an ABI — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **What Is an ABI** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Contracts, Not One

Imagine a library function:

```c
int add(int a, int b);
```

The **API** contract is everything in that one line of source: the name `add`, two `int` parameters, an `int` result. If your code calls `add(2, 3)` and the header declares it this way, your code *compiles*. That is the whole job of the API.

But compilation is only half the story. When the program runs, your compiled `add(2, 3)` has to physically hand `2` and `3` to the library's compiled `add` and physically receive `5` back. *Where* does `2` go? Into a CPU register? Which one? Onto the stack? At what offset? *Where* does `5` come back? The answers to all of those questions are the **ABI** contract. None of them appear in the source. They are decided by the compiler and the platform.

When two binaries agree on the ABI, the call works. When they disagree — even slightly — you get garbage values, crashes, or silent corruption.

### 2. What an ABI Actually Specifies

An ABI is a thick rulebook. The big-ticket items:

- **Calling convention.** Which registers hold the first, second, third argument; which register holds the return value; what order arguments go in; who is responsible for cleaning up the stack after the call. (We cover this in depth in the next topic.)
- **Data type sizes.** How many bytes is an `int`? A `long`? A pointer? This is *not* the same on every platform — a `long` is 8 bytes on Linux but only 4 bytes on 64-bit Windows.
- **Alignment.** A value of size *N* usually must live at an address that is a multiple of *N*. An 8-byte `double` wants an 8-byte-aligned address.
- **Struct and union layout.** Where each field sits, and how much **padding** the compiler inserts between fields to keep them aligned.
- **Register usage.** Which registers a called function is allowed to clobber, and which it must preserve and restore.
- **The stack frame.** How the stack is arranged during a call, where the return address lives, how local variables are stored.
- **Name mangling.** How source-level names become binary symbols (a big deal in C++, covered later).
- **The object/executable file format.** ELF on Linux, PE on Windows, Mach-O on macOS. The container that holds the machine code.
- **System call convention.** How a program asks the operating system kernel to do something.
- **Exception handling / stack unwinding.** How errors propagate up the call stack.
- **Thread-local storage.** How per-thread variables are found.

For now, focus on the first four — calling convention, sizes, alignment, and struct layout. They are where the everyday bugs come from.

### 3. Type Sizes Are Not Universal

Here is a fact that surprises almost everyone the first time: **`sizeof(long)` is not the same everywhere.**

| Type | Linux/macOS (64-bit) | 64-bit Windows |
|------|----------------------|----------------|
| `int` | 4 bytes | 4 bytes |
| `long` | **8 bytes** | **4 bytes** |
| `long long` | 8 bytes | 8 bytes |
| pointer | 8 bytes | 8 bytes |

This split has names. Linux and macOS use **LP64**: `Long` and `Pointer` are 64-bit. 64-bit Windows uses **LLP64**: only `Long Long` and `Pointer` are 64-bit, while `long` stays 32-bit.

Why does this matter? If you write a struct with a `long` field, compile it on Linux, and then a different program compiled on Windows tries to read that same struct, they disagree about how big the field is and where everything after it lives. The bytes line up wrong. This is an ABI difference baked into the platform, and it is exactly why portable code uses fixed-width types like `int32_t` and `int64_t` at any binary boundary.

### 4. Struct Layout and the Invisible Padding

Consider this struct:

```c
struct Example {
    char  a;   // 1 byte
    int   b;   // 4 bytes
    char  c;   // 1 byte
};
```

You might guess it is 6 bytes (1 + 4 + 1). It is almost always **12 bytes**. The compiler inserts **padding**:

```text
offset:  0      1   2   3   4      5      6   7   8      9  10  11
        [a] [pad pad pad] [   b (4 bytes) ] [c] [pad pad pad]
```

Three padding bytes go after `a` so that `b` starts at offset 4 (4-byte aligned). Then three more padding bytes go after `c` so the *whole struct* is a multiple of 4 (its largest member's alignment). Reorder the fields — put both `char`s together — and you get a smaller struct. The point for now: **a struct's layout in memory is not just the sum of its fields. The ABI dictates the padding.** If two binaries disagree about padding rules, they disagree about where every field is.

### 5. The C ABI: Everyone's Common Language

Every language that wants to talk to the outside world — call a system library, expose a plugin interface, be called from Python or Java or Go — speaks **C at the boundary**. Not C the language, but the **C ABI**.

Why C? Because the C ABI is the simplest, oldest, most stable, and most universally implemented binary contract in existence. It has no classes, no templates, no exceptions, no name mangling to speak of. A C function named `add` is just a symbol named `add` (or `_add`), and its calling convention is fully specified by the platform. Every operating system's libraries expose a C ABI. Every foreign-function interface — Python's `ctypes`, Java's JNI, Rust's `extern "C"`, Go's cgo — connects through the C ABI. It is the universal handshake. When people say "speak C at the boundary," they mean: expose your functionality through the C ABI so anything can call it.

### 6. ABI Stability: Upgrade Without Recompiling

Here is the big payoff of caring about ABIs. Suppose you have a program that uses a shared library — say `libcrypto.so`. A security fix comes out. The maintainers ship a new `libcrypto.so`. Can your already-compiled program use the new library *without being recompiled*?

**Yes — if and only if the ABI did not change.** This is **ABI stability**. If the new library kept every function's calling convention, every struct's layout, every type size identical, then your old binary's expectations still match the new binary's reality. You drop in the new `.so` and everything works. This is how Linux distributions ship security updates to millions of machines without recompiling every program.

If the ABI *did* change — say a struct grew a field, or a function's arguments changed in memory layout — your old program now has *wrong expectations*. It might pass arguments the new code reads incorrectly, or read a struct field at the wrong offset. The result is the dreaded "it used to work, now it crashes" after a library upgrade.

### 7. ABI Break vs API Break — They Are Independent

This is the subtle, important idea. **You can break the ABI while keeping the API intact.**

Suppose a library has:

```c
struct Config {
    int timeout;
};
```

In version 2, the maintainer adds a field:

```c
struct Config {
    int timeout;
    int retries;   // new field
};
```

The **API is unchanged** in the sense that `config.timeout` still compiles. But the **ABI is broken**: `struct Config` went from 4 bytes to 8 bytes. Any already-compiled program that allocates a `Config` based on the old 4-byte size, then passes it to the new library, has a struct that is the wrong size — the new library will read or write `retries` past the end of the caller's memory. Source-compatible, binary-incompatible. The reverse can also happen: you can break the *source* API (rename a function) while the old binary symbol still works. The two contracts move independently, and you have to think about both.

---

## Code Examples

### Seeing type sizes differ

```c
#include <stdio.h>

int main(void) {
    printf("char       = %zu\n", sizeof(char));
    printf("int        = %zu\n", sizeof(int));
    printf("long       = %zu\n", sizeof(long));
    printf("long long  = %zu\n", sizeof(long long));
    printf("void*      = %zu\n", sizeof(void *));
    return 0;
}
```

On Linux/macOS x86-64 you get `long = 8`. On 64-bit Windows you get `long = 4`. Same source, different ABI. This single difference has broken countless cross-platform programs.

### Seeing struct padding

```c
#include <stdio.h>
#include <stddef.h>

struct Bad  { char a; int b; char c; };   // fields in a wasteful order
struct Good { int b; char a; char c; };   // fields packed tightly

int main(void) {
    printf("Bad  size = %zu\n", sizeof(struct Bad));    // typically 12
    printf("Good size = %zu\n", sizeof(struct Good));   // typically 8
    printf("offset of Bad.b = %zu\n", offsetof(struct Bad, b)); // typically 4
    return 0;
}
```

Same three fields, different sizes, because of padding. The `offsetof` macro reveals where a field actually sits — and *that offset is part of the ABI*. If another binary expects `b` at a different offset, it reads the wrong bytes.

### Exposing a C ABI from C++ with `extern "C"`

```cpp
// mathlib.cpp — compiled as C++ but exposes a C ABI
extern "C" int add(int a, int b) {
    return a + b;
}
```

Without `extern "C"`, a C++ compiler **mangles** the name `add` into something like `_Z3addii` (the encoding includes the argument types). A C program, or Python's `ctypes`, looking for a plain symbol named `add` would not find it. `extern "C"` says: "expose this with the plain, stable C ABI and the plain name `add`." This one keyword is how C++ libraries make themselves callable from everything else.

### Calling a C function from Python (through the C ABI)

```python
import ctypes

# Load a shared library that exposes a C-ABI function `add`.
lib = ctypes.CDLL("./mathlib.so")

lib.add.argtypes = [ctypes.c_int, ctypes.c_int]   # describe the ABI
lib.add.restype  = ctypes.c_int

print(lib.add(2, 3))   # -> 5
```

Python has no idea what C is at the source level. It only needs to know the **ABI**: the symbol name (`add`), the argument types and sizes, and the return type. You are literally describing the binary contract by hand with `argtypes` and `restype`. Get any of those sizes wrong and you read garbage — that is an ABI mismatch you caused yourself.

### A struct ABI break in slow motion

```c
// library v1 — Config is 4 bytes
struct Config { int timeout; };

// library v2 — Config is now 8 bytes, source still "looks" compatible
struct Config { int timeout; int retries; };
```

A program compiled against v1 allocates 4 bytes for a `Config`. If you swap in v2's library without recompiling, the v2 code believes `Config` is 8 bytes and will read or write 4 bytes *past* the caller's allocation. The source never changed for `timeout` — the API looks fine — but the ABI broke. This is the canonical "compiled but crashes" failure.

---

## Coding Patterns

### Pattern 1: Use fixed-width types at any binary boundary

```c
#include <stdint.h>

struct WireMessage {
    int32_t  id;        // exactly 4 bytes, every platform
    int64_t  timestamp; // exactly 8 bytes, every platform
};
```

Never use `int`, `long`, or `unsigned` in a struct that crosses a binary boundary. Use `int32_t`, `uint64_t`, etc., so the size is identical on every platform. This sidesteps the LP64/LLP64 `long` trap.

### Pattern 2: Wrap C++ in `extern "C"` for any public interface

```cpp
extern "C" {
    void*  widget_create(void);
    void   widget_destroy(void* w);
    int    widget_value(void* w);
}
```

Expose an opaque pointer (`void*`) and plain C-ABI functions. Hide all the C++ classes behind them. Now anything — C, Python, Rust, Go — can call your library, and you are free to change the C++ internals without breaking callers.

### Pattern 3: Describe the ABI explicitly when calling foreign code

```python
import ctypes
lib = ctypes.CDLL("./widget.so")
lib.widget_create.restype  = ctypes.c_void_p
lib.widget_value.argtypes  = [ctypes.c_void_p]
lib.widget_value.restype   = ctypes.c_int
```

Always set `argtypes` and `restype`. If you skip them, `ctypes` guesses (defaulting to `int`-sized), which silently truncates pointers on 64-bit systems — a classic ABI bug.

### Pattern 4: Keep public structs opaque

Instead of exposing the fields of a struct (and freezing its layout forever), hand callers an **opaque handle** and provide accessor functions. Then you can change the struct's real layout in a future version without breaking the ABI, because callers never knew the layout to begin with.

---

## Best Practices

- **Treat "it compiled" as proving only the API.** The ABI is checked at runtime. Never assume binary compatibility from a clean compile.
- **Use fixed-width integer types** (`int32_t`, `uint64_t`) for anything that crosses a binary boundary. Avoid `long` like a trap — it is.
- **Speak C at the boundary.** Expose interoperable functionality through the C ABI (`extern "C"` in C++). It is the only contract everything understands.
- **Compile everything in a single program with one compiler and matching flags** where you can. Mixing compilers, standard-library versions, or build flags is a leading cause of ABI mismatch.
- **Keep public structs opaque** if you ever want to evolve them. Once you expose fields, their layout is frozen.
- **When calling foreign code, describe the ABI exactly** — argument types, sizes, return type. Do not let the FFI guess.
- **Be suspicious after a library upgrade.** "Used to work, now crashes" with no source change is a textbook ABI break.
- **Read the platform's ABI document** when you go low-level. There is an official one for each platform; it is the source of truth.

---

## Edge Cases & Pitfalls

- **`long` is 4 bytes on 64-bit Windows.** A struct or function signature using `long` will *not* be binary-compatible between Linux and Windows. Use `int64_t`.
- **Struct padding silently changes the size.** Reordering fields or changing one field's type can shift every later field's offset and break binary compatibility, even when the source still compiles.
- **Forgetting `extern "C"`** in a C++ library means the function gets a mangled name and a C caller or `ctypes` can't find the symbol at all — you get a "symbol not found" load error.
- **Mixing two C++ compilers (or two libstdc++ versions)** can fail because C++ ABIs differ between compilers. Two libraries compiled by different compilers may not link or may crash at runtime even with identical source.
- **Adding a field to a public struct is an ABI break,** not a harmless addition. The struct's size changes; old callers allocate the wrong size.
- **Skipping `argtypes`/`restype` in `ctypes`** lets Python assume `int`-sized arguments and returns, truncating 64-bit pointers to 32 bits on the way in or out. Memory corruption that looks random.
- **Assuming all platforms agree on enum size.** The width of an `enum` is implementation-defined; it can differ across compilers, breaking structs that embed enums.
- **Bit-fields have implementation-defined layout.** Two compilers can pack `int x : 3;` differently. Never put bit-fields in a cross-boundary struct.
- **Endianness** (byte order) is technically separate from the ABI but bites the same way: bytes laid out by a little-endian machine read wrong on a big-endian one.

---

## Apply it

1. Choose one small, known input for **What Is an ABI**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does What Is an ABI solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
