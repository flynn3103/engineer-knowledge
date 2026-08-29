# Fixed-Point & Arbitrary Precision — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Fixed-Point & Arbitrary Precision** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Binary Floats Cannot Hold 0.1

Your computer stores `double` values in **binary**. In binary, the only fractions that are exact are sums of `1/2, 1/4, 1/8, 1/16, ...` So `0.5` is exact (it's `1/2`). `0.25` is exact. But `0.1`? There is no finite sum of halves, quarters, and eighths that equals exactly 0.1 — it's a repeating binary fraction, the same way `1/3 = 0.3333...` repeats in decimal. The computer keeps about 15–16 significant decimal digits and rounds the rest away.

So when you write `0.1` in your code, the value actually stored is approximately `0.1000000000000000055511151231257827021181583404541015625`. Tiny error. But `0.1 + 0.2` produces a value whose nearest stored double is `0.30000000000000004`, and now the error is visible. Multiply that by a million transactions and the errors stop being invisible.

The key sentence: **a binary float can represent any power-of-two fraction exactly and almost nothing else exactly.** Money is in base 10. Base 10 and base 2 do not mix cleanly.

### 2. Fixed-Point: Store Money as Integers

The oldest, simplest, fastest fix: **don't store dollars, store cents.** $19.99 becomes the integer `1999`. $0.01 becomes `1`. Now:

- Addition is exact: `1999 + 1 = 2000` (= $20.00). No rounding, ever.
- There is no "0.1 problem" because integers have no fractional part to mess up.
- It's just integer math, which CPUs do perfectly and instantly.

This is **fixed-point**: a number with a fractional value, stored as an integer, with the position of the decimal point *fixed* and *implicit*. You — the programmer — remember "this integer is in cents." The computer just sees an integer.

The catch: you must be consistent and you must be careful at the boundaries (multiplication and division need extra thought — covered below and in `middle.md`).

### 3. Decimal Types: Base-10 Arithmetic on Demand

Sometimes you want fractions but cents aren't enough — currency conversion, tax at 8.25%, interest at 3.7% APR. For these, languages provide a **decimal type** that does arithmetic in base 10 *exactly*, carrying as many digits as you ask for.

```python
from decimal import Decimal
Decimal("0.1") + Decimal("0.2")   # -> Decimal('0.3')   exactly!
```

`Decimal("0.3")` is the *exact* value 0.3, because it stores the digits `3` and the scale (one place after the point) directly, in base 10. No binary approximation. The price you pay: it's slower than a hardware `double` (it's software, not a CPU instruction). For money, that's almost always a fine trade.

### 4. Arbitrary-Precision Integers (Bignums)

A normal 64-bit integer maxes out at about 9.2 quintillion (`9,223,372,854,775,807`). Add one more and it **overflows** — in C/Java/Go it silently wraps to a negative number; the result is wrong.

A **bignum** (big integer) has no such limit. It stores the number across as many machine words as needed and grows automatically. Compute `2^1000` or `100!` (the factorial of 100, a 158-digit number) and a bignum gives you the **exact** answer.

```python
2 ** 1000   # Python: a 302-digit exact integer, no overflow
```

Different languages handle this very differently, and this is a frequent source of confusion:

- **Python:** every `int` is *already* a bignum. You never overflow. (You also pay a little speed for it.)
- **JavaScript:** numbers are doubles; you must use the `BigInt` type (`10n`) explicitly.
- **Java:** `int`/`long` overflow silently; use `BigInteger` for unbounded.
- **Go:** `int64` overflows silently; use `math/big.Int`.
- **C/C++/Rust:** overflow on fixed-size types; use a library (GMP, `num-bigint`) for bignums.

### 5. Three Tools, Three Jobs

It's easy to confuse these. Keep them straight:

| You need... | Use |
|-------------|-----|
| Exact money with a fixed number of decimals (cents) | **Fixed-point integers** (store cents) |
| Exact decimal math with flexible precision (tax, interest) | **Decimal type** (`BigDecimal`, `Decimal`) |
| Huge whole numbers that never overflow (factorials, crypto, IDs) | **Bignum** (`BigInteger`, Python `int`, `BigInt`) |

---

## Code Examples

### The bug, in five languages

The classic float-money bug looks identical everywhere:

```python
# Python
price = 0.1
total = price * 3          # 0.30000000000000004
print(total == 0.3)        # False  ← would fail an equality check
```

```javascript
// JavaScript
console.log(0.1 + 0.2);          // 0.30000000000000004
console.log(0.1 + 0.2 === 0.3);  // false
```

```java
// Java
double total = 0.1 + 0.2;        // 0.30000000000000004
System.out.println(total == 0.3); // false
```

```go
// Go
package main
import "fmt"
func main() {
    fmt.Println(0.1 + 0.2)        // 0.30000000000000004
}
```

```c
// C
#include <stdio.h>
int main(void) {
    printf("%.17f\n", 0.1 + 0.2); // 0.30000000000000004
    return 0;
}
```

### Fix 1 — Fixed-point: store cents (works in any language)

```go
// Go — money as int64 cents. Exact, fast, no surprises.
package main

import "fmt"

func main() {
    var priceCents int64 = 1999 // $19.99
    var qty int64 = 3
    total := priceCents * qty // 5997 cents = $59.97, exact
    fmt.Printf("$%d.%02d\n", total/100, total%100) // $59.97
}
```

```python
# Python — same idea, integer cents
price_cents = 1999
total = price_cents * 3          # 5997, exact
dollars, cents = divmod(total, 100)
print(f"${dollars}.{cents:02d}") # $59.97
```

### Fix 2 — Decimal type (when cents aren't enough)

```python
# Python Decimal — exact base-10 arithmetic
from decimal import Decimal

price = Decimal("19.99")
qty = Decimal("3")
print(price * qty)               # 59.97  (exact)
print(Decimal("0.1") + Decimal("0.2"))  # 0.3  (exact!)
```

```java
// Java BigDecimal — ALWAYS construct from a String, never a double
import java.math.BigDecimal;

BigDecimal price = new BigDecimal("19.99");   // exact
BigDecimal qty   = new BigDecimal("3");
System.out.println(price.multiply(qty));      // 59.97

// WRONG: new BigDecimal(0.1) captures the binary error -> 0.1000000000000000055...
// RIGHT: new BigDecimal("0.1")  is exactly 0.1
```

### Fix 3 — Bignum (numbers that never overflow)

```python
# Python: int is already a bignum
print(2 ** 100)      # 1267650600228229401496703205376  (exact, 31 digits)
import math
print(math.factorial(50))  # exact 65-digit number
```

```java
// Java: BigInteger
import java.math.BigInteger;
BigInteger big = BigInteger.TWO.pow(100); // exact
System.out.println(big);                  // 1267650600228229401496703205376
```

```javascript
// JavaScript: BigInt with the `n` suffix
console.log(2n ** 100n); // 1267650600228229401496703205376n
console.log(9007199254740993n);          // exact; a plain Number can't hold this
```

```go
// Go: math/big
package main
import (
    "fmt"
    "math/big"
)
func main() {
    big1 := new(big.Int).Exp(big.NewInt(2), big.NewInt(100), nil)
    fmt.Println(big1) // 1267650600228229401496703205376
}
```

---

## Coding Patterns

**Pattern 1 — "Money is an integer count of minor units."** Pick the smallest unit (cents) and store everything as a whole number of them. Convert to a display string only when showing the user.

```python
def format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100}.{cents % 100:02d}"
```

**Pattern 2 — "Parse decimal input to cents safely."** Don't multiply a parsed float by 100 (that re-introduces float error). Parse with a decimal type, then convert.

```python
from decimal import Decimal
def to_cents(s: str) -> int:
    return int((Decimal(s) * 100).to_integral_value())  # "19.99" -> 1999
```

**Pattern 3 — "Construct decimals from strings, never from floats."** `Decimal("0.1")` is exact; `Decimal(0.1)` captures the binary error. Same warning for Java's `new BigDecimal("0.1")` vs `new BigDecimal(0.1)`.

**Pattern 4 — "A Money type, not a bare int."** Wrap the integer (and a currency code) in a small type/class so you can't accidentally add cents to dollars, or USD to EUR.

---

## Best Practices

1. **Never use `float`/`double` for money.** Not for storage, not for arithmetic, not even "just temporarily." This is the rule.
2. **Pick one representation per system and document it.** "All money is `int64` cents" or "all money is `BigDecimal` with scale 2." Mixing causes bugs.
3. **Construct decimals from strings.** `Decimal("0.1")`, `new BigDecimal("0.1")`. Never from a `double`.
4. **Round only at the boundary** (display, settlement, persistence to a fixed-scale column) — not in the middle of a calculation.
5. **Know your language's default.** Python ints are bignums (no overflow); Java/Go/C ints overflow silently. This changes which bugs you can hit.
6. **Don't compare floats (or money) with `==`.** For floats, compare within a tolerance. For money, use exact integer/decimal equality (which is safe *because* it's exact).
7. **Use the currency's real minor unit.** USD = 2 decimals, JPY = 0, some currencies/markets need 3 or 4. Hard-coding "always 2 decimals" is a bug for JPY.

---

## Edge Cases & Pitfalls

- **Constructing a decimal from a float.** `new BigDecimal(0.1)` in Java gives `0.1000000000000000055511151231257827021181583404541015625` — the binary error, captured forever. Always use the string constructor.
- **Multiplying two cent-values.** `priceCents * priceCents` gives "square cents," which is meaningless. Multiplication changes the scale; only multiply money by a *plain* quantity, and rescale carefully for percentages (see `middle.md`).
- **Float-to-int conversion truncates, not rounds.** `int(19.99 * 100)` in many languages gives `1998`, not `1999`, because `19.99 * 100` is actually `1998.9999...` in binary. Round explicitly, or parse with a decimal.
- **Silent integer overflow.** In C/Java/Go, a sum of money in `int64` *can* overflow for huge aggregates (national-scale totals in a tiny minor unit). It wraps to negative silently. Check, or use bignums/decimals.
- **JavaScript's `Number` can't hold all integers.** Past `2^53` (`9007199254740992`), plain JS numbers lose precision. Use `BigInt` for large integer IDs. A user ID arriving as JSON can silently corrupt.
- **JPY has no cents.** Storing yen "in cents" (×100) is wrong for the domain — there is no sub-yen unit. Use each currency's actual minor-unit count.
- **Bignums in a hot loop.** In Python, a tight numeric loop on big ints is far slower than on small ones, and you may not notice until the inputs grow. (Detailed in `senior.md`.)

---

## Apply it

1. Choose one small, known input for **Fixed-Point & Arbitrary Precision**.
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

- What problem does Fixed-Point & Arbitrary Precision solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
