# Floating-Point (IEEE 754) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Floating-Point (IEEE 754)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Floating Point Is Scientific Notation in Binary

You already know scientific notation: `6.022 × 10^23`. Three parts: a **sign** (positive), a **significand** (`6.022`), and an **exponent** (`23`). Floating point is exactly this, but in base 2:

```text
value = (-1)^sign  ×  1.fraction  ×  2^exponent
```

A `double` (binary64) splits its 64 bits like this:

```text
 ┌─┬───────────────┬──────────────────────────────────────────────────┐
 │S│   exponent    │                  fraction (mantissa)             │
 │1│   11 bits     │                       52 bits                    │
 └─┴───────────────┴──────────────────────────────────────────────────┘
```

A `float` (binary32) uses 1 sign + 8 exponent + 23 fraction bits. Same shape, fewer bits, less precision.

### 2. The Hidden Leading 1

Here's a clever trick. In binary scientific notation, the part before the point is always `1` (because you shift until there's exactly one non-zero digit, and in binary the only non-zero digit *is* 1). So `1.0110 × 2^3` — that leading `1` is *always there* for normal numbers. Since it's always 1, IEEE 754 **doesn't bother storing it**. It's implied. This is the "implicit leading 1," and it gives you one extra bit of precision for free. So a `double`'s 52 stored fraction bits actually act like 53 bits of significand.

### 3. The Bias on the Exponent

The exponent needs to represent both big numbers (positive exponents) and tiny numbers (negative exponents). But the bits are stored as an unsigned integer. The fix: add a **bias**. For `double`, the bias is 1023. So if you want an exponent of `3`, you store `3 + 1023 = 1026`. If you want `-4`, you store `-4 + 1023 = 1019`. To read it back, subtract the bias. This lets a simple unsigned comparison of the bits also work as a comparison of the numbers — a deliberate design choice.

### 4. Why `0.1` Is Not Representable

In base 10, `1/3 = 0.3333...` goes on forever. You can't write it exactly with finite digits. The same thing happens in base 2 for `0.1`. In binary, `0.1` is `0.0001100110011001100...` repeating forever. Since a `double` has only 52 fraction bits, it has to **stop somewhere and round**. The number actually stored for `0.1` is approximately `0.1000000000000000055511151231257827021181583404541015625`. Slightly more than `0.1`.

So when you write `0.1 + 0.2`:
- `0.1` is stored as *slightly more* than 0.1
- `0.2` is stored as *slightly more* than 0.2
- their sum rounds to *slightly more* than 0.3

And `0.30000000000000004` is what you see. The decimal you typed was never in there to begin with.

**The rule to remember:** a decimal fraction is exactly representable in binary floating point only if its denominator (in lowest terms) is a power of 2. `0.5 = 1/2` ✓, `0.25 = 1/4` ✓, `0.75 = 3/4` ✓, `0.1 = 1/10` ✗, `0.3 = 3/10` ✗.

### 5. Special Values: Zero, Infinity, NaN

IEEE 754 reserves bit patterns for special cases:

- **`+0.0` and `-0.0`** — yes, there are two zeros. They compare equal (`-0.0 == 0.0` is `true`) but they're different bit patterns, and `1.0/-0.0` gives `-Infinity` while `1.0/+0.0` gives `+Infinity`.
- **`+Infinity` and `-Infinity`** — what you get from `1.0/0.0` or when a number gets too big to store (overflow). You can do arithmetic with them: `Infinity + 1 == Infinity`, `1/Infinity == 0`.
- **`NaN` (Not a Number)** — the result of nonsense like `0.0/0.0`, `Infinity - Infinity`, or `sqrt(-1.0)`. NaN has a poisonous property: **any arithmetic with NaN produces NaN**, and **NaN is not equal to anything, including itself**. `NaN == NaN` is `false`. This is by design (and it's how you test for NaN: `x != x` is true only when `x` is NaN).

### 6. The Golden Rule: Never Compare Floats with `==`

Because floats are approximations, two values that *should* be equal often differ by a tiny amount. `0.1 + 0.2 == 0.3` is `false`. So the rule is:

**Never use `==` (or `!=`) to compare two floating-point values that came from calculations.**

Instead, check whether they're *close enough*:

```text
abs(a - b) < epsilon
```

where `epsilon` is a small tolerance you choose (often something like `1e-9` for doubles). We'll refine this in `middle.md` (absolute vs relative tolerance), but for a junior, "compare with a small tolerance" is 90% of the battle.

The exceptions where `==` is fine: comparing against exactly `0.0` when you *set* it to zero, or comparing integer-valued floats you never did arithmetic on. When in doubt, use a tolerance.

---

## Code Examples

### The `0.1 + 0.2` demo in every language

**Python:**

```python
print(0.1 + 0.2)            # 0.30000000000000004
print(0.1 + 0.2 == 0.3)     # False
print(f"{0.1:.17f}")        # 0.10000000000000001  (the real stored value)
```

**JavaScript** (every number is a `double`):

```javascript
console.log(0.1 + 0.2);          // 0.30000000000000004
console.log(0.1 + 0.2 === 0.3);  // false
```

**Java:**

```java
public class FloatDemo {
    public static void main(String[] args) {
        System.out.println(0.1 + 0.2);          // 0.30000000000000004
        System.out.println(0.1 + 0.2 == 0.3);   // false
    }
}
```

**Go:**

```go
package main

import "fmt"

func main() {
    fmt.Println(0.1 + 0.2)          // 0.30000000000000004
    fmt.Println(0.1+0.2 == 0.3)     // false
}
```

**C:**

```c
#include <stdio.h>
int main(void) {
    double a = 0.1, b = 0.2;
    printf("%.17g\n", a + b);        // 0.30000000000000004
    printf("%d\n", a + b == 0.3);    // 0
    return 0;
}
```

Every language prints the same `0.30000000000000004`, because they all use IEEE 754 binary64 and the same rounding. **The behavior is the standard, not the language.**

### Comparing floats the right way

Wrong:

```python
if total == 19.99:    # may silently never be true
    apply_discount()
```

Right — compare with a tolerance:

```python
EPSILON = 1e-9
if abs(total - 19.99) < EPSILON:
    apply_discount()
```

In Java:

```java
double EPSILON = 1e-9;
if (Math.abs(total - 19.99) < EPSILON) {
    applyDiscount();
}
```

In Go:

```go
import "math"

const epsilon = 1e-9
if math.Abs(total-19.99) < epsilon {
    applyDiscount()
}
```

### Detecting NaN and Infinity

NaN never equals itself, so the portable test is `x != x`. But every language also gives you a proper helper — prefer it:

```python
import math
x = float('nan')
print(x == x)            # False  (the trick)
print(math.isnan(x))     # True   (use this)
print(math.isinf(1e308 * 10))  # True — overflow to infinity
```

```java
double x = 0.0 / 0.0;          // NaN
System.out.println(x == x);             // false
System.out.println(Double.isNaN(x));    // true
System.out.println(Double.isInfinite(1.0 / 0.0)); // true
```

```go
import "math"
x := math.NaN()
fmt.Println(x == x)          // false
fmt.Println(math.IsNaN(x))   // true
fmt.Println(math.IsInf(1.0/0.0, 0)) // panics: integer div by zero — use math
```

> **Note for Go:** `1.0/0.0` with literal constants is a *compile error* in Go. You must compute infinity from variables or `math.Inf(1)`. This is Go protecting you.

### Seeing the two zeros

```python
print(0.0 == -0.0)            # True  (they compare equal)
import math
print(math.copysign(1, -0.0)) # -1.0  (but the sign is different!)
print(1.0 / 0.0 if False else 1.0 / -0.0 if False else "div by zero is an error in Python")
```

```c
#include <stdio.h>
int main(void) {
    double pz = 0.0, nz = -0.0;
    printf("%d\n", pz == nz);     // 1  (equal)
    printf("%g\n", 1.0 / pz);     // inf
    printf("%g\n", 1.0 / nz);     // -inf  (sign of zero matters here!)
    return 0;
}
```

### Money: don't use float

```python
# WRONG: floats for money
price = 0.10
total = 0.0
for _ in range(10):
    total += price
print(total)          # 0.9999999999999999  — not 1.0!

# RIGHT: integer cents
price_cents = 10
total_cents = sum(price_cents for _ in range(10))
print(total_cents / 100)   # 1.0  exactly, because the math was in integers
```

The lesson every junior must internalize: **never store money as a `float` or `double`.** Use integer cents, or a decimal type (`decimal.Decimal` in Python, `BigDecimal` in Java). More on this in `middle.md` and `professional.md`.

---

## Coding Patterns

### Pattern 1: Tolerance comparison helper

Write it once, use it everywhere:

```python
def close(a, b, eps=1e-9):
    return abs(a - b) < eps
```

```go
func Close(a, b float64) bool {
    const eps = 1e-9
    return math.Abs(a-b) < eps
}
```

### Pattern 2: Money as integers

```python
# store cents, never dollars
total_cents = 0
total_cents += 1099   # $10.99
total_cents += 250    # $2.50
print(f"${total_cents / 100:.2f}")   # $13.49
```

### Pattern 3: Format for display, don't round for storage

When you need 2 decimal places *for the user*, format on output. Don't try to "round the value" and keep computing with it:

```python
value = 0.1 + 0.2
print(f"{value:.2f}")   # "0.30"  — display only
# but `value` itself is still 0.30000000000000004 internally
```

### Pattern 4: Guard against NaN before it spreads

```python
import math
def safe_divide(a, b):
    if b == 0:
        return 0.0          # or raise, depending on your needs
    result = a / b
    if math.isnan(result):
        raise ValueError("computation produced NaN")
    return result
```

### Pattern 5: Prefer `double` over `float`

Unless you have a specific reason (huge arrays, GPU, memory pressure), use the 64-bit type (`double` / `float64` / `f64`). The extra precision prevents a whole class of bugs and costs little. A junior's default should be `double`.

---

## Best Practices

- **Default to `double`/`float64`.** Only drop to 32-bit `float` when memory or bandwidth demands it.
- **Never compare with `==`.** Use a tolerance. Make a `close()` helper and use it consistently.
- **Never store money as a float.** Integer cents or a decimal type.
- **Use the library NaN/Inf checks** (`isnan`, `isinf`, `Double.isNaN`), not hand-rolled bit tricks — except the `x != x` test, which is the one acceptable trick.
- **Format on output, compute in full precision.** Don't round intermediate values.
- **Be suspicious when you subtract two close numbers** — error can blow up (you'll learn why in `middle.md`).
- **Read the printed value with `%.17g`** when debugging — it shows the true stored value, not the friendly rounded display.
- **When summing many numbers, be aware order matters** — `(a+b)+c` can differ from `a+(b+c)`. (More in `middle.md`.)

---

## Edge Cases & Pitfalls

- **`0.1 + 0.2 != 0.3`** — the canonical surprise. Not a bug; the inputs aren't representable.
- **`NaN == NaN` is `false`.** A list containing NaN can't be de-duplicated with normal equality, and sorting a list with NaN can corrupt the sort order in some languages.
- **`-0.0 == 0.0` is `true`, but `1/-0.0` is `-Infinity`.** Sign of zero is invisible to `==` but visible to division.
- **Accumulating a float in a loop drifts.** Adding `0.1` ten times does not give `1.0`.
- **Large integers lose precision as doubles.** A `double` can hold integers exactly only up to 2^53 (≈ 9 quadrillion). Beyond that, `9007199254740993.0 == 9007199254740992.0` can be `true`. This bites JavaScript hard, since *all* its numbers are doubles.
- **Printing hides the truth.** `print(0.1)` shows `0.1`, but the stored value is `0.1000000000000000055...`. The printer rounds to the shortest string that reads back as the same double.
- **Comparing a `float` and a `double` of "the same" value can fail** — `(float)0.1 != (double)0.1` because they round to different dots.
- **`Math.sqrt(-1)` doesn't crash — it returns NaN** (in most languages). Your program keeps running with poison in it.

---

## Common Mistakes

1. **`if (price == 19.99)`.** Use a tolerance. This is the #1 float bug juniors write.
2. **Using `float`/`double` for currency.** Switch to integer cents or `BigDecimal`/`Decimal`.
3. **Assuming a sum of floats equals the obvious total.** Loop accumulation drifts.
4. **Testing NaN with `==`.** Use `isnan()`. `x == NaN` is always false, so the check never fires.
5. **Storing a giant integer in a `double` and expecting exactness** beyond 2^53.
6. **Rounding a value and continuing to compute with the rounded one** instead of formatting only at display time.
7. **Forgetting that division by zero gives Infinity (or NaN), not a crash**, in float math — so a bug silently spreads.
8. **Comparing `float` to `double`** without realizing they store the value differently.
9. **Believing the printed value is the stored value.** Print with `%.17g` to see reality.
10. **Mixing up `0.0` and `-0.0`** when the sign of a zero secretly matters (e.g., in `atan2` or division).

---

## Apply it

1. Choose one small, known input for **Floating-Point (IEEE 754)**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Floating-Point (IEEE 754) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
