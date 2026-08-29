# Integer Representation & Overflow — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Integer Representation & Overflow** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Binary: How Bits Make a Number (Unsigned)

In our everyday base-10 system, the digits of `253` mean `2×100 + 5×10 + 3×1`. Binary is the same idea with base 2: each position is a power of two. An unsigned 8-bit integer has 8 positions worth `128 64 32 16 8 4 2 1`:

```text
   bit:   1   1   1   1   1   1   0   1
 place: 128  64  32  16   8   4   2   1
        128 +64 +32 +16  +8  +4  +0  +1   = 253
```

So `11111101` in binary is 253. An **unsigned 8-bit** integer can hold the patterns from `00000000` (0) to `11111111` (255). That's **256 distinct values: 0 through 255**. In general, an n-bit unsigned integer holds `0` to `2ⁿ − 1`.

| Width | Unsigned range |
|-------|----------------|
| 8-bit | 0 … 255 |
| 16-bit | 0 … 65,535 |
| 32-bit | 0 … 4,294,967,295 (~4.3 billion) |
| 64-bit | 0 … 18,446,744,073,709,551,615 (~1.8×10¹⁹) |

### 2. How Do We Store Negative Numbers? (Two's Complement)

We need negatives too. The clever, universal trick is **two's complement**. Here's the rule for a signed n-bit integer: the **top bit's place value is made negative**. For a signed 8-bit, instead of the top bit meaning `+128`, it means `−128`:

```text
   bit:   1   0   0   0   0   0   0   0
 place:-128  64  32  16   8   4   2   1
       -128 + 0 ...                       = -128   (the most negative value)

   bit:   1   1   1   1   1   1   1   1
 place:-128  64  32  16   8   4   2   1
       -128 +64 +32 +16 +8 +4 +2 +1       = -1     (all ones = negative one)
```

So a signed 8-bit integer ranges from **−128 to +127**. Notice the asymmetry: there is **one more negative number than positive**, because zero takes up a slot on the "positive" side. Hold onto that — it causes a famous bug we'll meet later.

| Width | Signed range (two's complement) |
|-------|----------------------------------|
| 8-bit | −128 … 127 |
| 16-bit | −32,768 … 32,767 |
| 32-bit | −2,147,483,648 … 2,147,483,647 |
| 64-bit | −9,223,372,036,854,775,808 … 9,223,372,036,854,775,807 |

### 3. Why Two's Complement and Not Something Simpler?

A natural first idea is "use the top bit as a plus/minus sign and the rest as the magnitude" (called *sign-magnitude*). It seems obvious — but it's a mess in hardware:

- It has **two zeros**: `00000000` (+0) and `10000000` (−0). Now equality checks and loops have to special-case "is this the other zero?"
- **Addition needs special logic.** To add a positive and a negative you have to inspect the signs and decide whether to add or subtract magnitudes.

Two's complement fixes both:

- **Exactly one zero.** `00000000` is the only zero.
- **Addition just works.** The CPU adds the bit patterns as if they were unsigned, throws away any carry off the top, and the answer is correct for signed numbers too. `(-1) + 1`: `11111111 + 00000001 = 1 00000000`, drop the carried `1`, get `00000000 = 0`. The *same adder circuit* handles signed and unsigned. That hardware simplicity is why essentially every CPU since the 1970s uses two's complement.

### 4. Sign Extension: Widening a Number

When you copy a signed 8-bit value into a 32-bit slot, you can't just pad with zeros — `−1` is `11111111` in 8 bits, but `00000000 00000000 00000000 11111111` in 32 bits is **255**, not −1. To preserve the value you **copy the sign bit** into all the new high bits. `−1` becomes `11111111 11111111 11111111 11111111`. This is **sign extension**, and the hardware does it automatically when widening signed types. (Unsigned values just pad with zeros — "zero extension.")

### 5. Overflow: When the Box Is Too Small

Take a signed 8-bit `int` holding `127` (`01111111`) and add 1. Mathematically that's 128 — but 128 doesn't fit in `[−128, 127]`. Bit-wise, `01111111 + 1 = 10000000`, which in two's complement is **−128**. The number jumped from the most positive to the most negative. That's **overflow**, and the "rolling over" is **wraparound**.

```text
   ... 125  126  127  -128  -127 ...
                  ^      ^
                  └──────┘  +1 here wraps from +127 to -128
```

Unsigned overflow is the same odometer behavior at the top: an unsigned 8-bit `255 + 1 = 0`. And going below zero wraps the other way: unsigned `0 − 1 = 255`.

### 6. The Crucial Twist: Different Languages React Differently

This is the part juniors most need to internalize. **Overflow is not one behavior** — it depends entirely on your language:

| Language | Signed overflow does… |
|----------|------------------------|
| **C / C++** | **Undefined behavior.** The standard says *anything* may happen. The compiler may assume it never occurs and optimize accordingly. The most dangerous case. |
| **Java** | **Defined wraparound.** `Integer.MAX_VALUE + 1 == Integer.MIN_VALUE`. Silent but predictable. |
| **Go** | **Defined wraparound** (like Java). Silent, predictable, well-specified. |
| **Rust** | **Panics in debug builds** (crashes loudly so you catch it), **wraps in release builds** (for speed). Plus explicit `checked_add`, `wrapping_add`, `saturating_add`. |
| **Python** | **Never overflows.** Python integers grow to arbitrary size automatically. `2 ** 1000` just works. |
| **JavaScript** | Numbers are 64-bit floats; they lose precision past 2⁵³ rather than wrap. `BigInt` gives true arbitrary precision. |

The same line of code — `x + 1` — can crash, silently corrupt, or quietly produce a giant number, depending on the language. There is no universal answer; you must know your language's rule.

---

## Code Examples

We'll repeatedly take a value at the maximum and add 1, and watch each language react.

### C — Signed overflow is Undefined Behavior

```c
#include <stdio.h>
#include <limits.h>

int main(void) {
    int x = INT_MAX;          // 2147483647
    printf("INT_MAX   = %d\n", x);
    printf("INT_MAX+1 = %d\n", x + 1);   // UNDEFINED BEHAVIOR

    unsigned int u = UINT_MAX; // 4294967295
    printf("UINT_MAX   = %u\n", u);
    printf("UINT_MAX+1 = %u\n", u + 1);  // DEFINED: wraps to 0
    return 0;
}
```

On a typical compiler with no optimization you'll *see* `INT_MIN` printed for `x + 1`, which makes it look harmless. But it is **undefined behavior** — the compiler is allowed to assume signed overflow never happens and may delete an `if (x + 1 < x)` overflow check entirely. The unsigned case, by contrast, is *defined* to wrap to 0.

### Java — Defined silent wraparound

```java
public class Overflow {
    public static void main(String[] args) {
        int x = Integer.MAX_VALUE;     // 2147483647
        System.out.println(x);
        System.out.println(x + 1);     // -2147483648  (wraps, defined)

        // Math.addExact throws instead of wrapping:
        try {
            Math.addExact(x, 1);
        } catch (ArithmeticException e) {
            System.out.println("addExact caught: " + e.getMessage());
        }
    }
}
```

Java *guarantees* the wrap: `MAX + 1 == MIN`. It's predictable but silent, which is its own danger. Since Java 8, `Math.addExact` / `multiplyExact` throw on overflow when you want to be told.

### Go — Defined wraparound (and constants are checked)

```go
package main

import (
	"fmt"
	"math"
)

func main() {
	var x int32 = math.MaxInt32 // 2147483647
	fmt.Println(x)
	fmt.Println(x + 1) // -2147483648 (defined wrap)

	var u uint8 = 255
	fmt.Println(u + 1) // 0 (wraps)
}
```

Go's wraparound is fully specified. A nice safety net: Go rejects *constant* overflow at compile time — `var x int8 = 300` won't compile. But runtime variable overflow still wraps silently.

### Rust — Panics in debug, wraps in release, plus explicit APIs

```rust
fn main() {
    let x: i32 = i32::MAX;     // 2147483647

    // In a debug build, `x + 1` PANICS: "attempt to add with overflow".
    // In a release build, it WRAPS silently. So be explicit:

    println!("{:?}", x.checked_add(1));    // None  (overflowed)
    println!("{}",   x.wrapping_add(1));   // -2147483648
    println!("{}",   x.saturating_add(1)); // 2147483647 (clamps at max)
    let (v, of) = x.overflowing_add(1);
    println!("{} overflowed={}", v, of);   // -2147483648 overflowed=true
}
```

Rust is the most honest: it crashes loudly during development so you *find* overflow, and gives you four named operations so you say exactly what you mean — fail, wrap, clamp, or report.

### Python — Integers never overflow

```python
x = 2 ** 62
print(x)            # 4611686018427387904
print(x * x * x)    # a 187-digit number, computed exactly — no overflow

import sys
# There is no fixed-width int; Python promotes to arbitrary precision automatically.
print((2 ** 1000) + 1)   # works fine
```

Python's `int` is arbitrary precision: it grows as needed. You trade speed and memory for never having to think about overflow. (Inside NumPy, however, you're back to fixed-width types that *do* wrap.)

### JavaScript — Floats, then BigInt

```javascript
console.log(Number.MAX_SAFE_INTEGER);       // 9007199254740991  (2^53 - 1)
console.log(Number.MAX_SAFE_INTEGER + 1);    // 9007199254740992
console.log(Number.MAX_SAFE_INTEGER + 2);    // 9007199254740992  <-- WRONG, precision lost

console.log(9007199254740991n + 2n);         // 9007199254740993n  (BigInt: exact)
```

JS numbers are 64-bit floats. Past 2⁵³ they don't wrap — they lose the ability to represent every integer. `BigInt` (the `n` suffix) gives true arbitrary-precision integers.

---

## Coding Patterns

### Pattern 1: Choose a width that can't overflow for your domain

```go
// Counting nanoseconds in a 32-bit int overflows after ~2.1 seconds. Use 64-bit.
var elapsedNanos int64
```

The cheapest fix for overflow is to use a type big enough that overflow is physically impossible in your problem's lifetime.

### Pattern 2: Check before you compute (C/Java)

```java
// Instead of: int total = a + b;  (might overflow silently)
int total = Math.addExact(a, b);  // throws ArithmeticException on overflow
```

```c
// Use the compiler builtin (GCC/Clang) that returns whether overflow occurred:
int result;
if (__builtin_add_overflow(a, b, &result)) {
    // handle overflow
}
```

### Pattern 3: Say what you mean (Rust)

```rust
let total = a.checked_add(b).expect("transaction total overflowed");  // explicit failure
let hash  = a.wrapping_add(b);                                         // deliberate wrap
let level = a.saturating_add(b);                                       // clamp, never exceed max
```

### Pattern 4: Use unsigned for things that are never negative — carefully

```rust
let len: usize = data.len();   // a length is never negative; usize is correct
// but beware: `len - 1` when len == 0 wraps to a huge number. Guard it:
if len > 0 { let last = len - 1; /* ... */ }
```

---

## Clean Code

- **Name the width when it matters.** `int32`, `uint64`, `i8` are clearer than a bare `int` whose size varies by platform.
- **Pick signedness by meaning, not by habit.** A length or a count uses unsigned; a delta that can go negative uses signed.
- **Make overflow intent explicit in code that relies on it.** If you *want* wraparound (hashing), use the named API (`wrapping_add`, `Wrapping<T>`) so a reader knows it's deliberate, not a bug.
- **Don't reuse a too-small type to "save memory" on a hot counter.** The bytes saved are dwarfed by the bug risk. Default to the natural machine word.
- **Comment range assumptions.** If a function assumes its input fits in 16 bits, say so and validate it.

---

## Best Practices

- **Default to 64-bit for counters and accumulators** unless you have a measured reason to go smaller. It removes a whole class of bugs.
- **Validate external input ranges** before doing arithmetic. A `length` field from a network packet or file is attacker-controlled; a giant value can overflow your size math.
- **Use checked arithmetic on anything safety- or money-critical.** `addExact`/`checked_add`/`__builtin_*_overflow`. The performance cost is negligible compared to a wrong answer.
- **Never mix signed and unsigned in a comparison without thinking.** `-1 < someUnsigned` can be *false* because `-1` converts to a giant unsigned value. (Deep dive in `middle.md`.)
- **In C/C++, treat signed overflow as a bug to be prevented, never relied upon** — it's undefined behavior, and the optimizer will punish you.
- **Turn on the tools.** Compile C/C++ with `-fsanitize=signed-integer-overflow` (UBSan) in tests; run Rust tests in debug mode so overflow panics fire.

---

## Edge Cases & Pitfalls

- **`255 + 1 == 0`, `0 − 1 == 255`** for an unsigned 8-bit. Subtracting below zero on an unsigned type produces a *huge* number, not a negative one. This is the single most common unsigned bug.
- **`length - 1` when length is 0** on an unsigned type underflows to the maximum value — then used as an array bound, it reads way out of bounds.
- **Multiplication overflows long before addition.** `a * b` where both are large 32-bit numbers overflows easily even when `a + b` wouldn't. Size calculations (`count * elementSize`) are the classic overflow-to-exploit vector.
- **The most-negative number has no positive twin.** `−INT_MIN` cannot be represented (it would be `INT_MAX + 1`), so `abs(INT_MIN)` is broken. (Famous trap, detailed in `senior.md`.)
- **Narrowing truncates, it doesn't round or saturate.** Assigning a 32-bit `300` into an 8-bit type keeps only the low 8 bits → `300 & 255 == 44`.
- **`int` is not always 32 bits.** In C it's "at least 16"; on different platforms `long` is 32 or 64 bits. Use explicit-width types (`int32_t`, `int64_t`) when size matters.
- **A successful test run hides overflow bugs.** They only appear at the extreme values, which your tests probably don't hit. Test the boundaries explicitly.

---

## Common Mistakes

1. **Assuming `int` is big enough.** A 32-bit counter looks infinite until it isn't. Default to 64-bit for anything that grows over time.
2. **Treating unsigned subtraction like math.** `unsignedA - unsignedB` when `B > A` wraps to a huge number. Check `A >= B` first.
3. **Relying on C signed overflow "wrapping."** It's undefined behavior, not wraparound. The compiler may do something else entirely.
4. **Using `abs()` and forgetting `INT_MIN`.** `abs(INT_MIN)` is broken in C/Java. (See `senior.md`.)
5. **Computing `(a + b) / 2` for a midpoint.** If `a + b` overflows, your midpoint is wrong/negative — a real bug that lived in binary search for years. Use `a + (b - a) / 2`.
6. **Storing a size in a signed 32-bit on a system with >2 GB data.** The size goes negative. Use `size_t` / 64-bit.
7. **Assuming Python's behavior elsewhere.** Python never overflows, so habits formed there crash or wrap when you move to C/Go/Java.
8. **Mixing widths in arithmetic without noticing the promotion.** A `byte + byte` in Java is computed as `int`; in C it's worse with implicit conversions (covered in `middle.md`).

---

## Tricky Points

- **The same bits are two numbers.** `0xFF` is `255` *or* `−1`. Only the type decides. Reinterpreting type changes the value with zero memory movement.
- **Overflow is not an error in most languages — it's a result.** Java and Go return a wrong-but-defined value; only Rust-debug and checked APIs treat it as an event.
- **"It worked on my machine" is especially dangerous here.** Overflow depends on type width, which depends on platform (`int`, `long`, `size_t` vary). Same code, different range, different bug.
- **C's undefined signed overflow can delete your safety check.** `if (x + 1 < x)` looks like an overflow test, but since signed overflow "can't happen" per the standard, the compiler may optimize the whole `if` away. You must check *before* overflowing, not after.
- **Constants vs variables.** Many languages catch *constant* overflow at compile time (`int8 x = 300` fails) but silently wrap the identical *runtime* computation.

---

## Apply it

1. Choose one small, known input for **Integer Representation & Overflow**.
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

- What problem does Integer Representation & Overflow solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
