# Floating-Point (IEEE 754) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Floating-Point (IEEE 754)** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The exact bit layout, and what the exponent field encodes

For binary64, the 64 bits are: 1 sign `S`, 11 exponent bits `E` (as an unsigned integer 0–2047), and 52 fraction bits `F`. The **value** depends on `E`:

| `E` (raw) | Meaning | Value |
|-----------|---------|-------|
| `1` to `2046` | **Normalized** | `(-1)^S × 1.F × 2^(E - 1023)` |
| `0`, `F = 0` | **Zero** | `(-1)^S × 0` (so `+0` and `-0`) |
| `0`, `F ≠ 0` | **Subnormal** | `(-1)^S × 0.F × 2^(1 - 1023)` (note: no implicit 1, exponent fixed at the minimum) |
| `2047`, `F = 0` | **Infinity** | `(-1)^S × ∞` |
| `2047`, `F ≠ 0` | **NaN** | the fraction bits are the NaN "payload" |

The two reserved exponent values (`all-zeros` and `all-ones`) are what carve out the special cases. Everything else is a normal number.

### 2. Normalized vs subnormal (denormal) numbers

A normalized double's smallest positive value is `2^-1022 ≈ 2.2e-308`. What about numbers smaller than that but bigger than zero? Without a special case, there'd be a sudden gap — you'd jump from `2.2e-308` straight to `0`, a phenomenon called **underflow to zero**. IEEE 754 fills this gap with **subnormal numbers**: when the exponent field is all-zeros, the implicit leading bit becomes `0` instead of `1`, and the exponent is pinned at the minimum. This gives **gradual underflow** — as numbers shrink below `2^-1022`, they lose precision bit by bit instead of snapping to zero all at once. The smallest positive subnormal double is `2^-1074 ≈ 4.9e-324`.

The trade-off: subnormals are **slow** on many CPUs. Some hardware traps to microcode or even software to handle them, costing 100× the time of a normal operation. This is why high-performance code (audio DSP, ML) often enables **flush-to-zero (FTZ)** and **denormals-are-zero (DAZ)** modes — covered in `senior.md` — which sacrifice gradual underflow for speed.

### 3. ULP: the grid spacing of floating point

The key quantitative insight: **representable numbers are not evenly spaced.** They're spaced like `2^e × ε` — the gap doubles every time you cross a power of 2. The gap between a value and its nearest neighbor is one **ULP** (unit in the last place).

- Between `1.0` and `2.0`, the ULP is `2^-52 ≈ 2.2e-16`.
- Between `1024.0` and `2048.0`, the ULP is `2^-52 × 2^10 ≈ 2.3e-13` — a thousand times bigger.
- Between `2^52` and `2^53`, the ULP is exactly `1.0`. Above `2^53`, consecutive integers are no longer all representable.

This is why a fixed absolute tolerance is wrong: `1e-9` is far smaller than one ULP near a billion (you'd never find two "close" billion-sized values equal) and far larger than one ULP near `1e-15`.

### 4. Machine epsilon

**Machine epsilon (ε)** is the ULP at 1.0: the smallest number you can add to `1.0` and get something other than `1.0`. For double it is `2^-52 ≈ 2.220446049250313e-16`; for float it is `2^-23 ≈ 1.19e-7`. A useful interpretation: **ε is the relative rounding error of a single operation.** Any single correctly-rounded operation gives a result within `ε/2` (relative) of the true value. It's the building block for error analysis.

> Note: some languages (C++'s `numeric_limits::epsilon`, Python's `sys.float_info.epsilon`) define ε as exactly this `1.0`-to-next gap. Don't confuse it with "a small tolerance" — they're related but not the same.

### 5. Rounding modes, and why "round half to even"

When a result isn't representable, IEEE 754 must round it to a representable value. The standard defines four (plus one) rounding modes:

1. **Round to nearest, ties to even** — the **default**. Pick the nearest representable value; on an exact tie, pick the one whose last bit is `0` (even).
2. **Round to nearest, ties away from zero** — the "school" rounding (0.5 → 1).
3. **Round toward zero** (truncate).
4. **Round toward +∞** (ceiling).
5. **Round toward −∞** (floor).

Why is "ties to even" (banker's rounding) the default instead of the "round 0.5 up" you learned in school? Because rounding `0.5` always up introduces a **systematic bias**: across many roundings, results creep upward. Rounding ties to even has no such bias — half the ties round up, half round down, on average. For statistics, accounting, and long computations, removing that drift matters. `round(0.5)` gives `0`, `round(1.5)` gives `2`, `round(2.5)` gives `2` — surprising the first time, but bias-free. (This is also why Python 3's `round()` does ties-to-even and confuses people coming from Python 2.)

### 6. Catastrophic cancellation

The most important error mechanism to recognize: **subtracting two nearly-equal numbers destroys precision.** Suppose `a = 1.0000000123` and `b = 1.0000000001`, each known to ~10 significant digits. Their difference is `0.0000000122` — but the *leading* significant digits cancelled, and you're left with only a couple of meaningful digits; the rest of the result is rounding noise from the original approximations. The relative error in the difference can be enormous even though both inputs were accurate.

Classic victims:
- The quadratic formula `(-b ± sqrt(b² - 4ac)) / 2a` when `b² ≫ 4ac`: `-b + sqrt(b²-...)` cancels.
- Computing variance as `E[x²] - E[x]²` (the "naive" formula) — both terms can be huge and nearly equal.
- `1 - cos(x)` for small `x`.

The cure is *algebraic reformulation* to avoid the subtraction — e.g., rationalizing the quadratic formula, or using Welford's online algorithm for variance.

### 7. Absorption (swamping / loss of significance)

The mirror image: **adding a small number to a much larger one loses the small number entirely.** `1e16 + 1.0 == 1e16` in double, because `1.0` is smaller than one ULP at `1e16` — it falls off the bottom of the significand. This is why summing a large array of small numbers into a growing accumulator loses accuracy: late additions get "swamped" by the large running total. Kahan summation (below) fixes this.

### 8. Non-associativity: order changes the answer

Because every operation rounds, **floating-point addition and multiplication are not associative**:

```text
(1e16 + 1.0) - 1e16   →  0.0      (the 1.0 was absorbed, then subtracted away)
1e16 + (1.0 - 1e16)   →  ... different
```

A more practical statement: **summing the same list in a different order gives a different result.** This has real consequences:

- Parallel reductions (sum an array across threads) are non-deterministic in the low bits, because the combination order depends on scheduling.
- Compilers under `-ffast-math` (see `senior.md`) reorder sums and change results.
- "Sort smallest-magnitude-first" gives a more accurate sum than a random order, because it delays absorption.

### 9. Comparing floats correctly: absolute, relative, ULP

The junior advice "use a tolerance" needs three refinements:

- **Absolute tolerance**: `abs(a - b) < atol`. Correct only when you know the *scale* of the numbers and they're near a known magnitude (e.g., comparing to 0 within `1e-12`). Wrong across scales.
- **Relative tolerance**: `abs(a - b) <= rtol * max(abs(a), abs(b))`. Scale-independent — works for tiny and huge numbers. But it fails near zero (relative error explodes when both are ~0).
- **Combined**: `abs(a - b) <= max(atol, rtol * max(abs(a), abs(b)))`. This is what Python's `math.isclose` and NumPy's `allclose` do. The `atol` term saves you near zero; the `rtol` term saves you everywhere else.
- **ULP-based**: reinterpret the float bits as integers and compare the integer distance. `2` ULPs means "at most two representable values apart." The most precise notion of "almost equal," used in numerical libraries and test frameworks. Caveat: handle signs and NaN specially.

There is no universal tolerance. The right one depends on how the numbers were computed and how much error the algorithm accumulated.

---

## Code Examples

### Inspecting the bits

**C** — see the raw layout:

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>

void dump(double d) {
    uint64_t bits;
    memcpy(&bits, &d, sizeof bits);
    int sign = (int)(bits >> 63);
    int exp  = (int)((bits >> 52) & 0x7FF);
    uint64_t frac = bits & 0xFFFFFFFFFFFFFULL;
    printf("%-22.17g  S=%d  E=%4d (unbiased %5d)  F=%013llx\n",
           d, sign, exp, exp - 1023, (unsigned long long)frac);
}

int main(void) {
    dump(1.0);          // E=1023, F=0
    dump(0.1);          // repeating fraction, rounded
    dump(0.5);          // exact
    dump(2.0);          // E=1024
    dump(5e-324);       // smallest subnormal
    dump(1.0/0.0);      // +Inf: E=2047, F=0
    dump(0.0/0.0);      // NaN:  E=2047, F!=0
    return 0;
}
```

**Python** — same idea via `struct`:

```python
import struct
def bits(x):
    (b,) = struct.unpack('>Q', struct.pack('>d', x))
    return f"{b:064b}"
print(bits(1.0))   # 0 01111111111 0000...   (sign exp[1023] frac[0])
print(bits(0.1))   # 0 01111111011 1001100110011...  (repeating, rounded)
```

### Machine epsilon and ULP

```python
import sys, math
print(sys.float_info.epsilon)            # 2.220446049250313e-16
print(1.0 + sys.float_info.epsilon != 1.0)   # True
print(1.0 + sys.float_info.epsilon/2 == 1.0) # True (rounds away)

# ULP at a given magnitude:
print(math.ulp(1.0))      # 2.220446049250313e-16
print(math.ulp(1e9))      # 1.1920928955078125e-07  — far larger!
print(math.ulp(1e16))     # 2.0  — adjacent doubles are 2 apart here
```

### The 2^53 integer ceiling

```javascript
console.log(2 ** 53);            // 9007199254740992
console.log(2 ** 53 + 1);       // 9007199254740992  — the +1 vanished!
console.log(Number.MAX_SAFE_INTEGER); // 9007199254740991
```

### Catastrophic cancellation — the quadratic formula

```python
import math

def naive_root(a, b, c):
    d = math.sqrt(b*b - 4*a*c)
    return (-b + d) / (2*a)   # cancels when b is large and positive

def stable_root(a, b, c):
    d = math.sqrt(b*b - 4*a*c)
    # avoid cancellation by choosing the sign that adds magnitudes
    if b >= 0:
        q = -(b + d) / 2
    else:
        q = -(b - d) / 2
    return c / q              # use the product-of-roots identity

a, b, c = 1.0, 1e8, 1.0
print(naive_root(a, b, c))    # -7.450580596923828e-09  (garbage, lost digits)
print(stable_root(a, b, c))   # -1.0000000000000002e-08 (correct)
```

The true root is `-1e-8`. The naive form cancels `-b + sqrt(b² - 4)` ≈ `-1e8 + 1e8` and is left with noise.

### Non-associativity demonstrated

```python
a, b, c = 1e16, 1.0, -1e16
print((a + b) + c)   # 0.0   — b was absorbed, then a cancelled
print(a + (b + c))   # 0.0 here too, but...
print((1e16 + 1.0) - 1e16)   # 0.0   — the 1.0 is gone
print(1e16 + (1.0 - 1e16))   # 0.0
# A clearer case — summing a list in two orders:
xs = [1e16, 1.0, -1e16, 1.0]
print(sum(xs))                    # 2.0  if added left to right? Often 0.0!
print(sum(sorted(xs, key=abs)))   # 2.0  — small first preserves them
```

### Kahan (compensated) summation

```python
def kahan_sum(values):
    total = 0.0
    comp = 0.0          # running compensation for lost low-order bits
    for x in values:
        y = x - comp
        t = total + y
        comp = (t - total) - y   # recovers what was lost in (total + y)
        total = t
    return total

import random
data = [0.1] * 10_000_000
print(sum(data))        # 999999.9999...  drifts
print(kahan_sum(data))  # 1000000.0000... much closer
```

### Correct comparison with `isclose`

```python
import math
print(math.isclose(0.1 + 0.2, 0.3))                 # True
print(math.isclose(1e-18, 0.0))                     # False! rel_tol fails near 0
print(math.isclose(1e-18, 0.0, abs_tol=1e-12))      # True — abs_tol saves it
# signature: isclose(a, b, rel_tol=1e-09, abs_tol=0.0)
```

```go
import "math"

func almostEqual(a, b, relTol, absTol float64) bool {
    diff := math.Abs(a - b)
    return diff <= absTol || diff <= relTol*math.Max(math.Abs(a), math.Abs(b))
}
```

### ULP-based comparison

```c
#include <stdint.h>
#include <string.h>
#include <stdbool.h>

int64_t to_ordered(double d) {
    int64_t i;
    memcpy(&i, &d, sizeof i);
    // make the integer monotonic across the sign boundary
    return i < 0 ? (int64_t)0x8000000000000000ULL - i : i;
}

bool within_ulps(double a, double b, int64_t max_ulps) {
    int64_t ia = to_ordered(a), ib = to_ordered(b);
    int64_t d = ia > ib ? ia - ib : ib - ia;
    return d <= max_ulps;   // NaN handling omitted for brevity
}
```

---

## Coding Patterns

### Pattern 1: `isclose` with both tolerances

Never ship a bare `abs(a-b) < eps`. Use the combined form so it works near zero *and* at scale:

```python
def isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
```

### Pattern 2: Welford's online variance (cancellation-free)

```python
def variance(values):
    n = 0; mean = 0.0; m2 = 0.0
    for x in values:
        n += 1
        delta = x - mean
        mean += delta / n
        m2 += delta * (x - mean)
    return m2 / n if n else 0.0
```

### Pattern 3: Sort-then-sum for accuracy

```python
def accurate_sum(values):
    return sum(sorted(values, key=abs))   # smallest magnitude first
```

For the gold standard, use Kahan or pairwise summation (NumPy uses pairwise internally).

### Pattern 4: Rationalize to kill cancellation

`sqrt(x + 1) - sqrt(x)` cancels for large `x`. Multiply by the conjugate:

```python
import math
def diff_sqrt(x):
    # (sqrt(x+1) - sqrt(x)) * (sqrt(x+1)+sqrt(x)) / (...) = 1 / (sqrt(x+1)+sqrt(x))
    return 1.0 / (math.sqrt(x + 1) + math.sqrt(x))
```

### Pattern 5: Use `log1p` / `expm1` for small arguments

Standard libraries provide `log1p(x) = log(1+x)` and `expm1(x) = exp(x)-1`, which stay accurate when `x` is tiny and the naive form would cancel against 1.

```python
import math
print(math.log(1 + 1e-16))    # 0.0  — lost entirely
print(math.log1p(1e-16))      # 1e-16 — correct
```

---

## Best Practices

- **Choose tolerances by magnitude.** Use relative tolerance for general values, an absolute floor near zero. Prefer `math.isclose` / `numpy.allclose` over hand-rolled comparisons.
- **Recognize cancellation and reformulate.** Conjugate multiplication, `log1p`/`expm1`, the stable quadratic formula, Welford's variance.
- **Use compensated summation for long sums.** Kahan or pairwise. Sort smallest-first if you can't.
- **Know that round-to-even is the default** and don't fight it; it's the correct, unbiased choice.
- **Don't disable subnormals casually** — only flush-to-zero when you've measured a real performance problem and accepted the precision loss.
- **Reason in ULPs when writing numerical tests.** "Within 4 ULPs" is a precise, scale-independent assertion.
- **Prefer `double` for accumulation even if inputs are `float`** — accumulate in higher precision, store in lower.

---

## Edge Cases & Pitfalls

- **`1e16 + 1.0 == 1e16`.** Absorption. The `1.0` is below one ULP at that magnitude.
- **`(a + b) + c != a + (b + c)`.** Reordering a sum changes the result; parallel reductions are non-deterministic in low bits.
- **Round-to-even surprises:** `round(0.5) == 0`, `round(2.5) == 2` in Python 3, banker's rounding by design.
- **Subnormal performance cliff:** a filter or physics sim producing tiny values can suddenly run 50× slower when it enters the subnormal range.
- **Naive variance `E[x²] − E[x]²` can go negative** due to cancellation — then `sqrt` gives NaN.
- **Relative tolerance fails at zero:** `isclose(1e-300, 0.0)` is `False` without an `abs_tol`.
- **`float` accumulation overflows precision fast:** summing a million `float`s in `float` precision can be wildly off; accumulate in `double`.
- **The quadratic formula's "minus" branch** silently returns garbage when `b² ≫ 4ac`.
- **Comparing across types:** `0.1f` (float) and `0.1` (double) are different values; `(double)0.1f != 0.1`.

---

## Common Mistakes

1. **A single global `EPSILON = 1e-9` for all comparisons.** Wrong at large and tiny magnitudes.
2. **Subtracting nearly-equal numbers without noticing.** The classic source of "my result is mostly noise."
3. **Computing variance/stddev with the naive two-pass-into-one formula.** Use Welford.
4. **Summing a huge list in naive left-to-right order** and trusting the low digits.
5. **Expecting `round(2.5) == 3`.** It's `2` under ties-to-even.
6. **Flushing subnormals to zero "for speed" without measuring** — and silently changing results.
7. **Asserting exact equality in tests** for computed floats. Use ULP or `isclose`.
8. **Accumulating in `float` instead of `double`.** Always accumulate in the widest practical type.
9. **Ignoring that `b*b - 4*a*c` itself can cancel**, not just the outer formula.
10. **Believing two algebraically-equal expressions are numerically equal.** They round differently.

---

## Apply it

1. Find a real component where **Floating-Point (IEEE 754)** affects an interface or dependency.
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

- Which boundary is most affected by Floating-Point (IEEE 754)?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
