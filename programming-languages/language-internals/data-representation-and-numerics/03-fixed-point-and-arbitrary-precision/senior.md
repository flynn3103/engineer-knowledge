# Fixed-Point & Arbitrary Precision — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Fixed-Point & Arbitrary Precision** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Limb Representation

A bignum stores a magnitude as an array of limbs (words) in radix `B = 2^w` (w = 32 or 64), plus a sign and a length:

```
struct BigInt {
    int sign;        // -1, 0, +1
    size_t len;      // number of significant limbs
    uint64_t *limbs; // little-endian: limbs[0] is least significant
};
```

The value is `sign · Σ limbs[i] · B^i`. Most libraries keep numbers **normalized** (no leading zero limbs; a single canonical zero) so comparison and equality are cheap. Add and subtract are O(n) limb-walks with carry/borrow. The interesting cost is **multiplication and division**.

### 2. The Multiplication Ladder and the Cost Model

**Schoolbook (O(n²)).** For n-limb operands, multiply each limb of `a` by each limb of `b`, shifting and accumulating with carries. n² limb-multiplies. The constant factor is small and cache-friendly, so for small n (a few limbs) this *wins*. Every library uses it below its first threshold.

**Karatsuba (O(n^1.585)).** Split each operand into high/low halves: `a = a₁·B^k + a₀`, `b = b₁·B^k + b₀`. The naïve product needs four half-multiplies (`a₁b₁`, `a₁b₀`, `a₀b₁`, `a₀b₀`). Karatsuba's trick computes the middle term from the other two:

```
z2 = a1*b1
z0 = a0*b0
z1 = (a0+a1)*(b0+b1) - z2 - z0     // one multiply instead of two
result = z2·B^(2k) + z1·B^k + z0
```

Three half-size multiplies → recurrence `T(n) = 3·T(n/2) + O(n)` → O(n^log₂3). The extra additions cost something, so Karatsuba only beats schoolbook above a crossover (often ~20–40 limbs in GMP).

**Toom-Cook (Toom-3 ≈ O(n^1.465)).** Split into 3 (or more) parts, evaluate the operand polynomials at several points, multiply pointwise (5 multiplies for Toom-3), then interpolate. Lower exponent, but more overhead, so it wins only above a *higher* threshold than Karatsuba.

**FFT (Schönhage–Strassen, O(n log n log log n)).** Treat the digits as coefficients of a polynomial; multiplication is convolution; convolution is pointwise multiply in the frequency domain via FFT. The asymptotic champion, but the constant factor and memory are large, so it only wins for *very* large numbers (tens of thousands of bits and up — e.g., computing π to billions of digits).

The cost model in one line: **bignum multiply of two n-limb numbers is roughly O(n^1.585) in practice** (Karatsuba range) for "big but not astronomical" inputs, **and definitely not O(1).** That last fact is the source of most performance surprises.

### 3. Division, Modulo, and Modular Exponentiation

Division is harder than multiplication and is the bottleneck in modular arithmetic. Schoolbook long division is O(n·m). For cryptography you do `a^b mod m` thousands of times, so libraries avoid raw division per step:

- **Square-and-multiply** turns `a^b` into O(log b) multiplications.
- **Montgomery reduction** replaces each `mod m` with shifts/multiplies in a transformed domain — no trial division.
- **Barrett reduction** precomputes a reciprocal of `m` to turn `mod` into multiply-and-shift.

RSA-2048 signature verification, Diffie-Hellman, and ECC scalar multiplication all live and die by how fast these run.

### 4. Arbitrary-Precision Rationals

A rational `Rat` is two bignums `p/q` kept coprime via GCD after every operation:

```
a/b + c/d = (a·d + c·b) / (b·d)   then divide both by gcd(numerator, denominator)
```

Rationals are *exact* — no rounding ever — which is wonderful for exact geometry, computer algebra, and symbolic math. The trap: **denominators blow up.** Adding many rationals, or iterating a fraction-producing recurrence, makes `p` and `q` grow without bound; each GCD is itself a bignum operation. An "exact" rational loop can go from milliseconds to minutes as the fractions balloon. Use rationals only where you genuinely need exactness *and* the denominators stay bounded, or cap them deliberately.

### 5. Decimal Floating Point (IEEE 754 `decimal64`/`decimal128`)

Distinct from `BigDecimal`: hardware/standard **decimal floating point** stores a base-10 significand and a base-10 exponent in a fixed width (64 or 128 bits), giving exact representation of decimal fractions with *bounded* precision (16 or 34 significant digits). IBM POWER and z/Architecture have hardware decimal FP; C has `_Decimal64`/`_Decimal128` (TR 24732), and it's used heavily in financial/COBOL-adjacent systems. It sits between fixed-width binary floats (fast, inexact for decimals) and arbitrary `BigDecimal` (exact, unbounded, slow): exact for decimals, but fixed-width and therefore fast and overflow-bounded.

### 6. Where Bignums Silently Kill Performance

The recurring senior incident: an algorithm that's O(n) *assuming O(1) arithmetic* becomes O(n²) because the numbers themselves grow to O(n) digits.

- **Accumulating a product/factorial in a loop:** `prod *= i` where `prod` grows to n·log n digits — total work is O(n²) limb operations, not O(n).
- **Fibonacci by naive iteration:** `F(n)` has ~n bits, so each addition is O(n); computing up to `F(n)` is O(n²).
- **Python ints in a hot numeric loop:** every value is a bignum; small-int caching helps, but once values exceed one limb you pay allocation and limb-walking per operation, with no SIMD.
- **Immutability churn:** Java `BigInteger` and Go `big.Int` (when used immutably) allocate a fresh object per operation — a tight loop becomes an allocator and GC stress test. (Go lets you mutate a receiver to avoid this.)

The fix is to *expect* non-constant arithmetic, reuse buffers, and check whether a closed-form or modular-reduced approach keeps the operands small.

---

## Code Examples

### Karatsuba multiplication (illustrative, Python)

```python
def karatsuba(x: int, y: int) -> int:
    if x < 1 << 64 or y < 1 << 64:        # base case: small enough, use native
        return x * y
    n = max(x.bit_length(), y.bit_length())
    k = (n // 2)
    high_x, low_x = x >> k, x & ((1 << k) - 1)
    high_y, low_y = y >> k, y & ((1 << k) - 1)
    z2 = karatsuba(high_x, high_y)
    z0 = karatsuba(low_x, low_y)
    z1 = karatsuba(low_x + high_x, low_y + high_y) - z2 - z0
    return (z2 << (2 * k)) + (z1 << k) + z0
```

### The quadratic-factorial trap and a quick measurement (Python)

```python
import time

def factorial_loop(n: int) -> int:
    p = 1
    for i in range(2, n + 1):
        p *= i          # p grows to ~n*log2(n) bits: each multiply is NOT O(1)
    return p

# Doubling n roughly quadruples the time -> O(n^2)-ish, not O(n).
for n in (20000, 40000, 80000):
    t = time.perf_counter()
    factorial_loop(n)
    print(n, round(time.perf_counter() - t, 3), "s")
```

### Modular exponentiation, square-and-multiply (Go, math/big)

```go
package main

import (
    "fmt"
    "math/big"
)

func main() {
    base := new(big.Int).SetInt64(7)
    exp  := new(big.Int).SetInt64(1 << 20)
    mod  := new(big.Int)
    mod.SetString("32317006071311007300714876688669951960444102669715484032130345427524655138867", 10)

    // big.Int.Exp implements fast modular exponentiation (square-and-multiply + reduction)
    result := new(big.Int).Exp(base, exp, mod)
    fmt.Println(result)
}
```

### Reusing buffers to avoid allocation churn (Go)

```go
// Immutable style allocates a new big.Int each iteration:
//   sum = new(big.Int).Add(sum, term)   // garbage every loop
// Mutating receiver style reuses storage:
func sumTerms(terms []*big.Int) *big.Int {
    acc := new(big.Int)
    for _, t := range terms {
        acc.Add(acc, t) // writes into acc, no per-iteration allocation
    }
    return acc
}
```

### Arbitrary-precision rationals and the blow-up (Python Fraction)

```python
from fractions import Fraction

# Exact, but watch the denominator grow:
total = Fraction(0)
for k in range(1, 30):
    total += Fraction(1, k)     # harmonic sum; denominator = lcm(1..k), explodes
print(total.denominator.bit_length(), "bits in the denominator")
```

---

## Coding Patterns

**Pattern 1 — "Trust the library's cascade; don't hand-roll multiply."** GMP/`BigInteger`/`math/big` already pick schoolbook/Karatsuba/Toom/FFT optimally. Reimplement only to *learn*.

**Pattern 2 — "Keep operands small with modular reduction."** In crypto and number theory, reduce mod `m` early and often so values stay bounded; use Montgomery/Barrett for the hot loop.

**Pattern 3 — "Reuse receivers in mutable-bignum languages."** In Go, write into a destination `big.Int`; in Java, batch operations or use primitive paths when values fit a `long`.

**Pattern 4 — "Bound or avoid rationals."** Prefer fixed-scale decimals unless exact fractions are essential; if you must use rationals, cap denominators or periodically convert.

**Pattern 5 — "Use constant-time primitives for secrets."** Reach for vetted crypto libraries (`crypto/internal`, BoringSSL, libsodium), not generic bignum ops, on secret-dependent paths.

---

## Best Practices

1. **Re-analyze complexity assuming non-O(1) arithmetic** whenever numbers can exceed one machine word.
2. **Profile the actual operand-size distribution.** A library tuned for huge numbers may be slow for your "merely large" ones, and vice versa.
3. **Minimize allocations in bignum loops** (mutable receivers, buffer reuse, primitive fast paths).
4. **Never write your own modular exponentiation for production crypto.** Use audited, constant-time libraries.
5. **Prefer decimals over rationals** for money/measurement; reserve rationals for genuine exactness needs with bounded denominators.
6. **Choose decimal FP (`decimal128`) when you need bounded, exact decimal at speed** and your platform supports it.
7. **Watch for hidden bignums in "dynamic" languages.** Python/JS BigInt semantics can turn a simple loop quadratic without warning.

---

## Edge Cases & Pitfalls

- **O(n²) creep from growing operands:** factorials, products, Fibonacci, harmonic sums. The numbers, not the loop count, dominate.
- **Allocation storms:** immutable `BigInteger`/`big.Int` in tight loops thrash the allocator and GC.
- **Crossover misfires:** if most of your inputs sit just below a library threshold, you pay the slower algorithm; conversely, hand-tuned thresholds can regress after a library upgrade.
- **Timing side channels:** secret-dependent branches or variable-time multiplies leak key bits; even cache access patterns can leak. This is a *correctness* failure for crypto.
- **Rational denominator explosion:** exact fraction loops silently balloon memory and time; a "fast exact" approach becomes the slowest path.
- **Decimal FP overflow/rounding:** `decimal64`/`decimal128` are *fixed* width — they still round and can overflow, unlike `BigDecimal`.
- **Base conversion cost:** converting a huge bignum to/from a decimal string is *itself* super-linear (each division by 10 is O(n)); printing a million-digit number naively is slow. Libraries use divide-and-conquer base conversion.
- **`big.Float` is not decimal-exact:** Go's `big.Float` is arbitrary-precision *binary* floating point — it still can't represent 0.1 exactly. Use `big.Rat` or a decimal library for exact base-10.

---

## Apply it

1. State the system invariant that **Fixed-Point & Arbitrary Precision** must protect.
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

- Which invariant must remain true when Fixed-Point & Arbitrary Precision fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
