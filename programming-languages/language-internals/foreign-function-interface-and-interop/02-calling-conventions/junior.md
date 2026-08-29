# Calling Conventions — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Calling Conventions** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A function call is three machine-level steps

When you write `z = add(3, 4)`, the compiler emits roughly:

```text
1. Put the arguments where the convention says.   (load 3 → RDI, 4 → RSI)
2. CALL add.                                       (push return address, jump)
3. Read the result from where the convention says. (RAX → z)
```

Step 1 and step 3 are pure convention. There is nothing physically forcing `3` to go into `RDI` — it's a rule both sides obey. The `call` and `ret` instructions in step 2 are real hardware, but even they cooperate with the convention: `call` *pushes a return address onto the stack*, and the convention says the stack must look a certain way.

### 2. The first few arguments go in registers (on x86-64 Linux/macOS)

On the SysV AMD64 ABI — what you get on Linux and macOS — **integer and pointer arguments** are passed in these registers, in this exact order:

```text
1st arg → RDI
2nd arg → RSI
3rd arg → RDX
4th arg → RCX
5th arg → R8
6th arg → R9
7th arg and beyond → on the stack
```

So for `add(3, 4)`: `3` goes in `RDI`, `4` goes in `RSI`. For a function with ten integer arguments, the first six ride in registers and the last four are pushed onto the stack.

**Floating-point arguments** (`float`, `double`) use a *different* set of registers — `XMM0` through `XMM7` — counted independently. So `void f(int a, double b, int c)` puts `a` in `RDI`, `c` in `RSI` (the *second integer*), and `b` in `XMM0` (the *first float*). The integer count and the float count advance separately. This trips people up the first time.

> A handy mnemonic for the integer order on Linux/macOS: **"Diane's Silk Dress Cost $89"** → **D**I, **S**I, **D**X, **C**X, **8**, **9**.

### 3. The return value comes back in a register

An integer or pointer result comes back in **`RAX`**. So `add` ends with the sum in `RAX`, and the caller copies `RAX` into `z`. A `double` result comes back in `XMM0`. That's it for the common case — one register in, one register out.

### 4. The stack: where call and ret live

The `call` instruction doesn't just jump. It first **pushes the return address** (the instruction right after the `call`) onto the stack. When the callee runs `ret`, it **pops that address** and jumps back. This is how a function knows where to return — even though the same function may be called from a hundred different places.

```text
Before CALL:                 After CALL (inside callee):
  RSP ──► [ caller locals ]    RSP ──► [ return address ]   ◄── pushed by call
                                       [ caller locals ]
```

The stack grows *downward*: pushing makes `RSP` smaller. This is just the convention on x86-64; it's not a law of nature, but every tool assumes it.

### 5. Caller-cleanup: the caller fixes the stack afterward

On x86-64, if some arguments were passed on the stack, **the caller is responsible for removing them** after the call returns. The callee just does its job and returns; it doesn't tidy up arguments the caller pushed. This is called **caller cleanup** (the historical x86 name is `cdecl`). It's the default you'll meet first. (There's an alternative — *callee cleanup* / `stdcall` — but that's a `middle.md` topic, and it's mostly an old 32-bit Windows thing.)

### 6. Some registers must survive the call; some may not

Imagine you put a value in `RBX`, then call a function. When the function returns, is your value still in `RBX`? The answer depends on the convention's two categories:

- **Caller-saved (volatile)** registers: the callee is allowed to clobber them. If you need the value to survive, **you** save it first. `RAX`, `RDI`, `RSI`, `RDX`, `RCX`, `R8`–`R11` are caller-saved on SysV.
- **Callee-saved (non-volatile)** registers: the callee promises to restore them before returning. `RBX`, `RBP`, `R12`–`R15` are callee-saved on SysV.

You don't usually manage this by hand — the compiler does — but it explains why a debugger can recover some of your variables across a call and not others.

---

## Code Examples

### A function and what the compiler does with the call

```c
// add.c
int add(int a, int b) {
    return a + b;
}

int main(void) {
    int z = add(3, 4);
    return z;
}
```

Compile and disassemble on Linux/macOS x86-64:

```bash
gcc -O0 -c add.c -o add.o
objdump -d add.o          # show the machine code
```

The interesting part of `main` looks roughly like:

```asm
; main: int z = add(3, 4);
mov    esi, 4          ; 2nd argument → ESI (low half of RSI)
mov    edi, 3          ; 1st argument → EDI (low half of RDI)
call   add             ; push return address, jump to add
; result is now in EAX (low half of RAX)
mov    DWORD PTR [rbp-4], eax   ; store result into local z
```

And `add` itself:

```asm
; add:
mov    eax, edi        ; eax = a   (1st arg came in via EDI)
add    eax, esi        ; eax += b  (2nd arg came in via ESI)
ret                    ; return; result is in EAX
```

Read those two `mov`s in `main` carefully: **`3` is loaded into `EDI` and `4` into `ESI` *before* the `call`.** That is the calling convention in action. `add` doesn't "receive" parameters — it just reads `EDI` and `ESI` because the contract guarantees they hold the arguments. The result is left in `EAX`, and `main` reads it from there.

> `EDI`/`ESI`/`EAX` are the 32-bit halves of the 64-bit `RDI`/`RSI`/`RAX`. Because `int` is 32 bits, the compiler uses the 32-bit names. Same registers.

### Floats use different registers

```c
double scale(int n, double factor) {
    return n * factor;
}
```

Disassembly highlights:

```asm
; scale:
; n      arrived in EDI   (1st INTEGER argument)
; factor arrived in XMM0  (1st FLOAT argument)
cvtsi2sd xmm1, edi        ; convert int n to double in xmm1
mulsd    xmm1, xmm0       ; xmm1 = n * factor
movsd    xmm0, xmm1       ; result → XMM0 (float return register)
ret
```

Notice: the integer argument went to `EDI`, the floating argument went to `XMM0`, and the `double` result came back in `XMM0`. Two independent lanes.

### Calling a function with more than six integer arguments

```c
long sum8(long a, long b, long c, long d,
          long e, long f, long g, long h) {
    return a + b + c + d + e + f + g + h;
}
```

When `main` calls `sum8(1,2,3,4,5,6,7,8)`:

```asm
; first six go in registers:
mov edi, 1   ; a
mov esi, 2   ; b
mov edx, 3   ; c
mov ecx, 4   ; d
mov r8d, 5   ; e
mov r9d, 6   ; f
; the seventh and eighth go on the stack:
push 8       ; h   (pushed first / higher)
push 7       ; g
call sum8
add  rsp, 16 ; CALLER cleans up the two stack args (caller cleanup)
```

That final `add rsp, 16` is the caller removing the two 8-byte arguments it pushed — the "caller cleanup" rule made concrete.

---

## Coding Patterns

As a junior you rarely touch the convention directly, but a few patterns keep you safe:

### Pattern 1: Always declare `extern "C"` (or the equivalent) at FFI boundaries

When you expose a function to be called from another language, mark it with the plain C convention so name mangling and the convention are predictable:

```c
// In C++ — without extern "C", the name gets mangled and may use a
// different convention.
extern "C" int add(int a, int b) {
    return a + b;
}
```

### Pattern 2: Match the declared prototype exactly on both sides

The convention is computed from the function's *types*. If one side thinks the second argument is an `int` and the other thinks it's a `double`, they look at different registers (`RSI` vs `XMM0`) and the call goes wrong with no warning. Keep the header the single source of truth.

### Pattern 3: Let the compiler do the work — don't hand-roll calls

If you write inline assembly to call a function, you become responsible for the entire convention (argument placement, alignment, cleanup, register preservation). Avoid it until you genuinely need it. The compiler is correct by construction.

---

## Best Practices

- **Trust the prototype, keep it shared.** The function signature in a shared header is what generates correct calls on both sides. Never let two translation units disagree about a function's types.
- **Always use `extern "C"` for cross-language entry points** so the name and convention are the plain, predictable C ABI.
- **Don't assume registers survive a call.** If you're reading values in a debugger after a call, only callee-saved registers are guaranteed intact.
- **Compile both sides for the same platform/architecture.** The SysV convention on Linux differs from the Windows x64 convention; a 32-bit and a 64-bit build use different conventions entirely.
- **When something crashes "only in release builds," suspect a convention or undefined-behavior mismatch**, not the optimizer being "buggy."
- **Read the disassembly when confused.** `objdump -d` (or your IDE's disassembly view) shows you exactly which register each argument went into. It removes all guesswork.

---

## Edge Cases & Pitfalls

### Pitfall 1: Mismatched prototypes silently corrupt arguments

If a header declares `void f(int)` but the real function is `void f(double)`, the caller loads the value into `EDI` and the callee reads `XMM0`. No crash at the call — just garbage. **Always include the real header; never re-declare functions yourself.**

### Pitfall 2: Wrong platform's convention

A function compiled for Windows x64 expects its first argument in `RCX`, not `RDI`. If a tool calls it as if it were SysV, the first argument lands in the wrong register. This is why FFI glue must know the target OS, not just the architecture.

### Pitfall 3: Forgetting that floats live in separate registers

`f(int, double, int)` does **not** put the three arguments in `RDI`, `RSI`, `RDX`. It puts the two ints in `RDI`, `RSI` and the double in `XMM0`. Counting integers and floats together is a classic beginner error.

### Pitfall 4: Assuming the stack frame stays put

Stack-passed arguments and the return address sit in memory just above `RSP`. Writing past the end of a local array can overwrite the return address — and then `ret` jumps somewhere random. This is the mechanism behind classic stack-smashing bugs.

### Pitfall 5: Thinking the convention is "just how computers work"

It isn't — it's a *choice*. Different OSes, architectures, and even special function attributes change it. Treat "which convention?" as a real question whenever you cross a boundary between separately built code.

---

## Apply it

1. Choose one small, known input for **Calling Conventions**.
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

- What problem does Calling Conventions solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
