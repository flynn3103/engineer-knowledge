# Control-Flow Integrity — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Control-Flow Integrity** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. What "Control Flow" Actually Is

Think of your program as a recipe. Most steps are "do this, then the next line." But some steps say "go do *that* whole sub-procedure and come back," or "depending on a value, jump to one of several places." Those branching steps are where control flow gets interesting — and where attackers live.

Branches come in two flavors:

- **Direct branches** have their destination baked into the instruction itself: `jump to address 0x4011a0`. The attacker can't change these without rewriting the program's code (which NX/DEP forbids). These are safe.
- **Indirect branches** read their destination *from memory or a register at runtime*. Three kinds matter:
  - **Returns** — "go back to wherever I was called from." The destination is the **return address**, stored on the stack.
  - **Function-pointer calls** — `callback()` where `callback` is a variable holding an address.
  - **Virtual calls** — in C++, calling a method through a base-class pointer looks up the real function in a table (the *vtable*) at runtime.

CFI is entirely about indirect branches. Direct branches are fixed; indirect branches read a target from data, and **data can be corrupted**.

### 2. The Original Sin: The Return Address Lives in Writable Memory

When function `A` calls function `B`, the CPU has to remember where to resume in `A` once `B` finishes. On most architectures it pushes the **return address** onto the **stack**. So the stack ends up holding, mixed together:

```text
   higher addresses
   +--------------------+
   | return address     |   <- where we jump back to when B returns
   +--------------------+
   | saved registers    |
   +--------------------+
   | local buffer[64]   |   <- our data, e.g. a 64-byte array
   +--------------------+
   lower addresses
```

The buffer (data we might write into) and the return address (a jump target) sit in the **same writable region**, often only a few bytes apart. That adjacency is the whole problem.

### 3. Stack Smashing: Turning a Buffer Bug Into a Hijack

Suppose `B` copies attacker-controlled input into `buffer[64]` *without checking the length* (the classic `strcpy(buffer, input)` bug). If the input is longer than 64 bytes, the write keeps going — past the end of the buffer, over the saved registers, and right onto the **return address**.

Now when `B` finishes and does its `ret`, the CPU reads the (corrupted) return address and jumps to wherever the attacker put. Historically, the attacker would put the address of code they had *also* placed in the buffer — their **shellcode**. Result: the attacker's code runs with the program's privileges.

This single technique — overflow a stack buffer, overwrite the return address, jump to injected shellcode — was the dominant remote-exploitation pattern for over a decade. Every defense on this page exists to break some link in that chain.

### 4. First Defense — NX / DEP / W^X: "Data Can't Run"

The injected-shellcode attack has an obvious weak point: the shellcode is sitting in a *data* buffer (the stack), but the CPU is being asked to *execute* it. What if we forbid that?

**NX** (No-eXecute), marketed as **DEP** on Windows and generalized as **W^X** ("write XOR execute"), is a hardware-backed rule enforced by the CPU and OS: every page of memory is either **writable** or **executable**, **never both at once**. Code pages are executable but read-only. Data pages (stack, heap) are writable but non-executable.

With NX on, the attacker can still corrupt the return address — but if they point it at their shellcode on the (non-executable) stack, the CPU refuses and the process crashes. **Injected-code attacks are dead.** This was a huge win, deployed broadly in the mid-2000s.

### 5. The Attacker's Answer: Reuse Code That's Already Allowed to Run

NX stops you from running *new* code. It does nothing to stop you from running *existing* code in a new order. The program is full of executable code — your functions, and crucially the entire C library (`libc`) linked in, with powerful functions like `system("...")`.

The simplest version is **return-to-libc**: instead of pointing the corrupted return address at injected shellcode, point it at an *existing* function like `system`, and arrange the stack so that function's argument is a string the attacker controls (like `"/bin/sh"`). NX is satisfied — `system` is legitimate, executable code — yet the attacker still gets what they want. (`middle.md` shows how this generalizes into the far more powerful *return-oriented programming*.)

The lesson: **NX raised the bar but didn't end the game.** It turned "inject and run my code" into "reuse the program's own code against it." That shift is *why CFI exists* — CFI is about controlling *which existing code* an indirect branch is allowed to reach.

### 6. The Cheap, Ubiquitous Guard: Stack Canaries

While the big defenses (CFI, shadow stacks) were being designed, compilers shipped a cheap, effective guard against the *specific* attack of stack smashing: the **stack canary** (also called a **stack cookie**, from StackGuard and Microsoft's `/GS` flag).

The idea is a tripwire. When a function starts, the compiler inserts code that places a secret random value — the **canary** — on the stack *between the local buffers and the return address*:

```text
   +--------------------+
   | return address     |
   +--------------------+
   | CANARY (secret)    |   <- tripwire
   +--------------------+
   | buffer[64]         |
   +--------------------+
```

Because the buffer overflow writes *upward* through memory, an overflow large enough to reach the return address **must pass through the canary first**, corrupting it. Just before the function returns, the compiler inserts a check: "is the canary still the value I stored?" If not, the program calls `__stack_chk_fail` and aborts immediately — *before* the corrupted return address is ever used.

What canaries catch and miss is the start of every real security discussion:

- **Catch:** contiguous stack buffer overflows that smash the return address. (The original attack.)
- **Miss:** overflows that *don't* cross the canary — e.g., a write to a function pointer *before* the canary, or an overflow that overwrites a local variable used as a target. Also miss: attacks that *read* the canary first (an info leak) and then write the correct value back. And miss: heap overflows, use-after-free, type confusion — none of those touch the stack canary at all.

Canaries are a great example of the recurring CFI theme: a cheap, targeted defense that closes one door, after which attackers walk through the others.

---

## Code Examples

> These examples illustrate *mechanisms* defensively. The "vulnerable" snippets exist only to show *why* a defense is needed; none is a working exploit.

### 1. The shape of the vulnerable code (C)

```c
#include <string.h>
#include <stdio.h>

void greet(const char *name) {
    char buffer[64];
    // BUG: no length check. If `name` is longer than 64 bytes,
    // strcpy keeps writing past `buffer`, eventually over the
    // saved return address sitting higher on the stack.
    strcpy(buffer, name);
    printf("Hello, %s\n", buffer);
}                       // <- `ret` here reads the (maybe corrupted) return address

int main(int argc, char **argv) {
    greet(argv[1]);     // attacker controls argv[1]
    return 0;
}
```

The fix is to bound the copy. This is the most fundamental defense: don't overflow in the first place.

```c
void greet_safe(const char *name) {
    char buffer[64];
    snprintf(buffer, sizeof buffer, "%s", name);  // bounded; never overflows
    printf("Hello, %s\n", buffer);
}
```

### 2. Seeing NX / W^X in action (conceptual)

You don't write NX in C; the OS and compiler set it on memory regions. The stack is marked non-executable automatically. You can *observe* the protections on a binary:

```bash
# On Linux, inspect security mitigations baked into a binary.
# (checksec is a small helper script; many distros package it.)
$ checksec --file=./myprogram
RELRO     STACK CANARY  NX     PIE
Full RELRO  Canary found  NX enabled  PIE enabled
```

- **NX enabled** → the stack/heap are non-executable; injected shellcode won't run.
- **Canary found** → the compiler inserted stack-cookie checks.
- **PIE** → the program loads at a randomized base (works with ASLR to hide addresses).
- **Full RELRO** → certain tables are made read-only after startup (more in `middle.md`).

### 3. Turning the stack canary on/off (compiler flags)

The canary is a *compiler* feature. With GCC/Clang:

```bash
# Canaries on (this is the default on most modern toolchains):
$ gcc -fstack-protector-strong greet.c -o greet

# Canaries fully off (do NOT do this in production — shown to explain the flag):
$ gcc -fno-stack-protector greet.c -o greet
```

What the compiler *generates* for a protected function, in plain English:

```text
function prologue:
    load secret canary from a per-thread location
    store canary onto the stack, just below the return address

... function body runs (maybe overflows a buffer) ...

function epilogue (before ret):
    reload the secret canary
    compare it to the value still on the stack
    if they differ -> call __stack_chk_fail (abort the program)
    otherwise -> ret normally
```

### 4. A memory-safe language sidesteps the whole class

The reason this whole topic is "systems-level" is that memory-safe languages don't expose raw return-address corruption to ordinary code:

```go
// Go: writing past a slice's length panics with a bounds check.
// There is no path from this bug to "overwrite the return address."
func greet(name string) {
    buf := make([]byte, 64)
    copy(buf, name) // copy never writes past len(buf); it truncates safely
    fmt.Printf("Hello, %s\n", buf)
}
```

```rust
// Rust: an out-of-bounds index panics; the borrow checker and bounds
// checks prevent the classic stack-smash from being reachable in safe code.
fn greet(name: &str) {
    let mut buf = [0u8; 64];
    let n = name.len().min(buf.len());
    buf[..n].copy_from_slice(&name.as_bytes()[..n]); // bounded
}
```

The takeaway for a junior: **most CFI relevance is for C/C++ code.** When you can choose a memory-safe language for new code, you remove the *reason* CFI exists. CFI is the safety net for the code that *must* be C/C++.

---

## Coding Patterns

These are the day-one habits that *prevent the bug CFI is the backstop for*. CFI is a net; not falling is better.

**Pattern: Always bound your copies.**

```c
// Bad
strcpy(dst, src);
sprintf(dst, "%s", src);

// Good — always pass the destination size
snprintf(dst, sizeof dst, "%s", src);
strlcpy(dst, src, sizeof dst);   // where available
```

**Pattern: Validate lengths before writing.**

```c
if (input_len > sizeof buffer) {
    return ERR_TOO_LONG;        // reject, don't truncate-and-pray
}
memcpy(buffer, input, input_len);
```

**Pattern: Keep mitigations on.** Don't disable canaries, NX, PIE, or RELRO to "fix a build error." Those flags are your safety net.

**Pattern: Prefer memory-safe languages for new code.** If you're starting fresh and the domain allows it, Go/Rust/Java remove the entire attack class.

---

## Best Practices

1. **Treat all external input as hostile, especially in C/C++.** The overflow that smashes a return address starts with one unchecked length.
2. **Leave compiler mitigations enabled** (`-fstack-protector-strong`, NX, PIE, RELRO). Verify them with `checksec`.
3. **Know which edge a defense protects.** Canary → backward edge. Forward-edge CFI → forward edge. You need both.
4. **Don't treat any single mitigation as "secure."** Each one has a documented bypass class. Defense in depth.
5. **Use memory-safe languages where you can**, and isolate the C/C++ you can't avoid (sandboxing, least privilege).
6. **Keep your toolchain and libraries patched.** Mitigations improve every release; old binaries miss them.

---

## Edge Cases & Pitfalls

- **"Canary found means I'm safe."** No. The canary protects one narrow thing (contiguous stack overflow of the return address). Heap bugs, forward-edge hijacks, and info-leak-then-rewrite all walk around it.
- **"NX makes overflows harmless."** No. NX kills *injected code*. Code-reuse attacks (return-to-libc, ROP) defeat NX entirely.
- **Disabling mitigations to make a JIT work.** JITs legitimately need writable-then-executable memory; the right answer is careful permission management (W^X with explicit transitions), not turning NX off globally.
- **Stripped symbols ≠ security.** Hiding function names doesn't stop overflows; attackers don't need your symbol table.
- **"My language is memory-safe, so CFI doesn't matter."** It matters for the runtime, the interpreter, and any C extension/FFI you call. Your safety ends at the FFI boundary.

---

## Common Mistakes

- Believing a single mitigation is a complete defense.
- Using `strcpy`/`sprintf`/`gets` because "the input is trusted" — it rarely stays trusted.
- Turning off `-fstack-protector` or marking pages `RWX` to silence a warning.
- Confusing **forward edge** (calls) with **backward edge** (returns) when reasoning about what's protected.
- Assuming randomization (ASLR) alone is enough; a single address leak can undo it.

---

## Tricky Points

- **The canary catches the attack that *crosses* it, not all overflows.** An overflow that overwrites a local function pointer sitting *below* the canary never trips it.
- **NX and code reuse coexist.** The attacker obeys NX perfectly — they only ever jump to already-executable code. That's the point of code reuse.
- **A read bug can be as dangerous as a write bug.** Leaking the canary or a code address can be the key that unlocks an otherwise-blocked write exploit.
- **"Indirect" is the magic word.** Direct branches are fixed and safe. Every CFI concern is about *indirect* branches reading a target from corruptible memory.

---

## Apply it

1. Choose one small, known input for **Control-Flow Integrity**.
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

- What problem does Control-Flow Integrity solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
