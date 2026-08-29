# Floating-Point (IEEE 754) — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Floating-Point (IEEE 754)** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Money: the rules, and the systems that get it right

The rule is absolute: **never represent monetary amounts as binary `float`/`double`.** `0.10` is not representable; sums drift; `0.1 × 3 != 0.3`; and a one-cent error multiplied across millions of transactions is a real, auditable loss. The correct representations:

- **Scaled integers (minor units).** Store cents (or mills, or satoshis) as a 64-bit integer. `$10.99` → `1099`. Arithmetic is exact; you choose the rounding only at division (interest, splits, tax). This is what Stripe, most ledgers, and high-volume payment systems use. 64 bits of cents covers ~$92 quadrillion — enough.
- **Arbitrary-precision decimal.** `BigDecimal` (Java), `decimal.Decimal` (Python), `System.Decimal` (C#, 128-bit, 28-29 digits), `NUMERIC`/`DECIMAL` in SQL. Use when you need exact division, percentages, and many decimal places (FX rates, scientific billing). Slower than integers but exact in base 10.

Critical operational details:
- **Always set the rounding mode and scale explicitly** at every division/quantize step. The default differs by library and jurisdiction (HALF_EVEN for unbiased aggregates; HALF_UP for many tax authorities). An unspecified rounding mode is a latent bug.
- **The total must reconcile.** Splitting `$10.00` three ways is `$3.34 + $3.33 + $3.33` — the "largest remainder" allocation. Naive per-share rounding loses or invents a cent.
- **Store the currency with the amount.** `1099` is meaningless without "USD" (and its 2-decimal convention; JPY has 0, some currencies 3).
- **Never let a `double` into the path** — not even "temporarily for the percentage calc." That's exactly where the cent leaks.

### 2. Accumulated error in long-running systems

A 24/7 service that maintains a running floating-point total — a cumulative metric, a moving average, a physics integrator, a financial position in a (wrongly-chosen) double — accumulates rounding error that grows over time. The error of naive summation grows like `O(n·ε)` in the worst case and `O(√n·ε)` typically. Over a billion updates, even `√n·ε ≈ 3e4 × 2e-16 ≈ 6e-12` relative — usually fine, but **absorption** can make it far worse: once your accumulator dwarfs the increments, increments start vanishing entirely (`1e16 + 1.0 == 1e16`).

Defenses in production:
- **Re-baseline periodically.** Every N updates or every interval, recompute the aggregate from the source of truth and reset the accumulator. Discards all accumulated drift.
- **Compensated summation** (Kahan/Neumaier) for the running total — but beware fast-math deleting it (senior level).
- **Keep the accumulator in higher precision** than the inputs (sum `float` streams into a `double`, or `double` into a `double-double`).
- **For counters that must be exact, use integers.** A request counter is an `int64`, never a `double`.
- **Welford for running mean/variance** instead of summing `x` and `x²` separately (which cancels).

### 3. Reproducibility across a fleet

When does bit-exactness matter? Caching/memoization keyed on computed floats; deterministic replay (debugging, audit); lockstep simulation (multiplayer games, distributed physics); and **consensus** (a blockchain or a quorum that must agree on a computed value). On a heterogeneous fleet — Intel and AMD and ARM nodes, different `libm` versions, different compilers and flags — the same input can produce different floats (senior level: transcendentals, FMA contraction, x87, fast-math). Symptoms: a cache that never hits because the key drifts; a consensus round that can't reach quorum; a replay that diverges from the recording.

The professional answers, in order of preference:
1. **Don't put floats in the agreement path.** Use integers/fixed-point for anything that must match exactly across nodes. This is why serious financial and consensus systems avoid FP for the canonical value.
2. **If you must use floats, pin everything:** same compiler + flags (`-ffp-contract=off`, no fast-math, SSE2), and *vendor your own* transcendentals (a fixed polynomial, `crlibm`, or a pinned SLEEF) so `sin`/`exp` match.
3. **Round to a tolerance before the comparison** — quantize computed values to a coarser grid so platform jitter in the low bits doesn't matter (works for caching, not for consensus).

### 4. Performance: subnormals, vectorization, and FTZ

Floating-point *performance* problems in production are usually one of:
- **Subnormal stalls.** A decaying signal (audio reverb tail, a physics sim coming to rest, a leaky-integrator metric) produces denormalized numbers, and on many CPUs each denormal op costs 100+ cycles (microcode assist). A loop that ran at 2 GFLOPS suddenly runs at 0.02. The fix: enable **FTZ/DAZ** (`_MM_SET_FLUSH_ZERO_MODE`, `-ffast-math` includes it, or set MXCSR directly), accepting that gradual underflow is lost — almost always fine for audio/graphics/ML.
- **Failure to vectorize.** Strict IEEE ordering forbids the compiler from reassociating a reduction loop, so it can't use SIMD. `-ffp-contract=fast` + restricted reassociation (or `#pragma omp simd reduction`) unlocks 4-8× — at the cost of bit-reproducibility.
- **`double` vs `float` bandwidth.** In memory-bound kernels (large arrays, ML inference), `float` (or `bfloat16`/`fp16`) halves bandwidth and doubles SIMD lane count. Mixed precision: compute in `float`, accumulate in `double`.
- **Division and transcendentals are slow.** `1.0/x` is ~10-20 cycles; `sin`/`exp` are ~50-200. Reciprocal approximation + Newton, or a polynomial approximation, when the ULP budget allows.

### 5. Rounding-mode and conversion bugs at the boundary

Two production bug families that aren't about precision at all:
- **Float→int conversion.** `(int)x` truncates toward zero in C/Java; out-of-range conversions are **undefined behavior in C** (and were the Ariane 5 failure: a `double` velocity that fit in 64 bits was converted to a 16-bit integer, overflowed, and triggered an unhandled exception). `(int) 1e10` is UB in C; in Rust it saturates; in JS `| 0` wraps. Always range-check before narrowing.
- **Rounding-mode mismatch.** Two services computing the same total with different rounding modes (one HALF_EVEN, one HALF_UP) disagree by a cent on ~half the ties. This is the classic "finance and engineering don't reconcile" ticket. The fix is a single, documented, enforced rounding policy.

## Code Examples

### Money done right — scaled integers with correct splitting

```python
def split_evenly(total_cents: int, parts: int) -> list[int]:
    """Split an integer amount into `parts` shares that sum EXACTLY to total."""
    base, remainder = divmod(total_cents, parts)
    # distribute the leftover cents to the first `remainder` shares
    return [base + (1 if i < remainder else 0) for i in range(parts)]

shares = split_evenly(1000, 3)     # $10.00 / 3
print(shares, sum(shares))          # [334, 333, 333]  sum=1000  ✓ no cent lost
```

### Money with decimal and an explicit rounding policy

```python
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

def apply_tax(amount: Decimal, rate: Decimal, policy=ROUND_HALF_UP) -> Decimal:
    # quantize is the ONLY place rounding happens, and the mode is explicit
    return (amount * rate).quantize(Decimal('0.01'), rounding=policy)

print(apply_tax(Decimal('19.99'), Decimal('0.0825')))  # 1.65  (HALF_UP, regulatory)
```

```java
import java.math.BigDecimal;
import java.math.RoundingMode;

BigDecimal subtotal = new BigDecimal("19.99");
BigDecimal taxRate  = new BigDecimal("0.0825");
BigDecimal tax = subtotal.multiply(taxRate)
                         .setScale(2, RoundingMode.HALF_UP);  // explicit, documented
```

### Bounding drift: re-baselining a long-running accumulator

```python
class RunningTotal:
    """A double accumulator that periodically re-baselines from the source of truth."""
    def __init__(self, rebaseline_every=100_000):
        self._sum = 0.0
        self._n = 0
        self._every = rebaseline_every
        self._history = []          # in real systems, the durable source of truth

    def add(self, x: float):
        self._sum += x
        self._history.append(x)
        self._n += 1
        if self._n % self._every == 0:
            self._sum = math.fsum(self._history)   # exact re-sum, discards drift

import math
```

> `math.fsum` (Python) is a correctly-rounded full-precision sum — a production-grade alternative to hand-rolled Kahan when you have all values in hand.

### Catch NaN/Inf at the boundary, not downstream

```python
import math

def ingest_metric(name: str, value: float) -> float:
    if not math.isfinite(value):                  # catches NaN AND ±Inf
        raise ValueError(f"non-finite metric {name!r}: {value!r}")
    return value
```

```go
import "math"

func ingest(name string, v float64) (float64, error) {
    if math.IsNaN(v) || math.IsInf(v, 0) {
        return 0, fmt.Errorf("non-finite metric %q: %v", name, v)
    }
    return v, nil
}
```

### Safe float→int narrowing (the Ariane lesson)

```rust
// Rust: `as` saturates (won't UB), but be explicit about intent.
fn to_i16_checked(x: f64) -> Result<i16, &'static str> {
    if !x.is_finite() { return Err("non-finite"); }
    let r = x.round();
    if r < i16::MIN as f64 || r > i16::MAX as f64 {
        return Err("out of range");   // the check Ariane 5 lacked
    }
    Ok(r as i16)
}
```

```c
#include <math.h>
#include <limits.h>
// In C, out-of-range float->int is UNDEFINED BEHAVIOR. Always range-check.
int safe_d2i(double x, int *out) {
    if (!isfinite(x)) return -1;
    double r = nearbyint(x);
    if (r < (double)INT_MIN || r > (double)INT_MAX) return -1;
    *out = (int)r;
    return 0;
}
```

### Enabling FTZ/DAZ to kill subnormal stalls

```c
#include <pmmintrin.h>   // SSE3
// Call once per thread before the hot loop.
void enable_ftz_daz(void) {
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);       // subnormal results -> 0
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON); // subnormal inputs -> 0
}
```

### A reproducibility check across machines

```python
import struct, hashlib

def fp_fingerprint(values) -> str:
    """Hash the exact bit patterns so two machines can compare results."""
    h = hashlib.sha256()
    for v in values:
        h.update(struct.pack('>d', v))   # exact 8 bytes, not a decimal string
    return h.hexdigest()
# If two nodes disagree on this hash, the FP results diverged (FMA/libm/fast-math).
```

## Trade-offs

| You gain... | ...at the cost of... |
|-------------|----------------------|
| Scaled-integer money (exact) | Manual scale/currency handling; integer overflow at extreme magnitudes |
| Decimal money (exact, divisible) | 5-50× slower than binary FP; larger storage |
| Re-baselining accumulators | Extra recompute cost; needs a durable source of truth |
| FTZ/DAZ (no subnormal stalls) | Loses gradual underflow; changes results near zero |
| Vectorized reductions (fast) | Non-deterministic low bits; not bit-reproducible |
| Bit-reproducible FP | Vendored libm, no FMA/fast-math, big engineering cost, slower |
| Boundary NaN assertions | Slight overhead; must be placed at every edge |

## Coding Patterns

### 1. The "money type" wrapper

Wrap minor-unit integers in a type so a `double` can never accidentally enter:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Money:
    cents: int
    currency: str = "USD"
    def __add__(self, o): assert self.currency == o.currency; return Money(self.cents + o.cents, self.currency)
    def __str__(self): return f"{self.cents/100:.2f} {self.currency}"   # display only
```

### 2. Assert-finite boundary guards

Place `assert math.isfinite(x)` (or a raising check) at: after deserialization, before persistence, at API boundaries, and after any division. The cost is negligible; the diagnostic value is enormous.

### 3. Reference-oracle differential testing

For a critical numerical routine, compute the same thing two ways — production (`double`) and oracle (decimal / mpmath / double-double) — and assert they agree to a documented ULP/relative bound in CI. Catches algorithm regressions and platform drift.

### 4. Quantize-before-key for FP caches

```python
def cache_key(x: float) -> int:
    return round(x * 1e6)   # quantize to 1e-6 grid; platform jitter in low bits won't break the key
```

### 5. Local-origin coordinates to avoid cancellation

In geo/CAD, subtract a local origin from world coordinates *before* doing math, so you're not computing differences of two ~6,378,000 m numbers (which cancels to noise at `float` precision).

## Best Practices

- **Money: scaled integers or decimal, never binary float.** One enforced, documented rounding policy across every service. Store currency with amount.
- **Range-check every float→int (and double→float) narrowing.** Out-of-range is UB in C and a silent wrap/saturate elsewhere — both are bugs.
- **Assert finiteness at boundaries.** Catch NaN/Inf where it's born, with a stack trace.
- **Bound drift in long-lived accumulators:** re-baseline, compensate, or keep integers for exact counts.
- **For cross-fleet agreement, keep floats out of the consensus path.** If you can't, pin compiler/flags and vendor your `libm`.
- **Profile for subnormal stalls** in audio/DSP/physics; enable FTZ/DAZ on the hot path with eyes open.
- **Differential-test critical numerics against a high-precision oracle** in CI.
- **Pick the rounding mode deliberately** (HALF_EVEN for unbiased aggregates, HALF_UP for many regulators) and *write down why*.
- **Reconcile totals, don't round shares independently** — use largest-remainder allocation.

## Edge Cases & Pitfalls

- **A `double` accumulator that grows past `2^53`** stops counting small increments (absorption); your "total" silently freezes.
- **Out-of-range `(int)double` is UB in C/C++** — sanitizers catch it; production may not.
- **`-ffast-math` in a dependency** sets FTZ/DAZ process-wide, changing *your* subnormal results.
- **Two microservices, two rounding modes** → off-by-a-cent reconciliation failures on ties.
- **NaN in a sort comparator** corrupts ordering or throws "comparison contract violated."
- **`float` GPS/geo coordinates** lose ~1 m precision; differences cancel to garbage — use `double` + local origins.
- **`JSON.parse`/serialization not round-tripping** if you wrote with `%g` instead of shortest-round-trip.
- **JavaScript integer IDs over `2^53`** (`Number`) silently collide — use `BigInt` or strings for snowflake IDs.
- **Time as accumulated float seconds** drifts (Patriot) — accumulate integer ticks, convert at the edge.
- **Division by a value that can be `±0.0`** yields `±Inf` that poisons downstream silently.

## Common Mistakes

1. **Money in `double`** "because it's just a prototype" — prototypes ship.
2. **Unprotected float→int narrowing** — the Ariane class of bug, still common.
3. **Truncating instead of rounding** a value computed many times — the Vancouver class, a systematic bias.
4. **Long-running `double` accumulator** with no re-baseline — drifts, or freezes via absorption.
5. **Discovering NaN three layers downstream** because nobody asserted finiteness at the source.
6. **Assuming all fleet nodes compute identical floats** — they don't (FMA, libm, flags).
7. **Independent per-share rounding** that loses or invents a cent.
8. **Leaving a rounding mode unspecified**, inheriting a library/jurisdiction default nobody chose.
9. **Ignoring subnormal stalls** until a customer reports the audio plugin dropping frames.
10. **Storing 64-bit IDs as `double`/`Number`** and getting silent collisions above `2^53`.

## Debugging Playbook

When a ticket says "the numbers are wrong / don't match / show NaN":

1. **Reproduce with exact bits.** Print/log `%.17g` or the raw 8-byte hex, not the friendly decimal. The friendly printer hides the discrepancy.
2. **Localize the NaN/Inf.** Add finiteness asserts at module boundaries and bisect inward until the assert fires at the birthplace. Or run with FP exception trapping (`feenableexcept(FE_INVALID | FE_DIVBYZERO)`) to trap at the producing instruction.
3. **Diff against an oracle.** Recompute with `decimal`/`mpmath`/double-double. Where production and oracle first diverge is your cancellation or absorption site.
4. **For "matches on my machine, not in prod":** suspect FMA contraction, `libm`, fast-math, or x87. Compare build flags and CPU. Hash the bit patterns (fingerprint) on each node.
5. **For drift:** plot the error over time/iterations. Linear growth → biased step (truncation, like Vancouver). `√n` growth → unbiased accumulation. A sudden freeze → absorption past `2^53`.
6. **For money discrepancies:** check the rounding mode and scale at *every* division/quantize; check share-splitting reconciles; check no `double` snuck into the path.
7. **For float→int crashes/garbage:** check the range before the cast; enable UBSan (`-fsanitize=float-cast-overflow`).
8. **Confirm the fix with a regression test** that pins the exact bits or asserts the ULP/relative bound — so the drift can't silently return.

---

## Apply it

1. Define the user or business outcome that **Floating-Point (IEEE 754)** should improve.
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

- Which measurable outcome justifies investing in Floating-Point (IEEE 754)?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
