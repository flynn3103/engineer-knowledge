# Integer Representation & Overflow — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Integer Representation & Overflow** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Integer Promotion (C/C++): Small Types Become `int`

In C and C++, you cannot do arithmetic on a `char` or `short` directly. Before any arithmetic operator, **operands smaller than `int` are promoted to `int`** (the "integer promotions"). This produces results that surprise people:

```c
unsigned char a = 200, b = 100;
unsigned char c = a + b;     // a,b promoted to int: 200+100 = 300 (an int)
                             // then assigned back to unsigned char: 300 & 0xFF = 44
printf("%d\n", a + b);       // prints 300, NOT 44 — the expression is an int!
printf("%d\n", c);           // prints 44 — truncation happened on assignment
```

The expression `a + b` has type `int` and value `300`. Only when you *store* it into the 8-bit `c` does truncation to `44` occur. A common bug: people think 8-bit arithmetic wraps at 256, but the *arithmetic* happens in `int`; the wrap only happens at the narrowing store.

### 2. Usual Arithmetic Conversions: Finding the Common Type

When the two operands of `+ - * / % < > == &` etc. have different types, C/C++ converts them to a single "common type" by a ranked procedure (simplified):

1. Apply integer promotions to both.
2. If both are signed or both unsigned, convert to the higher-ranked type.
3. **If one is unsigned and the other signed, and the unsigned type's rank is ≥ the signed type's, the signed operand is converted to unsigned.** ← the dangerous rule.

That last rule is the root of the signed/unsigned comparison bug below.

### 3. The Signed/Unsigned Comparison Trap

```c
int a = -1;
unsigned int b = 1;
if (a < b) printf("less\n"); else printf("not less\n");
```

You expect "less" — `−1 < 1`. You get **"not less."** Why? `b` is `unsigned int`, same rank as `int`, so the signed `a` is converted to unsigned: `−1` becomes `4294967295`. Now the comparison is `4294967295 < 1`, which is false. The mathematical relationship inverted because of an implicit conversion you never wrote.

This is one of the most common real bugs in C/C++:

```c
int len = get_length();        // could return -1 on error
char buf[100];
if (len < sizeof(buf)) {       // sizeof is size_t (unsigned)!
    // if len == -1, it becomes a huge unsigned, condition FALSE,
    // so the "safe" branch is skipped — or in other framings, taken when it shouldn't be
}
```

### 4. Truncation: Narrowing Keeps the Low Bits

Assigning a wide value into a narrow type discards the high bits — it does **not** clamp or round:

```c
long big = 0x1_0000_002A;     // 4294967338
int  small = (int)big;        // keeps low 32 bits: 0x0000002A = 42
short tiny = (short)0x12345;  // keeps low 16 bits: 0x2345 = 9029
```

For signed targets, the kept low bits are then *reinterpreted* under the target's sign rule, which can flip the sign:

```c
int x = 0xFFFF_0001;          // some 32-bit value
short s = (short)x;           // low 16 bits = 0x0001 = 1   (fine here)
short t = (short)0x0000_8000; // low 16 bits = 0x8000 = -32768 (sign flips!)
```

### 5. Overflow Detection Technique A: Pre-Check Against Limits

The *correct, portable* way to detect overflow is to test the operands against the type's limits **before** computing, so you never actually overflow:

```c
#include <limits.h>
// Will a + b overflow a signed int?
bool add_overflows(int a, int b) {
    if (b > 0 && a > INT_MAX - b) return true;   // a + b would exceed INT_MAX
    if (b < 0 && a < INT_MIN - b) return true;   // a + b would go below INT_MIN
    return false;
}
```

This never triggers UB because it never performs the overflowing addition. The same shape works for multiplication (`a > INT_MAX / b`, with care for sign and zero).

### 6. Overflow Detection Technique B: Compute in a Wider Type

If a wider type exists, compute there and check the result fits:

```c
int32_t a, b;
int64_t wide = (int64_t)a + (int64_t)b;   // 32-bit operands can't overflow 64-bit sum
if (wide > INT32_MAX || wide < INT32_MIN) { /* overflow */ }
int32_t result = (int32_t)wide;
```

Clean and obvious — but it fails for the *widest* type (there's nothing wider than `int64_t` to promote a 64-bit sum into), and it costs a wider operation.

### 7. Overflow Detection Technique C: Compiler Builtins / Checked APIs

The best modern answer is to let the hardware/compiler tell you, using the CPU's overflow flag:

```c
int32_t a, b, r;
if (__builtin_add_overflow(a, b, &r)) { /* overflowed */ }   // GCC/Clang
```

```rust
let (r, overflowed) = a.overflowing_add(b);
match a.checked_mul(b) { Some(v) => /* ok */, None => /* overflow */ }
```

```java
int r = Math.addExact(a, b);   // throws ArithmeticException on overflow
```

```go
// Go has no builtin; use math/bits for the unsigned case:
sum, carry := bits.Add64(a, b, 0)   // carry != 0 means overflow
```

### 8. Why the Post-Check Trick Is a Trap in C

A classic "detect overflow after the fact" idiom:

```c
int r = a + b;
if (r < a) { /* overflowed */ }   // BUG in C for SIGNED ints
```

For **unsigned** this is valid (wraparound is defined, so a smaller result means it wrapped). For **signed**, the addition `a + b` *itself* is undefined behavior when it overflows — so by the time you check `r`, you've already invoked UB and the compiler may have assumed it never happened and deleted your check. **Detect before, not after, for signed types.**

---

## Code Examples

### C — The promotion + truncation surprise

```c
#include <stdio.h>

int main(void) {
    unsigned char a = 0xFF;     // 255
    unsigned char b = 0x01;     // 1
    printf("a + b as expr = %d\n", a + b);        // 256  (computed as int!)
    unsigned char c = a + b;                       // truncated to 8 bits
    printf("a + b stored   = %u\n", c);           // 0

    short s = -1;
    int   i = s;                                   // widening: sign-extended
    printf("widened -1     = %d\n", i);           // -1, not 65535
    return 0;
}
```

### C — Safe addition with pre-check vs builtin

```c
#include <stdio.h>
#include <limits.h>
#include <stdbool.h>

bool safe_add(int a, int b, int *out) {
    if (b > 0 && a > INT_MAX - b) return false;   // would overflow high
    if (b < 0 && a < INT_MIN - b) return false;   // would overflow low
    *out = a + b;                                  // now guaranteed safe
    return true;
}

bool safe_add_builtin(int a, int b, int *out) {
    return !__builtin_add_overflow(a, b, out);     // hardware flag, GCC/Clang
}

int main(void) {
    int r;
    printf("%d\n", safe_add(INT_MAX, 1, &r));      // 0 (refused)
    printf("%d\n", safe_add(2, 3, &r));            // 1, r = 5
    return 0;
}
```

### C — The signed/unsigned comparison bug, demonstrated and fixed

```c
#include <stdio.h>

int main(void) {
    int n = -1;
    unsigned int count = 5;

    if (n < count) printf("n < count\n");          // does NOT print!
    else           printf("n NOT < count\n");      // prints (because -1 -> 4294967295)

    // Fix: compare in a common SIGNED domain, or guard the sign first:
    if (n < 0 || (unsigned)n < count) printf("fixed: n < count\n");
    return 0;
}
```

### Java — Promotion and the cast-back gotcha

```java
public class Promotion {
    public static void main(String[] args) {
        byte a = 100, b = 100;
        // byte + byte is computed as int; you MUST cast to store in a byte:
        // byte sum = a + b;          // compile error: possible lossy conversion
        byte sum = (byte)(a + b);     // 200 doesn't fit in byte -> wraps to -56
        System.out.println(sum);      // -56

        int big = 300;
        byte truncated = (byte) big;  // 300 & 0xFF = 44
        System.out.println(truncated);// 44

        // Java has no unsigned types (pre-Java 8 helpers exist):
        int x = -1;
        System.out.println(Integer.toUnsignedLong(x)); // 4294967295
        System.out.println(Integer.compareUnsigned(-1, 1) > 0); // true
    }
}
```

### Go — Explicit conversions, no implicit mixing

```go
package main

import (
	"fmt"
	"math/bits"
)

func main() {
	var a int32 = 2_000_000_000
	var b int32 = 2_000_000_000
	// Go forbids mixing types implicitly; you must convert.
	wide := int64(a) + int64(b) // compute in 64-bit, no overflow
	fmt.Println(wide)           // 4000000000

	// Detecting unsigned overflow with math/bits:
	sum, carry := bits.Add64(^uint64(0), 1, 0) // MAX + 1
	fmt.Println(sum, carry)                     // 0 1  (carry==1 => overflowed)

	// Go also forbids signed/unsigned mixing — a whole bug class is gone:
	// var s int = -1; var u uint = 1; _ = s < u  // compile error
}
```

Go's design choice — **no implicit conversions at all** — eliminates the C signed/unsigned comparison trap by construction. You must write every conversion, which is verbose but safe.

### Rust — Conversions are explicit; choose your overflow semantics

```rust
fn main() {
    let a: i32 = 2_000_000_000;
    let b: i32 = 2_000_000_000;

    // `as` truncates/reinterprets silently — the one footgun in Rust:
    let truncated = 300_i32 as u8;        // 44
    println!("{}", truncated);

    // Prefer fallible conversions that report loss:
    let r: Result<u8, _> = u8::try_from(300_i32);
    println!("{:?}", r);                  // Err(TryFromIntError(()))

    // Choose overflow semantics explicitly:
    println!("{:?}", a.checked_add(b));   // None (overflow)
    println!("{}",   a.wrapping_add(b));  // -294967296
    println!("{}",   a.saturating_add(b));// 2147483647

    // Wider-type compute:
    let wide = a as i64 + b as i64;       // 4000000000
    println!("{}", wide);
}
```

---

## Coding Patterns

### Pattern 1: Overflow-safe multiplication via division check

```c
bool mul_overflows(size_t a, size_t b) {
    if (a == 0 || b == 0) return false;
    return a > SIZE_MAX / b;    // if a > MAX/b, then a*b > MAX
}
```

### Pattern 2: Overflow-safe binary-search midpoint

```c
// BAD:  int mid = (lo + hi) / 2;          // lo + hi can overflow
// GOOD:
int mid = lo + (hi - lo) / 2;              // no overflow when lo <= hi
```

This exact bug lived in `java.util.Arrays.binarySearch` for years until Joshua Bloch wrote it up in 2006.

### Pattern 3: Guard unsigned subtraction

```rust
// BAD:  let last = len - 1;               // panics/wraps if len == 0
// GOOD:
let last = len.checked_sub(1);             // None when len == 0
if let Some(idx) = last { /* safe */ }
```

### Pattern 4: Compare signed and unsigned safely

```java
// Don't let one operand silently convert. Normalize the domain:
if (Integer.compareUnsigned(x, y) < 0) { ... }   // Java
```

```c
if (a < 0 || (size_t)a < n) { ... }   // handle the sign before converting
```

### Pattern 5: Validate-then-narrow

```rust
let small: u16 = u16::try_from(value).map_err(|_| Error::TooLarge)?;
```

Never narrow blindly; convert through a fallible path that reports the loss.

---

## Clean Code

- **Make every conversion visible and intentional.** Prefer `try_from`/`compareUnsigned`/explicit casts over relying on implicit promotion. A reader should see where a value changes width or sign.
- **Compute at the right width from the start.** If a product can exceed 32 bits, declare the operands or an intermediate as 64-bit; don't compute narrow then "fix" it.
- **Encapsulate overflow checks in named helpers** (`safe_add`, `checked_size`) so the call sites read as intent, not arithmetic.
- **Comment why a wrap is deliberate.** `hash = hash.wrapping_mul(31)  // intentional modular hashing` saves the next reader a panic.
- **Prefer the type the domain demands.** `size_t`/`usize` for sizes, signed for deltas, fixed-width (`int32_t`) when wire/format compatibility matters.

---

## Best Practices

- **Validate ranges at trust boundaries.** Any integer from a file, socket, or user gets checked against the limits before it participates in arithmetic.
- **Use checked/builtin overflow operations for size and money math.** The performance hit is negligible next to the bug cost.
- **Never compare signed and unsigned directly in C/C++.** Enable `-Wsign-compare` (it's in `-Wextra`) and treat every warning as a bug.
- **Avoid narrowing where you can; when you must, do it through a fallible conversion.**
- **Compile tests with UBSan** (`-fsanitize=signed-integer-overflow,unsigned-integer-overflow`) — it pinpoints the exact line and values at runtime.
- **Prefer languages/APIs that remove the footgun** when you have the choice: Go's no-implicit-conversion rule and Rust's `try_from` eliminate whole categories of these bugs.

---

## Edge Cases & Pitfalls

- **`char + char` is `int` in C.** People expecting 8-bit wrap during the arithmetic are wrong; the wrap only happens on the narrowing store.
- **`sizeof` is `size_t` (unsigned).** Comparing a signed length against `sizeof(buf)` silently converts the signed value — the classic bug.
- **Post-overflow checks for signed ints are UB in C.** `if (a + b < a)` has already overflowed before the check; the compiler may delete it.
- **`% ` of a negative number varies by language.** C's `-7 % 3` is `-1`; Python's is `2`. Ring-buffer index math `(i + n) % cap` can return negative in C if `i` is signed and negative.
- **Multiplying then dividing in the wrong order overflows needlessly.** `(a * b) / c` may overflow where `a * (b / c)` (when exact) or wider math wouldn't.
- **Mixed-width shifts.** `1 << 31` is UB/overflow for a signed 32-bit `int` (the sign bit); use `1u << 31` or a 64-bit literal.
- **`int` width is platform-dependent.** LP64 (Linux/macOS) has 32-bit `int`, 64-bit `long`; LLP64 (Windows) has 32-bit `int` *and* 32-bit `long`, 64-bit `long long`. Code that assumes `long` is 64-bit breaks on Windows.

---

## Common Mistakes

1. **Comparing a signed length to `sizeof`/`.size()`.** The signed side converts to a huge unsigned and the check inverts.
2. **Detecting signed overflow with a post-check** (`r < a`) — undefined behavior; the check can be optimized away.
3. **Truncating without validating.** `(int)bigValue` silently loses the high bits; a 5 GB size becomes a small or negative `int`.
4. **`(lo + hi) / 2` midpoints.** Overflows for large indices; the canonical binary-search bug.
5. **Assuming 8/16-bit arithmetic wraps mid-expression in C.** It promotes to `int` first.
6. **`for (size_t i = n - 1; i >= 0; i--)`.** `i >= 0` is always true for unsigned; infinite loop, or underflow on the last decrement.
7. **Forgetting Java has no unsigned types.** Treating `int` as unsigned without `Integer.*Unsigned` helpers gives wrong comparisons and divisions.
8. **Relying on `long` being 64-bit.** True on Linux/macOS, false on Windows. Use `int64_t`/`<stdint.h>`.

---

## Tricky Points

- **The conversion happens at the operator, not at the variable.** `a < b` converts *for that comparison*; `a` itself doesn't change. Two comparisons of the same variable can convert it differently depending on the other operand.
- **Unsigned makes the *whole expression* unsigned.** One unsigned operand of sufficient rank "infects" the comparison/arithmetic, dragging the signed operand into the unsigned domain.
- **Wider-type detection breaks at the top.** You can detect 32-bit overflow with 64-bit math, but you can't detect 64-bit overflow that way — there's no 128-bit standard type in C. Use builtins or 128-bit extensions.
- **Saturating and wrapping are *both* "correct" — for different problems.** Audio sample mixing wants saturation (clipping, not a pop); a hash wants wrapping. The bug is using one where you meant the other.
- **UBSan changes the program.** Code that "works" because of incidental wraparound will start aborting under UBSan — that's the point, but it means UBSan can surface latent bugs in old code suddenly.

---

## Apply it

1. Find a real component where **Integer Representation & Overflow** affects an interface or dependency.
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

- Which boundary is most affected by Integer Representation & Overflow?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
