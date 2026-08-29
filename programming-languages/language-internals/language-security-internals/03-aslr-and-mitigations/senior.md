# ASLR & Mitigations — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **ASLR & Mitigations** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The modern exploit shape ASLR forces

With NX + ASLR + Full RELRO + canaries deployed, the attacker can no longer inject shellcode, can no longer hardcode addresses, can no longer overwrite the GOT, and can no longer naively smash the stack past a canary. So the canonical exploit becomes a **two-bug** affair:

1. **An information leak** to defeat ASLR — recover the base of a region containing useful code (often libc).
2. **A memory-corruption primitive** to hijack control flow — overwrite a return address, a function pointer, or a vtable.

The hijack then drives a **code-reuse chain** (ROP/JOP) built from gadgets at addresses the leak revealed. The whole point of the senior view is that each mitigation you removed from the attacker's path *added a required capability to their attack.* ASLR's specific contribution: it converts "I know where the gadgets are" into "I must leak where the gadgets are." That's why **the info leak is the master key.**

### 2. Bypass class A: info-leak-then-reuse

The dominant class. Any primitive that discloses a real pointer suffices: an out-of-bounds *read* (format-string `%p`, a length-confusion that returns adjacent memory, an uninitialized-memory disclosure, a type confusion that reads a vtable pointer). Because a region's internal layout is fixed and only its base is randomized, **one leaked pointer yields the base by subtraction**, and from the base every address in that region is computable. Defensive implications:

- Out-of-bounds *reads* are as dangerous as writes — they're ASLR's undoing. Treat read-disclosure bugs as critical.
- Minimizing what a leak reveals (e.g., not co-locating sensitive code with leakable data) raises the cost.
- This class is why **re-randomization** and **leak-resistant designs** (below) exist: the only structural answer to "they will eventually leak something" is to make the leak stale or useless.

### 3. Bypass class B: brute force on forking servers (the BROP insight)

`fork()` copies the parent's address space, *including its randomization*. A server that forks a worker per connection and respawns identically on crash gives the attacker **many attempts against the same layout**. Two consequences:

- **Brute force becomes feasible even at 64-bit entropy** for the *purpose of locating a few key addresses*, because the attacker isn't guessing the whole space at once — they probe one byte/region at a time, using the **crash-vs-no-crash signal** as an oracle. Each probe either crashes the child (wrong) or doesn't (right), and the layout never changes, so information accumulates across attempts.
- **BROP (Blind ROP)** generalizes this: an attacker with *no copy of the binary and no explicit leak* can, against such a server, discover enough gadgets to build a chain purely from the crash oracle, then use a write primitive to dump the binary and complete a normal ROP attack.

Defensive answer: **break the shared-layout assumption.** Re-`exec` workers (fresh randomization), use crash-only respawn that re-randomizes, rate-limit/penalize crashes, and detect crash storms. The vulnerability isn't ASLR's entropy; it's the *reuse of one randomized layout across many trials*.

### 4. Bypass class C: partial overwrites and low-entropy footholds

Recall ASLR randomizes high bits; the page offset (low ~12 bits) is fixed. If a bug lets the attacker overwrite only the **low byte(s)** of a saved pointer, they can retarget it *within the same page or nearby* with **certainty**, not probability — no entropy is defeated because the randomized bits are untouched. This is potent against vtable/function pointers where a nearby method or gadget is reachable by changing a few low bits. Defensive implications:

- High entropy doesn't help against partial overwrites; you need to stop the *write* (bounds checking, memory safety) or make the nearby targets useless (CFI/IBT).
- Co-locating hostile-reachable pointers near useful code is risky.

### 5. Bypass class D: JIT spray vs. ASLR/DEP

A JIT compiler must allocate **executable** memory and fill it with attacker-influenceable content (the program being JIT-compiled). **JIT spray** exploits this: the attacker writes high-level code whose *constants* encode useful machine instructions; when the JIT emits the constants, the executable region contains attacker-chosen instruction bytes — sidestepping both DEP (the region is legitimately executable) and ASLR (the JIT region is large and/or predictably placed, so jumping into it doesn't require a precise address). Defensive answers, mostly the JIT's responsibility:

- **W^X for JIT memory:** never have a page simultaneously writable and executable; emit to a writable mapping, then flip to executable (dual-mapping / `MAP_JIT` on macOS, `mprotect` toggling, or a separate writer).
- **Constant blinding:** XOR constants with a per-process random key so attacker-controlled constants don't survive into emitted code verbatim.
- **Randomize JIT region placement and add guard pages / NOP insertion** to break the predictability JIT spray relies on.

### 6. Bypass class E: side-channel de-randomization

Randomization assumes the attacker can't learn the layout. **Microarchitectural side channels** break that assumption without any logical disclosure:

- **Cache/TLB timing** can reveal whether a given virtual address is mapped or which page a victim touched, leaking layout bits.
- **Branch-predictor and prefetch side channels** have been shown to recover kernel and user ASLR offsets.
- **Speculative-execution attacks** (the Meltdown/Spectre family) can read memory across protection boundaries; **Meltdown in particular was used to defeat KASLR** by reading kernel memory from user space, recovering the kernel's randomized base.

The defensive lesson: **ASLR's secret is only as strong as the hardware's ability to keep it.** Side channels are largely addressed at the hardware/OS level (KPTI, microcode, speculation barriers), not by application code — but a senior must know that "we have ASLR" is not a guarantee against an attacker with a side-channel primitive.

### 7. KASLR and its breaks

**KASLR** randomizes the *kernel's* base address so that kernel exploits can't hardcode kernel symbol addresses. It faces the same weaknesses as user-space ASLR, amplified:

- **Lower practical entropy** historically (the kernel maps into a constrained range), and many side channels target it specifically.
- **Meltdown** (2018) read kernel memory from unprivileged user space, trivially recovering the kernel base and defeating KASLR. The mitigation, **KPTI (Kernel Page-Table Isolation)**, unmaps most of the kernel from the user page tables, which both blocks Meltdown's read *and* removes the mapped kernel addresses a timing side channel could probe — restoring much of KASLR's value (at a context-switch performance cost).
- **FGKASLR (function-granular KASLR)** goes further by randomizing the *order of functions* within the kernel, so leaking one kernel address no longer reveals all of them — directly attacking the "move the deck, not the cards" weakness.

### 8. Modern hardening: making addresses-in-hand insufficient

The strategic shift: instead of only hiding addresses (which leaks defeat), make **knowing the address insufficient to hijack control flow.**

- **Re-randomization:** periodically re-randomize a live process (e.g., on a timer, or after handling a request) so any leaked address goes stale. The challenge is doing it cheaply and consistently (fixing up all live pointers), which limits adoption but research systems (e.g., Shuffler-style designs) demonstrate it.
- **Shadow stacks:** keep a second, protected copy of every return address. On `ret`, hardware/runtime compares; a mismatch (because an overflow rewrote the normal stack's return address) aborts. This **neutralizes return-address overwrite even when the attacker knows every address** — it attacks the corruption, not the secrecy.
- **Intel CET = shadow stack + IBT.** IBT requires every indirect call/jump target to be an `endbr64` landing pad, sharply constraining JOP/COP gadget chains. ARM's analogues are **PAC (Pointer Authentication)** — signing pointers with a key so a corrupted pointer fails verification — and **BTI (Branch Target Identification)**.
- **CFI (Control-Flow Integrity)**, software or hardware-assisted, restricts indirect transfers to a precomputed legal set, gutting reuse chains.

The senior framing: **ASLR is the probabilistic layer; shadow stacks/CET/PAC/CFI are the deterministic layer.** Modern defense combines both, so that beating ASLR (via leak) still leaves the attacker facing control-flow enforcement that an address alone can't bypass.

---

## Code Examples

Defensive and observational; no exploits.

### Checking for CET / shadow-stack support and opt-in

```bash
# Does the CPU/OS advertise CET shadow stack + IBT?
grep -o 'user_shstk\|ibt' /proc/cpuinfo | sort -u
# Is a binary built with CET landing pads / shstk?
readelf -n ./program | grep -i 'SHSTK\|IBT'     # GNU property notes
```

```bash
# Build with CET (shadow stack + IBT) where supported:
gcc -O2 -fcf-protection=full -fPIE -pie \
    -Wl,-z,relro,-z,now,-z,shstk program.c -o program
```

### Confirming KASLR and KPTI on Linux

```bash
# Is the kernel base randomized? (look for 'nokaslr' to know it's OFF)
cat /proc/cmdline | tr ' ' '\n' | grep -i kaslr   # absence of nokaslr => on

# Is KPTI (Meltdown mitigation, also re-strengthens KASLR) active?
cat /sys/devices/system/cpu/vulnerabilities/meltdown
# e.g.: "Mitigation: PTI"
dmesg | grep -i 'page table isolation'
```

### Detecting a forking server's shared-layout exposure (audit, not attack)

```bash
# Compare the libc base across two children of the same forking parent.
# If identical, the parent did fork WITHOUT exec -> shared randomization.
for pid in $(pgrep -P "$PARENT_PID"); do
  grep -m1 libc /proc/"$pid"/maps | awk '{print $1}'
done | sort -u
# One unique base => shared layout (brute-forceable). Many => re-exec'd.
```

### Re-exec-on-fork pattern (restores re-randomization)

```c
// After fork(), do NOT just run the handler in the child.
// execve() the worker so the kernel re-randomizes its layout.
pid_t pid = fork();
if (pid == 0) {
    // Child: replace image -> fresh ASLR for this worker.
    execve("/path/to/worker", argv, envp);
    _exit(127);   // exec failed
}
// Parent continues accepting connections.
```

### W^X discipline for a JIT region (conceptual)

```c
// NEVER map writable+executable at once. Write, then flip.
void *code = mmap(NULL, len, PROT_READ | PROT_WRITE,        // writable, not exec
                  MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
emit_machine_code(code, len);                                // fill it
mprotect(code, len, PROT_READ | PROT_EXEC);                  // now exec, not write
// Plus: constant-blind emitted immediates, randomize placement, add guard pages.
```

---

## Coding Patterns

### Pattern 1: Pair secrecy with enforcement

Never rely on ASLR alone. Enable a deterministic control-flow defense (CET/shadow stack on x86, PAC/BTI on ARM, or software CFI) so that a leak that beats ASLR still doesn't yield control-flow hijack.

### Pattern 2: Deny the brute-force oracle

For forking/crash-respawn servers: re-`exec` workers for fresh randomization; cap crash rate per source; treat a crash storm as an attack signal, not noise. The defense targets *layout reuse*, not entropy.

### Pattern 3: Treat read-disclosure bugs as critical

Out-of-bounds reads, uninitialized-memory disclosure, and verbose error/diagnostic output that emits pointers are ASLR-bypass primitives. Gate them like memory-corruption bugs.

### Pattern 4: Lock down JIT memory

W^X (write-then-flip, never both), constant blinding, randomized + guard-paged placement. The JIT is where DEP and ASLR have the least leverage.

### Pattern 5: Where possible, remove the bug class

The most durable answer to every bypass class is **memory safety**: a memory-safe language (or safe subset / sanitizer-verified code) removes the out-of-bounds reads and writes that all of these classes depend on. Mitigations are for the native code you can't yet make safe.

---

## Best Practices

- **Deploy both layers:** ASLR/KASLR (secrecy) *and* shadow stack/CET/PAC/CFI (enforcement).
- **Full RELRO, NX, PIE, canaries, FORTIFY** remain table stakes; add `-fcf-protection=full`, `-z shstk` where supported.
- **Re-`exec` forked workers; rate-limit and alert on crashes** to kill the BROP/brute-force class.
- **Audit for shared randomization** (fork-without-exec, restored snapshots, golden images) — it's the recurring structural flaw.
- **Treat info leaks (including OOB reads) as critical**, equal to corruption bugs.
- **Harden JITs** with W^X, constant blinding, and randomized placement.
- **Keep KPTI/microcode/microarch mitigations on** for kernels and sensitive hosts; budget the perf cost deliberately.
- **Pursue memory safety** for new code — it dissolves the prerequisites the bypass classes need.

---

## Edge Cases & Pitfalls

- **Coarse enforcement still leaves gadgets.** IBT only requires landing on *an* `endbr`; coarse CFI allows a large legal set. Attackers adapt with reuse chains that respect the coarse policy. Enforcement raises the bar but isn't absolute.
- **Shadow stacks protect returns, not forward edges.** They stop return-address overwrite but not indirect call/jump (vtable, function-pointer) hijacks — pair with IBT/CFI.
- **Re-randomization can be defeated by a fast leak-and-use** if the window between re-randomizations is larger than the attacker's leak-to-use latency. Frequency matters.
- **PAC/CET keys and gadgets.** Signing-gadget reuse, key leakage, or unsigned-pointer paths can erode pointer-authentication guarantees. Coverage gaps matter.
- **KASLR without KPTI is weak.** A kernel info leak or Meltdown-style read collapses it; KPTI and FGKASLR are what make KASLR worth the name.
- **JIT W^X "toggling" races.** If the window where a page is writable overlaps with when it's executable (or another thread executes during the writable phase), the protection is moot. Use dual-mapping or strict serialization.
- **Containers/VMs sharing a base image** can share randomization-relevant state (e.g., identical layouts if checkpoint/restore is used). Verify each instance re-randomizes.

---

## Common Mistakes

1. **Treating ASLR as sufficient.** It's a secrecy layer; leaks defeat it. Without an enforcement layer, one leak ends the game.
2. **Respawning forked workers as clones.** Re-uses one layout for unlimited attacker attempts (BROP).
3. **Underrating out-of-bounds reads.** They're the master key to ASLR.
4. **Shipping a JIT with a writable-executable region** or without constant blinding.
5. **Enabling KASLR but not KPTI** (or running on un-patched microcode) and assuming the kernel base is hidden.
6. **Assuming high entropy stops partial overwrites.** It doesn't — the randomized bits aren't touched.
7. **Relying on shadow stacks for forward-edge protection.** They only protect returns.
8. **Believing coarse CFI/IBT eliminates reuse.** It constrains, not eliminates.

---

## Tricky Points

- **A leak de-randomizes only the region it points into.** Leaking a heap pointer doesn't give you libc unless you can chain to a libc pointer. Attackers plan leaks to reach the region they'll reuse; defenders can make cross-region pivots harder by separating data and code.
- **Brute force on forks doesn't fight entropy head-on.** It uses the crash oracle to recover a few addresses incrementally against a fixed layout. The fix is layout *non-reuse*, not more bits.
- **FGKASLR attacks the "fixed internal layout" assumption.** By randomizing function order, it ensures one leaked kernel address no longer reveals the rest — the kernel analogue of shuffling the cards, not just the deck.
- **Meltdown's relevance here is specifically KASLR.** It read kernel memory from user space, recovering the randomized kernel base; KPTI's unmapping both blocks the read and removes the addresses a side channel could probe.
- **CET's shadow stack is hardware-enforced and cheap** because it's a separate stack the CPU maintains — it's the rare deterministic defense with low overhead, which is why it's the modern centerpiece.
- **PAC and CET solve overlapping problems differently:** PAC signs pointers (corruption fails on use); CET tracks legal targets (transfers must land on landing pads / match the shadow stack). Both make "address known" insufficient.

---

## Apply it

1. State the system invariant that **ASLR & Mitigations** must protect.
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

- Which invariant must remain true when ASLR & Mitigations fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
