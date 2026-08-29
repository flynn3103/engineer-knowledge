# ASLR & Mitigations — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **ASLR & Mitigations** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Who randomizes what, and when

Randomization is not one mechanism; it's a division of labor:

- **The kernel** randomizes the **stack base**, the **mmap base** (which determines where libraries and large allocations land), and the **brk heap** offset. On Linux this is governed by `randomize_va_space` (0/1/2) plus per-architecture entropy settings.
- **The kernel's ELF loader** applies a random **load bias** to a PIE executable when it `exec`s it — that's what randomizes your own code.
- **The dynamic linker** (`ld.so`) then loads each shared library at an address derived from the randomized mmap base and applies **relocations** so the code works at its new location.

So a single `exec` of a PIE program involves the kernel randomizing the executable's base, the stack, and the mmap region, and `ld.so` placing libraries within that randomized mmap region. Each of these is a separate source of entropy with its own bit count.

### 2. Entropy, quantified

"More bits is better" — but the actual numbers matter because they decide whether brute force is feasible.

- **Why 32-bit is weak:** On 32-bit x86 Linux, the classic result (Shacham et al., 2004) is that the mmap region had only **16 bits** of entropy for library placement. 2^16 = 65,536 positions. A forking server that doesn't re-randomize across child crashes can be brute-forced in seconds to minutes, because each wrong guess just crashes a child and the attacker retries against the *same* layout.
- **Why 64-bit is strong:** On x86-64 Linux, mmap entropy is typically **28 bits** (and stack/PIE entropy often higher). 2^28 ≈ 268 million. Each wrong guess on most targets crashes the process, so without a leak, brute force is impractical — you'd need hundreds of millions of crashes.
- **Region asymmetry:** Not all regions get the same entropy. Historically the executable (PIE) base, the stack, and the mmap base differed. An attacker targets the *lowest-entropy* region in the process. A region with only 8 bits is a soft underbelly even when everything else has 28.

The headline rule for a mid-level engineer: **ASLR's strength is the minimum entropy across the regions the attacker can target, not the maximum.**

### 3. Position-independent code, concretely

PIC's job: produce code that runs correctly no matter what base it's loaded at. The trick is to never embed an absolute address. Two mechanisms:

- **RIP-relative addressing (x86-64):** "load from *here + offset*" instead of "load from *absolute address*." The CPU computes the target relative to the current instruction pointer. Self-relative references inside the same module need no fix-up at all.
- **GOT/PLT indirection for *external* references:** A call to another module's function can't be self-relative (the other module's bias is unknown at compile time), so it's resolved at runtime and stored in the GOT.

### 4. The GOT/PLT walk-through

Picture a PIC program calling `printf`. Compile time produces:

```text
call printf@plt        # not a direct call to printf
```

`printf@plt` is a tiny stub in the **PLT**. With **lazy binding**, the first call works like this:

```text
1. call printf@plt
2. PLT stub: jump to *GOT[printf]
3. GOT[printf] initially points BACK into the PLT (the "resolver" path)
4. resolver (in ld.so) computes printf's real address
5. resolver writes that real address into GOT[printf]
6. control transfers to printf
   --- on every later call ---
1. call printf@plt
2. PLT stub: jump to *GOT[printf]   # now points straight at printf
```

The GOT must be **writable** for step 5 to work. That writability is exactly what an attacker wants to abuse: overwrite `GOT[printf]` with the address of some other function, and the next `printf` call jumps there instead. **RELRO** closes this.

### 5. RELRO: Partial vs. Full

- **Partial RELRO** (`-z relro` alone): The linker groups read-only-after-relocation data together and `mprotect`s it read-only after startup. But the **`.got.plt`** (the part of the GOT used by lazy binding) stays writable, because lazy binding needs to write to it on first call. So **function-pointer GOT entries remain hijackable.**
- **Full RELRO** (`-z relro -z now`): `-z now` forces **eager binding** — every symbol is resolved at load time. Now nothing needs to write to the GOT afterward, so the loader can make the *entire* GOT read-only. A GOT-overwrite attack is dead. The cost is slightly slower startup (resolve everything up front) and you lose lazy binding's "only pay for what you call."

A mid-level takeaway: **Full RELRO is the one to want.** Partial RELRO sounds protective but leaves the most attacked table writable.

### 6. NX / DEP / W^X and what it forces

NX marks data pages (stack, heap, `.data`, `.bss`) non-executable. This kills the oldest exploit shape — inject machine code into a buffer, overwrite a return address to point at it, run it. With NX, the injected bytes are data and can't be executed.

NX doesn't stop the attacker from *taking control*; it changes *what they can do with it*. They pivot to **code reuse**: chaining together fragments of *already-executable* code (the program's own code, libc, etc.). That's return-to-libc and ROP, covered at the senior level. The key composition fact for now: **NX is what makes ASLR matter so much.** If you could inject and run code, you wouldn't care where existing code lives. NX forces reuse, and reuse requires knowing addresses, which ASLR hides. The two mitigations are designed to work as a pair.

### 7. Stack canaries and FORTIFY, in composition

- **Stack canaries** (covered in depth in a sibling stack-protection topic) place a random value between local buffers and the saved return address. A *contiguous* overflow that reaches the return address must pass through the canary; the function-epilogue check then aborts. Canaries compose with ASLR by adding *another* secret the attacker must either avoid disturbing or leak. Note their limits: they don't stop *non-contiguous* writes (e.g., an attacker-controlled index that writes directly at the return address), and the canary value itself can be leaked.
- **FORTIFY_SOURCE** rewrites calls like `memcpy(dst, src, n)` to `__memcpy_chk(dst, src, n, __builtin_object_size(dst, ...))` when the destination size is known at compile time, aborting on overflow. It requires optimization (`-O1`+) and only helps where the size is statically derivable. It's a cheap, targeted layer that catches the most common library-function overflows.

### 8. Prelink: how an optimization weakened ASLR

A historical cautionary tale worth knowing. **Prelink** was a Linux tool that pre-computed and *baked in* fixed load addresses for shared libraries to speed up program startup (skipping relocation work). The side effect: every prelinked library loaded at the *same* address across runs and across machines — effectively **disabling ASLR for those libraries.** It traded a security property for a small startup speedup. Modern systems have largely abandoned prelink (faster hardware and better linking made the speedup marginal, and the ASLR cost unacceptable). The lesson generalizes: **any optimization that fixes an address re-introduces the predictability ASLR removed.** Watch for it in your own systems — pinned addresses, cached layouts, shared snapshots.

---

## Code Examples

Defensive and observational only.

### Seeing the actual memory map and its randomization

```bash
# Map of a running process: bases of stack, heap, each library.
cat /proc/$$/maps | head
# Example lines:
# 55a3b1e91000-55a3b1e92000 r-xp ... /usr/bin/bash      <- code (PIE base)
# 7f3c9a100000-7f3c9a2c0000 r-xp ... /usr/lib/libc.so.6 <- libc base
# 7ffe1a200000-7ffe1a221000 rw-p ... [stack]            <- stack
```

Run a PIE program twice and diff the bases — they move. Run a non-PIE program twice and its *code* base stays fixed while stack/heap/libs still move.

### Measuring stack entropy empirically (safe)

```bash
# Print a stack address many times; count distinct high bits to estimate entropy.
for i in $(seq 1 20); do
  ./addrs | awk '/stack var/ {print $4}'
done | sort -u | head
# Many distinct values => randomization is active.
```

### Lazy vs. eager binding, observed

```bash
# Force eager binding for one run (resolve all symbols at startup):
LD_BIND_NOW=1 ./program
# With Full RELRO compiled in (-z now), this is the default behavior.
```

### Inspecting GOT/PLT and RELRO status

```bash
# Is RELRO partial or full? Look for GNU_RELRO segment and BIND_NOW flag.
readelf -d ./program | grep -E 'BIND_NOW|FLAGS'
# DT_FLAGS BIND_NOW present  => eager binding => Full RELRO

readelf -l ./program | grep GNU_RELRO     # presence of the RELRO segment

# checksec summarizes it:
checksec --file=./program     # RELRO column: "Full RELRO" vs "Partial RELRO"
```

### A FORTIFY_SOURCE demonstration (defensive)

```c
#include <string.h>
#include <stdio.h>

int main(void) {
    char buf[8];
    const char *input = "this string is way too long for buf";
    // With -O2 -D_FORTIFY_SOURCE=2, the compiler rewrites this strcpy to
    // __strcpy_chk, which detects the overflow and aborts:
    //   *** buffer overflow detected ***: terminated
    // Without FORTIFY, this silently corrupts the stack.
    strcpy(buf, input);     // intentional bug, caught by FORTIFY
    printf("%s\n", buf);
    return 0;
}
```

```bash
gcc -O2 -D_FORTIFY_SOURCE=2 demo.c -o demo && ./demo
# *** buffer overflow detected ***: terminated   <- FORTIFY caught it
gcc -O0 demo.c -o demo_unsafe && ./demo_unsafe
# (no check at -O0 — silent corruption / crash)
```

### Building with the full hardening set (and what each flag buys)

```bash
gcc -O2 \
    -D_FORTIFY_SOURCE=2     `# size-checked libc funcs` \
    -fstack-protector-strong `# canaries` \
    -fstack-clash-protection `# defends against stack/heap clash` \
    -fcf-protection=full     `# Intel CET (shadow stack + IBT) where supported` \
    -fPIE -pie               `# randomize the executable` \
    -Wl,-z,relro,-z,now      `# Full RELRO` \
    -Wl,-z,noexecstack       `# NX stack` \
    -Wl,-z,separate-code     `# don't mix exec + writable in one page` \
    program.c -o program
```

---

## Coding Patterns

### Pattern 1: Re-randomize per request where it matters

A forking server's children share the parent's layout. If a worker can crash and respawn, an attacker gets repeated identical-layout attempts (the brute-force-the-fork class). Defenses:

- **`execve` after `fork`** (not just `fork`) for new workers, so the child gets a fresh randomized layout.
- **Crash-only design:** on a worker crash, fully re-exec rather than silently respawning a clone, so the attacker can't grind the same layout.

### Pattern 2: Eager binding by default

Compile with `-z now` (Full RELRO). The slightly slower startup is almost always worth a read-only GOT for a security-sensitive service.

### Pattern 3: Don't reintroduce fixed addresses

Audit for anything that pins an address: prelink-style caching, fixed `mmap(MAP_FIXED, ...)` at a constant address, shared memory at a constant address, JIT regions allocated at a predictable base. Each is a fixed anchor. If you must use `MAP_FIXED`, derive the address from a randomized base.

### Pattern 4: Make pointer disclosure impossible by construction

Strip raw pointers from logs, error messages, serialized output, and debug endpoints. Where you need a stable identifier, use an opaque, randomized handle that doesn't reveal an address.

---

## Best Practices

- **Compile 64-bit, PIE, Full RELRO, NX, canaries, FORTIFY** — the full set, as a build default and a CI gate.
- **Prefer eager binding** (`-z now`) for anything security-relevant.
- **Audit for the weakest region and for fixed anchors**, not just "is ASLR on."
- **Restore re-randomization in forking/crash-respawn servers** by re-`exec`ing children.
- **Treat info leaks as critical** — they're the master bypass.
- **Keep toolchain and OS current** to get entropy improvements and CET/shadow-stack support.
- **Don't ship prelinked or non-PIE modules** into hardened processes.
- **Verify, don't assume** — `checksec` and `readelf` on the actual artifact, every build.

---

## Edge Cases & Pitfalls

- **Partial RELRO masquerading as protection.** Many binaries ship Partial RELRO and look "hardened," but the lazy-binding GOT (`.got.plt`) is still writable — the most-attacked table. Insist on Full RELRO.
- **Forking servers re-use layout.** The single biggest practical ASLR weakness for servers. `fork` copies the layout; only `exec` re-randomizes.
- **Partial overwrites beat high entropy.** ASLR randomizes the *high* bits of an address; the *low* bits within a page are fixed. An attacker who can overwrite only the low byte(s) of a pointer can retarget it within a known page *without* defeating randomization at all. This is why "high entropy" isn't a complete answer.
- **Low-entropy stragglers.** A single region with weak entropy undermines the rest. Audit per-region.
- **Mixed PIE/non-PIE process.** One non-PIE library or executable provides a fixed anchor; the attacker doesn't need to beat ASLR for the rest if they can pivot from the fixed module.
- **`MAP_FIXED` and hugepages.** Code that maps memory at a fixed address (some allocators, some JITs, some DBs) creates predictable regions.
- **`_FORTIFY_SOURCE` quietly off.** At `-O0`, or when the destination size isn't statically known, FORTIFY does nothing. Don't assume it's protecting a given call.
- **`LD_PRELOAD`/`LD_LIBRARY_PATH` and setuid.** The loader ignores these for setuid binaries (good), but mis-set environments can change which libraries load where in non-privileged contexts.

---

## Common Mistakes

1. **Accepting Partial RELRO as "RELRO is on."** The function-pointer GOT is still writable.
2. **Forgetting forks share layout.** Respawning a crashed worker as a clone gives attackers unlimited identical attempts.
3. **Trusting entropy numbers as an average.** The minimum-entropy region is what matters.
4. **Ignoring partial overwrites.** High entropy doesn't help when the attacker only needs to flip low bits within a page.
5. **Building with `_FORTIFY_SOURCE` at `-O0`** and believing it's active.
6. **Leaving a non-PIE module in a hardened process** and assuming ASLR covers everything.
7. **Reintroducing fixed addresses** via `MAP_FIXED`, prelink-style caching, or constant-address shared memory.
8. **Disclosing pointers** in logs/errors and treating it as cosmetic.

---

## Tricky Points

- **ASLR randomizes pages, not bytes.** The low ~12 bits (the page offset) are *not* randomized — they're determined by alignment within the region. That's the foothold for partial overwrites.
- **The GOT for data vs. for functions are different.** Partial RELRO protects the former and not the latter. The distinction is the whole point of "partial."
- **Lazy binding requires a writable GOT, which is the security cost.** Eager binding (`-z now`) is what *enables* a read-only GOT. RELRO and binding-mode are linked.
- **NX is what gives ASLR teeth.** Reason about them together: NX forces reuse, ASLR hides the reuse targets. Either one alone is much weaker.
- **A single leaked pointer de-randomizes only its *own* region.** Leaking a stack pointer doesn't tell you libc's base unless you can chain to a libc pointer. Attackers often need a leak that reaches the region they want to reuse.
- **Re-randomization on `fork` doesn't happen; on `exec` it does.** This single fact drives the secure design of forking servers.

---

## Apply it

1. Find a real component where **ASLR & Mitigations** affects an interface or dependency.
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

- Which boundary is most affected by ASLR & Mitigations?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
