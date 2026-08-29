# Side Channels & Spectre — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Side Channels & Spectre** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The organizing question: which structure, which boundary?

Every transient-execution attack answers two questions. Memorize them; they classify the whole zoo.

- **Which microarchitectural structure does it mislead?** A predictor (conditional, BTB, RSB, memory disambiguation) or a deferred check (permission fault) or an internal buffer (line-fill, store buffer, load port).
- **What boundary does the leak cross?** A *bounds check* within the same privilege level (the **Spectre** family — you trick a victim into leaking *its own* in-bounds-checked data) versus a *privilege/protection boundary* (the **Meltdown / L1TF / MDS** family — you directly read data you were never permitted to access).

A blunt but useful summary: **Spectre = "make the victim leak its own secret across a software check."** **Meltdown-class = "read data across a hardware protection boundary that the CPU enforces too late."** The defenses differ accordingly: Spectre is fought at the gadget and the predictor; Meltdown-class is fought by removing the data from reach (KPTI, flushing buffers, not sharing cores).

### 2. Spectre v1 — bounds-check bypass (recap, conditional branch predictor)

Covered in depth in `middle.md`. Mislead structure: the **conditional branch predictor**. Boundary crossed: a software **bounds check** (no privilege boundary). Defense: `lfence` or **index masking** (`array_index_nospec`) at the gadget; isolation of untrusted code. Software-fixable because the gadget is in your code.

### 3. Spectre v2 — branch-target injection (indirect branch predictor / BTB)

Indirect branches — calls/jumps through a function pointer, vtable, or jump table — get their *target* predicted by the **BTB**. v2 trains the BTB (often from a *different* context, e.g., an attacker process or sibling SMT thread) so that when the victim executes an indirect branch, the CPU **speculatively jumps to an attacker-chosen address** — a "Spectre gadget" already present in the victim's code. That gadget transiently performs a secret-dependent load and encodes it in cache.

This is more dangerous than v1: the attacker steers *where* the victim speculatively executes, not just *whether* it skips a check. Defenses are mostly **microcode/firmware + compiler**:

- **Retpoline** (compiler): replace indirect branches with a "return trampoline" — a contrived `call`/`ret` sequence whose speculation is steered to a benign infinite-loop pad, so the BTB can't redirect it. Costs indirect-call performance.
- **IBRS / eIBRS** (microcode/hardware): restrict or isolate indirect-branch prediction so a less-privileged domain can't influence a more-privileged one. eIBRS is the modern always-on hardware version.
- **STIBP**: prevent one SMT sibling from influencing the other's indirect-branch predictor.
- **IBPB**: a barrier that flushes indirect-branch predictor state on a context/domain switch.

### 4. Meltdown — transient read across the user/kernel boundary (deferred fault)

Meltdown is the Meltdown-class archetype. A user-mode load of a *kernel* address normally faults — but on affected CPUs the **permission check is resolved at retirement, not at issue**. So the load's *data* is forwarded to dependent instructions **transiently**, *before* the fault squashes everything. The attacker uses that brief window to do the standard encode: `probe[kernel_byte * 64]`, leaving a cache footprint, then reads it back. Architecturally the fault is delivered and no kernel value lands in a register — but the cache footprint already leaked it.

Meltdown is *not* fixed by patching code (there is no gadget — the attacker writes the whole thing). It is fixed **structurally** by **KPTI/KAISER**: unmap the kernel from the user-mode page tables, so when user code transiently reads a kernel address, there is simply *no mapping* and *no data* to forward. The cost is a page-table switch (and historically a TLB flush) on every user↔kernel transition — the headline "Meltdown patch slowdown." Newer CPUs fix the deferred-fault behavior in hardware, removing the need for KPTI.

### 5. Spectre v4 — speculative store bypass (memory-disambiguation predictor)

When a load follows a store whose address isn't yet computed, the CPU *predicts* whether they alias. If it predicts "no alias," the load **speculatively bypasses the older store** and reads the *stale* value from cache/memory — then later discovers they *did* alias and squashes. During that window, code can transiently operate on stale data, which can become a gadget (notably in language sandboxes/JITs that rely on a just-written guard or mask). Mislead structure: the **memory-disambiguation / store-to-load-forwarding predictor**. Defense: **SSBD (Speculative Store Bypass Disable)** via microcode/MSR (turn off the bypass for sensitive code), plus sandbox hardening. SSBD has a performance cost, so it is often enabled selectively (e.g., for processes that run untrusted code).

### 6. MDS / RIDL / Fallout / ZombieLoad — sampling internal buffers

The MDS family is different in spirit: instead of choosing an address, the attacker **samples whatever data happens to be in flight** in internal CPU buffers — the **line-fill buffer**, **store buffer**, and **load ports**. A faulting or assisting load can transiently receive *stale data from these buffers* that belongs to another context (another thread, another privilege level, even another VM on the same core via SMT). It's a "scoop up whatever's passing through" attack — lower precision (you don't target a specific address; you sample and filter), but it crosses boundaries the address-based attacks can't.

- **RIDL** (line-fill buffer), **Fallout** (store buffer), **ZombieLoad** (multiple buffers) are the named instances.
- Defense: **microcode that flushes the affected buffers on security-boundary crossings** (re-purposed `VERW`), often combined with **disabling SMT** for the strongest guarantee, since an SMT sibling shares those buffers concurrently. Later CPUs fix it in hardware.

### 7. L1TF / Foreshadow — L1 terminal fault

L1TF abuses page-table entries marked *not present* (or with manipulated physical address bits). On affected CPUs, a load to such an address can **transiently read whatever data sits at that physical address in the L1 cache**, ignoring the not-present bit during speculation. This is potent: it breaks **SGX enclaves** (Foreshadow), and across **hypervisor/VM** boundaries it lets a guest read host or other-guest data resident in L1. Defenses: **flush L1D on VM entry**, **page-table inversion** for not-present entries (so the physical address bits point to non-existent memory), and — for the cross-VM SMT case — **core scheduling / disabling SMT** so an attacker VM and victim VM never share a core's L1 simultaneously.

### 8. Retbleed and the PACMAN-class — the arms race continues

Mitigations created assumptions that later attacks broke:

- **Retbleed** showed that on some CPUs, `ret` instructions can be predicted via the same BTB-style machinery as indirect branches, so the retpoline assumption ("returns are safe") didn't hold universally. The fix involved additional microcode and, on affected parts, return-stack-stuffing / IBPB-style measures — at a real performance cost.
- **PACMAN** (a class on ARM) attacked **Pointer Authentication (PAC)**: it used speculation to *brute-force a PAC value without crashing the process*, since wrong guesses are squashed transiently rather than faulting architecturally. This undermines a *memory-safety* mitigation using a *side channel*, illustrating the recurring theme: **transient execution can quietly probe any check that would normally fault, by testing it speculatively where mistakes are free.**

The senior takeaway is not the name list — it's the pattern: each new structure or each new mitigation assumption is a new attack surface, and the defense map keeps expanding.

### 9. The defense map (structure → mitigation → layer)

| Attack | Structure misled | Boundary | Primary mitigation | Layer |
|--------|------------------|----------|--------------------|-------|
| Spectre v1 | Conditional predictor | Bounds check | `lfence` / index masking | Software / compiler |
| Spectre v2 | BTB (indirect) | Bounds/domain | Retpoline + IBRS/eIBRS/STIBP/IBPB | Compiler + microcode |
| Spectre v4 | Mem-disambiguation | Stale-data | SSBD (selective) | Microcode + sandbox |
| Meltdown | Deferred fault | User↔kernel | KPTI/KAISER | OS (or HW fix) |
| MDS/RIDL/etc. | Internal buffers | Cross-domain/SMT | Buffer flush (VERW) + disable SMT | Microcode + scheduling |
| L1TF/Foreshadow | L1 + not-present PTE | Enclave/VM | L1D flush + PTE inversion + core sched | OS/hypervisor + microcode |
| Retbleed | RSB/BTB for `ret` | Domain | Extra microcode + return stuffing | Microcode + kernel |
| PACMAN | Speculation vs. PAC | Memory-safety mitigation | HW/arch hardening of PAC checks | Hardware/arch |

---

## Code Examples

### Recognizing a v2 indirect-branch gadget surface

```c
/* Indirect branches through attacker-influenceable function pointers are the
 * v2 attack surface. Retpoline (compiler flag) converts these so the BTB
 * cannot redirect speculation. You usually enable the flag, not hand-write it. */
typedef int (*handler_t)(int);
int dispatch(handler_t h, int arg) {
    return h(arg);     /* indirect call -> BTB-predicted target -> v2 surface */
}
/* Build with -mretpoline (or the toolchain's equivalent) for untrusted-input code. */
```

### Spectre v4 (SSB) — the stale-load shape (for recognition)

```c
/* A guard write followed quickly by a dependent load. If the store's address
 * resolves late, the load may speculatively bypass it and read STALE data. */
void sandbox_check(uint8_t *guard, uint8_t *data, size_t idx) {
    *guard = 0;                 /* "deny" written here */
    if (*guard) {               /* may transiently still read the OLD (allow) value */
        leak(data[idx]);        /* gadget runs on stale guard */
    }
}
/* Mitigation: SSBD (microcode/MSR) for processes running untrusted code;
   plus restructuring so security guards don't depend on store-to-load timing. */
```

### Constant-time discipline is still your application-layer job

```rust
// Transient-execution variants are mitigated below your code (microcode/OS/
// compiler). What YOU still own at the app layer is classic constant-time:
use subtle::ConstantTimeEq; // the `subtle` crate

fn verify_tag(a: &[u8], b: &[u8]) -> bool {
    // Constant-time, branch-free, no early exit, no secret-indexed memory.
    a.ct_eq(b).into()
}
```

> The senior point: the transient-execution zoo is fought by the platform; your code's responsibility is to (a) not write Spectre-v1 gadgets in security-sensitive index-handling code, (b) keep untrusted code off shared cores, and (c) keep classic constant-time hygiene.

---

## Coding Patterns

**Pattern: classify-then-check.** For any new variant, write down (structure misled, boundary crossed) → look up the mitigation layer → verify it's active in your kernel/microcode/compiler flags.

**Pattern: defense in depth across layers.** No single mitigation covers the zoo. Combine compiler (retpoline, v1 masking), microcode (IBRS/SSBD/VERW), OS (KPTI), and scheduling (SMT/core isolation).

**Pattern: isolate by trust, not just by tenant.** Put untrusted code on its own cores/processes/VMs; never let it share a core's buffers/caches with high-value secrets.

**Pattern: don't let mitigations lull you.** Re-audit when a new attack breaks a mitigation assumption (retbleed vs. retpoline; PACMAN vs. PAC).

---

## Best Practices

1. **Memorize the two-question classifier** (structure? boundary?) so you can place any new variant fast.
2. **Map each mitigation to the boundary it protects** — KPTI for user/kernel, VERW+SMT-off for cross-thread buffers, L1D flush for VM/enclave, retpoline/eIBRS for indirect branches.
3. **Decide SMT policy deliberately.** For workloads that co-locate untrusted code with secrets on shared cores, disabling SMT may be necessary despite the throughput hit.
4. **Keep microcode, kernel, and compilers current.** Most of these are mitigated below your application; your job is ensuring the mitigations are present and enabled.
5. **Treat every mitigation as provisional.** Track follow-on research (retbleed, PACMAN) that erodes prior assumptions.
6. **Still write constant-time application crypto.** The classic channel never went away and is fully in your control.

---

## Edge Cases & Pitfalls

- **Confusing Spectre with Meltdown.** They need *different* defenses. Calling a privilege-boundary leak "a Spectre variant" leads to applying the wrong mitigation.
- **Assuming KPTI helps against Spectre.** KPTI addresses Meltdown (data-in-reach), not Spectre v1/v2 (gadget/predictor). Different problem, different fix.
- **Leaving SMT on for confidential workloads.** Many cross-domain attacks (MDS, L1TF) require concurrent SMT siblings; "we patched microcode" may not be enough without SMT off.
- **Trusting retpoline post-retbleed.** On affected CPUs retpoline alone is insufficient; additional measures are needed.
- **Forgetting the read phase still needs a timing primitive.** Cutting high-resolution timers and shared-memory timers (in browsers) degrades the read phase for *all* of these.
- **Over-mitigating uniformly.** Applying every mitigation to every workload wastes enormous performance. Mitigate by *trust boundary exposure*, not blanket fear.
- **Assuming hardware fixes are universal.** Newer silicon fixes some variants in hardware, but your fleet is heterogeneous; the oldest CPU sets your exposure.

---

## Apply it

1. State the system invariant that **Side Channels & Spectre** must protect.
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

- Which invariant must remain true when Side Channels & Spectre fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
