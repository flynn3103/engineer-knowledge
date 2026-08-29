# What Is an ABI — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **What Is an ABI** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Calling Convention in Detail (System V AMD64)

The calling convention is the most-touched part of any ABI. On **System V AMD64** (Linux, macOS, BSD on x86-64), integer and pointer arguments are passed in this order of registers:

```text
arg #:   1     2     3     4     5     6     7+...
reg:    rdi   rsi   rdx   rcx   r8    r9    (stack)
```

The first six integer/pointer arguments go in those six registers, in that exact order. Argument seven onward is pushed onto the stack (right-to-left, so arg 7 is closest to the top). Floating-point arguments use a *separate* set: `xmm0` through `xmm7`. The integer and SSE registers are counted independently — a function `f(int a, double b, int c)` puts `a` in `rdi`, `c` in `rsi`, and `b` in `xmm0`.

The integer return value comes back in **`rax`** (and `rdx` for a 128-bit return); a floating-point return comes back in **`xmm0`**.

```c
long f(long a, long b, long c) { return a + b + c; }
```

compiles, on System V AMD64, to roughly:

```asm
f:
    lea  rax, [rdi + rsi]   ; rax = a + b   (a=rdi, b=rsi)
    add  rax, rdx           ; rax += c      (c=rdx)
    ret                     ; return value in rax
```

You can *see the ABI* directly: `a`, `b`, `c` arrived in `rdi`, `rsi`, `rdx`, and the result left in `rax`. None of that is in the source. The ABI put it there. (We cover calling conventions as their own topic next; here the goal is to recognize that the calling convention is *one component* of the larger ABI.)

### 2. Caller-Saved vs Callee-Saved Registers

The ABI partitions the register file into two classes, and getting this wrong corrupts data silently.

- **Callee-saved (non-volatile):** on System V AMD64, `rbx`, `rbp`, `r12`–`r15`, and the stack pointer `rsp`. If a function wants to use any of these, it must **save** the old value (push it) on entry and **restore** it before returning. The caller can rely on these surviving a call.
- **Caller-saved (volatile):** `rax`, `rcx`, `rdx`, `rsi`, `rdi`, `r8`–`r11`. A called function may clobber these freely. If the caller has a live value in one across a call, *the caller* must save it.

This division is a contract: it lets the caller and callee cooperate without either knowing the other's internals. It also means an inline-assembly block that scribbles on `rbx` without saving it is an ABI violation that produces "impossible" bugs in the calling function.

### 3. The Stack Frame and Stack Alignment

The ABI dictates the stack's shape during a call. On System V AMD64:

- The stack grows **downward** (toward lower addresses).
- A `call` instruction pushes the 8-byte return address.
- **At the point of a `call`, `rsp` must be 16-byte aligned** (so on function entry, after the return address is pushed, `rsp % 16 == 8`). This alignment exists so that SSE instructions, which want 16-byte-aligned operands, work on stack data. Violating it is a real source of crashes when a callee uses aligned SSE moves.
- A **red zone** of 128 bytes below `rsp` is reserved for the current function's use without adjusting `rsp` — a small optimization for leaf functions. (Windows x64 has no red zone; this is an ABI difference.)

### 4. How Aggregates (Structs) Are Passed

Scalars are easy. The hard, ABI-defining question is: *how do you pass a struct?* System V AMD64 uses a **classification algorithm**:

1. If the struct is larger than 16 bytes, or contains unaligned fields, it is passed **in memory** (the caller writes it to the stack and passes a pointer, conceptually).
2. If it is 16 bytes or smaller, it is split into **eight-byte chunks**, and each chunk is classified as INTEGER or SSE based on its fields. INTEGER chunks go in the next integer argument registers; SSE chunks go in the next SSE registers.

So a `struct { double x, y; }` (16 bytes, two doubles) is passed in `xmm0` and `xmm1` — *not* on the stack. A `struct { long a; long b; }` goes in `rdi` and `rsi`. A `struct { int a; float b; }` (8 bytes, one chunk, mixed) — the chunk has both an integer and a float field, so it classifies as... it depends on the exact rule, and *this* is precisely the kind of detail the ABI document specifies to the bit. The takeaway: struct passing is not "push it on the stack"; it is a precise decomposition, and two compilers must agree on it exactly.

### 5. Struct Layout: Size, Alignment, Offsets

Separate from *passing* a struct is *laying it out in memory*. The ABI fixes:

- Each scalar type's **size** and **alignment** (e.g. `double` is 8 bytes, 8-aligned).
- A field's **offset** is the smallest offset ≥ the end of the previous field that satisfies the field's alignment.
- The struct's **alignment** is the maximum of its members' alignments.
- The struct's **size** is rounded up to a multiple of its alignment (trailing padding).

```c
struct S {
    char  a;     // offset 0, size 1
    // 7 bytes padding
    double b;    // offset 8  (8-aligned)
    int   c;     // offset 16
    // 4 bytes trailing padding -> size 24, alignment 8
};
```

You can verify this with `pahole` or `offsetof`. The offsets are part of the ABI: a binary that reads `b` expecting it at offset 4 instead of 8 reads garbage. This is why `#pragma pack` (which changes alignment) is so dangerous across a boundary — it produces a struct whose layout no longer matches the default ABI.

### 6. Name Mangling

C symbols are nearly raw: a C function `int add(int, int)` becomes a symbol named `add` (or `_add` with a leading underscore on some platforms). That is why C is so easy to link against.

C++ cannot do that. With overloading, you can have `add(int, int)` and `add(double, double)` — two different functions with the same source name. The compiler **mangles** the name to encode the full signature into a unique symbol. Under the Itanium C++ ABI (used by GCC and Clang):

```text
int add(int, int)          ->  _Z3addii
double add(double, double) ->  _Z3adddd
namespace foo { void bar(); }  ->  _ZN3foo3barEv
```

`_Z` is the mangling prefix, `3add` is the length-prefixed name, `ii` means "two ints," `dd` means "two doubles," `N...E` brackets a nested name. You decode these with `c++filt`. Mangling is part of the C++ ABI, and **different compilers can mangle differently** — which is one reason C++ libraries don't always interoperate across compilers. `extern "C"` disables mangling for a function, giving it the plain C symbol so anything can link to it. (Name mangling is its own topic later; here it is one inventory item among the ABI's components.)

### 7. The Object/Executable File Format

The machine code has to live in a *file* with a defined structure, and that structure is part of the platform ABI:

- **ELF** (Executable and Linkable Format) — Linux, BSD, most Unix. Sections, a symbol table, relocations, program headers, dynamic-linking metadata.
- **PE/COFF** (Portable Executable) — Windows. `.exe` and `.dll`.
- **Mach-O** — macOS and iOS.

The format defines how the loader maps the file into memory, where the entry point is, how the symbol table is structured, and how dynamic linking resolves symbols at load time. Two systems with the same CPU but different file formats (Linux ELF vs Windows PE on the same x86-64) cannot run each other's binaries even though the *machine code* is the same — the *container* ABI differs.

### 8. The System Call Convention

Calling the kernel is its own ABI, separate from the function-call ABI. On Linux x86-64:

```text
syscall number -> rax
args           -> rdi, rsi, rdx, r10, r8, r9   (note: r10, not rcx!)
issue with     -> the `syscall` instruction
return value   -> rax
```

Note `r10` is used for the fourth syscall argument instead of `rcx` — because the `syscall` instruction itself clobbers `rcx`. This is a deliberate ABI divergence from the *function* calling convention. The syscall ABI is also remarkably stable: Linux famously never breaks userspace, meaning the syscall numbers and conventions are a frozen contract decades old.

### 9. Unwind Information and Thread-Local Storage

Two more inventory items, briefly:

- **Stack unwinding / exception handling.** When a C++ exception is thrown, or a debugger prints a backtrace, the runtime must walk the stack frames in reverse. It uses **unwind information** — DWARF Call Frame Information (`.eh_frame`) on Linux, Structured Exception Handling (SEH) on Windows. The *format* of this metadata is part of the ABI, and it is why C++ exceptions don't cross a compiler/ABI boundary cleanly.
- **Thread-local storage (TLS).** Variables declared `thread_local` need a per-thread instance, found via a thread pointer (`fs` segment on Linux x86-64, accessed through a defined TLS ABI). The model — how the thread pointer is set up and how TLS variables are addressed — is specified by the ABI.

---

## Code Examples

### See the calling convention as assembly

```bash
cat > f.c <<'EOF'
long f(long a, long b, long c) { return a + b + c; }
EOF
gcc -O2 -S -masm=intel f.c -o -    # prints assembly to stdout
```

You will see `a`, `b`, `c` consumed from `rdi`, `rsi`, `rdx` and the result placed in `rax`. That is the System V AMD64 calling convention, visible.

### See struct padding with `pahole`

```c
struct S { char a; double b; int c; };
```

```bash
gcc -g -c s.c -o s.o
pahole s.o
```

`pahole` prints each field's offset and size and explicitly annotates the **holes** (padding bytes). It is the fastest way to spot a layout problem in a cross-boundary struct.

### See name mangling with `nm` and `c++filt`

```cpp
// names.cpp
int add(int, int)        { return 0; }
double add(double, double){ return 0; }
namespace foo { void bar() {} }
extern "C" int c_add(int, int) { return 0; }
```

```bash
g++ -c names.cpp -o names.o
nm names.o                 # raw mangled symbols
nm names.o | c++filt       # demangled, human-readable
```

You will see `_Z3addii`, `_Z3adddd`, `_ZN3foo3barEv` raw — and `c_add` *unmangled*, because of `extern "C"`. Pipe through `c++filt` to read them.

### See the file format and symbols with `readelf`

```bash
readelf -h libfoo.so      # ELF header: class, machine, type
readelf -d libfoo.so      # dynamic section (needed libraries, soname)
readelf --dyn-syms libfoo.so   # exported/imported symbols
```

This reads the container ABI directly: the ELF class (ELF64), the machine (`Advanced Micro Devices X86-64`), and the dynamic symbol table that the loader uses to wire calls.

### Demonstrate caller/callee-saved with inline asm (the bug)

```c
#include <stdio.h>

long compute(void) {
    long x = 42;
    // BUG: rbx is callee-saved. Clobbering it without telling the
    // compiler (no clobber list) corrupts whatever the caller had in rbx.
    asm volatile ("mov $99, %%rbx" ::: /* missing: "rbx" */);
    return x;
}

int main(void) {
    printf("%ld\n", compute());
    return 0;
}
```

Declaring the clobber (`::: "rbx"`) makes the compiler save/restore `rbx`, honoring the ABI. Omitting it is an ABI violation: the compiler assumes `rbx` survived, and you get nondeterministic corruption in the caller. This is the inventory item "register usage / callee-saved" failing in practice.

---

## Coding Patterns

### Pattern 1: Always declare clobbers in inline assembly

```c
long add_asm(long a, long b) {
    long r;
    asm ("add %1, %0" : "=r"(r) : "r"(a), "0"(b));
    return r;   // let the compiler allocate registers; declare what you touch
}
```

Tell the compiler every register and memory location your asm touches. The compiler then preserves the ABI contract around your block. Hand-picking callee-saved registers without saving them is the classic bug.

### Pattern 2: Inspect layout before shipping a cross-boundary struct

Make `pahole` (or a static-assert on `sizeof` and `offsetof`) part of the build for any struct that crosses a binary boundary:

```c
_Static_assert(sizeof(struct WireMsg) == 16, "WireMsg size changed — ABI break!");
_Static_assert(offsetof(struct WireMsg, ts) == 8, "WireMsg layout changed!");
```

Now a layout change that would silently break the ABI fails the build instead.

### Pattern 3: `extern "C"` plus an opaque handle for a C++ library

```cpp
struct Engine;                       // opaque to callers
extern "C" Engine* engine_new();
extern "C" void    engine_run(Engine*);
extern "C" void    engine_free(Engine*);
```

The C ABI handles the calling convention and unmangled symbols; the opaque pointer hides the C++ layout so you never freeze it. Anything can call this, and you can change `Engine`'s real definition freely.

### Pattern 4: Pin the ABI with a version symbol

Export a symbol or function whose presence/value encodes the ABI version, and check it at load time. If a plugin was built against a different ABI version than the host expects, refuse to load it rather than crash later.

---

## Best Practices

- **Learn to read your platform's calling convention from disassembly.** `gcc -S -masm=intel` plus a couple of small functions teaches it faster than any document.
- **Use `pahole` / static asserts on `sizeof` and `offsetof`** for every struct that crosses a binary boundary. Catch layout drift at build time.
- **Never hand-clobber callee-saved registers** without saving them; always declare clobbers in inline asm.
- **Pipe symbol dumps through `c++filt`** when chasing "symbol not found" — it instantly tells you if mangling is the issue.
- **Keep C++ exceptions inside the C++ world.** Do not let them propagate across a C ABI boundary; catch and convert to error codes.
- **Match the whole toolchain** — same compiler, same standard-library version, same flags — for any binaries that must interoperate at the C++ level.
- **Treat the syscall ABI as off-limits to touch directly** unless you have a reason; use libc wrappers, which track the stable convention for you.
- **When cross-compiling, change your mental model fully:** new file format, new type sizes, new calling convention. Re-check the inventory.

---

## Edge Cases & Pitfalls

- **`#pragma pack(1)` changes alignment and thus layout.** A packed struct is binary-incompatible with the default-aligned version of the same source. Only use it deliberately, on both sides.
- **A struct that "looks small" can still go to memory.** Anything over 16 bytes (System V AMD64) or containing unaligned members is passed in memory, not registers — relevant when matching hand-written assembly to a C signature.
- **Variadic functions have special rules.** On System V AMD64, `al` must hold the number of SSE registers used when calling a variadic function like `printf`. Get it wrong and floating-point varargs read garbage. This is an easy-to-miss ABI detail.
- **The Windows x64 shadow space.** Windows requires the caller to reserve 32 bytes of "shadow space" on the stack for the four register arguments — System V does not. Mixing conventions here corrupts the stack.
- **Mangling differs between compilers and even compiler versions** for edge cases (some templates, lambdas). Two C++ binaries built by different compilers may fail to link or, worse, link to subtly different symbols.
- **Enum size is implementation-defined.** A struct embedding an `enum` can change size between compilers, silently breaking layout.
- **Bit-field layout is implementation-defined** in order and packing. Never cross a boundary with bit-fields.
- **Returning a large struct by value** triggers the "hidden first argument" rule: the caller passes a pointer to return-value storage in `rdi`, shifting all other argument registers by one. Surprising when reading disassembly.
- **`long double` is a portability minefield:** 80-bit extended on x86 System V, 64-bit on Windows, 128-bit on some others. Never put it in a cross-boundary interface.

---

## Apply it

1. Find a real component where **What Is an ABI** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by What Is an ABI?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
