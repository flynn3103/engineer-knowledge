# Stack Management & Unwinding — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Stack Management & Unwinding** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Calling Convention Is a Contract

When `caller` calls `callee`, both sides must agree on:

- **Where arguments go.** SysV passes the first 6 integer/pointer args in `rdi, rsi, rdx, rcx, r8, r9`, and the first 8 floating-point args in `xmm0–xmm7`. Win64 passes the first 4 args in `rcx, rdx, r8, r9` (integers) or `xmm0–xmm3` (floats), *by position* — the second arg is always in `rdx`/`xmm1` regardless of type.
- **Where the return value goes.** `rax` (and `rdx` for 128-bit), or `xmm0` for floats, on both conventions.
- **Who preserves which registers** (next section).
- **Stack alignment** at the call site.

Two compilers can interoperate *only because* they both implement the same convention. This is also why FFI (calling C from Go, Rust, Python via ctypes) requires care: you're manually honoring the ABI across a language boundary.

### 2. Caller-Saved vs Callee-Saved

There are not enough registers for every function to have its own private set, so the ABI splits them:

- **Callee-saved (non-volatile):** the callee promises to leave them exactly as it found them. If it wants to use one, it must `push` it in the prologue and `pop` it in the epilogue. On SysV: `rbx, rbp, r12–r15`.
- **Caller-saved (volatile):** the callee may trash them freely. If the *caller* has a live value in one across a call, *the caller* must save it first. On SysV: `rax, rcx, rdx, rsi, rdi, r8–r11`.

This split is a performance bargain: short functions that don't call anything can use the volatile registers without any save/restore overhead, and only pay to preserve callee-saved registers if they actually need them.

### 3. Precise SysV Frame Layout

Here is a typical SysV frame for a function that *does* use a frame pointer and *does* call other functions:

```text
   high addresses
   +-----------------------------+
   |  7th, 8th, ... stack args   |  (args beyond the 6 register args)
   +-----------------------------+
   |  return address             |  <- pushed by caller's `call`
   +-----------------------------+
   |  saved rbp (caller's FP)    |  <- prologue: push rbp
   +-----------------------------+  <- rbp points here
   |  saved callee-saved regs    |  (rbx, r12-r15 if this fn uses them)
   |  local variables            |
   |  spilled temporaries        |
   +-----------------------------+
   |  outgoing arg area / pad    |  (kept 16-byte aligned for next call)
   +-----------------------------+  <- rsp points here
   |  ...128-byte RED ZONE...    |  (below rsp; only safe in leaf fns)
   +-----------------------------+
   low addresses
```

Locals are addressed relative to `rbp` (e.g. `[rbp-8]`), which stays put even as `rsp` moves during the function.

### 4. The Red Zone (SysV)

On SysV, the 128 bytes *immediately below* `rsp` are the **red zone**. A **leaf function** (one that calls nothing) may store its locals there *without bothering to subtract from `rsp` at all* — saving two instructions. This is safe only because nothing else will touch that region: there's no `call` to push a return address over it, and the kernel guarantees signal handlers won't run on the user stack's red zone (they allocate below it).

```asm
; A SysV leaf function using the red zone — note: NO `sub rsp, N`.
leaf:
    mov   [rsp-8], rdi      ; stash arg in the red zone
    mov   rax, [rsp-8]
    ret                     ; rsp never moved
```

**Pitfall:** code that *does* run asynchronously on the stack (some signal handlers, interrupt-like contexts, hand-written assembly) can corrupt the red zone. Kernels compile with `-mno-red-zone` for exactly this reason.

### 5. Shadow Space (Win64)

Windows x64 has no red zone. Instead it has the opposite idea: **shadow space** (a.k.a. *home space*). The *caller* must allocate **32 bytes** on the stack (room for 4 eightbyte slots) *before* the return address, even though the 4 arguments are passed in registers. The callee may use these 32 bytes to spill `rcx, rdx, r8, r9` if it wants their values on the stack (e.g. for debugging or because it's variadic).

```text
   Win64 at the moment a callee is entered:
   +-----------------------------+
   |  5th, 6th, ... stack args   |
   +-----------------------------+
   |  shadow space for arg4 (r9) |
   |  shadow space for arg3 (r8) |
   |  shadow space for arg2 (rdx)|
   |  shadow space for arg1 (rcx)|  <- caller reserved these 32 bytes
   +-----------------------------+
   |  return address             |  <- rsp on entry
   +-----------------------------+
```

Forgetting to reserve shadow space when hand-writing Win64 assembly or doing FFI is a classic stack-corruption bug.

### 6. Stack Alignment

Both conventions require `rsp` to be **16-byte aligned at the point of a `call`**. Because `call` then pushes the 8-byte return address, a function is *entered* with `rsp ≡ 8 (mod 16)`. The prologue's `push rbp` makes it 16-aligned again. Misalignment doesn't always crash, but SIMD instructions (`movaps`, etc.) that *require* 16-byte alignment will fault — a notoriously confusing bug when it shows up only on certain code paths.

### 7. Frame-Pointer Omission — and Why It Breaks Walking

`rbp` is a perfectly good general-purpose register. If the compiler doesn't *need* it as a frame anchor — because it can address all locals relative to `rsp` instead — it can free `rbp` for computation. That's **frame-pointer omission**, enabled by `-fomit-frame-pointer` (default at `-O1`+ on many targets). The win: one more register, and two fewer instructions per call (`push rbp` / `pop rbp`).

The cost is fundamental to this whole topic. The naive stack walk — "read the saved `rbp`, that's the next frame; the slot next to it is the return address; repeat" — **depends on the frame-pointer chain existing**. With FPO there is no chain: `rbp` holds an unrelated computed value, and the saved-FP slots aren't there. A profiler or debugger walking the stack the naive way will read garbage and either stop, produce a bogus trace, or crash.

```asm
; WITH frame pointer (walkable by following rbp):
f:  push rbp
    mov  rbp, rsp
    sub  rsp, 32
    ; locals at [rbp-8], [rbp-16] ...
    leave            ; mov rsp,rbp ; pop rbp
    ret

; WITH -fomit-frame-pointer (no rbp chain; rbp is free):
f:  sub  rsp, 40
    ; locals at [rsp+0], [rsp+8] ...  (relative to a moving rsp!)
    add  rsp, 40
    ret
```

So how does anything walk an FPO stack? **Unwind tables**: side data, emitted by the compiler, that says "at this instruction offset, the return address is at `rsp + N` and the CFA is `rsp + M`." That's DWARF CFI on Unix and `.pdata`/`.xdata` on Windows — the entire subject of `senior.md`. The key insight to carry forward: *with FPO, finding the caller is a lookup, not a pointer-chase.*

---

## Code Examples

### Example 1: See the convention with your own compiler

```bash
# Compile to assembly and read the prologue/epilogue and arg registers.
cat > frame.c <<'EOF'
long add3(long a, long b, long c) {
    long sum = a + b + c;   // a in rdi, b in rsi, c in rdx (SysV)
    return sum;             // result in rax
}
EOF
gcc -O0 -S -masm=intel frame.c -o frame_O0.s   # frame pointer kept
gcc -O2 -S -masm=intel frame.c -o frame_O2.s   # FPO likely; rbp gone
diff frame_O0.s frame_O2.s
```

At `-O0` you'll see the `push rbp; mov rbp, rsp` prologue. At `-O2`, for a small leaf like this, the frame may vanish entirely (locals stay in registers, no stack used at all).

### Example 2: Force the frame pointer back on

```bash
# -O2 speed, but keep walkable stacks for the profiler:
gcc -O2 -fno-omit-frame-pointer -S -masm=intel frame.c -o frame_fp.s
```

This is the single most common flag in modern "make `perf` work again" guidance. You give up one register and a couple of instructions per call in exchange for cheap, reliable stack walking. (Why this is "back in fashion" is covered in `professional.md`.)

### Example 3: The red zone, made visible

```c
// A leaf function: gcc -O2 may use the red zone (no `sub rsp`).
// Compile with and without -mno-red-zone and diff the assembly.
long square(long x) {
    long tmp = x * x;   // small leaf: may live in red zone or just a register
    return tmp;
}
// gcc -O2 -S -masm=intel redzone.c
// gcc -O2 -mno-red-zone -S -masm=intel redzone.c   <- kernel-style build
```

### Example 4: An FFI ABI bug (the abstract shape)

```text
A Go program calls a C function via cgo. The C function is declared in Go
with the wrong argument count. Go arranges arguments per the SysV ABI for
the signature *it believes*; C reads them per the signature *it* was
compiled with. The two disagree about which register holds which argument,
or about stack-arg layout. Result: garbage arguments, or a corrupted stack
and a crash whose backtrace is nonsense — because the corruption broke the
very frame chain the debugger walks.

Lesson: an ABI mismatch corrupts the structure the backtrace depends on,
so the symptom (bad trace) is downstream of the real cause (bad contract).
```

### Example 5: Alignment matters for SIMD

```c
// If rsp is misaligned at a call (e.g. hand-written asm forgot the +8),
// a callee that does an aligned 16-byte vector load can fault:
#include <immintrin.h>
void uses_simd(float *p) {
    __m128 v = _mm_load_ps(p);   // needs 16-byte alignment
    // ... if the compiler also aligns a stack temporary to 16 and rsp was
    //     misaligned coming in, the aligned spill/reload can #GP fault.
    (void)v;
}
```

---

## Coding Patterns

**Pattern: Build with frame pointers in performance-critical, profiled services.** The whole industry (Linux distros, large server fleets) has been re-enabling `-fno-omit-frame-pointer` because reliable profiling is worth the ~1%. Make it your default for code you'll profile.

**Pattern: When writing assembly, honor the convention explicitly.**

```asm
; SysV: preserve callee-saved regs you use; keep 16-byte alignment.
my_asm:
    push rbx            ; rbx is callee-saved -> must restore it
    sub  rsp, 8         ; realign: entry rsp is 16k+8; push made it 16k;
                        ; we need 16k+8 again before our own `call`... count carefully!
    ; ... body, calls ...
    add  rsp, 8
    pop  rbx
    ret
```

**Pattern: For Win64 FFI/asm, always reserve 32 bytes of shadow space before a call**, even if you pass everything in registers. Forgetting it lets the callee's spills overwrite *your* stack.

**Pattern: Verify your ABI assumptions by reading the generated assembly.** `gcc -S -masm=intel` (or `objdump -d`) is the ground truth. Don't guess which register an argument is in — look.

---

## Best Practices

1. **Default to `-fno-omit-frame-pointer` for anything you profile.** The reliability of flame graphs and crash traces is worth the small cost.
2. **Never trust a backtrace from an FPO build without DWARF or LBR backing it.** It may be silently truncated or wrong.
3. **Match the ABI exactly at FFI boundaries.** Argument count, types, and the `extern "C"` convention must agree on both sides.
4. **Reserve shadow space on Win64; respect the red zone on SysV.** Disable the red zone (`-mno-red-zone`) wherever async code runs on the user stack.
5. **Keep `rsp` 16-byte aligned before every `call`** in hand-written assembly. Alignment bugs surface only under SIMD and are miserable to diagnose.
6. **Save and restore every callee-saved register you touch** in assembly. Forgetting clobbers the caller and produces "impossible" corruption.

---

## Edge Cases & Pitfalls

- **Mixed FPO / non-FPO code.** A stack walk that crosses from a frame-pointer build into an FPO library (or vice versa) can desync mid-walk, producing a plausible-looking but wrong trace.
- **Red-zone corruption by signal/interrupt code.** Async code that uses the stack below `rsp` silently smashes a leaf function's locals. Symptom: rare, data-dependent wrong answers.
- **Forgetting shadow space on Win64.** The callee spills its register args over your stack data. Corruption with no obvious cause.
- **Off-by-8 alignment in assembly.** Everything works until a SIMD instruction faults. The arithmetic of "entry is 16k+8, each push subtracts 8" is easy to get wrong.
- **Variadic functions need the convention's extra rules.** On SysV, `al` must hold the number of vector registers used for a variadic call; getting it wrong corrupts argument passing.
- **Assuming `rbp` is always the frame pointer.** In FPO builds `rbp` holds arbitrary data. Tools that hardcode "follow `rbp`" produce garbage.
- **Tail calls reuse the frame.** A tail-call-optimized call replaces the current frame instead of adding one — so the *caller* may be missing from the backtrace (more in `senior.md`).

---

## Apply it

1. Find a real component where **Stack Management & Unwinding** affects an interface or dependency.
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

- Which boundary is most affected by Stack Management & Unwinding?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
