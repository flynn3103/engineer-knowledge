# Floating-Point (IEEE 754) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Floating-Point (IEEE 754)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Correctly-rounded operations vs library functions

IEEE 754 mandates **correct rounding** for `+`, `−`, `×`, `÷`, `√`, remainder, and FMA: the answer is the true mathematical result rounded once. This is why `+−×÷√` are *portable* — every conforming machine gives bit-identical results for them.

It does **not** require correct rounding for transcendentals (`sin`, `cos`, `exp`, `log`, `pow`). The reason is the **Table Maker's Dilemma**: to round `sin(x)` correctly you may need to compute it to arbitrarily many extra digits to resolve a near-tie, and nobody can bound how many. So `libm` implementations settle for "faithfully rounded" (within 1 ULP) and *differ across platforms*. glibc's `sin`, macOS's `sin`, and MSVC's `sin` can disagree in the last bit. **This is the single biggest source of cross-platform FP non-determinism in real code**, and it is not a bug in any of them.

### 2. Fused multiply-add (FMA)

`fma(a, b, c)` computes `a*b + c` with the full-precision product, adding `c`, and rounding **once**. A naive `a*b + c` rounds twice (once after the multiply, once after the add). Consequences:

- FMA is **more accurate** — it's the foundation of accurate dot products, polynomial evaluation (Horner's method), and Newton iterations.
- FMA **changes results**. Code compiled with `-mfma` produces different bits than without it. `a*a - b*b` via two FMAs can even yield a *different sign* near zero than the separated form.
- FMA enables exact error extraction: `err = fma(a, b, -(a*b))` gives the exact rounding error of `a*b` — the building block of double-double arithmetic and TwoProduct.
- The C standard lets the compiler **contract** `a*b+c` into an FMA at its discretion unless you set `#pragma STDC FP_CONTRACT OFF`. So "the same source" silently rounds differently depending on `-ffp-contract`.

### 3. x87 extended precision and `FLT_EVAL_METHOD`

The original x86 FPU (x87) has an 80-bit internal stack. When you compute `double x = a*b + c` on x87, the intermediate `a*b` is held in **80-bit precision**, not 64-bit, until it's stored back to memory as a `double`. This causes the infamous **"works in debug, breaks in release"** and **"the value changes when I print it"** bugs: a value living in an 80-bit register compares unequal to the same value after being spilled to a 64-bit memory slot.

`FLT_EVAL_METHOD` tells you the regime:
- `0` — intermediates evaluated to their type (SSE2 default on x86-64). Clean and portable.
- `1` — `float` intermediates promoted to `double`.
- `2` — everything in `long double` / 80-bit (classic 32-bit x87).

Modern x86-64 uses **SSE2** scalar instructions (`FLT_EVAL_METHOD == 0`) by default, which killed most of the 80-bit surprises. But 32-bit x86 targets, `long double`, and `-mfpmath=387` resurrect them. The lesson: on x87, an expression's value depends on *register allocation* — a property the language standard does not control.

### 4. `-ffast-math`: what you actually give up

`-ffast-math` (GCC/Clang) is a bundle. Each sub-flag trades a guarantee for speed:

- `-fno-signaling-nans`, `-ffinite-math-only` — **assume no NaN or Inf exist.** Now `x == x` may be optimized to `true` even when `x` is NaN; `isnan(x)` can be folded to `false`. Your NaN checks *stop working*.
- `-fassociative-math` — **allow reassociation.** `(a+b)+c → a+(b+c)`, vectorized reductions, Kahan summation gets *optimized away* (the compiler "simplifies" the compensation to zero).
- `-freciprocal-math` — replace `x/y` with `x * (1/y)`, losing a rounding.
- `-fno-trapping-math`, `-funsafe-math-optimizations` — assume no FP exceptions.
- Flush subnormals to zero.
- It also sets `-fno-honor-nans` in a way that can change `min`/`max` semantics.

The danger is that fast-math is **not local** — linking a fast-math object can set the FTZ/DAZ MXCSR bits process-wide (notoriously, some libraries' static initializers do this), changing the behavior of code that never opted in. **Rule: never put `-ffast-math` on a whole project.** Apply `-ffp-contract=fast` and targeted `__attribute__((optimize))` to the hot kernels you've validated, and keep the rest strict.

### 5. Deterministic floating point across platforms

"Bit-identical results everywhere" is achievable but requires discipline, because every layer above conspires against it:

- **Compiler:** disable FMA contraction (`-ffp-contract=off`), forbid reassociation (don't use fast-math), pin the rounding mode.
- **Hardware:** force SSE2 (not x87), set consistent FTZ/DAZ, beware that `sqrt` is correctly rounded but `rsqrt`/`recip` *approximations* (`vrsqrtps`) are not — and differ across vendors.
- **Library:** the killer. You cannot rely on `sin`/`exp` matching across platforms. For determinism you must **ship your own** correctly-rounded or fixed implementations (e.g., a vendored polynomial, `crlibm`, or SLEEF in a pinned mode).
- **Language runtime:** Java's `strictfp` (pre-Java 17 it was opt-in; Java 17 made *all* FP strict by default) guaranteed reproducibility at a small speed cost. Most languages have no such mode.

Games (lockstep multiplayer), blockchains (consensus on computed values), and scientific reproducibility all hit this. The pragmatic answer is often "avoid floats in the consensus path" — use integers/fixed-point for anything that must agree bit-for-bit across nodes.

### 6. NaN: quiet vs signaling, payloads, propagation

All NaNs share `exponent = all-ones, fraction ≠ 0`. The **top fraction bit** distinguishes them:

- **Quiet NaN (qNaN):** top fraction bit = 1. Propagates silently: any operation with a qNaN yields a qNaN. This is the NaN you normally see.
- **Signaling NaN (sNaN):** top fraction bit = 0 (rest nonzero). Using it in arithmetic raises the **invalid-operation** exception; if unmasked, it traps. Intended to flag uninitialized memory. Rarely used because most languages can't even produce one without bit tricks, and loading an sNaN into a register often quiets it.

The remaining **payload** bits can carry diagnostic data (which operation produced this NaN), but the standard barely constrains propagation of payloads, and most hardware just picks one of the input NaNs (or a canonical qNaN). Don't rely on payloads in portable code.

Practical NaN facts a senior must own: `NaN != NaN` (so `x != x` ⇔ `isnan(x)`); `min(NaN, 5)` is **platform-dependent** in older specs (IEEE 754-2008 `minNum` returns the non-NaN operand; 754-2019 changed this — `fmin`/`fmax` vs `min`/`max` differ); sorting arrays with NaN can violate the comparator's total-order contract and corrupt the sort (Java's `Arrays.sort` handles it via total-order bits, but a raw `<` comparator does not).

### 7. Decimal floating point (IEEE 754-2008)

Binary floating point cannot represent `0.10` exactly. IEEE 754-2008 added **decimal** formats — `decimal32`, `decimal64`, `decimal128` — where the significand is a *decimal* integer and the exponent is a power of 10. Now `0.1` is exact. These power:

- IBM POWER and z/Architecture mainframes (hardware decimal FP — banking runs on them).
- Java's `BigDecimal` (software, arbitrary precision), C#'s `decimal` (128-bit, 28-29 digits), Python's `decimal.Decimal`.
- The C `_Decimal64` type (GCC extension).

Two competing significand encodings exist: **DPD** (Densely Packed Decimal, IBM, packs 3 digits into 10 bits) and **BID** (Binary Integer Decimal, Intel, stores the significand as a plain binary integer). They represent the same values but with different bit patterns; libraries pick one. For money, decimal FP or scaled integers are the correct tools — binary FP never is.

### 8. The print/parse round-trip problem

Converting binary64 → decimal string → binary64 must round-trip: you should get the *same* double back. Two sub-problems:

- **Shortest representation:** there are infinitely many decimal strings that round to a given double; you want the *shortest* one that's unambiguous (`0.1`, not `0.1000000000000000055`). This is the Steele & White "Dragon4" problem (1990). Modern algorithms: **Grisu** (Loitsch, 2010) — fast but occasionally falls back to a slow path — and **Ryū** (Adams, 2018) — always fast, always shortest, now used in Java, Rust, and many stdlibs. Go uses a Grisu-derived shortest algorithm in `strconv`.
- **Correct parsing:** `strtod`/`ParseFloat` must return the correctly-rounded double nearest the decimal. This is harder than it looks (Clinger 1990; the "Eisel-Lemire" fast parser, 2020, made it both fast and correct).

The practical knobs: `%.17g` always round-trips a double (17 significant decimal digits suffice for binary64; `9` for binary32), but it's *not shortest* — it prints `0.30000000000000004`. The shortest-round-trip printer prints `0.1` for `0.1`. Know which your language's default uses: Python `repr`, Go `%v`, Rust `{}`, modern JS all print shortest-round-trip; C `printf("%g")` does not.

### 9. The fast inverse square root, as a cultural artifact

The Quake III `0x5f3759df` trick computes `1/sqrt(x)` by reinterpreting the float bits as an integer, doing `i = 0x5f3759df - (i >> 1)`, reinterpreting back, and running one Newton-Raphson step. It works because **the exponent field of an IEEE 754 float is (almost) the base-2 logarithm of the number**, so an integer right-shift halves the log → square roots, and the subtraction implements the `-1/2` of the inverse-sqrt exponent plus a bias correction. The magic constant restores the bias and minimizes the linear approximation error.

Its real lesson for a senior is not the constant — modern CPUs have `rsqrtss` that's faster and the trick is obsolete — but the **insight that a float's bit pattern, read as an integer, is a piecewise-linear approximation of its logarithm.** That same insight powers ULP comparison (middle level), `frexp`/`ldexp`, and fast `log2` estimates. The number `0x5f3759df` is a museum piece; the bit-pattern-as-log intuition is permanent.

## Code Examples

### FMA changes the answer

```c
#include <stdio.h>
#include <math.h>
int main(void) {
    double a = 1.0 + 0x1p-27;   // 1 + 2^-27
    double b = 1.0 - 0x1p-27;
    // a*b = 1 - 2^-54 exactly; but rounding a*b to double gives exactly 1.0
    double sep  = a*b - 1.0;          // -> 0.0  (a*b rounded to 1.0 first)
    double fused = fma(a, b, -1.0);   // -> -2^-54  (single rounding keeps it)
    printf("separate: %.20g\n", sep);    // 0
    printf("fused:    %.20g\n", fused);  // -5.5511151231257827021e-17
    return 0;
}
```

`fma` recovers the exact `-2^-54`; the separated form lost it to double rounding. This is why `fma(a,b,-(a*b))` extracts the exact product error.

### x87 vs SSE: the value that changes when stored

```c
// Compile 32-bit with -mfpmath=387 to observe; on x86-64 SSE this is clean.
#include <stdio.h>
int main(void) {
    volatile double x = 0.1 + 0.2;   // volatile forces a store to 64-bit memory
    double y = 0.1 + 0.2;            // may stay in an 80-bit x87 register
    printf("x == y ? %d\n", x == y); // can print 0 under x87! same source, different precision
    return 0;
}
```

The `volatile` store rounds to 64 bits; the register-held `y` may carry 80. They compare unequal — the textbook "it changes when I print it" bug.

### Reassociation under fast-math kills Kahan summation

```c
// gcc -O2            -> Kahan works
// gcc -O2 -ffast-math -> compiler "simplifies" comp to 0, accuracy lost
double kahan(const double *v, int n) {
    double sum = 0.0, comp = 0.0;
    for (int i = 0; i < n; i++) {
        double y = v[i] - comp;
        double t = sum + y;
        comp = (t - sum) - y;   // -ffast-math reassociates this to 0!
        sum = t;
    }
    return sum;
}
```

`-fassociative-math` proves `(t - sum) - y == (sum + y - sum) - y == 0` algebraically and deletes the compensation. The defense: isolate this function from fast-math, or use `volatile` on `comp`/`t`.

### Detecting NaN survives only without `-ffinite-math-only`

```c
#include <math.h>
int has_nan(const double *v, int n) {
    for (int i = 0; i < n; i++)
        if (v[i] != v[i]) return 1;   // -ffinite-math-only folds this to 'return 0'
    return 0;
}
```

### Quiet vs signaling NaN bit patterns

```python
import struct
def make_nan(signaling: bool, payload: int = 1):
    # exponent all ones; top fraction bit = quiet flag
    frac = payload & ((1 << 51) - 1)
    quiet_bit = 0 if signaling else (1 << 51)
    bits = (0x7FF << 52) | quiet_bit | (frac or 1)
    return struct.unpack('>d', struct.pack('>Q', bits))[0]

qnan = make_nan(signaling=False)
print(qnan, qnan != qnan)   # nan True
# Note: most CPUs quiet an sNaN on load; producing a *persistent* sNaN in pure
# Python is essentially impossible — this is why sNaNs are rare in practice.
```

### Decimal floating point for money

```python
from decimal import Decimal, getcontext, ROUND_HALF_EVEN
getcontext().rounding = ROUND_HALF_EVEN
price = Decimal('0.10')
total = sum((price for _ in range(10)), Decimal('0'))
print(total)            # 1.00  exactly — base-10 significand, no binary error
print(Decimal('0.1') + Decimal('0.2') == Decimal('0.3'))  # True
```

```java
import java.math.BigDecimal;
import java.math.RoundingMode;
BigDecimal price = new BigDecimal("0.10");
BigDecimal total = price.multiply(new BigDecimal(10));
System.out.println(total.setScale(2, RoundingMode.HALF_EVEN)); // 1.00
```

### Shortest round-trip vs 17-digit printing

```go
package main

import (
    "fmt"
    "strconv"
)

func main() {
    x := 0.1 + 0.2
    fmt.Println(x)                                  // 0.30000000000000004 (shortest that round-trips)
    fmt.Println(strconv.FormatFloat(x, 'g', -1, 64)) // same: -1 precision = shortest (Ryū-like)
    fmt.Println(strconv.FormatFloat(x, 'g', 17, 64)) // 0.30000000000000004 (forced 17 digits)
    fmt.Println(0.1)                                // 0.1  ← shortest, not 0.1000000000000000055
}
```

## Trade-offs

| You gain... | ...at the cost of... |
|-------------|----------------------|
| FMA accuracy + speed | Different bits than non-FMA; breaks bit-reproducibility |
| x87 80-bit intermediates | Value depends on register allocation; non-portable |
| `-ffast-math` throughput (often 2-4×) | NaN/Inf checks break, Kahan deleted, subnormals flushed, non-IEEE |
| FTZ/DAZ (no subnormal stalls) | Gradual underflow lost; tiny values snap to 0 |
| Decimal FP exactness for money | Slower, larger, software-emulated off mainframes |
| Bit-deterministic FP across nodes | Must vendor your own libm and disable FMA/reassoc — big effort |
| Shortest round-trip printing (Ryū) | More complex than `%.17g`; historically slower (Ryū fixed that) |

## Coding Patterns

### 1. Error-free transforms (TwoSum / TwoProduct)

```c
// exact sum: s = round(a+b), e = the exact rounding error, so a+b == s+e exactly
void two_sum(double a, double b, double *s, double *e) {
    *s = a + b;
    double bb = *s - a;
    *e = (a - (*s - bb)) + (b - bb);
}
// exact product via FMA:
void two_product(double a, double b, double *p, double *e) {
    *p = a * b;
    *e = fma(a, b, -*p);   // requires hardware FMA
}
```

These are the atoms of double-double / compensated arithmetic.

### 2. Pin the floating-point environment for determinism

```c
#pragma STDC FP_CONTRACT OFF        // forbid implicit FMA contraction
// build flags: -ffp-contract=off -fno-fast-math -msse2 (not -mfpmath=387)
#include <fenv.h>
fesetround(FE_TONEAREST);           // explicit default rounding
```

### 3. Quarantine fast-math to validated kernels

```c
// Only this function is fast; the rest of the TU stays strict.
__attribute__((optimize("fast-math")))
double hot_kernel(const float *a, const float *b, int n) { /* ... */ }
```

Never `-ffast-math` globally; never let it touch NaN checks or Kahan loops.

### 4. Java strictfp for reproducibility (pre-17)

```java
public strictfp class Deterministic {   // Java 17+: all FP is strict by default
    static double f(double x) { return x * x + x; }
}
```

### 5. Decimal/scaled-integer money types

```python
# scaled-integer money: store minor units (cents), do exact integer math,
# format only at the boundary. Decimal when you need division/percentages.
from decimal import Decimal
def tax(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate).quantize(Decimal('0.01'))  # explicit rounding step
```

## Best Practices

- **Decide your FP contract per module:** strict-and-portable, or fast-and-local. Document it. Never let fast-math leak project-wide.
- **Set `-ffp-contract` explicitly.** Don't let "did I get an FMA?" be implicit — it changes results.
- **Never rely on transcendental functions matching across platforms.** If you need that, vendor the implementation or use integers.
- **On x86, ensure SSE2, not x87.** Avoid `long double` if you need portability; it's 80-bit on x86, 64-bit on MSVC, 128-bit on some ARM.
- **For money, use decimal or scaled integers. Always.** Pick the rounding mode explicitly (usually HALF_EVEN, or HALF_UP for regulatory rounding).
- **Use shortest-round-trip printing for persistence**, `%.17g` only when you need guaranteed-but-verbose round-trip.
- **Use FMA-based error-free transforms** when you need extra precision without a bignum library.
- **Test numerics under the exact build flags you ship** — `-O2 -ffast-math` can pass tests that `-O0` fails, and vice versa.

## Edge Cases & Pitfalls

- **FMA flips the sign of `a*a - b*b` near `a ≈ b`** because it removes an intermediate rounding — surprising in geometry predicates.
- **Linking one fast-math object sets FTZ/DAZ process-wide** via a static initializer, silently changing unrelated subnormal behavior.
- **`long double` is a portability trap:** 80-bit (x86 Linux), 64-bit (MSVC, so identical to `double`), 128-bit (AArch64, IBM double-double on POWER). Same code, three precisions.
- **`min`/`max` with NaN are not portable across IEEE 754 revisions** — 2008's `minNum` returned the non-NaN; 2019 deprecated it for `minimum`/`maximumNumber`. C's `fmin` returns the non-NaN; `<` does not.
- **Sorting with a `<` comparator and NaN present** breaks total-order assumptions; Java throws `IllegalArgumentException` ("Comparison method violates its general contract") in some paths.
- **`0.0 == -0.0` but `1/0.0 != 1/-0.0`** — sign of zero survives through division and `atan2`, `copysign`, `signbit`.
- **`pow(x, 0.5)` is not always `sqrt(x)`** — `pow` is faithfully rounded, `sqrt` is correctly rounded; they can differ by a ULP.
- **Casting `double`→`float`→`double` is lossy and non-idempotent** for most values.
- **`printf("%g")` does not round-trip;** parsing its output can give a different double.

## Common Mistakes

1. **Global `-ffast-math`** that silently breaks NaN handling and Kahan summation somewhere far away.
2. **Assuming `sin`/`exp` are bit-identical across OSes** in a reproducibility-critical path.
3. **Using `long double` for "more precision"** without knowing it's just `double` on MSVC.
4. **Relying on FMA contraction being on (or off)** without setting `-ffp-contract`.
5. **Shipping binary floats for money** because "doubles have 15 digits, that's plenty."
6. **Comparing values that may live in 80-bit x87 registers** with `==` and getting flaky results.
7. **Trusting `%g`/`%f` to round-trip** for serialization.
8. **Flushing subnormals to zero** without realizing a static-init in a dependency already did it for you (or didn't).
9. **Writing a custom NaN-aware sort with a raw `<`** and corrupting the order.
10. **Believing IEEE 754 makes everything deterministic** — it makes `+−×÷√` deterministic; the rest is up to you.

## Tricky Points

- **Double rounding:** computing in 80-bit then storing to 64-bit can round *twice* and give a different result than a single direct 64-bit round (the "double-rounding" pathology). FMA and SSE avoid it; x87 reintroduces it.
- **`fma` without hardware support is slow** — softfloat `fma` can be 50× slower; check that your target actually has FMA before relying on it for speed.
- **Signaling NaNs rarely survive** — most loads/moves quiet them; `memcpy` preserves them, register moves may not.
- **Correctly-rounded `sqrt` but approximate `rsqrt`:** `vrsqrtps` gives ~12-bit accuracy; you must Newton-refine. Vendors' approximations differ → non-determinism.
- **`FLT_EVAL_METHOD == 2` makes `float` comparisons lie** — a `float` compared in `long double` precision passes a check it fails after assignment.
- **Java's pre-17 `strictfp`** only mattered on x87; on SSE2 it was already strict. Java 17 removed the distinction by making everything strict.
- **Decimal FP rounding has *more* modes** (round-half-up, round-half-even, round-ceiling…) and you must pick one explicitly; the default differs by library.
- **The shortest-round-trip string is not unique across formats:** a number printed shortest as a `double` may not be the shortest for the `float` that produced it.

---

## Apply it

1. State the system invariant that **Floating-Point (IEEE 754)** must protect.
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

- Which invariant must remain true when Floating-Point (IEEE 754) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
