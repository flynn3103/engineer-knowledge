# Side Channels & Spectre — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Side Channels & Spectre** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Mitigations cost real money; quantify before you enable

Every mitigation buys safety with performance. At fleet scale, the cost is the headline. You must reason about the *shape* of each cost, because it interacts with your workload:

- **KPTI (Meltdown):** adds work to every user↔kernel transition. A compute-bound service that rarely syscalls barely notices; a syscall-storm service (small-packet networking, high-IOPS storage, databases doing tiny reads) can lose a meaningful fraction of throughput. **PCID/INVPCID** support cuts this sharply by avoiding TLB flushes. Lever: measure your *syscall rate*; the tax is proportional to it.
- **Retpoline (Spectre v2):** taxes every *indirect* branch (virtual calls, function pointers, interpreter dispatch). Pointer-chasing, polymorphic, or interpreter-heavy code pays most; straight-line numeric code barely. eIBRS in hardware is much cheaper and often supersedes retpoline on modern parts.
- **SSBD (Spectre v4):** a per-process throughput cost; enable it for processes that *run untrusted code* (browsers, JITs, serverless), not for trusted batch jobs.
- **MDS buffer flush (VERW):** a cost per security-boundary crossing; combined with the big one —
- **Disabling SMT:** the heaviest hammer. SMT typically adds substantial throughput; turning it off to fully close MDS/L1TF cross-thread leakage can cost a large slice of fleet capacity. This is the decision with the biggest dollar sign attached, and it must be made by *threat boundary*, not blanket policy.

The professional move is to **measure each mitigation's cost on *your* workload** (microbenchmarks plus production canaries) rather than trusting generic numbers, because the spread between "negligible" and "severe" is entirely workload-shaped.

### 2. Mitigation policy follows the threat model, not the news cycle

The single most important professional skill here is *not over-mitigating*. Ask, per workload:

1. **Does an attacker run code on this hardware?** If no untrusted code shares the machine, most cross-domain attacks (MDS, L1TF, cross-tenant v2) are not in your threat model. A single-tenant, trusted-code-only host running behind a firewall does **not** need SMT disabled for MDS.
2. **What boundary protects the secret?** User/kernel → KPTI matters. Process/VM with untrusted neighbors → SMT, core scheduling, SSBD, buffer flush matter. Same-process untrusted code (a browser tab, a WASM module) → site/process isolation plus v1/v4 hardening matter.
3. **What is the asset?** A host that holds long-lived signing keys or other tenants' data warrants maximal mitigation even at high cost; a stateless cache node may not.

This produces a **tiered policy**: e.g., "secrets tier: SMT off, full mitigations; multi-tenant compute tier: SMT off, core scheduling, SSBD; trusted internal batch tier: defaults only, SMT on." Document the reasoning so the next audit can re-evaluate as hardware and attacks evolve.

### 3. Constant-time programming: the rules

The transient zoo is fought below your code, but the *classic* timing/cache channel is yours, and it shows up wherever you write or maintain crypto, auth, or any secret-handling primitive. The rules of constant-time code:

- **No secret-dependent branches.** `if (secret) {...}` leaks via timing and via the branch predictor. Replace with branchless selection.
- **No secret-dependent memory addresses.** `table[secret]` leaks via the cache (the original AES-table attack). Either avoid the table, scan it fully, or use hardware crypto.
- **No secret-dependent variable-latency instructions.** Integer division/modulo, some multiplies, and certain floating-point ops take *data-dependent* cycles on some CPUs. Avoid them on secret operands or use known-constant-time alternatives.
- **No secret-dependent loop bounds.** The iteration count must not reveal the secret (the early-exit comparison, generalized).
- **Beware compiler "help."** The compiler can turn your branchless code back into a branch, vectorize away your padding, or constant-fold your blinding. CT code must be checked *at the assembly/binary level*, and sometimes written with compiler barriers or in assembly.

### 4. Constant-time techniques

- **Branchless selection (masking):** compute both results, then select with an all-ones/all-zeros mask derived from the (non-secret-leaking) condition:
  `result = (mask & a) | (~mask & b);`
- **Conditional swap/move:** the building block of constant-time sorting and constant-time elliptic-curve scalar multiplication (`cswap`).
- **Full-table scan or hardware crypto:** instead of `table[secret]`, read *every* entry and select the right one with a mask — or use AES-NI / CLMUL / SHA extensions that have no secret-dependent memory access.
- **Blinding:** randomize the operand (e.g., RSA blinding multiplies the ciphertext by `r^e` before decryption and divides out `r` after), so each run's side-channel signature is decorrelated from the key. The standard defense for variable-latency big-integer math.
- **DIT/DOIT modes:** on supporting CPUs, enable Data-Independent Timing so a documented set of instructions runs in secret-independent time, removing a class of microarchitectural timing variation.

### 5. You cannot eyeball it — verify

The defining professional practice: **prove** constant-timeness, don't assert it. Three tiers of tooling:

- **dudect (statistical, black-box):** run the function many times with two input classes — a *fixed* secret and *random* secrets — and statistically test whether the two timing distributions differ (Welch's t-test on the measured cycles). A significant difference is evidence of a leak. dudect is easy to wire into CI, requires no source annotations, and tests on the *real* CPU, but it can only *detect* leaks, not prove their absence, and it needs a quiet machine and enough samples.
- **ctgrind / MemSan-style taint (dynamic, white-box):** mark the secret bytes as "uninitialized" (poisoned) under Valgrind's Memcheck; any branch on, or memory access indexed by, a poisoned value is reported. This pinpoints *where* the leak is in the source, on real execution paths, but only on paths you exercise.
- **ct-verif / Binsec/Rel (formal/relational):** prove, over all inputs, that two executions differing only in the secret are indistinguishable in the leakage model (branches + addresses). Strongest guarantee, highest effort; used for the most critical primitives.

The pragmatic recipe most teams adopt: **ctgrind to find leaks during development, dudect in CI as a regression gate on the real target, and formal verification reserved for the crown-jewel primitives.**

### 6. Defense in depth and the residual-risk reality

No combination of mitigations is complete forever — new variants keep arriving, and hardware fixes lag the fleet. The professional posture is **layered and explicit about residual risk**:

- **Platform layer:** current microcode, kernel, hypervisor, compiler mitigations; SMT/core-scheduling policy per tier.
- **Isolation layer:** keep untrusted code off shared cores/processes with secrets; site isolation; per-tenant cores for the highest tiers.
- **Code layer:** constant-time crypto/auth, verified in CI; no Spectre-v1 gadgets in index-handling code.
- **Detection/governance layer:** track new CVEs, re-run the threat-model mapping, and re-evaluate the SMT decision as hardware refreshes change the cost/benefit.

State the residual risk plainly: e.g., "on this tier we accept cross-tenant L1 leakage risk in exchange for SMT throughput, mitigated by single-tenant scheduling." Security at scale is documented trade-offs, not absolutes.

---

## Code Examples

### Branchless constant-time select (the workhorse)

```c
/* Returns a if cond (0 or 1), else b — without a secret-dependent branch.
 * Build mask = all-ones if cond==1, all-zeros if cond==0. */
uint32_t ct_select(uint32_t cond, uint32_t a, uint32_t b) {
    uint32_t mask = (uint32_t)0 - (cond & 1);   /* 0xFFFFFFFF or 0x00000000 */
    return (mask & a) | (~mask & b);
}

/* Constant-time conditional swap — used in scalar multiplication, sorting. */
void ct_cswap(uint32_t cond, uint32_t *x, uint32_t *y) {
    uint32_t mask = (uint32_t)0 - (cond & 1);
    uint32_t t = mask & (*x ^ *y);
    *x ^= t;
    *y ^= t;
}
```

### Avoiding a secret-indexed table (cache-attack surface)

```c
/* Instead of t[secret] (leaks via cache), scan the WHOLE table and select. */
uint8_t ct_table_lookup(const uint8_t *t, size_t n, uint8_t secret_idx) {
    uint8_t out = 0;
    for (size_t i = 0; i < n; i++) {
        uint8_t mask = (uint8_t)(0 - (i == secret_idx)); /* careful: '==' must be CT */
        out |= mask & t[i];                              /* touches every line */
    }
    return out;
}
/* In production: prefer AES-NI / vetted bitsliced impls over hand-rolled scans. */
```

### Wiring dudect-style leakage testing into CI (sketch)

```c
/* Conceptual: measure cycle counts for two input classes and t-test them.
 * A significant |t| (e.g., > ~4.5) across enough samples flags a leak.
 * Real frameworks (dudect.h) handle warmup, outlier rejection, and the stats. */
for (size_t i = 0; i < N; i++) {
    bool class_fixed = (i & 1);
    prepare_input(class_fixed ? FIXED_SECRET : random_secret());
    uint64_t t0 = rdtsc_serialized();
    function_under_test();              /* the CT candidate */
    uint64_t dt = rdtsc_serialized() - t0;
    record(class_fixed, dt);            /* feed into Welch's t-test */
}
report_t_statistic();                   /* gate the build on it */
```

### Mitigation policy as code (illustrative)

```yaml
# Per-tier mitigation policy derived from threat model (illustrative).
secrets_tier:        # holds signing keys / other tenants' PII
  smt: off
  kpti: on
  ssbd: force
  l1d_flush: on
  scheduling: single_tenant_cores
multitenant_compute:
  smt: off
  ssbd: on           # untrusted guest code
  scheduling: core_scheduling
trusted_batch:
  smt: on            # no untrusted code co-located; defaults suffice
  mitigations: auto
```

---

## Coding Patterns

**Pattern: tiered, documented mitigation policy.** Encode mitigations per workload tier, justified by an explicit threat model, and re-evaluate on hardware refresh and new CVEs.

**Pattern: CT primitive + verification gate.** Every secret-handling primitive ships with a dudect/ctgrind check in CI; the build fails on a detected leak.

**Pattern: prefer hardware crypto; mask when you can't.** Use AES-NI/CLMUL/SHA-ext where available; fall back to verified bitsliced/branchless implementations, never to secret-indexed tables.

**Pattern: verify the binary, not the source.** Inspect generated assembly (or run binary-level CT tools) for critical code, because the compiler may reintroduce leaks.

**Pattern: write down residual risk.** Each accepted trade-off (e.g., SMT on for a tier) is documented with its rationale and revisit trigger.

---

## Best Practices

1. **Mitigate by threat boundary and asset value, not by headline.** Over-mitigation is a real, expensive failure mode.
2. **Measure mitigation cost on your own workloads** before fleet-wide rollout; the spread is enormous and workload-shaped.
3. **Keep KPTI but exploit PCID;** profile syscall rate to predict the tax.
4. **Make constant-time a verified property, not an aspiration** — dudect in CI, ctgrind in development, formal proof for crown jewels.
5. **Don't trust the source; trust the verified binary.** Compilers undo CT; check the assembly.
6. **Use hardware crypto and vetted libraries;** never hand-roll secret-indexed lookups or comparisons.
7. **Maintain an explicit, re-visitable residual-risk register** for accepted trade-offs.
8. **Re-run the threat-model mapping on every new variant** and on hardware refresh, since cost/benefit shifts.

---

## Edge Cases & Pitfalls

- **Blanket "enable everything" at scale.** It can quietly cost double-digit percentages of capacity for risk you don't actually carry. Always justify by threat model.
- **Disabling SMT where no untrusted code runs.** Pure cost, no benefit, on a single-tenant trusted host.
- **Trusting source-level constant-time.** The optimizer reintroduces branches, vectorizes away padding, constant-folds blinding. Verify the binary.
- **dudect on a noisy CI runner.** Frequency scaling, neighbors, and interrupts inflate variance and hide leaks (false negatives) or fabricate them (false positives). Pin frequency, isolate the core, use enough samples.
- **`==` inside a "constant-time" function.** A naive equality comparison in your masking helper can itself be a non-CT branch. Build comparisons from CT primitives.
- **Variable-latency arithmetic slipping in.** A `secret % n` or a data-dependent multiply can leak even in otherwise branchless code; know your target's latency tables or enable DIT/DOIT.
- **Forgetting the read phase mitigations.** Timer hardening and shared-memory restrictions degrade *every* cache-attack read phase; don't quietly re-enable high-resolution timers in a sandbox for a perf win.
- **Stale residual-risk register.** Accepted trade-offs that are never revisited become silent vulnerabilities after a hardware refresh or a new attack changes the math.
- **Assuming hardware fixes covered you.** Fleets are heterogeneous; the oldest in-service CPU defines exposure, not the newest.

---

## Apply it

1. Define the user or business outcome that **Side Channels & Spectre** should improve.
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

- Which measurable outcome justifies investing in Side Channels & Spectre?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
