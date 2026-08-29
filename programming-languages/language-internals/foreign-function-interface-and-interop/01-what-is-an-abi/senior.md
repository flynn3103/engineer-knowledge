# What Is an ABI — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **What Is an ABI** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why the Same C Source Differs Across Platform ABIs

A single C function compiled for Linux, Windows, and ARM produces three different binaries that cannot call each other, even on conceptually identical hardware. The differences are the platform ABIs:

| Clause | System V AMD64 (Linux/mac/BSD) | Windows x64 | AArch64 AAPCS64 |
|--------|--------------------------------|-------------|-----------------|
| Integer arg registers | `rdi, rsi, rdx, rcx, r8, r9` (6) | `rcx, rdx, r8, r9` (4) | `x0`–`x7` (8) |
| Float arg registers | `xmm0`–`xmm7` | `xmm0`–`xmm3` | `v0`–`v7` |
| Return register | `rax` / `xmm0` | `rax` / `xmm0` | `x0` / `v0` |
| Caller-reserved stack | 128-byte **red zone** below `rsp` | 32-byte **shadow space** above return addr | (no red zone) |
| `long` size | 8 bytes (LP64) | 4 bytes (LLP64) | 8 bytes (LP64) |
| Struct passing | classify ≤16B into regs | ≤8B by value in 1 reg, else by pointer | up to 16B in regs, HFA rules |

The Windows convention passing only four arguments in registers, with mandatory shadow space, is fundamentally incompatible with System V's six-register, red-zone model — a function compiled for one and called as the other corrupts the stack and reads arguments from the wrong registers. This is why "it's the same x86-64 CPU" does not mean "the binaries are interchangeable." The CPU is the same; the ABI is not.

### 2. The x86 Legacy: cdecl, stdcall, fastcall

Before x86-64 unified things, 32-bit x86 had a zoo of calling conventions, and you still meet them in Windows headers and legacy code:

- **cdecl** — the C default. Arguments pushed right-to-left on the stack; the **caller** cleans up. Supports variadic functions (the caller knows the arg count). Names decorated with a leading underscore (`_func`).
- **stdcall** — the Win32 API convention. Arguments on the stack right-to-left, but the **callee** cleans up. Cannot be variadic. Names decorated like `_func@12` (the number is the bytes of arguments).
- **fastcall** — passes the first two arguments in `ecx`/`edx`, the rest on the stack; callee cleans up. Decorated `@func@12`.

The senior point: on 32-bit x86 the calling convention is *not implied by the platform* — it is per-function, declared in the header (`__cdecl`, `__stdcall`). Get it wrong and the stack is cleaned by the wrong party, corrupting it. x86-64 mercifully collapsed this to one convention per OS, but the historical zoo still shows up in Win32 declarations and FFI bindings.

### 3. The C++ ABI Problem, Decomposed

Here is the central senior insight: **C++ has no single universal ABI, and that is why C++ libraries don't reliably interoperate across compilers.** The problem decomposes into three *independent* incompatibilities. Two compilers must agree on *all three* to interoperate, and the two major families — Itanium (GCC/Clang) and MSVC — agree on *none*.

**(a) Name mangling.** Itanium mangles `int foo(int)` to `_Z3fooi`; MSVC mangles it to `?foo@@YAHH@Z`. Completely different schemes. A symbol exported by one is invisible to the other.

**(b) Vtable layout.** A polymorphic object holds a pointer to a vtable — an array of function pointers. *Where* the vtable pointer sits in the object, *what order* the virtual functions appear in the table, where RTTI and the typeinfo pointer live, and how multiple/virtual inheritance arranges multiple vtables — all of this differs between Itanium and MSVC. Even if you could find the right symbol, calling a virtual function through a mismatched vtable jumps to the wrong slot.

**(c) Exception handling.** Itanium uses a table-driven, DWARF-based unwinding model (`__cxa_throw`, `.eh_frame`, the Itanium EH ABI). MSVC uses an SEH-based model. A C++ exception thrown in a GCC-built library cannot be caught in an MSVC-built one; the unwinder doesn't understand the other's tables. Worse, an exception that unwinds *across* an incompatible boundary typically calls `std::terminate` or corrupts the stack.

Add standard-library type layout (`std::string`, `std::vector` have different internal layouts between libstdc++, libc++, and the MSVC STL) and template instantiation, and you have the full picture: passing a `std::string` across a compiler boundary is undefined behavior because the two sides disagree about what a `std::string` *is* in memory.

### 4. `extern "C"`: Escaping to the Stable C ABI

The escape hatch from all of section 3 is to expose **only a C ABI** at the boundary:

```cpp
extern "C" {
    void*  obj_create();
    int    obj_method(void* self, int arg);
    void   obj_destroy(void* self);
}
```

`extern "C"` does three things at once: disables name mangling (plain symbol `obj_create`), and — by restricting you to C types and no exceptions/vtables across the line — sidesteps vtable layout and exception-handling incompatibility entirely. The C ABI has none of C++'s problem features, so it is the same across every compiler on a platform. This is why every cross-language and cross-compiler interface is a C interface, even when both sides are written in C++. The cost: you marshal everything into C types (opaque pointers, primitive scalars, no exceptions across the line, no templates), losing C++'s expressiveness at the seam.

### 5. ABI Versioning: Symbol Versioning in glibc

How does glibc ship a new `realpath` or `memcpy` without breaking every binary ever linked against it? **Symbol versioning.** A single `libc.so.6` exports multiple versioned definitions of the same symbol:

```text
memcpy@GLIBC_2.2.5      (old behavior)
memcpy@@GLIBC_2.14      (new default; @@ marks the default version)
```

A binary linked years ago recorded a dependency on `memcpy@GLIBC_2.2.5`; the loader binds it to the old implementation. A freshly linked binary binds to `memcpy@@GLIBC_2.14`. Both coexist in one library file. This is how glibc maintains backward compatibility across decades while still fixing and improving symbols. You can see it with `readelf -V` (version definitions and requirements). The famous `memcpy` regression of 2011 — where new glibc's `memcpy` copied backward and broke programs that illegally passed overlapping buffers — was navigated partly through this mechanism.

### 6. The libstdc++ Dual-ABI / `std::string` Saga

The canonical real-world ABI break: in 2015, C++11 required `std::string` and `std::list` to change their internal layout (C++11 banned copy-on-write strings and required O(1) `list::size()`). libstdc++ could not just change `std::string`'s layout — that would break every existing C++ binary that passes a `std::string` across a library boundary. Their solution was the **dual ABI**: both the old (`std::string`) and new (`std::__cxx11::string`) layouts coexist in the same `libstdc++.so`, selected at compile time by the macro `_GLIBCXX_USE_CXX11_ABI` (default 1 on modern systems, 0 for the legacy ABI).

The operational pain this caused — and still causes — is the dreaded link error:

```text
undefined reference to `foo(std::__cxx11::string)`
```

This means one object file was compiled with `_GLIBCXX_USE_CXX11_ABI=1` (new `std::__cxx11::string`) and another with `=0` (old `std::string`), and the mangled names no longer match. The fix is to compile *everything* in the program with the same setting. This single macro has consumed untold engineering hours and is the textbook example of why exposing standard-library types across a binary boundary is dangerous.

### 7. soname and Major-Version Compatibility

ELF libraries carry a **soname** — `libfoo.so.1` — recorded in the binary. The convention: the *major* number changes on an ABI break, and the loader matches binaries to libraries by soname. A program linked against `libfoo.so.1` will load `libfoo.so.1.2.3` (a compatible point release) but will refuse `libfoo.so.2` (an ABI-incompatible major bump). This is the mechanism that operationalizes "ABI break = major version." Libraries that get this wrong — bumping the soname when nothing broke, or *not* bumping it when the ABI did break — cause either needless rebuilds or silent corruption. Tools like `abidiff` (libabigail) compare two builds of a library and report whether the ABI actually changed, removing the guesswork.

### 8. AArch64 AAPCS64 Specifics Worth Knowing

ARM's 64-bit ABI is increasingly relevant (Apple Silicon, AWS Graviton, mobile). Key clauses that differ from x86-64:

- Eight integer argument registers `x0`–`x7` and eight SIMD/FP registers `v0`–`v7` — twice System V's integer count, so more arguments stay in registers.
- **Homogeneous Floating-point Aggregates (HFA):** a struct of up to four identical floating-point members (e.g. `struct { float a, b, c, d; }`) is passed in consecutive SIMD registers — a rule with no x86-64 analogue.
- Apple's AArch64 ABI deviates from the generic AAPCS64 in argument-passing for variadic functions and in some alignment rules — a subtle source of bugs when porting Linux-ARM code to macOS-ARM.

The lesson: even within "AArch64," there are dialects. The ABI is the platform's, not the CPU's.

---

## Code Examples

### Watch a C++ symbol differ from its C counterpart

```cpp
// lib.cpp
int  cpp_add(int a, int b)            { return a + b; }   // mangled
extern "C" int c_add(int a, int b)    { return a + b; }   // plain
```

```bash
g++ -c lib.cpp -o lib.o
nm lib.o | grep add
#  _Z7cpp_addii   <- mangled (Itanium): name+signature encoded
#  c_add          <- plain C symbol, callable from anything
```

`_Z7cpp_addii` cannot be reliably found by another compiler or by `dlsym("cpp_add")`. `c_add` can. This is the C++ ABI problem and its escape hatch in three lines.

### A vtable layout you can read

```cpp
struct Base {
    virtual void a();
    virtual void b();
    virtual ~Base();
};
```

```bash
g++ -fdump-lang-class -c base.cpp        # GCC: dumps vtable layout
# Inspect the .class dump: the vtable lists a(), b(), the two destructors,
# the typeinfo pointer — in an order fixed by the Itanium ABI.
```

The *order* of `a`, `b`, the two destructor variants, and the placement of the typeinfo pointer are Itanium-ABI-defined. MSVC arranges them differently. Calling a virtual through a mismatched layout dispatches to the wrong slot.

### Inspect symbol versioning in glibc

```bash
readelf -V /lib/x86_64-linux-gnu/libc.so.6 | grep -A2 memcpy
# Shows multiple versioned definitions: memcpy@@GLIBC_2.14, memcpy@GLIBC_2.2.5
objdump -T /lib/x86_64-linux-gnu/libc.so.6 | grep memcpy
```

This is the live evidence that one library file exports several ABI-versioned implementations of the same function for backward compatibility.

### Reproduce the dual-ABI link error

```bash
# Compile two TUs with different std::string ABIs:
g++ -D_GLIBCXX_USE_CXX11_ABI=1 -c provider.cpp   # new std::__cxx11::string
g++ -D_GLIBCXX_USE_CXX11_ABI=0 -c consumer.cpp    # old std::string
g++ provider.o consumer.o -o app
# undefined reference to `foo(std::__cxx11::basic_string<...>)'
```

The mangled names differ because the string type differs. Compiling both with the *same* macro value resolves it. This is the single most common C++ ABI footgun in the wild.

### Check whether a library upgrade is ABI-compatible

```bash
abidiff libfoo.so.1.0   libfoo.so.1.1
# Reports added/removed/changed symbols and struct layout changes.
# Empty output => ABI-compatible; you can ship without a soname bump.
```

`abidiff` (libabigail) mechanically answers "did I break the ABI?" — far more reliable than eyeballing a diff.

---

## Coding Patterns

### Pattern 1: The C-ABI facade over a C++ implementation

```cpp
// engine.hpp (C++ internals, hidden)
class Engine { /* ... rich C++ ... */ };

// engine_c.h  (the only thing customers see)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct Engine Engine;          // opaque
Engine* engine_create(void);
int     engine_step(Engine*, int);
void    engine_destroy(Engine*);
#ifdef __cplusplus
}
#endif
```

The customer links against a stable C ABI; you keep full C++ inside. No vtables, exceptions, or STL types cross the line.

### Pattern 2: Catch all exceptions at the C boundary

```cpp
extern "C" int engine_step(Engine* e, int x) {
    try {
        return reinterpret_cast<Engine*>(e)->step(x);
    } catch (...) {
        return -1;        // never let a C++ exception unwind across the C ABI
    }
}
```

A C++ exception unwinding through a C frame (or a foreign-compiler frame) is undefined behavior. Convert exceptions to error codes at the seam.

### Pattern 3: Pin the standard-library ABI in the build

```bash
# Enforce one std::string ABI across the whole build, fail otherwise.
add_compile_definitions(_GLIBCXX_USE_CXX11_ABI=1)
```

Set it once, project-wide, and document it. Mixed settings are the dual-ABI link error.

### Pattern 4: Version the plugin ABI explicitly

```c
#define PLUGIN_ABI_VERSION 3
typedef struct {
    int abi_version;             // host checks this first
    int (*init)(void*);
    int (*process)(void*, const char*, size_t);
} PluginVTable;
```

The host refuses to load a plugin whose `abi_version` it doesn't support, turning a future ABI break into a clean rejection instead of a crash.

---

## Best Practices

- **Expose only a C ABI across any boundary you don't fully control** (compiler, language, support window). It is the only universally honored contract.
- **Never pass STL types or throw exceptions across a binary boundary.** Marshal to C primitives and opaque handles; catch-all at the seam.
- **Pin `_GLIBCXX_USE_CXX11_ABI` (and equivalents) project-wide** and document it. Mixed values produce the classic dual-ABI link error.
- **Bump the soname major version on every ABI break,** and never on a compatible change. Run `abidiff` in CI to know which it is.
- **Use opaque handles for anything you might evolve.** Once a struct's fields are public, its layout is frozen forever.
- **Treat the platform (OS + toolchain), not the CPU, as the ABI's owner.** "Same x86-64" never implies binary compatibility.
- **For ARM ports, read AAPCS64 and your vendor's deviations** (Apple's differ from generic). Don't assume x86 struct/variadic behavior carries over.
- **Provide stable C entry points even from C++ libraries** so other languages can bind through one universal interface.

---

## Edge Cases & Pitfalls

- **Throwing through a `noexcept` or foreign-compiler frame** calls `std::terminate` or corrupts unwinding. Exceptions are ABI-bound; they don't cross.
- **Inline functions and templates leak ABI.** An inline function or template instantiated in two TUs with different compiler versions can violate the ODR, producing one definition silently winning — a layout mismatch that crashes far from the cause.
- **Default arguments and `enum` underlying types** are part of the C++ ABI surface in subtle ways; changing them can break binary compatibility while keeping source compatibility.
- **Adding a virtual function** to a base class changes the vtable layout (every later slot shifts) — an ABI break even though source compiles. Adding a *non-virtual* method usually doesn't.
- **Changing a class's member order or adding a data member** changes its size and layout — ABI break. Reserve padding fields up front if you anticipate growth.
- **Mixing libstdc++ and libc++** in one process is generally undefined: two incompatible STL implementations means two incompatible `std::string` layouts.
- **Apple Silicon variadic deviations:** code relying on the generic AAPCS64 variadic rules can misbehave on macOS-ARM. Test on the actual platform.
- **`long double` across ABIs:** 80-bit on x86 System V, 64-bit on Windows/AArch64-some — never in a cross-ABI interface.
- **Static linking does not fully escape the C++ ABI problem:** if two statically linked archives were built with different ABIs, you still get ODR violations at link or runtime.

---

## Apply it

1. State the system invariant that **What Is an ABI** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when What Is an ABI fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
