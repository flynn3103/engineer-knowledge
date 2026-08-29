# Calling Conventions — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Calling Conventions** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The SysV classification algorithm (the heart of struct passing)

To pass or return a struct on SysV AMD64, the ABI runs this procedure:

1. **If the aggregate is larger than 16 bytes** (more than two eightbytes), or has unaligned fields, the whole thing is **MEMORY** → passed on the stack (and for returns, via `sret`).
2. **Otherwise**, split it into one or two eightbytes. Classify each eightbyte:
   - If *every* field overlapping that eightbyte is a float/double → **SSE**.
   - If *any* field overlapping it is an integer/pointer → **INTEGER**.
3. **Merge** the per-field classes within each eightbyte (INTEGER wins over SSE if they mix in the same eightbyte).
4. **Post-merge fixups** (e.g., if either eightbyte ended up MEMORY, the whole thing is MEMORY).
5. **Assign registers:** each INTEGER eightbyte consumes the next integer register (`RDI`→`RSI`→…), each SSE eightbyte the next XMM. **If not enough registers remain, the whole aggregate goes to MEMORY** (it is not split across registers and stack).

The consequences are deeply non-obvious:

```c
struct A { float x, y; };          // 8 bytes, one SSE eightbyte → ONE xmm reg
struct B { double a; double b; };  // 16 bytes, two SSE eightbytes → XMM0, XMM1
struct C { long a; double b; };    // 16 bytes: int8b → RDI, sse8b → XMM0 (!)
struct D { long a, b, c; };        // 24 bytes → MEMORY, on the stack
struct E { int a; float b; };      // 8 bytes, mixed in one eightbyte → INTEGER (RDI)
```

Look at `struct A`: two `float`s pack into one eightbyte that is all-float → **SSE** → passed in **one** `XMM` register (the two floats packed into its low 64 bits). Look at `struct C`: the first eightbyte is integer (`long`), the second is float (`double`), so it's passed split across `RDI` and `XMM0`. And `struct E` mixes an int and a float in the *same* eightbyte, so the merge rule makes it **INTEGER** — both fields ride in `RDI`. No casual observer would predict these.

### 2. Returning small structs: registers; large structs: `sret`

For **returns**, SysV runs the same classification on the return type:

- ≤ 16 bytes → comes back in `RAX`/`RDX` (INTEGER eightbytes) and/or `XMM0`/`XMM1` (SSE eightbytes), per classification. So `struct {int x, y;}` returns in `RAX`, and `struct {double a, b;}` returns in `XMM0:XMM1`.
- \> 16 bytes (MEMORY) → **the caller allocates the storage and passes a hidden pointer to it as an implicit first argument.** The function writes the result through that pointer and returns the pointer in `RAX`. This implicit pointer is called **`sret`** (structure return). Crucially, **it shifts every real argument down one integer register**: the real first argument now lands in `RSI`, not `RDI`.

```c
struct Big { double m[8]; };  // 64 bytes > 16  → sret
struct Big make(int seed);
// At the machine level this behaves like:
// void make(struct Big *hidden_ret /* RDI */, int seed /* RSI */);
```

This is the same mechanism C++ uses for **RVO/NRVO**: the compiler constructs the returned object *directly* in the caller-provided `sret` slot, so there's no copy on return. The ABI's hidden-pointer rule is precisely what makes (N)RVO an ABI-level guarantee rather than just an optimization.

### 3. Windows x64 handles structs completely differently

Windows x64 has no eightbyte classification. The rule is brutally simple and *different*:

- A struct/union is passed **by value in a single register only if its size is exactly 1, 2, 4, or 8 bytes**.
- **Anything else** (3, 5, 6, 7 bytes, or > 8 bytes) is passed **by reference**: the caller copies it to a temporary and passes a *pointer* in the argument register.
- Returns: a struct that is 1/2/4/8 bytes comes back in `RAX`; otherwise the caller allocates and passes a hidden pointer (in `RCX`), shifting real args down — same idea as `sret`, different register.

So `struct {double a, b;}` (16 bytes) is passed **in two XMM registers on SysV** but **by reference (a pointer) on Windows**. A marshaller that copies the SysV behavior to Windows shifts fields catastrophically. "Returns the right struct on Linux, garbage on Windows" is almost always this.

### 4. AArch64: HFAs and the indirect-return pointer

AArch64 adds the **Homogeneous Float Aggregate (HFA)** case: a struct of up to four members *all* of the same floating/vector type is passed in consecutive `V` registers (so `struct {float x, y, z;}` → `V0, V1, V2`). Other small aggregates (≤ 16 bytes) go in `X` registers; larger ones are passed indirectly. Large returns use the dedicated indirect-result register `X8` (the caller puts the result address there before the call).

### 5. Variadic functions: how `printf` really works

A variadic function declares only its fixed parameters; the rest arrive "somehow," and `<stdarg.h>` walks them. Under the hood on SysV:

- Fixed arguments occupy registers as usual. Variadic arguments *also* go in the remaining argument registers (and then the stack), classified the same way.
- The callee's prologue, if it ever calls `va_start`, **spills all the argument registers into a "register save area"** on its own stack — all six integer registers and (potentially) all eight XMM registers — so `va_arg` can later fetch them by index.
- **The `AL` rule:** to avoid spilling eight XMMs on every variadic call, the *caller* sets `AL` to the **number of vector registers actually used** by the variadic arguments. The prologue checks `AL` and saves only that many XMMs. If `AL` is wrong (e.g., you call a variadic function through a mismatched pointer and `AL` isn't set), the callee may not save the XMM holding a `double` argument, and `va_arg(ap, double)` returns garbage.

```asm
; SysV call: printf("%d %f\n", 42, 3.14);
lea  rdi, [fmt]        ; format string  → RDI
mov  esi, 42           ; "%d" arg       → RSI (integer)
movsd xmm0, [pi]       ; "%f" arg       → XMM0 (one vector reg used)
mov  al, 1             ; <-- number of vector registers used: 1
call printf
```

That `mov al, 1` is mandatory and invisible in C source. Omit it (as a hand-written or mis-generated call easily does) and floating variadic arguments break.

On **Windows x64**, variadics are simpler and stricter: floating-point variadic arguments are passed in **both** the integer register *and* the XMM register (the callee reads whichever it needs), and there's no `AL` rule. AArch64 has its own variadic register-save layout. So the *one* construct — `printf` — has three different ABIs, which is exactly why hand-rolling variadic FFI is a recurring source of bugs.

### 6. Why FFI tools must encode all of this — and the name-decoration tie-in

A binding generator or marshaller can't just "pass the bytes." To call `f(struct C c)` correctly it must run the classification to know `c` occupies `RDI` *and* `XMM0`. To call a function returning `struct Big` it must allocate the `sret` slot and shift arguments. To call `printf` it must set `AL`. Get any of these wrong and there is no diagnostic — only shifted fields or garbage floats. This is why robust FFI defers to the C compiler (e.g., generating a C shim) rather than reimplementing the ABI.

Closely related is **name decoration / mangling** (its own topic): the symbol name a function is exported under often *encodes* part of the convention. On 32-bit Windows, stdcall names are decorated with `@N` (the argument byte count), cdecl with a leading underscore, fastcall with `@`-prefix — so the linker can catch some convention mismatches. C++ mangling encodes parameter types entirely. The convention and the symbol name are two halves of the same binary contract; FFI must respect both.

---

## Code Examples

### Watching a struct land in two register files (SysV)

```c
// classify.c
struct C { long a; double b; };     // INTEGER eightbyte + SSE eightbyte
long use(struct C c) { return c.a + (long)c.b; }
```

```bash
gcc -O2 -S classify.c -o -      # read the assembly
```

`use` reads its argument from **both** `RDI` (the `long`) and `XMM0` (the `double`) — proof that one struct argument was split across the integer and SSE register files:

```asm
use:
    cvttsd2si rax, xmm0    ; (long)c.b  — b came in XMM0
    add       rax, rdi     ; + c.a      — a came in RDI
    ret
```

### Two floats in one XMM register

```c
struct A { float x, y; };           // 8 bytes, one all-float eightbyte
float sumA(struct A a) { return a.x + a.y; }
```

`sumA` receives the whole struct in `XMM0` (the two floats packed into its low 64 bits) and uses `movshdup`/`addss` to add them — never touching an integer register. A marshaller that passes `x` in `XMM0` and `y` in `XMM1` is wrong.

### A large return becomes a hidden pointer

```c
struct Big { double m[8]; };        // 64 bytes > 16 → sret
struct Big scaled(double k);
```

The caller side compiles to (conceptually):

```asm
    lea  rdi, [result_slot]   ; hidden sret pointer  → RDI
    movsd xmm0, [k]           ; real first arg 'k'   → XMM0 (NOT shifted; it's SSE)
    call scaled               ; scaled writes through RDI, returns RDI in RAX
    ; result lives in [result_slot]
```

For a returned-large-struct function with an integer first argument, that integer argument moves from `RDI` to `RSI` because `sret` consumed `RDI`. Tools must account for the shift.

### The `AL` register on a variadic call

```c
extern int printf(const char *, ...);
int main(void) { return printf("%d %.2f\n", 7, 2.5); }
```

```asm
    lea   rdi, [fmt]
    mov   esi, 7
    movsd xmm0, [two_point_five]
    mov   al, 1            ; one vector register used by varargs
    call  printf
```

Delete the `mov al, 1` (e.g., by calling through a `void(*)()` cast that drops the prototype) and the `%f` reads garbage on SysV — a textbook variadic-FFI failure.

### Same struct, opposite ABI on Windows

```c
struct P { double a, b; };          // 16 bytes
double sum(struct P p);
```

- **SysV:** `p.a` in `XMM0`, `p.b` in `XMM1` (two SSE eightbytes).
- **Windows x64:** the caller copies `p` to a temporary and passes a **pointer** to it in `RCX`; the callee dereferences it.

An FFI binding must branch on the target OS here, or fields silently transpose.

---

## Coding Patterns

### Pattern 1: Prefer pointers to structs across the FFI boundary

Passing/returning structs *by value* drags in the full classification. Passing a *pointer* to a struct is trivially portable — it's just an integer argument. When you control both sides of an FFI, prefer `void f(const Foo *in, Foo *out)` over by-value aggregates.

```c
// Portable and ABI-trivial: pointers only.
void transform(const struct Vec3 *in, struct Vec3 *out);
```

### Pattern 2: Generate a C shim instead of hand-classifying

Let the compiler own the ABI: emit a tiny C function with the real signature and call *that* from your runtime via a uniform pointer-based interface.

```c
// Generated shim — the C compiler applies classification/sret/AL for you.
void shim_make(struct Big *out) { *out = make(SEED); }
```

### Pattern 3: Wrap variadics behind a fixed-arity `va_list` entry point

Don't FFI a variadic function directly. Call its `v`-suffixed sibling (`vprintf`, `vsnprintf`) which takes a `va_list` you build deliberately, removing the `AL`/register-spill guesswork.

### Pattern 4: Pin the struct layout that the ABI depends on

Because adding or reordering a field silently changes a by-value struct's ABI, freeze such structs (explicit padding, `static_assert(sizeof(...) == ...)`, no casual edits) when they cross an FFI boundary.

---

## Best Practices

- **Run the classification mentally (or with the compiler) before trusting a by-value struct's register placement.** Never assume "each field gets its own register."
- **Branch on OS for aggregate passing/returning.** SysV and Windows use entirely different models; AArch64 adds HFAs.
- **Model large returns as a hidden first-argument out-pointer**, and remember it shifts the real arguments down a register.
- **Always set `AL` correctly for SysV variadic calls** — or avoid hand-emitting them; use the `va_list` variant.
- **Prefer pointer-to-struct over struct-by-value at FFI boundaries** for portability and to avoid classification entirely.
- **Generate C shims and let the C compiler apply the ABI** rather than reimplementing it.
- **Treat the symbol name as part of the contract:** stdcall decoration, C++ mangling, and the convention must all line up (see the name-decoration topic).
- **Verify with the disassembler.** For any struct argument or return, confirm in the assembly which registers and/or `sret` slot are actually used.

---

## Edge Cases & Pitfalls

### Pitfall 1: Adding a field silently changes a function's ABI

`struct {int a; int b;}` returns in `RAX`; add a third int and it's 12 bytes (still ≤ 16, two eightbytes → `RAX:RDX`); add a fifth and it's > 16 → `sret`. A "trivial" struct edit can flip the calling convention of every function using it. Recompile *all* sides.

### Pitfall 2: Assuming each struct field gets its own register

`struct {float x, y;}` is *one* XMM register, not two; `struct {int a; float b;}` is *one* integer register (the float merges to INTEGER). Marshallers that assign per-field corrupt the layout.

### Pitfall 3: Forgetting the `sret` argument shift

When a function returns a MEMORY-class struct, the hidden pointer takes `RDI`, so the declared first argument is actually in `RSI`. Hand-written callers that load the first arg into `RDI` overwrite the `sret` pointer.

### Pitfall 4: Copying SysV struct rules to Windows (or vice versa)

A 16-byte struct goes in two registers on SysV but *by reference* on Windows. Returns differ too. This is the canonical "right on Linux, garbage on Windows" struct bug.

### Pitfall 5: Variadic `AL` not set / prototype lost

Calling a variadic function through a non-variadic function-pointer cast drops the `AL` setup; floating variadic arguments then read garbage on SysV. Keep the variadic prototype, or use the `va_list` variant.

### Pitfall 6: `va_arg` type mismatch and default promotions

Variadic arguments undergo default argument promotions (`float`→`double`, small ints→`int`). `va_arg(ap, float)` is undefined — you must use `va_arg(ap, double)`. Mismatching the type desynchronizes the cursor and corrupts every subsequent fetch.

### Pitfall 7: AArch64 HFA surprises

`struct {float x, y, z;}` occupies `V0, V1, V2` on AArch64 (an HFA) but is handled by eightbyte classification on SysV x86-64. Cross-arch marshallers need an HFA branch.

---

## Apply it

1. State the system invariant that **Calling Conventions** must protect.
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

- Which invariant must remain true when Calling Conventions fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
