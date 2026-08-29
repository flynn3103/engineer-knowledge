# Memory-Safety Mechanisms — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Memory-Safety Mechanisms** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. ARM MTE — Probabilistic Lock-and-Key, Production-Affordable

**MTE** turns memory safety into a hardware tag match. Memory is divided into **16-byte granules**; each granule carries a **4-bit tag** stored in separate tag memory. Pointers carry a matching 4-bit tag in their unused top byte (via **Top-Byte-Ignore**). On every load/store, the hardware compares the **pointer's tag (key)** against the **granule's tag (lock)**. Mismatch → fault.

How it catches the bug classes:

- **Spatial (OOB):** the allocator gives *adjacent* allocations *different* tags. An overflow from allocation A (tag 5) into allocation B (tag 9) accesses a granule tagged 9 with a pointer tagged 5 → mismatch → fault.
- **Temporal (UAF):** on `free`, the allocator *re-tags* the freed granules to a new value. The old dangling pointer still carries the old tag; using it now mismatches → fault. This is the key win: **MTE provides *temporal* protection cheaply**, which sanitizers and guard pages struggle to do in production.

Why "probabilistic": only **4 bits = 16 possible tags**. With ~1/16 chance, a wild access lands on a granule that *happens* to share the pointer's tag and is missed. So MTE is not a *proof* of safety — it's a high-probability detector. But across a fleet of billions of devices, a 15/16 catch rate makes most bugs surface (and, as a *mitigation*, makes exploitation unreliable — an attacker must win the tag lottery repeatedly). It ships in production (Pixel 8+ offers MTE; Android's "Advanced Protection" enables it), at single-digit-percent overhead in async mode — *orders of magnitude* cheaper than ASan, making it viable in production, not just testing.

MTE's two modes matter operationally: **synchronous** faults precisely at the bad access (great for debugging, higher cost) and **asynchronous** batches checks for lower overhead but imprecise blame (great for fleet hardening). Many deployments run async in production and sync in testing.

### 2. CHERI — Deterministic Safety via Unforgeable Capabilities

**CHERI** is the more radical, deterministic design. It replaces integer pointers with **capabilities**: 128-bit objects that bundle the address *with* its **bounds** (base + length), **permissions** (read/write/execute), and a separate **1-bit validity tag** kept out-of-band in tagged memory. The hardware enforces three unbreakable rules:

1. **Bounds are checked on every dereference** — access outside [base, base+length) faults. Deterministic *spatial* safety; no 1/16 gap.
2. **Capabilities are unforgeable** — you cannot fabricate a valid capability from integer arithmetic. The validity tag is cleared the moment you do non-capability operations on the bits. (Provenance is enforced by hardware.)
3. **Authority only narrows (monotonic non-increase)** — a capability derived from another can have *equal or less* authority (smaller bounds, fewer permissions), never more. You can hand out a restricted view; you cannot escalate.

Because every pointer carries its own bounds, CHERI is essentially **hardware fat pointers** enforced by the CPU. This gives *deterministic* spatial safety to **unmodified C/C++ semantics** (you recompile for CHERI; pointers become capabilities), eliminating buffer overflows and OOB by construction. Temporal safety is harder even for CHERI (a capability can still point at freed-then-reused memory), but CHERI enables efficient temporal-safety schemes (e.g. **CHERIvoke / Cornucopia**-style sweeping revocation: invalidate all capabilities to freed regions before reuse, made cheap because capabilities are *findable* in memory via their tags).

CHERI is realized in research/early silicon — notably **Arm Morello** (an experimental CHERI-enabled aarch64 board) and the **CHERI-RISC-V** efforts. It's not yet mainstream, but it represents the "deterministic memory safety in hardware for legacy C/C++" endgame. The cost is real: ~doubled pointer size (cache/memory pressure), ISA and toolchain changes, and an ecosystem port.

### 3. MTE vs CHERI — The Spectrum of Hardware Safety

| Dimension | MTE | CHERI |
|-----------|-----|-------|
| Guarantee | **Probabilistic** (1/16 miss) | **Deterministic** spatial |
| Mechanism | tag match (lock/key) | bounds+perms in capability |
| Temporal safety | yes (re-tag on free), probabilistic | needs revocation scheme, deterministic when applied |
| Pointer size | unchanged (tag in spare byte) | ~2× (128-bit capability) |
| Deployment | **production today** (ARMv8.5+, Pixel) | research/early (Morello) |
| Overhead | single-digit % (async) | moderate, mostly memory/cache |
| Compat | recompile + tagging allocator | recompile for CHERI ABI |

The professional reading: **MTE is the pragmatic near-term win** — affordable, shipping, dramatically raises the bar — *at the cost of being probabilistic*. **CHERI is the principled long-term answer** — deterministic, comprehensive — *at the cost of not being here yet at scale*. They are not mutually exclusive; the industry is pursuing both.

### 4. Why Temporal Safety Resists Cheap Hardware Too

The senior-level theme — *temporal is harder than spatial* — persists into hardware. Spatial safety needs only *local* info: the bounds of the object you're accessing (MTE's adjacent-tag trick, CHERI's per-pointer bounds). Temporal safety needs a *global, time-varying* fact: "has this exact object been freed and the memory reused?"

- MTE handles it *probabilistically* by re-tagging on free — but tag reuse (only 16 values) means a freed-then-reallocated region can collide tags.
- CHERI handles it *deterministically* only with an added **revocation sweep**: before reusing freed memory, find and invalidate every capability that points into it (feasible because capabilities are tagged and thus findable — impossible with raw integer pointers). That sweep has real cost, though research shows it can be amortized to small overhead.

The durable lesson: any time you see disproportionate machinery (GC, quarantine, MTE re-tagging, CHERI revocation), it is buying **temporal** safety. Spatial safety is comparatively cheap everywhere — software *or* silicon.

### 5. Bounds-Check Elimination — Why Spatial Safety Is Often Free

A frequent objection to safe languages is "bounds checks cost performance." In practice they often cost *nothing*, because optimizing compilers perform **bounds-check elimination (BCE)**: when the compiler can *prove* an index is in range, it removes the check.

- A `for i in 0..arr.len()` loop: the compiler knows `i < len` by construction → no per-iteration check.
- Range analysis / induction-variable reasoning proves many derived indices safe.
- Hoisting: a check that's invariant across a loop is done once before the loop.
- Rust and modern JITs (HotSpot, V8) are aggressive here; Go has improved BCE substantially over releases.

The practical implication for a professional: **don't disable bounds checks reflexively for performance.** Measure first. The checks that survive optimization are usually on genuinely-dynamic indices where you *want* the safety, and the cost is a well-predicted branch. The narrative "safe = slow" is largely obsolete; the real cost of safety today is GC pauses/footprint and Rust authoring effort, not bounds checks.

### 6. The Migration Playbook — Backed by Data

The hardware story protects existing C/C++. The *language* story prevents new bugs. The evidence base that drives strategy:

- **~70% of severe CVEs are memory-safety bugs** (Microsoft, Chromium — independently).
- **Bugs concentrate in new/recently-changed code.** Google's analysis showed memory-safety vulnerability density is highest in *young* code and decays as code ages and is hardened. *This is the strategic linchpin.*
- **Android's results:** as the proportion of new code written in memory-safe languages rose, the fraction of memory-safety vulnerabilities fell from **~76% (2019) to ~24% (2024)** — *without* rewriting the old code, because the *new* code (where bugs are born) stopped producing them. New Rust code shipped with near-zero memory-safety CVEs.

This yields the **"safe by default for new code"** strategy and the migration playbook:

1. **Stop the bleeding:** mandate memory-safe languages for *new* components and *new* high-risk surfaces (parsers, network-facing code handling untrusted input). You get most of the benefit because that's where most new bugs are.
2. **Harden the legacy in place:** production mitigations (`_FORTIFY_SOURCE`, hardened allocator, stack canaries, CFI, **enable MTE where the hardware supports it**), plus sanitizers + fuzzing in CI.
3. **Rewrite selectively, by risk:** rewrite the *highest-exposure* legacy components (the ones touching attacker-controlled data) into Rust/MSL — not a big-bang rewrite. Interop carefully across the FFI boundary (the new attack surface).
4. **Measure:** track memory-safety CVE fraction, new-code MSL percentage, and bug density by code age. Report the trend to leadership; the curve is the ROI story.

CISA and the NSA now publish formal guidance ("memory-safe roadmaps") recommending exactly this, and the White House ONCD has urged the move. As a professional you're expected to translate this into a concrete plan for your codebase.

### 7. Mitigations Are Not Safety — Know the Difference

A professional must not conflate **exploit mitigations** with **memory safety**:

- **ASLR, DEP/NX, stack canaries, CFI, hardened allocators** make exploitation *harder/less reliable*. They are *probabilistic* or *partial*, and the attacker-defender arms race routinely bypasses each (info leaks defeat ASLR, JIT-spray defeats DEP, etc.). The bug is still there.
- **Memory safety** (safe languages, deterministic CHERI) makes the *bug class impossible or always-caught*. There's nothing to bypass.
- **MTE** sits in between: a strong, cheap, *probabilistic* mitigation that's close enough to safety to meaningfully change the economics, but is not a deterministic guarantee.

Communicating this distinction — "we have many mitigations, but the only thing that *removes* the bug class is memory-safe code" — is part of the senior-to-principal security conversation.

---

## Code Examples

> Conceptual/defensive. These illustrate *mechanisms and tooling*, not exploits.

### MTE conceptually: tag-on-alloc, retag-on-free

```text
malloc(size):
    p = allocate(size)
    tag = random_4bit() != tag_of_neighbor   // different tag from neighbors
    color_granules(p, size, tag)             // set "lock" in tag memory
    return p_with_tag(p, tag)                // pointer carries "key" in top byte

free(p):
    new_tag = random_4bit()                  // RE-TAG the freed region
    color_granules(p, size, new_tag)         // old pointers now mismatch -> UAF caught
    actually_free(p)

load/store *q:
    if tag_of(q) != granule_tag_at(q): FAULT // hardware does this every access
```

This is why MTE catches both adjacent-overflow (neighbor has a different tag) and use-after-free (region re-tagged on free) — cheaply, in hardware, probabilistically (1/16 collision).

### Enabling MTE-style hardening in a real toolchain

```bash
# Compile with stack and heap tagging (ARMv8.5+ target, hardware-gated):
clang -target aarch64-linux-android \
      -fsanitize=memtag-stack -fsanitize=memtag-heap \
      -march=armv8.5-a+memtag app.c -o app
# At runtime the kernel/allocator must enable MTE (sync or async mode).
# This is a PRODUCTION mitigation, unlike -fsanitize=address (testing only).
```

### Bounds-check elimination: the optimizer removes the cost

```rust
// Rust: the compiler proves every index is in range -> NO runtime check emitted.
fn sum(a: &[u32]) -> u64 {
    let mut s = 0u64;
    for i in 0..a.len() {     // i < a.len() is guaranteed -> bound check elided
        s += a[i] as u64;     // optimizer also uses iterators to prove safety
    }
    s
}
// Idiomatic version is even clearer to the optimizer and equally checked:
fn sum_iter(a: &[u32]) -> u64 { a.iter().map(|&x| x as u64).sum() }
```

### Migration: a risk-ranked plan as code review policy

```text
POLICY (enforced in CI + review):
  new network-facing parser?          -> MUST be Rust (or other MSL). Block C/C++.
  new code in existing C/C++ module?  -> allowed, but +ASan/UBSan CI, +fuzz target
  touching attacker-controlled input? -> highest priority for Rust rewrite
  legacy untouched & low-exposure?    -> leave; harden via _FORTIFY_SOURCE+MTE+CFI

METRIC dashboards:
  - % of new LOC in memory-safe languages   (target: up and to the right)
  - memory-safety CVE fraction over time     (target: down)
  - bug density by code age                  (validates "new code" hypothesis)
```

---

## Coding Patterns

```text
TOOLCHAIN (production, ARM):
  -march=armv8.5-a+memtag -fsanitize=memtag-stack,memtag-heap
  link an MTE-aware allocator; run async in prod, sync in CI repro
  keep -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fcf-protection (CFI)

CI (still essential at the boundary):
  ASan+UBSan, MSan, libFuzzer, TSan; sanitizers find what tags miss in test

FFI DISCIPLINE (Rust<->C, the new surface):
  - narrow, audited extern boundary; validate all sizes/pointers at the seam
  - run Miri / sanitizers across the boundary; treat it like `unsafe`

GOVERNANCE:
  - "new high-risk code must be memory-safe" as a merge gate
  - dashboard: %MSL new code, CVE fraction, bug density by age
```

---

## Best Practices

- **Enable MTE in production where the hardware allows** — it's the cheapest large reduction in exploitability available for native code, and it covers the *temporal* gap.
- **Don't disable bounds checks for speed without measurement.** BCE removes most; the survivors are usually exactly where you want the check. The "safe = slow" story is largely outdated.
- **Drive migration with the bug-age data.** Mandate memory-safe languages for *new and high-risk* code first — that's where the ROI is, per Android's results.
- **Harden legacy and prevent new bugs simultaneously** — it's two prongs, not a choice. Mitigations buy time; MSLs remove the class.
- **Treat the FFI boundary as the new critical surface.** When you introduce Rust into C/C++ (or vice versa), the interop seam inherits all the old risks; audit it like `unsafe`.
- **Distinguish mitigation from safety in every security conversation.** ASLR/canaries/CFI/MTE raise cost; only safe code/CHERI remove the bug class. Leadership decisions depend on this distinction.
- **Measure and report the trend.** The memory-safety CVE fraction over time is your proof the strategy works; make it a tracked metric.

---

## Edge Cases & Pitfalls

- **MTE's 1/16 tag collision** means a determined or lucky wild access can be missed; it's a strong mitigation, not a proof. Don't market it as "we're now memory-safe."
- **MTE async mode gives imprecise blame** — great for fleet hardening, frustrating for root-causing; reproduce in sync mode.
- **CHERI doubles pointer size**, pressuring caches and memory bandwidth and breaking code that assumes `sizeof(void*) == sizeof(long)` or stuffs bits into pointers.
- **CHERI temporal safety still needs revocation** — recompiling for CHERI gives you *spatial* safety "for free," but UAF protection requires the sweeping-revocation machinery, which has its own cost/tuning.
- **The FFI boundary undoes guarantees.** A Rust program calling C, or MTE-tagged code calling untagged libraries, has a seam where the guarantee lapses. Mixed-tag environments need care.
- **Migration metric gaming.** "% MSL code" can be inflated by trivial new files; pair it with *CVE fraction* and *bug density by age* so the metric reflects real risk reduction.
- **Mistaking mitigation stacking for safety.** Piling ASLR+canaries+CFI feels safe but each is independently bypassable; they don't compose into a guarantee.

---

## Common Mistakes

- Claiming MTE makes a system "memory-safe" — it's probabilistic (1/16 miss). It makes exploitation unreliable and surfaces most bugs; that's mitigation, not a guarantee.
- Treating a Rust migration as all-or-nothing and concluding "we can't afford it." The data says rewrite *new and high-risk* first; that's affordable and captures most benefit.
- Disabling bounds checks for "performance" without profiling — usually a self-inflicted vulnerability for negligible gain, since BCE already removed the cheap ones.
- Forgetting the FFI seam when introducing a safe language, re-importing every classic bug at the boundary.
- Reporting "% safe code written" without "% memory-safety CVEs" — measuring activity, not outcome.
- Assuming CHERI gives temporal safety automatically on recompile (it gives spatial; temporal needs revocation).

---

## Tricky Points

- **Why is MTE "good enough" at only 4 bits?** Because exploitation usually requires *reliable, repeated* control. A 15/16 per-access catch rate makes both *bug discovery* (across a fleet) and *exploitation* (which needs many successful accesses) overwhelmingly likely to trip a fault — even though a single random access has a 1/16 escape. Probabilistic-but-pervasive beats deterministic-but-unaffordable for fleet defense.
- **Why can CHERI enforce temporal safety when raw pointers can't, even with the same revocation idea?** Because capabilities are *tagged and findable* in memory — the runtime can *sweep* memory to locate and invalidate every capability into a freed region. With raw integer pointers you can't tell a pointer from an integer, so you can't find (let alone revoke) them. CHERI makes pointers *first-class and discoverable*, which is precisely what temporal revocation needs.
- **Why does "safe by default for new code" work without rewriting the old code?** Because vulnerability density is far higher in *new/recently-modified* code; old code that survived has been hardened by exposure. Stopping new memory bugs at the source removes most *future* CVEs even though the legacy lines remain.
- **Why isn't a stack of mitigations equivalent to safety?** Each mitigation is independently bypassable (info leak → ASLR; tag guess → MTE; gadget → CFI). Their *product* is not a guarantee because attackers chain bypasses. Safety (or CHERI determinism) removes the bug class, leaving nothing to chain.

---

## Apply it

1. Define the user or business outcome that **Memory-Safety Mechanisms** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Memory-Safety Mechanisms?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
