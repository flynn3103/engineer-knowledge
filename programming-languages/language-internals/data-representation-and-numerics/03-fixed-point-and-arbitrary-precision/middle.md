# Fixed-Point & Arbitrary Precision — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Fixed-Point & Arbitrary Precision** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Q-Notation: The Decimal Point in Binary

Embedded and DSP code often can't afford floating-point hardware, so it uses **binary fixed-point**. The format is **Qm.n**: split an integer's bits into `m` integer bits and `n` fraction bits. The real value is `stored_integer / 2^n`.

- `Q16.16` in a 32-bit int: top 16 bits are the integer part, bottom 16 are the fraction. Scale = `2^16 = 65536`. The value `1.5` is stored as `1.5 * 65536 = 98304`.
- `Q8.24`: more fractional precision, smaller integer range.

To convert: `to_fixed(x) = round(x * 2^n)`; `to_real(f) = f / 2^n`.

**Addition and subtraction** of two same-format Q values is just integer add/subtract — the scales already match. Easy.

### 2. Fixed-Point Multiplication: The Rescale and the Overflow

Here's the crux. If `a` and `b` are both `Qm.n` (scale `S = 2^n`), then as integers `a = A·... ` — more precisely `a_real = A/S` and `b_real = B/S`. Their product:

```
a_real * b_real = (A/S) * (B/S) = (A*B) / S^2
```

But you want the result back in `Qm.n` (scale `S`), so you must **divide the integer product by S once**:

```
result_int = (A * B) / S        // = (A * B) >> n  for Q with n fraction bits
```

Two things follow:

1. **The intermediate `A * B` needs double the bits.** Two 32-bit `Q16.16` values multiply to a number that can need **64 bits** before the shift. If you do `(int32_t)(A * B) >> 16` in C, the multiply overflows *first* and you get garbage. The fix: widen the intermediate. `((int64_t)A * B) >> 16`, then narrow back to 32. On systems with 64-bit fixed-point, you reach for `__int128` as the intermediate.

2. **Division mirrors this.** `a_real / b_real = (A/S)/(B/S) = A/B` — which *loses* the scale, so you must multiply the numerator first: `result_int = (A << n) / B`, again needing a wider intermediate for `A << n`.

This "widen for the intermediate, then rescale" is the single most important fixed-point skill.

### 3. Decimal Types: Scale, Precision, and the Unscaled Integer

A decimal type like Java's `BigDecimal` or Python's `Decimal` is, internally, an **arbitrary-precision integer plus a scale**:

```
value = unscaledValue * 10^(-scale)
BigDecimal("1.23")  ->  unscaled = 123, scale = 2
BigDecimal("1.230") ->  unscaled = 1230, scale = 3   (different object! same value, different scale)
```

This is why `new BigDecimal("1.23").equals(new BigDecimal("1.230"))` is **false** in Java (`equals` compares scale too) but `.compareTo(...) == 0` is **true** (compareTo is value-only). A classic gotcha.

- **Scale** controls how many fractional digits. Operations have defined scale rules: `add`/`subtract` take the *max* scale of the operands; `multiply` *adds* the scales (1.2 [scale 1] × 1.2 [scale 1] = 1.44 [scale 2]); `divide` can produce a non-terminating result and therefore **requires** you to specify a scale and rounding mode or it throws `ArithmeticException`.
- **Precision** is total significant digits. Java's `MathContext` lets you cap precision (e.g., `MathContext(7, RoundingMode.HALF_EVEN)` keeps 7 significant digits).

Python's `Decimal` uses a global/thread-local **context** (`getcontext()`) carrying precision (default 28 significant digits) and rounding mode.

### 4. Rounding Modes: Who Gets the Half?

When a value lands exactly between two representable numbers (a *tie*, like 2.5 rounding to an integer), the rounding mode decides:

| Mode | 0.5 | 1.5 | 2.5 | -0.5 | Use when |
|------|-----|-----|-----|------|----------|
| **HALF_UP** | 1 | 2 | 3 | -1 | Human-facing "round half up" (taxes in some jurisdictions) |
| **HALF_EVEN** (banker's) | 0 | 2 | 2 | 0 | Statistical/financial sums — **unbiased**, the IEEE-754 default |
| **HALF_DOWN** | 0 | 1 | 2 | 0 | Rarely; ties toward zero |
| **FLOOR** | toward −∞ | | | | Always round down |
| **CEILING** | toward +∞ | | | | Always round up (e.g., billing units you can't fractionally sell) |
| **DOWN** | truncate toward 0 | | | | Truncation |
| **UP** | away from 0 | | | | Always grow the magnitude |

**Why banker's rounding (HALF_EVEN) matters:** if you always round 0.5 *up*, then over many numbers you systematically inflate the total — a tiny upward bias that, across millions of line items, becomes real money in one direction. HALF_EVEN sends ties up half the time and down half the time, so the bias cancels. That's why it's the default in IEEE 754 and in many accounting standards. **But** some tax authorities legally mandate HALF_UP. There is no universal "correct" mode — there is only "the mode your domain/regulator specifies." Hard-code it explicitly; never rely on a default.

### 5. Allocation: Making the Pennies Add Up

Split $100 (10000 cents) among 3 parties. `10000 / 3 = 3333` cents with remainder `1`. If you give everyone `3333`, you've distributed `9999` — **one cent vanished**. You can't return $33.33 three times and claim it's $100.

The fix is an **allocation algorithm** (Fowler's "Money allocate"): compute the base share, then hand out the leftover remainder one minor unit at a time:

```
total = 10000, n = 3
base = total // n = 3333
remainder = total - base*n = 1
shares = [3333, 3333, 3333]
# distribute the 1 leftover cent to the first `remainder` shares:
shares = [3334, 3333, 3333]   # sums to exactly 10000
```

For weighted/ratio splits (e.g., allocate by 1:1:1 or by a tax breakdown), the same principle holds: compute each share by rounding *down*, then distribute the leftover units to the shares with the largest fractional remainders (largest-remainder method). The invariant is sacred: **the parts must sum to the whole.** Never round each share independently and hope.

---

## Code Examples

### Fixed-point Q16.16 multiply with safe intermediate (C)

```c
#include <stdint.h>

#define FRAC_BITS 16
#define SCALE     (1 << FRAC_BITS)   // 65536

typedef int32_t fixed_t;             // Q16.16

static inline fixed_t fx_from_double(double x) { return (fixed_t)(x * SCALE); }
static inline double  fx_to_double(fixed_t f)  { return (double)f / SCALE; }

static inline fixed_t fx_add(fixed_t a, fixed_t b) { return a + b; }

// WRONG: (a * b) overflows int32 before the shift.
// RIGHT: widen to int64 for the intermediate, then rescale.
static inline fixed_t fx_mul(fixed_t a, fixed_t b) {
    int64_t product = (int64_t)a * (int64_t)b; // up to 64 bits
    return (fixed_t)(product >> FRAC_BITS);     // rescale back to Q16.16
}

static inline fixed_t fx_div(fixed_t a, fixed_t b) {
    int64_t numerator = (int64_t)a << FRAC_BITS; // widen before dividing
    return (fixed_t)(numerator / b);
}
```

### BigDecimal: scale, equals vs compareTo, and division (Java)

```java
import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

BigDecimal a = new BigDecimal("1.23");   // unscaled 123, scale 2
BigDecimal b = new BigDecimal("1.230");  // unscaled 1230, scale 3

System.out.println(a.equals(b));        // false  (scale differs!)
System.out.println(a.compareTo(b) == 0); // true   (value equal)

// Division can be non-terminating -> MUST specify scale + rounding, else ArithmeticException
BigDecimal x = new BigDecimal("10");
BigDecimal y = new BigDecimal("3");
// x.divide(y);                          // throws: non-terminating decimal expansion
BigDecimal q = x.divide(y, 4, RoundingMode.HALF_EVEN); // 3.3333

// Cap significant digits with a MathContext:
BigDecimal r = x.divide(y, new MathContext(5, RoundingMode.HALF_EVEN)); // 3.3333
```

### Python Decimal: context, rounding mode, quantize

```python
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, ROUND_HALF_UP

getcontext().prec = 28  # significant digits for the context

price = Decimal("19.99")
tax_rate = Decimal("0.0825")
tax = (price * tax_rate)                       # 1.649175
# quantize() rounds to a fixed number of decimal places, with an explicit mode:
tax_2dp = tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)  # 1.65
print(tax_2dp)

# Compare rounding modes on a tie:
half = Decimal("2.5")
print(half.quantize(Decimal("1"), ROUND_HALF_UP))    # 3
print(half.quantize(Decimal("1"), ROUND_HALF_EVEN))  # 2
```

### Penny allocation (largest-remainder), Python

```python
def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """Split total_cents by weights so the parts sum EXACTLY to total_cents."""
    w_sum = sum(weights)
    # floor share + fractional remainder for each part
    raw = [(total_cents * w) // w_sum for w in weights]
    remainders = [(total_cents * w) % w_sum for w in weights]
    distributed = sum(raw)
    leftover = total_cents - distributed       # whole cents still to assign
    # give leftover cents to the parts with the largest remainders
    order = sorted(range(len(weights)), key=lambda i: remainders[i], reverse=True)
    for i in order[:leftover]:
        raw[i] += 1
    return raw

print(allocate(10000, [1, 1, 1]))  # [3334, 3333, 3333] -> sums to 10000
print(allocate(10005, [1, 1, 1]))  # [3335, 3335, 3335] -> sums to 10005
```

### Go: fixed-point cents multiply by a rate, rounding half-even

```go
// Multiply integer cents by a rate given as basis points (1bp = 0.0001).
// e.g. 825 bp = 8.25%. Use a wide intermediate, then round half-even.
func applyRate(cents int64, basisPoints int64) int64 {
    num := cents * basisPoints       // intermediate (could be large; int64 usually ok)
    // we want num / 10000, rounded half-even
    q := num / 10000
    r := num % 10000
    if twice := 2 * r; twice > 10000 || (twice == 10000 && q%2 != 0) {
        q++
    }
    return q
}
```

---

## Coding Patterns

**Pattern 1 — "Wide intermediate, then rescale."** Every fixed-point multiply/divide: promote to a wider type, do the op, rescale, narrow. Encapsulate it so callers can't forget.

**Pattern 2 — "Round once, at quantize time."** Keep full precision through the calculation; call `quantize`/`setScale` exactly once, at the end, with an explicit mode.

**Pattern 3 — "Allocate, don't divide-and-round."** Whenever a total is split, route it through an `allocate()` function that conserves the sum.

**Pattern 4 — "Carry the rounding policy in the type/config."** Make the rounding mode a field on your Money/Calculator, not a literal scattered through the codebase, so it's set once and audited in one place.

**Pattern 5 — "compareTo for value equality."** With `BigDecimal`, use `compareTo(...) == 0` for "same amount"; reserve `equals` for when scale matters too.

---

## Best Practices

1. **Always widen the intermediate in fixed-point multiply/divide.** `int64` intermediate for `Q16.16`; `__int128` for 64-bit fixed-point.
2. **Specify scale and rounding mode on every decimal division.** Don't let the default throw or surprise you.
3. **Choose the rounding mode from the domain, not the default.** HALF_EVEN for unbiased sums; HALF_UP where law requires; document which and why.
4. **Use allocation for every split.** Test the invariant `sum(parts) == total` explicitly.
5. **Round exactly once, at the boundary.** Intermediate rounding accumulates error.
6. **Mind `BigDecimal.equals` vs `compareTo`.** They differ on scale; pick deliberately, especially as map keys or in tests.
7. **Pick the right minor-unit scale per currency.** 2 for USD, 0 for JPY, sometimes 3–4 for crypto or FX.

---

## Edge Cases & Pitfalls

- **Intermediate overflow in fixed-point multiply.** `(int32_t)(a*b) >> 16` overflows before the shift. The bug only appears for large operands, so small-input tests pass.
- **`BigDecimal.divide` with no scale throws.** `10.divide(3)` raises `ArithmeticException: Non-terminating decimal expansion`. Always pass a scale/MathContext.
- **`equals` mismatch from scale.** `"2.0".equals("2.00")` is false. This breaks `HashSet`/`HashMap` membership and naive test assertions. Use `compareTo` or normalize scale first.
- **Multiply doubles the scale.** `1.23 (s=2) × 1.23 (s=2) = 1.5129 (s=4)`. If your column is scale 2, you must round after, deliberately.
- **Rounding-mode mismatch with a regulator.** Using HALF_EVEN where the tax authority mandates HALF_UP produces small, systematic discrepancies that fail audit.
- **Allocation forgotten on weighted splits.** Independently rounding a 70/30 split of an odd amount can lose or duplicate a cent. Route through `allocate`.
- **Negative numbers and rounding.** HALF_UP rounds −2.5 to −3 (away from zero); FLOOR rounds it to −3 but rounds −2.4 to −3 too. Know the direction for refunds/credits.
- **Python context is thread-local and mutable.** Changing `getcontext().prec` globally can surprise other code. Prefer `localcontext()` for scoped changes.

---

## Apply it

1. Find a real component where **Fixed-Point & Arbitrary Precision** affects an interface or dependency.
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

- Which boundary is most affected by Fixed-Point & Arbitrary Precision?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
