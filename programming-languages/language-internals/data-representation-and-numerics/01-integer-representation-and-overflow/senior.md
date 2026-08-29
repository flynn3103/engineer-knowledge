# Integer Representation & Overflow — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Integer Representation & Overflow** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Algebra of Two's Complement

For an n-bit pattern with bits `bₙ₋₁ … b₀`, two's complement defines the value as:

```text
   value = −bₙ₋₁ · 2ⁿ⁻¹  +  Σ (i=0..n-2) bᵢ · 2ⁱ
```

Only the top bit's weight is negated. This single definition gives every desirable property:

- **One zero.** `0` has exactly one representation, `000…0`.
- **Negation is "flip all bits, add 1."** `−x = ~x + 1`. Provable from the definition; it's why hardware negation is trivial.
- **Signed and unsigned addition are bit-identical.** Add the patterns mod 2ⁿ; the result is correct under *both* interpretations. One adder, two readings.
- **Subtraction is addition of the negation.** `a − b = a + (~b + 1)`, again one adder.
- **Overflow is detectable from the sign bits.** Signed overflow occurred iff the two operands had the same sign and the result has the opposite sign — exactly the condition the x86 OF flag encodes.

Contrast the historical alternatives — **sign-magnitude** (two zeros, separate add/subtract logic) and **ones' complement** (two zeros, "end-around carry" needed for addition). Both were used in real machines (CDC, PDP-1) and both lost precisely because two's complement makes the hardware adder do double duty with no special cases. *This is the "why" behind the whole topic.*

### 2. The `INT_MIN` Asymmetry — and Why It Breaks Things

An n-bit signed type ranges over `[−2ⁿ⁻¹, 2ⁿ⁻¹ − 1]`. There are `2ⁿ⁻¹` negatives but only `2ⁿ⁻¹ − 1` positives, because zero consumes a non-negative slot. Consequence: **`INT_MIN` has no positive counterpart.** `−INT_MIN = INT_MAX + 1`, which overflows. This poisons several operations:

```c
int x = INT_MIN;            // -2147483648
int y = -x;                 // UB: -INT_MIN overflows (would be 2147483648)
int z = abs(x);             // UB / returns INT_MIN (negative!) — abs is broken here
int q = INT_MIN / -1;       // UB; on x86 it TRAPS (SIGFPE), same as div-by-zero
int r = INT_MIN % -1;       // same trap on many platforms
```

The `INT_MIN / −1` trap surprises everyone: division by −1 should be negation, but the negation overflows, and the x86 `idiv` instruction raises `#DE` (divide error) — the *same exception as divide-by-zero*. A robust signed-division guard must check **both** `b == 0` **and** `(a == INT_MIN && b == -1)`.

`abs(INT_MIN)` is undefined in C and returns `INT_MIN` (still negative) in Java's `Math.abs(int)`. Rust's `i32::MIN.abs()` panics in debug. The correct tool is `checked_abs`/`unsigned_abs` (Rust), `Math.absExact` (Java 15+), or manual handling.

### 3. What "Undefined Behavior" Actually Licenses

C/C++ make signed overflow UB. The practical meaning is not "it might wrap weirdly" — it's "**the optimizer may assume the program never overflows and rewrite code accordingly.**" Examples that bite seniors:

```c
// 1. The optimizer assumes x + 1 > x always:
for (int i = 0; i <= n; i++) { ... }   // may be assumed to terminate even if n == INT_MAX
                                       // (it would never terminate with wrapping)

// 2. Deletion of "redundant" overflow checks:
int f(int a) {
    if (a + 100 < a) return ERROR;     // looks like overflow detection
    return a + 100;                    // compiler: "a+100<a is impossible (UB),
}                                      //  so delete the check." Your guard vanishes.

// 3. Promoting int loop counters to 64-bit / vectorizing,
//    valid only if no wrap occurs.
```

The famous demonstrations (Chris Lattner's "What Every C Programmer Should Know About Undefined Behavior," and the Linux kernel's `-fno-strict-overflow` adoption) show that overflow checks written *after* the overflow are routinely optimized away. The senior takeaways:

- **Detect overflow before performing it** (pre-checks, builtins) — covered in `middle.md`, now you know *why* the post-check fails.
- **Know the escape hatches:** `-fwrapv` makes signed overflow defined-to-wrap (kills the UB and the optimizations that depend on it). `-ftrapv` makes it trap. `-fsanitize=signed-integer-overflow` makes it diagnosable. The Linux kernel compiles with `-fno-strict-overflow`.

### 4. Hardware: Flags, Sign Extension, and the Single Adder

At the ISA level, one `add` instruction serves both signednesses; the CPU sets **both** OF (signed overflow) and CF (unsigned carry) on every add, and *you* (or the compiler) read whichever is relevant. This is why Rust's `overflowing_add`, Go's `bits.Add64` carry-out, and `__builtin_add_overflow` are cheap — they compile to one `add` plus a conditional read of a flag, not a separate slow check.

Sign extension is likewise a single instruction (`movsx`, `cdqe` for eax→rax). When you widen a signed value, the hardware replicates the sign bit; when you widen unsigned, it zero-extends (`movzx`). A senior should be able to predict which the compiler emits from the source types.

### 5. The Cross-Language Overflow Model, Precisely

| Language | Signed overflow | Unsigned overflow | Width model | Escape / explicit ops |
|----------|-----------------|-------------------|-------------|------------------------|
| **C/C++** | **UB** | wraps (defined) | `int`≥16, impl-defined widths; `<stdint.h>` for fixed | `-fwrapv`, `-ftrapv`, `__builtin_*_overflow`, C23 `ckd_*` |
| **Rust** | panic (debug) / wrap (release) | same | fixed widths, `usize`/`isize` = pointer width | `checked_*`, `wrapping_*`, `saturating_*`, `overflowing_*`, `Wrapping<T>` |
| **Go** | wraps (defined) | wraps (defined) | fixed; `int`/`uint` = platform word | `math/bits` for carry; const overflow is a compile error |
| **Java** | wraps (defined) | n/a (no unsigned) | fixed (8/16/32/64); `int` always 32 | `Math.*Exact`, `Integer.*Unsigned`, `BigInteger` |
| **Python** | impossible (bignum) | impossible | arbitrary precision | n/a; NumPy reintroduces fixed widths that wrap |
| **JS** | n/a (f64) | n/a | `Number` = f64 (safe to 2⁵³); `BigInt` arbitrary | `BigInt`, `Math.imul`, `>>> 0` for uint32 |
| **Swift** | **traps** by default | traps | fixed | `&+`/`&-`/`&*` overflow operators, `addingReportingOverflow` |

Two observations a senior should internalize. First, **safety-by-default and speed-by-default are a deliberate dial**: Swift and Rust-debug trap (find bugs early), C wraps-or-UB and Rust-release wrap (speed), Java/Go define wrap (predictable but silent). Second, **the "defined wrap" languages still have bugs** — defined-but-wrong is a wrong answer; only the *checked* path is correct for arithmetic that must not silently lie.

### 6. Why Java Has No Unsigned Types (and How It Copes)

Java deliberately omitted unsigned integers (Gosling's stated reason: they confuse more than they help, given the conversion traps you saw in `middle.md`). The cost: bytes are signed (`byte` is `[−128,127]`), so reading raw bytes needs `b & 0xFF`. Java 8 added a *functional* unsigned layer — `Integer.toUnsignedLong`, `Integer.divideUnsigned`, `Integer.compareUnsigned`, `Long.parseUnsignedLong` — that operate on the same `int`/`long` bit patterns with unsigned semantics. The pattern is "signed storage, unsigned operations on demand," which is exactly how you should think about Java's `int` when it holds a hash, a color, or a raw byte run.

---

## Code Examples

### C — The `INT_MIN` traps, all of them

```c
#include <stdio.h>
#include <limits.h>
#include <stdlib.h>

int safe_negate(int x, int *out) {
    if (x == INT_MIN) return 0;   // -INT_MIN would overflow
    *out = -x; return 1;
}

int safe_div(int a, int b, int *out) {
    if (b == 0) return 0;
    if (a == INT_MIN && b == -1) return 0;  // would overflow AND traps on x86
    *out = a / b; return 1;
}

int main(void) {
    int o;
    printf("negate INT_MIN ok? %d\n", safe_negate(INT_MIN, &o)); // 0
    printf("INT_MIN / -1 ok?  %d\n", safe_div(INT_MIN, -1, &o)); // 0
    // Demonstrating abs is broken:
    printf("abs(INT_MIN) = %d\n", abs(INT_MIN));  // INT_MIN, still negative (UB)
    return 0;
}
```

### C — Watching the optimizer delete an overflow check

```c
// Compile twice: gcc -O0 and gcc -O2 -fstrict-overflow, observe the difference.
#include <stdio.h>
#include <limits.h>

__attribute__((noinline))
int check_then_add(int a) {
    if (a + 100 < a)          // "overflow check" — but a+100<a is UB-impossible
        return -1;            // at -O2, the optimizer may PROVE this never fires
    return a + 100;
}

int main(void) {
    printf("%d\n", check_then_add(INT_MAX)); // -O0: -1; -O2: may be INT_MAX+100 (UB)
    return 0;
}
```

The fix is to check before overflowing (`if (a > INT_MAX - 100) ...`) or compile with `-fwrapv` to make the wrap defined so the check is meaningful.

### Rust — The full overflow API, and why release ≠ debug

```rust
fn main() {
    let x = i32::MIN;

    // INT_MIN handling, the right way:
    println!("{:?}", x.checked_neg());      // None
    println!("{:?}", x.checked_abs());      // None
    println!("{}",   x.unsigned_abs());     // 2147483648 (returns u32, can't overflow)
    println!("{:?}", x.checked_div(-1));    // None

    // Semantics dial:
    println!("{}", 200u8.wrapping_add(100));    // 44
    println!("{}", 200u8.saturating_add(100));  // 255 (clamped)
    let (v, o) = 200u8.overflowing_add(100);
    println!("{} {}", v, o);                    // 44 true

    // Wrapping<T> makes wraparound the type's default (for hashing etc.):
    use std::num::Wrapping;
    let mut h = Wrapping(0u32);
    for &b in b"hash" { h = h * Wrapping(31) + Wrapping(b as u32); } // never panics
    println!("{}", h.0);
}
```

### Go — Defined wrap, plus carry-aware big arithmetic

```go
package main

import (
	"fmt"
	"math"
	"math/bits"
)

func main() {
	// Defined signed wrap:
	fmt.Println(int8(127) + 1) // -128

	// INT_MIN / -1 in Go does NOT trap — it's defined to overflow-wrap to MIN:
	fmt.Println(math.MinInt32 / -1) // -2147483648 (no SIGFPE; Go specifies it)

	// 128-bit-ish multiply via math/bits (no native int128):
	hi, lo := bits.Mul64(1<<40, 1<<40) // 2^80, split across two words
	fmt.Printf("hi=%d lo=%d\n", hi, lo)

	// Detecting unsigned add overflow:
	_, carry := bits.Add64(math.MaxUint64, 1, 0)
	fmt.Println("overflow:", carry == 1) // true
}
```

Note the genuinely useful contrast: Go *defines* `MinInt32 / -1` to wrap rather than trap — a deliberate spec choice to avoid the x86 SIGFPE surprise. C leaves it UB; Go nails it down.

### Java — No unsigned, but unsigned-on-demand

```java
public class Unsigned {
    public static void main(String[] args) {
        int x = -1;                                  // bits 0xFFFFFFFF
        System.out.println(Integer.toUnsignedLong(x));   // 4294967295
        System.out.println(Integer.divideUnsigned(-2, 3));// large unsigned quotient
        System.out.println(Integer.compareUnsigned(-1, 1) > 0); // true (huge > 1)

        // INT_MIN trap, Java edition:
        System.out.println(Math.abs(Integer.MIN_VALUE)); // MIN_VALUE (still negative!)
        try {
            Math.absExact(Integer.MIN_VALUE);            // Java 15+: throws
        } catch (ArithmeticException e) {
            System.out.println("absExact threw: " + e.getMessage());
        }
    }
}
```

---

## Coding Patterns

### Pattern 1: The complete signed-division guard

```c
bool safe_div(int32_t a, int32_t b, int32_t *out) {
    if (b == 0) return false;
    if (a == INT32_MIN && b == -1) return false;  // overflow + SIGFPE on x86
    *out = a / b;
    return true;
}
```

### Pattern 2: `unsigned_abs` to dodge the `INT_MIN` trap

```rust
// abs() can overflow; unsigned_abs() returns the unsigned magnitude, which always fits:
let magnitude: u32 = value.unsigned_abs();   // i32::MIN -> 2147483648, no panic
```

### Pattern 3: Make wraparound a type, not a per-call decision

```rust
use std::num::Wrapping;
type Hash = Wrapping<u64>;   // every + and * on Hash is modular by construction
```

### Pattern 4: Compile-flag the UB away in legacy C

```bash
# Make signed overflow defined-to-wrap across a legacy codebase you can't fully audit:
gcc -fwrapv ...
# Or find the bugs first:
gcc -fsanitize=signed-integer-overflow -fsanitize=unsigned-integer-overflow ...
```

### Pattern 5: Read the flag instead of recomputing

```c
// One add + one flag read, vs a separate comparison the optimizer might break:
int32_t r;
if (__builtin_add_overflow(a, b, &r)) handle_overflow();   // compiles to add+jo
```

---

## Clean Code

- **Encode overflow policy in the type.** `Wrapping<T>`, a `Saturating<T>` newtype, or a `Checked<T>` wrapper communicates intent better than scattered `wrapping_add` calls.
- **Centralize the `INT_MIN`/div guards.** A single audited `safe_div`/`safe_neg`/`safe_abs` beats re-deriving the asymmetry at every call site.
- **State the compilation contract.** If a module relies on `-fwrapv`, document it at the top — building it without that flag silently changes semantics.
- **Prefer `unsigned_abs`/`checked_abs` over `abs`** in any code that could see `INT_MIN`.
- **Name the width and signedness in the type, not in a comment.** `u32`/`int64_t`/`size_t` carry the contract; a bare `int` hides it.

---

## Best Practices

- **In C/C++, never rely on signed wrap; never post-check signed overflow.** Use pre-checks, builtins, or C23 `ckd_*`. Compile tests under UBSan.
- **Guard signed division for both `b==0` and `INT_MIN/-1`.** The second is as real as the first and traps identically on x86.
- **Choose the overflow semantics explicitly** (checked/wrapping/saturating) — defaulting is how silent bugs ship.
- **For the widest type, use hardware-assisted detection** (`__builtin_mul_overflow`, `unsigned __int128`, `math/bits.Mul64`) since you can't "compute in a wider standard type."
- **Keep crypto off bignums on hot paths** and off secret-dependent branches; fixed-width constant-time is the requirement.
- **When porting C from x86 to ARM/RISC-V, audit overflow assumptions** — wrap behavior that "worked" under x86 incidentals is not guaranteed, and UB is UB everywhere.

---

## Edge Cases & Pitfalls

- **`INT_MIN / −1` traps (SIGFPE) on x86**, identically to divide-by-zero. Guarding only `b == 0` is incomplete.
- **`abs(INT_MIN)` returns a negative number** (Java) or is UB (C). `unsigned_abs`/`absExact` are the fixes.
- **`-x` is UB for `x == INT_MIN`** in C; `negate` needs a guard.
- **`1 << 31` on a signed 32-bit `int` is UB** (shifting into the sign bit). Use `1u << 31` or a wider type.
- **`-fwrapv` changes program meaning**, not just suppresses warnings — code that depended on UB-driven optimizations (e.g., assumed loop termination) can change behavior.
- **`%` sign follows the dividend in C/Java/Go/Rust but the divisor in Python.** `-7 % 3` is `-1` in C, `2` in Python. Modular index math differs.
- **Bignum timing leaks.** A "just use BigInteger" fix in crypto introduces a side channel; the running time depends on operand magnitude.
- **`int` vs `long` width across ABIs** (LP64 vs LLP64) silently changes ranges; `<stdint.h>` is mandatory for portable width.

---

## Common Mistakes

1. **Reasoning about C signed overflow as "it wraps."** It's UB; the compiler may do anything, including deleting your check.
2. **Post-checking signed overflow** (`r < a`) — self-contradictory under UB; valid only for unsigned.
3. **Guarding division for zero but not `INT_MIN/-1`.** A real crash in production.
4. **Calling `abs`/`-x` on a value that can be `INT_MIN`.** Returns wrong sign or is UB.
5. **Shifting into the sign bit of a signed type.** `1 << 31` UB; use unsigned literals.
6. **Assuming Go/Java wrap means it's *correct*.** Defined ≠ intended; use `*Exact`/`checked_*` when the answer must be right.
7. **Switching on `-O2` and "fixing" a behavior change with a sleep/volatile** instead of finding the UB. Use UBSan.
8. **Using bignums in constant-time code.** Reintroduces timing side channels.

---

## Tricky Points

- **The same expression is defined in Go and undefined in C.** `MinInt32 / -1` wraps in Go (spec'd), traps/UB in C. Portability of "what overflow does" is a per-language promise, not a hardware fact.
- **UBSan and `-fwrapv` are different tools.** UBSan *detects* (aborts/reports), `-fwrapv` *defines* (wraps, no report). Don't ship `-fwrapv` thinking you've found the bugs; you've only hidden the UB.
- **OF and CF are both always set by `add`.** Whether overflow "happened" depends on which interpretation you query — there's no single "did it overflow" without a signedness.
- **Saturating arithmetic isn't free in software** unless the ISA has it (SSE/NEON `padds`); a scalar `saturating_add` compiles to a compare + cmov.
- **Two's complement's negation `~x + 1` itself overflows at `INT_MIN`** — the asymmetry is baked into the algebra, not bolted on.
- **`size_t` is unsigned by deliberate design**, so loop-down-to-zero with `size_t` is an underflow trap; this is not an accident but a frequent foot-gun.

---

## Apply it

1. State the system invariant that **Integer Representation & Overflow** must protect.
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

- Which invariant must remain true when Integer Representation & Overflow fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
