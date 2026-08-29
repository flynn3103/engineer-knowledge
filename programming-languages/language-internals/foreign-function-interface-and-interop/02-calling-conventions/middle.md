# Calling Conventions — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Calling Conventions** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The three 64-bit conventions, side by side

| | **SysV AMD64** (Linux/macOS) | **Windows x64** | **AArch64 AAPCS64** |
|---|---|---|---|
| Integer arg registers | RDI, RSI, RDX, RCX, R8, R9 | RCX, RDX, R8, R9 | X0–X7 |
| Float/vector arg registers | XMM0–XMM7 | XMM0–XMM3 | V0–V7 |
| Integer return | RAX (+RDX for 128-bit) | RAX | X0 (+X1) |
| Float return | XMM0 | XMM0 | V0 |
| Register/stack pairing | int & float counted **separately** | by **position**: 4th arg → R9 *or* XMM3, not both | int & float counted separately |
| Shadow space | none | **32 bytes**, caller-reserved | none |
| Red zone | **128 bytes** below RSP | none | none (but 16-byte SP alignment) |
| Stack alignment at call | RSP % 16 == 0 | RSP % 16 == 0 | SP % 16 == 0 |
| Stack cleanup | caller | caller | caller |

The two most dangerous differences for FFI:

1. **Different first-argument register.** SysV: `RDI`. Windows: `RCX`. AArch64: `X0`. Mixing these up corrupts every argument.
2. **Windows pairs by position, not by separate counts.** In `f(int a, double b, int c, double d)` on Windows, `a→RCX`, `b→XMM1` (slot 2), `c→R8` (slot 3), `d→XMM3` (slot 4). Each *positional* slot maps to one integer register **or** one XMM register. SysV instead counts integers and floats independently, so `b→XMM0` and `c→RSI`.

### 2. Windows shadow space (home space)

On Windows x64, **the caller must allocate 32 bytes of stack space immediately above the return address before every call**, even if all four arguments fit in registers. This "shadow space" (also "home space") gives the callee a place to spill `RCX`, `RDX`, `R8`, `R9` back to memory if it wants to take their address or just needs the registers.

```asm
; Windows x64 call to f(1, 2):
mov  rcx, 1
mov  rdx, 2
sub  rsp, 32          ; allocate the 32-byte shadow space
call f
add  rsp, 32          ; reclaim it
```

Forget the `sub rsp, 32` and the callee will spill into *your* stack frame, corrupting locals. This is a top cause of "works on Linux, crashes on Windows" FFI bugs.

### 3. The SysV red zone

On SysV, the 128 bytes **below** `RSP` are reserved for the current function: a **leaf function** (one that calls nothing) may freely use that space for scratch without ever decrementing `RSP`. Signal handlers and the OS promise not to clobber it.

```asm
; SysV leaf function using the red zone:
mov  [rsp-8],  rdi    ; scratch storage BELOW rsp, no 'sub rsp'
mov  [rsp-16], rsi
; ... compute ...
ret                    ; no stack adjustment needed
```

The catch: **the red zone does not exist on Windows.** Hand-written assembly or a custom code generator that assumes a red zone will silently corrupt memory on Windows, because an interrupt or the next call can overwrite that region. This is also why kernel code (where interrupts use the same stack) is compiled with `-mno-red-zone`.

### 4. 16-byte stack alignment and the `movaps` fault

Both SysV and Windows x64 require `RSP` to be **16-byte aligned at the moment a `call` executes**. Because `call` then pushes an 8-byte return address, **on entry to the callee `RSP` is 16n + 8** — i.e., 8 *off* alignment. The callee's prologue (`push rbp` makes it 16-aligned again, or `sub rsp, N` with the right N) restores 16-byte alignment before it issues any aligned SSE instruction.

Why it matters: instructions like `movaps`, `movdqa`, and many vectorized library routines require a 16-byte-aligned memory operand. If your hand-written call site leaves `RSP` misaligned by 8, the *callee's* first aligned SSE access faults with a general-protection (`#GP`) fault. The symptom — a crash inside `memset` or `printf` on the first SSE move — looks unrelated to your call until you check `RSP & 15`.

```text
At the CALL:        RSP % 16 == 0          (required)
After CALL pushes:  RSP % 16 == 8          (8 bytes of return addr)
Callee prologue:    push rbp  →  RSP % 16 == 0  again
```

AArch64 has the same spirit: `SP` must be 16-byte aligned at any point an instruction accesses memory relative to it, and always at a public function boundary.

### 5. Caller-saved vs callee-saved — the full tables

**SysV AMD64:**

```text
caller-saved (volatile):  RAX RCX RDX RSI RDI R8 R9 R10 R11
                          XMM0–XMM15
callee-saved (preserved): RBX RBP R12 R13 R14 R15   (and RSP)
```

**Windows x64:**

```text
caller-saved (volatile):  RAX RCX RDX R8 R9 R10 R11
                          XMM0–XMM5
callee-saved (preserved): RBX RBP RDI RSI R12 R13 R14 R15
                          XMM6–XMM15   (and RSP)
```

Note the asymmetry: **`RSI` and `RDI` are caller-saved on SysV but callee-saved on Windows**, and Windows treats `XMM6`–`XMM15` as callee-saved while SysV treats *all* XMM registers as caller-saved. Hand-written assembly ported between the two that forgets to save `RDI`/`RSI` (or `XMM6+`) on Windows will corrupt the caller's state.

**AArch64 AAPCS64:**

```text
caller-saved:  X0–X18 (X16/X17 are intra-call temps, X18 is platform-reserved)
               V0–V7, V16–V31
callee-saved:  X19–X28, FP (X29), LR (X30)
               V8–V15 (low 64 bits only)
```

### 6. The x86 cleanup conventions (still matter)

On 32-bit x86 there were no argument registers in the original conventions — everything went on the stack — so the *cleanup* question was central:

- **cdecl:** caller cleans up. Supports variadics (the callee can't know how many args were pushed, but the caller does). The C default.
- **stdcall:** callee cleans up with `ret N` (pop N bytes on return). Smaller call sites. **The entire Win32 API uses stdcall** (`WINAPI`/`__stdcall`).
- **fastcall:** first two integer args in `ECX`, `EDX`; rest on stack; callee cleans up.
- **thiscall:** the C++ MSVC convention for member functions — `this` in `ECX`.

Why this still bites you: if you declare a Win32 function as cdecl (caller cleanup) but it's really stdcall (callee cleanup), **both sides clean up the same stack arguments** — the stack pointer ends up wrong by the argument size after every call. A few calls in, the stack is hopelessly corrupted. This is the legendary "calling a stdcall function as cdecl" bug, and on 64-bit it's why everyone collapsed to a single convention.

> On 64-bit x86 these distinctions largely vanished: there is one convention per OS, always caller-cleanup, with the keywords kept only for source compatibility (the compiler ignores `__stdcall` in 64-bit builds).

---

## Code Examples

### Same function, three conventions — argument loading

```c
long f(long a, long b, long c) { return a + b + c; }
```

**SysV (Linux/macOS):**

```asm
; caller: f(10, 20, 30)
mov  edi, 10        ; a → RDI
mov  esi, 20        ; b → RSI
mov  edx, 30        ; c → RDX
call f
```

**Windows x64:**

```asm
; caller: f(10, 20, 30)
mov  ecx, 10        ; a → RCX
mov  edx, 20        ; b → RDX
mov  r8d, 30        ; c → R8
sub  rsp, 32        ; shadow space — required!
call f
add  rsp, 32
```

**AArch64:**

```asm
; caller: f(10, 20, 30)
mov  x0, 10         ; a → X0
mov  x1, 20         ; b → X1
mov  x2, 30         ; c → X2
bl   f             ; bl = branch-and-link; return addr → LR (X30)
```

### Mixed int/float, SysV vs Windows (the positional trap)

```c
double g(int a, double b, int c, double d);
```

**SysV** — integers and floats counted separately:

```asm
mov   edi, ...      ; a → RDI   (1st integer)
movsd xmm0, ...     ; b → XMM0  (1st float)
mov   esi, ...      ; c → RSI   (2nd integer)
movsd xmm1, ...     ; d → XMM1  (2nd float)
```

**Windows x64** — by *positional* slot, int OR xmm per slot:

```asm
mov   ecx, ...      ; a → RCX   (slot 1)
movsd xmm1, ...     ; b → XMM1  (slot 2)
mov   r8d, ...      ; c → R8    (slot 3)
movsd xmm3, ...     ; d → XMM3  (slot 4)
```

Same source, completely different register assignment. An FFI tool that hard-codes "floats go in XMM0, XMM1, …" is correct on SysV and *wrong* on Windows.

### Keeping the stack aligned by hand

```asm
; SysV leaf that needs to make ONE call and keep 16-byte alignment:
my_func:
    push rbp            ; rsp: 16n+8 → 16n  (now aligned)
    mov  rbp, rsp
    sub  rsp, 16        ; reserve 16 bytes of locals, still aligned
    ; ... rsp is 16-aligned here, safe to call ...
    call other
    leave              ; mov rsp,rbp ; pop rbp
    ret
```

If you `sub rsp, 8` instead of 16, the next `call` happens with `RSP` misaligned and the callee may fault on `movaps`.

### Demonstrating the red zone (SysV only)

```c
// Compile twice and diff the assembly:
//   gcc -O2 -S leaf.c               (uses [rsp-8], no 'sub rsp')
//   gcc -O2 -S -mno-red-zone leaf.c (adds 'sub rsp, 8')
long leaf(long x) {
    long tmp = x * x;     // scratch the compiler may park in the red zone
    return tmp + 1;
}
```

With the red zone, the compiler stores `tmp` at `[rsp-8]` without adjusting `RSP`. With `-mno-red-zone` it must `sub rsp` first. This flag is mandatory for kernel and interrupt code.

---

## Coding Patterns

### Pattern 1: Select the convention per platform with attributes

GCC/Clang let you force a convention regardless of the host:

```c
#ifdef _WIN32
  #define CB __attribute__((ms_abi))
#else
  #define CB __attribute__((sysv_abi))
#endif

// A callback that must follow a specific OS's convention even when
// compiled on the other OS (useful for emulators, loaders, JITs).
int CB on_event(int code, void *ctx);
```

### Pattern 2: Always reserve shadow space in emitted Windows calls

If you generate code, make "reserve 32 bytes + align to 16" a non-negotiable step of your call-emission routine. Bake it in so it can't be forgotten per-call.

### Pattern 3: Annotate Win32 declarations precisely

```c
// Match the OS convention; on 64-bit the keyword is a harmless no-op,
// on 32-bit it's load-bearing (callee cleanup).
int WINAPI MessageBoxA(void *hWnd, const char *text,
                       const char *caption, unsigned type);
```

### Pattern 4: Keep alignment arithmetic explicit in assembly

Comment every `push`/`sub rsp`/`call` with the resulting `RSP mod 16`. Reviewers (and you, later) can verify alignment by reading the comments.

---

## Best Practices

- **Decide the convention from OS + architecture first**, every time, before touching registers.
- **On Windows x64, always allocate the 32-byte shadow space** before a call, even when every argument is in a register.
- **Keep `RSP` 16-byte aligned at every `call`.** When hand-writing, track it instruction by instruction.
- **Compile kernel/interrupt code with `-mno-red-zone`.** The red zone is unsafe wherever interrupts share the stack.
- **Match cleanup conventions exactly on 32-bit x86.** Never declare a stdcall function as cdecl or vice versa.
- **Watch the callee-saved tables when porting assembly** — `RSI`/`RDI` and `XMM6+` change category between SysV and Windows.
- **Reproduce the crash under a debugger and inspect `RSP & 15` and the argument registers.** Convention bugs are obvious once you look at the actual register state.

---

## Edge Cases & Pitfalls

### Pitfall 1: The `movaps` crash from an 8-byte misalignment

A call site that leaves `RSP` at `16n+8` makes the callee fault on its first aligned SSE move. The crash appears deep inside a library function, with a stack that looks fine. Always check alignment at *your* call site, not the library's.

### Pitfall 2: Forgetting shadow space on Windows

No shadow space → the callee spills `RCX`/`RDX`/`R8`/`R9` over your local variables. Symptoms are corrupted locals that change as you edit unrelated code. Add `sub rsp, 32`.

### Pitfall 3: Assuming the red zone exists on Windows

Hand assembly or a code generator that uses `[rsp-8]` scratch works on Linux and silently corrupts data on Windows (and in any interrupt context). The red zone is a SysV-only luxury.

### Pitfall 4: stdcall ↔ cdecl mismatch

If declarations disagree about who cleans up, the stack pointer drifts by the argument size each call until the program collapses. On 32-bit Win32 code this is the classic "random crash after N calls."

### Pitfall 5: Windows positional pairing vs SysV separate counts

`f(int, double, int, double)` puts the floats in different XMM registers on the two platforms. An FFI marshaller that assumes "Nth float → XMM(N-1)" is wrong on Windows. Use the positional rule there.

### Pitfall 6: Porting assembly that clobbers `RSI`/`RDI` on Windows

They're scratch on SysV but callee-saved on Windows. Reuse them without saving and you corrupt the caller. Same trap with `XMM6`–`XMM15`.

---

## Apply it

1. Find a real component where **Calling Conventions** affects an interface or dependency.
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

- Which boundary is most affected by Calling Conventions?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
