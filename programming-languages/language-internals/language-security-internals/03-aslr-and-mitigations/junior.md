# ASLR & Mitigations — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **ASLR & Mitigations** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Where the pieces of a program live

When a process starts, its virtual address space is carved into regions. A simplified picture:

```text
high addresses
  ┌───────────────────────────┐
  │  stack (grows downward)   │   local variables, return addresses
  ├───────────────────────────┤
  │           ...             │
  │   shared libraries        │   libc, libssl, ...
  │           ...             │
  ├───────────────────────────┤
  │  heap (grows upward)      │   malloc / new
  ├───────────────────────────┤
  │  BSS / data               │   globals
  │  text (code)              │   your program's machine instructions
  └───────────────────────────┘
low addresses
```

Each of those regions has a **base address**. Without ASLR, those bases are the *same every run* — predictable. An attacker can open the binary, note that some useful function sits at, say, `0x401234`, and bake that number into their attack. It will work every time.

### 2. What ASLR actually randomizes

ASLR shifts the base address of each region by a random amount each time the program starts:

- **Stack base** — randomized.
- **Heap / `mmap` base** — randomized (this also covers where shared libraries land).
- **Shared libraries** — each loaded at a random offset.
- **The executable itself** — randomized *only if it's a PIE*. A non-PIE executable's code stays at a fixed address even with ASLR on. This is a crucial gap.

So `0x401234` is no longer a stable target. The same function might be at `0x55a3b1e91234` this run and `0x7f02c4d51234` the next. The attacker's hardcoded number is now wrong.

### 3. Entropy: why 64-bit beats 32-bit

The strength of ASLR is the number of possible positions, measured in **bits of entropy**. If there are 2^N possible base addresses, the attacker has a 1-in-2^N chance of guessing right.

- On **32-bit** systems, the usable address space is small, so ASLR can only offer roughly 8–16 bits of entropy for some regions. 2^8 = 256, 2^16 = 65,536. Those are small enough that an attacker who can retry quickly can simply **brute-force** them — guess until one works.
- On **64-bit** systems, there's vastly more room, so regions can get ~28–30+ bits of entropy. 2^28 ≈ 268 million guesses. Brute-forcing becomes impractical for most attacks (and each wrong guess usually crashes the process, which is noisy and slow).

**Takeaway:** 32-bit ASLR is weak by design; 64-bit ASLR is genuinely strong. If you can build 64-bit, do.

### 4. PIE and PIC: making the code itself movable

For the libraries to be relocatable, their code must not contain hardcoded absolute addresses. **Position-Independent Code (PIC)** uses *relative* addressing ("jump 200 bytes forward from here") and routes external references through a small table. A **Position-Independent Executable (PIE)** applies the same technique to your main program, so the OS can load *it* at a random base too.

When PIC code needs to call an external function like `printf`, it doesn't jump to a fixed address. It goes through two tables:

- The **PLT (Procedure Linkage Table)** — a small stub for each external function.
- The **GOT (Global Offset Table)** — where the *real, resolved* address of each external function gets stored at runtime.

The first call to `printf` resolves its real address and stores it in the GOT; later calls jump straight through. This indirection is what makes the code position-independent. It's also a target: if an attacker can overwrite a GOT entry, they can redirect a function call. That's exactly why **RELRO** exists.

### 5. The companion mitigations

ASLR is one layer. The others:

- **DEP / NX / W^X:** Marks the stack, heap, and data pages as **non-executable**. An old attack technique was to inject machine code into a buffer and jump to it; NX makes that injected code un-runnable. This forces attackers toward more complex techniques (reusing existing code instead of injecting new code).
- **Stack canaries:** The compiler inserts a random value between local variables and the saved return address. Before a function returns, it checks the canary. A linear buffer overflow that overwrites the return address *also* overwrites the canary, the check fails, and the program aborts. (Covered in depth in a sibling stack-protection topic; here we just note it composes with ASLR.)
- **RELRO:** After the dynamic linker resolves external addresses into the GOT, **Full RELRO** marks the GOT read-only. Now an attacker can't overwrite GOT entries to hijack calls. **Partial RELRO** protects less.
- **FORTIFY_SOURCE:** When you call `strcpy(dst, src)` and the compiler can see the size of `dst`, FORTIFY swaps in a checked version that aborts on overflow instead of corrupting memory.

### 6. Why they're stronger together

Imagine an attacker with a buffer overflow:

- With **NX** on, they can't inject and run shellcode. They must reuse existing code.
- To reuse existing code, they need to know *where that code is* — but **ASLR** randomized it.
- To learn where it is, they need an **info leak** (a separate bug that discloses an address).
- Even with a leak, **canaries** make smashing the stack to reach the return address risky.
- Even if they redirect a call, **Full RELRO** stopped the easy GOT overwrite.

Each layer doesn't *prevent* the next attack outright; it *raises the cost*. The attacker now needs the overflow **plus** an info leak **plus** a way around the canary, instead of just the overflow. That compounding cost is the whole point of defense in depth.

### 7. The one weakness to remember: info leaks

This is the single most important caveat about ASLR, and it's worth memorizing now: **ASLR is defeated by an information leak.** If any bug lets the attacker read even *one* real pointer from a randomized region, they learn that region's base, and the *entire region is de-randomized*. Leak one libc pointer, and you know where *all* of libc is, because the internal layout of a library is fixed — only the base moves. ASLR randomizes *where the deck starts*, but the cards are still in the same order. See one card's position and you know them all.

This is why modern exploits are usually **two bugs**: an info-leak bug to beat ASLR, and a memory-corruption bug to take control.

---

## Code Examples

We are **defensive** here. The examples below are about *building* and *checking* protections, not attacking. There are no exploits.

### Checking ASLR status on Linux

```bash
# 0 = off, 1 = partial (stacks/libs/mmap), 2 = full (also brk heap)
cat /proc/sys/kernel/randomize_va_space
# Most modern distros report: 2
```

### Observing that addresses move between runs

A tiny, safe program that prints the address of a stack variable, a heap allocation, and a libc function. Run it a few times: with ASLR on, the numbers change each run.

```c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int local = 0;
    int *heap = malloc(sizeof(int));
    printf("stack var : %p\n", (void *)&local);
    printf("heap alloc: %p\n", (void *)heap);
    printf("printf @  : %p\n", (void *)printf);  // a libc address
    free(heap);
    return 0;
}
```

```bash
$ ./addrs ; ./addrs
stack var : 0x7ffe1a2b3c4c
heap alloc: 0x55d9e4f012a0
printf @  : 0x7f3c9a1b2d40
stack var : 0x7ffd88c4e91c    # different each run = ASLR working
heap alloc: 0x561af20b32a0
printf @  : 0x7f81c33a4d40
```

If those numbers were *identical* across runs, ASLR would be off (or the binary is non-PIE for the executable's own addresses).

### Compiling with the protections turned on (GCC/Clang on Linux)

```bash
# PIE + non-executable stack + stack canaries + Full RELRO + FORTIFY
gcc -O2 -D_FORTIFY_SOURCE=2 \
    -fstack-protector-strong \
    -fPIE -pie \
    -Wl,-z,relro,-z,now \
    -Wl,-z,noexecstack \
    program.c -o program
```

- `-fPIE -pie` → the executable's code is position-independent and gets randomized.
- `-fstack-protector-strong` → stack canaries on functions that need them.
- `-Wl,-z,relro,-z,now` → Full RELRO (resolve everything at load, then make the GOT read-only).
- `-Wl,-z,noexecstack` → ensure the stack page is non-executable (NX).
- `-D_FORTIFY_SOURCE=2` → bounds-checked variants of common functions (needs optimization, e.g. `-O2`).

### Reading a `checksec` report

```bash
$ checksec --file=./program
RELRO           STACK CANARY      NX            PIE
Full RELRO      Canary found      NX enabled    PIE enabled
```

That is the "all green" report you want for a hardened native binary. A report showing `No RELRO`, `No canary found`, `NX disabled`, or `No PIE` flags a binary that's easier to attack.

### Confirming a binary is a PIE

```bash
$ file ./program
./program: ELF 64-bit LSB pie executable, x86-64, ...
#                          ^^^ "pie executable" — good

# A non-PIE binary would say "LSB executable" without "pie".
```

### Checking ASLR-relevant settings on other platforms (conceptual)

- **Windows:** ASLR (and DEP) are controlled per-binary by linker flags (`/DYNAMICBASE` for ASLR, `/NXCOMPAT` for DEP, `/HIGHENTROPYVA` for 64-bit high-entropy ASLR). System-wide and per-app policy can also be set via **Exploit Protection** (the modern successor to the older EMET tool) in Windows Security.
- **macOS:** ASLR is on by default; system binaries are built position-independent, and the loader (`dyld`) randomizes the shared cache and library placement.

---

## Coding Patterns

### Pattern 1: Make hardening flags a build default, not an afterthought

Bake the flags into your build system so every binary gets them, instead of relying on memory:

```makefile
CFLAGS  += -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE
LDFLAGS += -pie -Wl,-z,relro,-z,now -Wl,-z,noexecstack
```

### Pattern 2: Verify in CI, don't trust

Add a CI step that fails the build if a binary loses a protection:

```bash
# Fail if PIE, RELRO, NX, or canary is missing.
checksec --file=./build/program --output=json \
  | grep -q '"pie":"yes"' || { echo "FAIL: not a PIE"; exit 1; }
```

(Use the tool's actual JSON keys; the point is *automated enforcement*.)

### Pattern 3: Don't undo ASLR by accident

Avoid build or runtime settings that disable randomization unless you have a strong reason:

- Don't `setarch -R` (which disables ASLR) outside of debugging.
- Don't ship a non-PIE executable in a process that loads PIE libraries — the fixed module becomes the attacker's anchor.
- Don't bake absolute addresses into your own code or config.

### Pattern 4: Treat info leaks as critical, not cosmetic

A log line, error message, or debug endpoint that prints a raw pointer is an **ASLR bypass primitive**. Strip pointers from anything an attacker can read. Treat "this prints an address" as a security bug, not a logging nuisance.

---

## Best Practices

- **Build 64-bit when you can.** It's the single biggest entropy win.
- **Turn everything on:** PIE, NX, Full RELRO, stack canaries, FORTIFY. The combined cost is small; the combined benefit is large.
- **Audit with `checksec`** (or platform equivalents) and enforce the result in CI.
- **Don't let one non-PIE module weaken the process.** Hardening is only as strong as the least-hardened loaded object.
- **Fix the bug, don't just rely on the mitigation.** ASLR makes exploitation harder, not impossible. Memory-safe languages and careful bounds-checking remove the bug class entirely.
- **Treat any pointer disclosure as a serious vulnerability.** It's the master key to ASLR.
- **Keep your OS and libraries updated.** Entropy improvements, stronger KASLR, and CET/shadow-stack support arrive through updates.
- **On Windows, opt into high-entropy 64-bit ASLR** (`/HIGHENTROPYVA`) and DEP (`/NXCOMPAT`), and consider Exploit Protection policies.

---

## Edge Cases & Pitfalls

- **Non-PIE in an ASLR world.** Turning ASLR on does **not** randomize a non-PIE executable's own code — only the stack, heap, and libraries move. The fixed code becomes a reliable anchor for attackers. You must compile with `-fPIE -pie` to randomize the executable.
- **One un-randomized module breaks the chain.** A process is a mix of the executable and all its libraries. If even one of them is loaded at a fixed address (non-PIC, or a legacy DLL without ASLR), the attacker has a fixed reference point that doesn't depend on guessing.
- **Low-entropy regions.** Not all regions get equal randomization. Historically some had far fewer bits than others; an attacker targets the weakest region.
- **Forking servers don't re-randomize.** When a process `fork()`s, the child inherits the *same* memory layout as the parent — same randomization. A server that handles each request in a fork, and *crashes and respawns from the same parent* on failure, gives the attacker many identical-layout attempts. This is the core insight behind brute-forcing forking servers, even on 64-bit.
- **`_FORTIFY_SOURCE` needs optimization.** It only kicks in with `-O1` or higher; at `-O0` it silently does nothing. A debug build is less protected than a release build.
- **Disabling ASLR for debugging and forgetting.** Developers often disable ASLR to make debugging reproducible (`setarch -R`, or core-dump tooling). Make sure production never runs that way.
- **JITs and ASLR.** Just-in-time compilers generate executable code at runtime, which interacts with NX/W^X. Done carelessly, a JIT region can become an attacker's playground (see "JIT spray" in later levels). This is an advanced concern; just know JITs need special handling.

---

## Common Mistakes

1. **Thinking ASLR fixes the bug.** It doesn't. It makes the bug harder to *exploit*. The buffer overflow is still there.
2. **Shipping a non-PIE binary and assuming ASLR covers it.** The executable's own code stays put without PIE.
3. **Leaving `_FORTIFY_SOURCE` on but building at `-O0`.** It does nothing without optimization.
4. **Printing pointers in logs or errors.** That's a free ASLR bypass handed to anyone who reads the output.
5. **Disabling ASLR globally "to make a crash reproducible" and never re-enabling it** in the shipped artifact.
6. **Confusing Partial and Full RELRO.** Partial RELRO leaves the GOT writable; only Full RELRO (`-z now`) makes it read-only.
7. **Assuming 32-bit ASLR is strong.** It's brute-forceable. Don't rely on it.
8. **Forgetting that mitigations compose.** Enabling only one (say, just NX) leaves the others' attack paths wide open.

---

## Apply it

1. Choose one small, known input for **ASLR & Mitigations**.
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

- What problem does ASLR & Mitigations solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
