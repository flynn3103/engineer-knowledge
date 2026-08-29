# Name Mangling & Linking — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Name Mangling & Linking** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. MSVC mangling: same job, different alphabet

Microsoft's compiler decorates C++ names too, but the scheme is unrelated to Itanium. It starts with `?`, and crucially it encodes the **calling convention** and **storage class** in addition to name and types. `add(int, int)` becomes:

```text
  GCC/Clang (Itanium):  _Z3addii
  MSVC:                 ?add@@YAHHH@Z
```

Reading the MSVC form roughly: `?` opens it, `add@@` is the name with an empty scope, `Y` marks a free function, `A` is `__cdecl`, the first `H` is the return type (`int`), the next two `H`s are the `int` parameters, `@Z` terminates. A member function `Point::dist(int) const` looks like `?dist@Point@@QEBAHH@Z` — `Point@@` is the class scope, `QEBA` packs access/`const`/calling-convention, etc. It is denser and far less readable than Itanium, and the demangler is `undname` (or `dumpbin /symbols` on the object file), not `c++filt`.

Two operational facts dominate:

- **MSVC and Itanium are mutually unintelligible.** You cannot link `.obj` files from `cl.exe` against `.o` files from `g++` and expect C++ symbols to resolve — the names differ and the ABIs differ. Even two *MSVC* versions can differ in the standard library ABI.
- **The calling convention is part of the name.** Change `__cdecl` to `__stdcall` and the symbol changes. On 32-bit Windows especially, a calling-convention mismatch shows up as an unresolved-symbol link error — which is the linker doing you a favor by catching it.

### 2. Rust mangling: legacy vs `v0`

Rust mangles because monomorphized generics, modules, traits, and closures all produce distinct functions that need distinct symbols. The **legacy** scheme produced names like:

```text
_ZN4core3fmt5write17h2e8f9a1b3c4d5e6fE
                                ^^^^^^^^^^^^^^^^^ disambiguating hash
```

It reused the Itanium `_ZN…E` envelope but appended a compiler-internal **hash** to disambiguate, which made names *lossy* (you couldn't always reconstruct generic arguments) and *unstable* across compiler versions.

The modern **`v0`** scheme (RFC 2603, opt-in via `-C symbol-mangling-version=v0`, increasingly the default) starts with `_R` and is a fully specified, hash-free, reversible grammar that encodes generic parameters precisely:

```text
_RNvCs1234_5cratename3foo      (v0: starts _R, no hash, demangle-able)
```

Use `rustfilt` (or recent `c++filt`, which learned `v0`) to demangle. The point for a senior: **Rust symbols are mangled and version-fragile by default**, which is exactly why you don't expose mangled Rust symbols across an FFI boundary.

### 3. `#[no_mangle]` and `extern "C"`: Rust's FFI export switch

To call Rust from C (or any FFI), you must give the function a stable, unmangled, C-callable symbol:

```rust
#[no_mangle]
pub extern "C" fn rust_add(a: i32, b: i32) -> i32 {
    a + b
}
```

`extern "C"` sets the C calling convention; `#[no_mangle]` forces the plain symbol name `rust_add` (not `_RNv...`). Without `#[no_mangle]`, the C side can't find the symbol (it's mangled and version-dependent); without `extern "C"`, the calling convention is Rust's, which C doesn't speak. Both are required — this is the exact analogue of `extern "C"` in C++.

### 4. Vague linkage: why the same symbol appears everywhere

Consider an inline function or a template in a header included by 50 source files. Each translation unit that *uses* it emits its *own* copy of the machine code (the compiler can't know which TU will be the "owner"). Naively that's 50 definitions of one symbol — a multiple-definition catastrophe. C++ resolves this with **vague linkage**: such symbols (inline functions, instantiated templates, vtables, RTTI, static data members of templates) are emitted as **weak/COMDAT** symbols, and the linker is told *"these are all the same entity; keep one, discard the rest."*

This is why you can put an `inline` function or a template in a header, include it everywhere, and not get a link error. The linker **folds** the duplicates.

### 5. Weak vs strong symbols, and COMDAT folding

- A **strong** symbol must be unique; two strong definitions → multiple-definition error.
- A **weak** symbol may be defined multiple times; the linker keeps one. A **strong** definition *overrides* a weak one (this is how you provide a default that can be overridden — e.g. `__attribute__((weak))`).
- **COMDAT** (the section-grouping mechanism, called COMDAT on both ELF and PE/COFF) is how vague-linkage symbols are tagged so the linker knows "all copies of `_Z3maxIiET_S0_S0_` are interchangeable — pick any one."

The folding rule: among interchangeable COMDAT copies, the linker keeps the first (or one per its policy) and drops the rest. **This is correct only if the copies really are identical.** When they're not — when two TUs were compiled with different flags, different `#define`s, or different struct definitions and emitted *different* code under the *same* symbol — you have an **ODR violation**, and the linker silently keeps one. The program links, runs, and behaves according to whichever copy won. No error. This is one of the nastiest senior-level bugs.

### 6. The ODR violation that silently wins

A concrete, classic ODR trap: two `.cpp` files include a header defining `struct Config`, but one is compiled with `-DDEBUG` that adds a field, so `sizeof(Config)` differs between TUs. The header's `inline Config make_config()` is emitted in both, with *different* layouts, under the *same* weak symbol. The linker folds them to one. Now half the program thinks `Config` is 16 bytes and half thinks it's 24, but only one `make_config` body runs — fields are written at the wrong offsets, and you get memory corruption that has *nothing to do with the line where it manifests*. The fix is discipline: identical definitions across all TUs, consistent flags, no flag-dependent struct layouts in shared headers.

### 7. ABI mismatch is more than mangling

Mangling is the *visible* part of the ABI, but a true cross-compiler mismatch involves more: calling convention, struct/class layout, vtable layout, name of the standard-library symbols (libstdc++ vs libc++ vs MSVC STL), and the exception-handling model. Two libraries can have *matching* C symbol names yet still be incompatible if they assume different `std::string` layouts. This is why the only *guaranteed*-stable cross-compiler C++ interface is a **C interface** (`extern "C"` functions passing only C-compatible types — POD structs, pointers, primitives), and why mature cross-language SDKs expose a flat C API even when implemented in C++ or Rust.

---

## Code Examples

### Comparing Itanium and MSVC for the same function

```cpp
int add(int a, int b) { return a + b; }
```

```text
# Linux / Itanium
$ g++ -c add.cpp && nm add.o
0000000000000000 T _Z3addii

# Windows / MSVC (cl /c add.cpp ; dumpbin /symbols add.obj)
... SECT1 ... External | ?add@@YAHHH@Z (int __cdecl add(int,int))
```

```text
# Demangle MSVC on Windows:
> undname ?add@@YAHHH@Z
int __cdecl add(int,int)
```

Same function, two unrelated symbols. They will never resolve against each other.

### MSVC encodes calling convention into the symbol

```cpp
int __cdecl   f_cdecl(int);     // ?f_cdecl@@YAHH@Z
int __stdcall f_stdcall(int);   // ?f_stdcall@@YGHH@Z   (note Y_A_ vs Y_G_)
```

Changing only the calling convention changes the mangled name. A 32-bit Windows link error like `unresolved external symbol _f@4` vs `f` is almost always a calling-convention/declaration mismatch — the decoration didn't match.

### Rust mangling: legacy vs v0

```rust
// lib.rs
pub fn compute(x: i32) -> i32 { x * 2 }
```

```text
# Legacy mangling (hash suffix)
$ rustc --crate-type=lib -C symbol-mangling-version=legacy lib.rs
$ nm liblib.rlib | grep compute
... _ZN3lib7compute17h9f3c2a1b8e7d6c5fE   (Itanium envelope + hash)

# v0 mangling (hash-free, demangle-able)
$ rustc --crate-type=lib -C symbol-mangling-version=v0 lib.rs
$ nm liblib.rlib | grep compute
... _RNvCsXXXX_3lib7compute              (starts _R, no hash)

$ nm liblib.rlib | rustfilt
... lib::compute
```

The legacy name carries an opaque hash; the `v0` name is structured and reversible.

### Rust callable from C

```rust
// ffi.rs
#[no_mangle]
pub extern "C" fn rust_add(a: i32, b: i32) -> i32 {
    a + b
}
```

```text
$ rustc --crate-type=staticlib ffi.rs -o libffi.a
$ nm libffi.a | grep rust_add
0000000000000000 T rust_add        ← plain, unmangled; C can link it
```

From C:

```c
extern int rust_add(int, int);     /* matches the unmangled symbol */
int main(void) { return rust_add(2, 3); }
```

Drop `#[no_mangle]` and the C side gets `undefined reference to rust_add` — the real symbol was `_RNv...`.

### Vague linkage: the same template symbol in many objects

```cpp
// max.hpp
template <typename T> T mymax(T a, T b) { return a > b ? a : b; }
```

```cpp
// a.cpp
#include "max.hpp"
int  use_a() { return mymax(1, 2); }     // instantiates mymax<int>
```

```cpp
// b.cpp
#include "max.hpp"
int  use_b() { return mymax(3, 4); }     // ALSO instantiates mymax<int>
```

```text
$ g++ -c a.cpp b.cpp
$ nm a.o b.o | grep mymax
a.o: 0000000000000000 W _Z5mymaxIiET_S0_S0_      ← 'W' = weak (COMDAT)
b.o: 0000000000000000 W _Z5mymaxIiET_S0_S0_      ← same weak symbol

$ g++ a.o b.o use.o -o app     # links fine: linker folds the two copies
```

The `W` (weak) marks the COMDAT vague-linkage symbol. Both objects define `mymax<int>`; the linker keeps one. No multiple-definition error — that's vague linkage working.

### A weak symbol as an overridable default

```c
/* default.c */
__attribute__((weak)) int config_value(void) { return 42; }   // weak default
```

```c
/* override.c (optional) */
int config_value(void) { return 100; }   // strong: overrides the weak default
```

If `override.c` is linked, the strong `config_value` wins and returns 100; if not, the weak default (42) is used. This is the mechanism behind overridable library hooks and `__attribute__((weak))`-declared optional functions.

### An ODR violation that links cleanly (do not do this)

```cpp
// header.hpp — included by both files
struct Widget {
#ifdef EXTRA
    int extra;       // present only when EXTRA is defined
#endif
    int id;
};
inline Widget make_widget(int i) { Widget w; w.id = i; return w; }
```

```text
$ g++ -c               a.cpp -o a.o    # Widget = {id}        (4 bytes)
$ g++ -c -DEXTRA       b.cpp -o b.o    # Widget = {extra, id} (8 bytes)
$ g++ a.o b.o -o app                   # LINKS. No error.
```

Two different `make_widget` bodies (different `Widget` layouts) under one weak symbol. The linker folds them, one wins, and now `w.id` is written at the wrong offset in half the program. The link is clean; the behavior is undefined. Consistent flags and never-flag-dependent layouts in shared headers are the only defense.

---

## Coding Patterns

### Pattern 1: Flat C API over a C++/Rust core

```cpp
// public C++ implementation, private
class Engine { /* ... */ };

// flat, stable, C-callable surface
extern "C" {
    void* engine_create(void)            { return new Engine(); }
    int   engine_run(void* e, int input) { return static_cast<Engine*>(e)->run(input); }
    void  engine_destroy(void* e)        { delete static_cast<Engine*>(e); }
}
```

Opaque `void*` handle plus `extern "C"` functions taking only C-compatible types. This survives compiler and ABI changes that any direct C++ interface would not.

### Pattern 2: Cross-platform export macro

```cpp
#if defined(_WIN32)
#  define EXPORT __declspec(dllexport)
#  define IMPORT __declspec(dllimport)
#else
#  define EXPORT __attribute__((visibility("default")))
#  define IMPORT
#endif

#ifdef BUILDING_MYLIB
#  define MYLIB_API EXPORT
#else
#  define MYLIB_API IMPORT
#endif

extern "C" MYLIB_API int mylib_init(void);
```

The same macro exports when building the library and imports when consuming it, on both PE (MSVC) and ELF (GCC/Clang).

### Pattern 3: Rust FFI boundary

```rust
#[no_mangle]
pub extern "C" fn parser_new() -> *mut Parser { Box::into_raw(Box::new(Parser::new())) }

#[no_mangle]
pub extern "C" fn parser_free(p: *mut Parser) {
    if !p.is_null() { unsafe { drop(Box::from_raw(p)); } }
}
```

Every FFI-exported Rust function is `#[no_mangle] pub extern "C"` and passes only C-ABI types or raw pointers.

### Pattern 4: ODR hygiene for shared headers

- Never make a struct/class layout depend on a `#define` that varies between translation units.
- Compile all TUs that share a header with the *same* relevant flags (`-D`, `-std`, ABI flags).
- Treat inline functions and templates in headers as code that *must* be byte-identical everywhere.

---

## Best Practices

- **Expose only a C ABI across compiler/language boundaries.** `extern "C"` (C++) and `#[no_mangle] extern "C"` (Rust), passing POD and pointers. This is the only contract that survives ABI drift.
- **Never link C++ objects from different compilers** (GCC `.o` against MSVC `.obj`) or, often, even different major versions of the same compiler/STL. Re-expose through a C boundary instead.
- **Demangle with the right tool per scheme:** `c++filt` (Itanium), `undname`/`dumpbin` (MSVC), `rustfilt` (Rust). Feeding a name to the wrong demangler yields garbage.
- **Prefer `v0` Rust mangling** when you need to inspect or symbolize Rust binaries; it's stable and demangle-able.
- **Treat every inline/template symbol as a vague-linkage symbol** and keep its definition byte-identical across all TUs. ODR violations don't error — they corrupt.
- **Keep build flags consistent** across all TUs sharing a header (especially layout-affecting `-D` and `-std`). Inconsistent flags are the #1 cause of silent ODR violations.
- **Use weak symbols deliberately, sparingly,** and document where a strong override is expected.

---

## Edge Cases & Pitfalls

- **Mixing GCC-built and MSVC-built C++ libraries.** The symbols don't match and the ABIs differ; it won't link, or worse, links and corrupts. Use a C boundary.
- **MSVC standard-library ABI drift.** Even between MSVC toolset versions, `std::string`/iterator layouts can change; binaries built with different `/MD` vs `/MT` runtimes mix badly. The symbol may resolve while the layout doesn't.
- **Forgetting `#[no_mangle]` *or* `extern "C"` in Rust FFI.** Missing `#[no_mangle]` → mangled `_R...` symbol the C side can't find. Missing `extern "C"` → wrong calling convention even if the name matched.
- **Calling-convention mismatch on 32-bit Windows.** Declaring a `__stdcall` function as `__cdecl` (or vice versa) changes the decorated name and gives an unresolved-symbol error — read the decoration, not just the bare name.
- **ODR violation across translation units.** Different inline/template definitions (or flag-dependent layouts) under one weak symbol fold silently; the bug manifests far from its cause. The hardest class of linker-adjacent heisenbug.
- **Identical Code Folding (ICF) surprises.** A linker that folds *functionally identical* functions can make two distinct function pointers compare *equal*, breaking code that uses function-pointer identity. Disable ICF (or use `-fno-icf`/`--icf=none`) if you depend on distinct addresses.
- **Weak override not happening.** A weak symbol is only overridden by a strong definition *that the linker actually pulls in*. If the strong definition lives in an archive member nothing else references, it's never pulled, and the weak default wins unexpectedly.
- **`inline` in C vs C++.** C's `inline` linkage rules (C99) differ from C++'s; an `inline` function in a C header without a matching `extern inline` definition can produce a missing-symbol error. The two languages' vague-linkage stories are not identical.

---

## Apply it

1. State the system invariant that **Name Mangling & Linking** must protect.
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

- Which invariant must remain true when Name Mangling & Linking fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
