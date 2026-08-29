# Side Channels & Spectre — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Side Channels & Spectre** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why CPUs execute out of order and speculatively

A memory load that misses all caches can cost **hundreds of cycles** — main RAM is glacially slow compared to the core. If the CPU stalled, waiting, every time it issued a load, it would spend most of its life idle. So modern cores do two things:

- **Out-of-order execution:** while one instruction waits on a slow load, the CPU executes *later* instructions whose inputs are already available. Results are computed eagerly but only *retired* (made official) in program order, so the program's visible behavior is unchanged.
- **Speculative execution:** control flow has branches. To keep the pipeline full *past* a branch, the CPU asks the **branch predictor** to guess the outcome and starts executing the predicted path *before the branch condition is resolved*. If the guess is right (predictors are right ~95%+ of the time), that work is already done — a big speedup. If wrong, the CPU **squashes** the speculative work and restarts down the correct path.

Both mechanisms are decades old, near-universal, and account for a large fraction of single-core performance. They are not bugs. They are the optimizations that make the hole.

### 2. The leak hides in the incomplete rollback

When speculation is wrong, the CPU squashes the bad instructions: it restores registers, cancels pending memory writes — the **architectural** state is clean, as if the speculation never happened. Your program cannot observe the squashed work *through normal means*.

But during that transient window, the speculated instructions may have issued **loads** that pulled data into the cache. The squash does not evict those lines — *the cache is left warm*. So a load that "never officially happened" has left a **microarchitectural** fingerprint. If *which line got warmed* depended on a secret, the secret has leaked into the cache. All that remains is for the attacker to read it out — and that is what the cache-attack toolkit does.

> The one sentence to memorize: **transient execution rolls back the architectural state but not the cache; if the transient work touched memory based on a secret, the secret is now encoded in cache state.**

### 3. The cache-attack toolkit

These techniques let an attacker learn *which cache lines a victim touched*. They are the "read" half of every Spectre-class attack (and standalone attacks against, e.g., table-based crypto).

**Flush+Reload** (needs memory shared with the victim — e.g., a shared library, or a known buffer):
1. **Flush** a target line out of all caches with `clflush`.
2. **Wait** while the victim runs.
3. **Reload** the line and *time* it. A **fast** reload means the line is cached — the victim must have touched it. A **slow** reload means the victim did not.

It is high-resolution and low-noise, which is why it is the textbook tool. The catch: it needs shared memory between attacker and victim.

**Prime+Probe** (needs *no* shared memory — works across processes/VMs):
1. **Prime:** the attacker fills an entire cache *set* with its own data.
2. **Wait** while the victim runs. If the victim accesses an address mapping to that set, it **evicts** one of the attacker's lines.
3. **Probe:** the attacker re-reads its own data and times it. A **slow** re-read of some line means the victim evicted it ⇒ the victim touched that set.

Prime+Probe is noisier but far more general — it is the workhorse of cross-VM cloud attacks because it needs nothing shared.

**Evict+Time** (coarser): evict a line, then time the victim's *whole* operation. If the operation is slower, it needed the evicted line. Lower resolution, but simple.

All three exploit the same fact: **a cache hit and a cache miss differ by a measurable amount of time, and that timing reveals the victim's memory-access pattern.**

### 4. Spectre v1: bounds-check bypass, step by step (conceptual)

Spectre v1 is the cleanest member of the family. Consider this innocent-looking, *fully bounds-checked* code that runs in a victim (say, a kernel, a JIT, or a server handling an attacker-supplied index `x`):

```c
if (x < array1_size) {           // (1) the bounds check
    y = array2[ array1[x] * 64 ]; // (2) secret-dependent dependent load
}
```

In normal execution this is safe: if `x` is out of bounds, the `if` is false and the body never runs. The exploit defeats the *timing* of the check, not its logic:

1. **Train the predictor.** The attacker calls this code many times with *in-bounds* `x`, so the branch predictor learns "this branch is usually taken (true)."
2. **Set up the cache read-out.** The attacker flushes `array1_size` from cache (so resolving the branch will be *slow*) and flushes the `array2` probe region (so it can later detect which line got warmed).
3. **Pass a malicious `x`.** Now the attacker calls with `x` chosen so `array1[x]` points *out of bounds* — at a secret byte somewhere in memory.
4. **Speculation runs ahead.** Because resolving `x < array1_size` is slow (it had to wait for `array1_size` from RAM) and the predictor says "taken," the CPU **speculatively executes the body** with the malicious `x`. Transiently, it reads the secret byte `array1[x]`, then uses it as an index: `array2[secret * 64]`. That load **pulls one specific line of `array2` into the cache** — the line index encodes the secret.
5. **Squash.** The branch finally resolves: `x` was out of bounds, the guess was wrong, the CPU squashes everything. Architecturally, nothing happened — no out-of-bounds value is in any register your program can read.
6. **Read the secret out of the cache.** The attacker now does **Flush+Reload** across the `array2` probe region: exactly one line is fast (warm). Its index *is the secret byte*. Repeat for each byte of the secret.

Notice what makes this so dangerous: **there was no memory-safety bug.** The code bounds-checks correctly. The leak comes from the CPU *speculating past* a correct check, plus the cache not being rolled back. That is why Spectre cannot be fixed by "just bounds-check better" — the check is already there.

### 5. Mitigating Spectre v1 in software

Because v1 lives in *your* code's bounds check, defenses are at the software level:

- **Speculation barrier (`lfence`).** Insert an `lfence` between the bounds check and the dependent access. `lfence` forces the CPU to *resolve prior instructions* before executing later ones — it stops the speculation that would have read out of bounds. Effective but slow if overused; compilers can insert it automatically (MSVC `/Qspectre`, similar in others).
- **Index masking.** Instead of trusting the branch, *clamp the index in data* so that even speculatively it cannot go out of bounds:

```c
if (x < array1_size) {
    x &= (array1_size - 1);          // mask (when size is a power of two)
    y = array2[array1[x] * 64];      // speculation can't escape the array now
}
```
  Masking is cheaper than a fence because it doesn't serialize the pipeline — it just makes the out-of-bounds value *impossible even transiently*. (Generalized "array_index_nospec" helpers in the Linux kernel do exactly this.)
- **Removing the gadget.** If attacker-controlled indices never feed a secret-dependent dependent load, there is no gadget. Auditing for the bounds-check-then-dependent-load pattern is the structural fix.

### 6. Why browsers and clouds changed everything after Spectre

Spectre needs the attacker to *run code on the same hardware* as the victim's secrets. Two environments make that easy:

- **Browsers** run untrusted JavaScript/WASM from any website, in the same process as your other tabs' data. Spectre let a malicious page read memory from the same renderer. The response was **Site Isolation** (put each site in its own OS process so a Spectre leak only sees that one site's data) plus **reducing timer resolution** and **restricting `SharedArrayBuffer`** (which provided the high-resolution timing that cache attacks need).
- **Clouds** run many tenants' VMs on the same physical CPU. Prime+Probe and L1TF (in `senior.md`) made cross-tenant leakage a real concern, driving core-scheduling, cache partitioning, and "do not co-locate untrusted workloads" policies.

The lesson for a middle engineer: **process and hardware isolation are not bureaucratic — they are the load-bearing defense.** Don't run untrusted code in the same process/VM/core as secrets if you can help it.

---

## Code Examples

### A Spectre-v1 gadget (for *recognition*, not exploitation)

```c
/* This is the SHAPE to learn to recognize and avoid in security-sensitive
 * code that handles attacker-controlled indices. It is not an exploit;
 * exploiting it requires the cache-attack machinery and precise timing. */
uint8_t leak_gadget(size_t x) {            /* x is attacker-controlled */
    if (x < array1_size) {                  /* correct bounds check */
        uint8_t v = array1[x];              /* transiently may read OOB */
        return array2[v * CACHE_LINE];      /* secret-dependent cache footprint */
    }
    return 0;
}
```

### Mitigation A: speculation barrier

```c
uint8_t safe_gadget_fence(size_t x) {
    if (x < array1_size) {
        _mm_lfence();                       /* stop speculation past the check */
        uint8_t v = array1[x];
        return array2[v * CACHE_LINE];
    }
    return 0;
}
```

### Mitigation B: index masking (cheaper, no pipeline stall)

```c
/* Linux-kernel-style: clamp the index in DATA so even a mis-speculated
 * path cannot read out of bounds. mask is all-ones if x<size, else all-zeros. */
static inline size_t array_index_mask(size_t x, size_t size) {
    return ~((size_t)((x - size) >> (sizeof(size_t) * 8 - 1)) - 1);
    /* conceptual; real code uses arch-specific, audited helpers */
}

uint8_t safe_gadget_mask(size_t x) {
    if (x < array1_size) {
        x &= array_index_mask(x, array1_size); /* OOB index becomes 0 */
        uint8_t v = array1[x];
        return array2[v * CACHE_LINE];
    }
    return 0;
}
```

> In real code, use the kernel's `array_index_nospec()` or the compiler's automatic mitigations rather than hand-rolling the masking arithmetic.

### Constant-time crypto (the non-transient side channel you control)

```go
// Don't index tables with secrets; use the platform's vetted, constant-time
// crypto. Go's stdlib uses AES-NI when available, which avoids the
// secret-indexed table lookups that classic cache attacks exploited.
import (
    "crypto/aes"
    "crypto/subtle"
)

func ctEqual(a, b []byte) bool {
    return subtle.ConstantTimeCompare(a, b) == 1 // no early exit
}

func newCipher(key []byte) {
    _, _ = aes.NewCipher(key) // hardware AES: no secret-dependent table index
}
```

---

## Coding Patterns

**Pattern: barrier-or-mask at the bounds check.** In a confirmed gadget (attacker index → dependent secret-laden access), insert `array_index_nospec()`/masking, or an `lfence`, between the check and the access.

**Pattern: minimize shared, attacker-mappable memory.** Flush+Reload needs shared pages. Avoid mapping the same read-only data into attacker-controlled and victim contexts where it isn't necessary.

**Pattern: deny the high-resolution clock.** In sandboxes, reduce timer resolution and restrict `SharedArrayBuffer`-style shared-memory timers so cache timing becomes too noisy to exploit.

**Pattern: isolate the secret, not just guard it.** Put secrets in a separate process/enclave so a transient leak in untrusted code simply can't reach them.

---

## Best Practices

1. **Learn to *recognize* the gadget shape:** a bounds (or type) check followed by a secret-dependent dependent memory access on an attacker-influenced value.
2. **Prefer masking to fences** where applicable — same protection, far less performance cost. Use audited helpers (`array_index_nospec`), not hand-rolled bit tricks.
3. **Turn on compiler/OS mitigations for untrusted-input code** and understand which attack each one addresses.
4. **Don't co-locate untrusted code with secrets.** Process/VM/core isolation is the most reliable defense; it removes the precondition.
5. **Keep secrets out of indices and branches** in crypto and authentication code; use hardware crypto and constant-time libraries.
6. **Measure the cost.** Mitigations are not free; know what you are paying and decide deliberately, per workload.

---

## Edge Cases & Pitfalls

- **Over-fencing.** Sprinkling `lfence` everywhere tanks performance and is usually unnecessary — only the actual gadget needs protection. Profile and target.
- **Masking only works if it truly clamps.** A subtly wrong mask (off-by-one, non-power-of-two size) leaves the gadget exploitable. Use vetted helpers.
- **The compiler may defeat you.** Just as it can reintroduce branches into "constant-time" code, the compiler can reorder or elide your barrier. Verify the generated assembly for security-critical gadgets, or rely on the compiler's own mitigation pass.
- **"We bounds-check, so we're safe" is the exact misconception Spectre exploits.** The check is fine; speculation runs *past* it.
- **Forgetting the read phase needs a timer.** If you remove the attacker's high-resolution clock, you remove their ability to decode the cache — a real, deployed mitigation in browsers.
- **Assuming Prime+Probe needs shared memory.** It does not — that's why it works cross-VM in clouds and why cache partitioning matters.
- **Treating v1 as the only one.** v1 is the cleanest, but v2, v4, Meltdown, MDS, L1TF, and retbleed each have their own mechanism and their own mitigation — that's `senior.md`.

---

## Apply it

1. Find a real component where **Side Channels & Spectre** affects an interface or dependency.
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

- Which boundary is most affected by Side Channels & Spectre?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
