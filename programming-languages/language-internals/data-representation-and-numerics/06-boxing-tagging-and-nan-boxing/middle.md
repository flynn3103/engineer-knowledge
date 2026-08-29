# Boxing, Tagging & NaN-Boxing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Boxing, Tagging & NaN-Boxing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why Alignment Gives You Free Bits

Allocators align objects so the CPU can load them efficiently. If every heap object is 8-byte aligned, its address is a multiple of 8: `...000` in binary. Three low bits, guaranteed zero, carrying no information. That's a gift.

```text
8-byte-aligned address:  0x7FFE_C0DE_0000_1000
                                              ^^^
                            low 3 bits always 000
```

A runtime declares a convention: the low bits *are* the tag. For example:
- `xxx...xx0` → not a pointer; the upper bits are a small integer (Ruby, OCaml shift-style).
- `xxx...xx1` → a real heap pointer; clear the tag bit before dereferencing.

Because the tag rides in bits the pointer never used, you pay *nothing* in pointer space. You pay only when you want to use a tagged value: you must **untag** (mask or shift) first.

### 2. Pointer Tagging Scheme A: Low-Bit "Is-Pointer" Flag (V8 SMI)

V8 distinguishes a **Small Integer (SMI)** from a **HeapObject pointer** by the *low* bit:

```text
SMI            value << 1 | 0      (low bit 0)
HeapObject     pointer    | 1      (low bit 1)
```

On a 64-bit build, an SMI is a 32-bit signed integer stored in the *upper* 32 bits, with the low 32 bits as the tag region (historically `value << 32`). On 32-bit builds it was `value << 1`, giving a 31-bit SMI. The check is one instruction:

```text
is_smi(x)    ==  (x & 1) == 0
smi_value(x) ==  x >> 1            (arithmetic shift, sign-preserving)  // 32-bit build
```

The tradeoff: an SMI cannot represent all 64-bit integers — only the 31-/32-bit range. A number outside that range becomes a **HeapNumber** (a boxed double on the heap). This is the engine of the "small integers are fast, big integers are slow" reality of JavaScript.

### 3. Pointer Tagging Scheme B: Shift-and-Tag Integers (OCaml, Ruby)

OCaml and Ruby use the *low* bit to mark **integers** instead of pointers:

```text
OCaml:   tagged_int(n) = (n << 1) | 1     low bit 1 → "this is an int"
                                          low bit 0 → "this is a pointer"
```

So an OCaml `int` is **63 bits** on a 64-bit platform (one bit spent on the tag). The brilliance: a tagged int with low bit 1 can never be confused with an aligned pointer (low bit 0). Arithmetic is adjusted to keep the tag:

```text
add:  (a + b) - 1        because (2a+1) + (2b+1) = 2(a+b)+2, need 2(a+b)+1
sub:  (a - b) + 1
mul:  (a>>1) * (b>>1) ... then re-tag   // multiplication must untag first
```

Ruby (MRI) generalizes this: the low bits encode several immediate kinds. Historically `Fixnum` (now folded into `Integer`) used the lowest bit; `nil`, `true`, `false`, and `Symbol` get their own immediate bit patterns. A value is a heap object only if none of the immediate tags match.

### 4. Ruby's Immediate Encoding (Concrete)

In MRI Ruby on a 64-bit platform, a `VALUE` (one word) encodes:

```text
...xxxx1     Fixnum:  (n << 1) | 1          (integer, 63-bit-ish)
0x00         Qfalse   (false is literally 0 — also "falsy" test is cheap)
0x08         Qnil     (nil)
0x14         Qtrue
...xx1100    Symbol   (specific low-bit pattern)
low bits 000 heap object pointer (RObject, RString, ...)
```

The exact constants vary by version, but the shape is permanent: **a handful of immediate bit patterns, then "everything else is a pointer."** This is why `nil`, `true`, `false`, small integers, and symbols are never allocated in Ruby — they're values, not objects, even though Ruby pretends "everything is an object."

### 5. The IEEE-754 Double, and Where NaN Hides

A 64-bit double:

```text
 bit 63    bits 62..52        bits 51..0
┌──────┬──────────────────┬────────────────────────────┐
│ sign │ exponent (11 b)  │ fraction / mantissa (52 b)  │
└──────┴──────────────────┴────────────────────────────┘
```

The value is **NaN** when the exponent is all ones (`0x7FF`) *and* the fraction is non-zero. Count the patterns: 11 exponent bits forced to 1, the sign free, and any of the 2⁵² − 1 non-zero fractions. That is **2 × (2⁵² − 1) ≈ 2⁵³ distinct NaN bit patterns** — and a program only ever needs *one* NaN. The rest are free storage.

The top fraction bit (bit 51) distinguishes **quiet** (1) from **signaling** (0) NaNs. NaN-boxing uses quiet NaNs to avoid raising FP exceptions, leaving roughly **51 payload bits** to carry data:

```text
NaN-box skeleton:
┌──────┬──────────────────┬─┬───────────────────────────┐
│ sign │ 1111111 1111 (=NaN)│q│  ~48-bit payload (ptr/int) │
└──────┴──────────────────┴─┴───────────────────────────┘
                            ^ quiet bit
```

### 6. Why a Pointer Fits in the Payload

A 51-bit payload sounds tight for a 64-bit pointer — but real pointers don't use 64 bits. On x86-64 today, only **48 bits** of virtual address are meaningful (the "canonical" form sign-extends bit 47 into the top 16). ARM64 is similar (48 bits, optionally 52 with extensions). So a userspace pointer is *effectively 48 bits*, which slots neatly into the NaN payload with bits left over for a small tag distinguishing pointer-payloads from integer-payloads from immediate-payloads.

This is the keystone of NaN-boxing: **48-bit pointers + 51-bit NaN payload ⇒ a pointer fits, with room for a tag.** `professional.md` covers what happens when that 48-bit assumption is challenged (5-level paging, ARM PAC).

### 7. Tag Check and Untag: What the CPU Actually Does

Every operation on a tagged or NaN-boxed value begins by asking "what kind is this?" The check must be cheap — ideally one or two instructions, predictable for the branch predictor.

```text
Pointer tagging (V8-style):
  is_smi:     test low bit          (1 instr)
  untag smi:  arithmetic shift      (1 instr)
  untag ptr:  clear/subtract tag    (1 instr)

NaN-boxing:
  is_double:  is the exponent NOT all-ones, OR is it the one real NaN?  (compare)
  is_boxed:   (bits & QNAN_MASK) == QNAN_MASK                            (and + compare)
  untag ptr:  bits & PAYLOAD_MASK                                        (and)
```

The whole reason these schemes exist is that the check and untag are a handful of cheap, branch-predictable instructions — orders of magnitude cheaper than a heap allocation plus a cache-missing pointer dereference.

---

## Code Examples

### C — Alignment really does zero the low bits

```c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

int main(void) {
    for (int i = 0; i < 4; i++) {
        void *p = malloc(64);            // typically 16-byte aligned
        uintptr_t a = (uintptr_t)p;
        printf("addr=%p  low3=%lu\n", p, (unsigned long)(a & 0x7));
        free(p);
    }
    return 0;
}
```

The `low3` column prints `0` every time: heap allocations are aligned, so the bottom three bits are free for tagging.

### C — A minimal tagged-pointer scheme (Ruby/OCaml style)

```c
#include <stdio.h>
#include <stdint.h>

typedef uintptr_t Value;

// low bit 1 => small int (63-bit); low bit 0 => pointer
static inline Value tag_int(intptr_t n)   { return (Value)((n << 1) | 1); }
static inline int   is_int(Value v)       { return v & 1; }
static inline intptr_t untag_int(Value v) { return (intptr_t)v >> 1; }   // arithmetic shift

static inline Value tag_ptr(void *p)      { return (Value)p; }            // low bit already 0
static inline int   is_ptr(Value v)       { return (v & 1) == 0; }
static inline void *untag_ptr(Value v)    { return (void *)v; }

// Tagged addition keeps the tag: (2a+1)+(2b+1) = 2(a+b)+2  =>  result - 1
static inline Value add_tagged(Value a, Value b) { return a + b - 1; }

int main(void) {
    Value a = tag_int(20), b = tag_int(22);
    Value c = add_tagged(a, b);
    printf("is_int(c)=%d  value=%ld\n", is_int(c), (long)untag_int(c)); // 1, 42
    return 0;
}
```

This is the *actual* arithmetic OCaml emits for tagged ints: addition is `a + b - 1`, no untag needed; multiplication must untag first.

### C — Sketching NaN-box encode/decode

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>

// Quiet-NaN mask: exponent all ones + quiet bit. Pointer payload in low 48 bits.
#define QNAN      0x7FFC000000000000ULL
#define SIGN_BIT  0x8000000000000000ULL
#define TAG_PTR   (QNAN | SIGN_BIT)            // pointers: set sign + qNaN
#define PAYLOAD   0x0000FFFFFFFFFFFFULL        // low 48 bits

typedef uint64_t Value;

static Value from_double(double d) { Value v; memcpy(&v, &d, 8); return v; }
static double to_double(Value v)   { double d; memcpy(&d, &v, 8); return d; }

static int    is_double(Value v) { return (v & QNAN) != QNAN; }
static Value  box_ptr(void *p)   { return TAG_PTR | ((uint64_t)p & PAYLOAD); }
static void  *unbox_ptr(Value v) { return (void *)(uintptr_t)(v & PAYLOAD); }

int main(void) {
    Value d = from_double(3.14);
    printf("is_double(3.14) = %d  -> %g\n", is_double(d), to_double(d)); // 1 -> 3.14

    int local = 7;
    Value p = box_ptr(&local);
    printf("is_double(ptr) = %d  -> *p = %d\n", is_double(p), *(int*)unbox_ptr(p)); // 0 -> 7
    return 0;
}
```

A real double passes the `is_double` test; a boxed pointer fails it (its bits collide with the qNaN pattern). The pointer survives a round-trip through the 48-bit payload. `senior.md` extends this to ints and immediates.

### JavaScript — Watching SMI vs HeapNumber boundaries

```javascript
// Conceptually: small integers are SMIs (fast, inline); others are HeapNumbers (boxed).
const SMI_MAX = 2 ** 31 - 1;   // V8 32-bit-build SMI range (illustrative)

console.log(Number.isInteger(SMI_MAX));        // true
console.log(Number.isInteger(SMI_MAX + 1));    // true, but now likely a HeapNumber/double
console.log(0.1 + 0.2 === 0.3);                // false — always a double, FP rounding

// Integer-keyed arrays stay on the fast (SMI) path:
const fast = [1, 2, 3];        // packed SMI elements
const slow = [1.5, 2.5];       // packed double elements (different internal kind)
```

You can't see SMIs directly, but the performance cliff at large integers and the "packed elements kind" transitions are their observable shadow.

---

## Coding Patterns

### Pattern 1: Tag check before every use

```c
if (is_int(v))      handle_int(untag_int(v));
else                handle_ptr(untag_ptr(v));
```

Never dereference or arithmetic-on a tagged value without first asking its kind.

### Pattern 2: Keep the tag through arithmetic

```c
// OCaml-style add avoids untag/retag:
Value sum = a + b - 1;     // not untag, add, retag
```

Fold the tag fix-up into the operation rather than round-tripping through the untagged form.

### Pattern 3: Reserve one canonical NaN

```c
// Use a single, well-known qNaN for genuine NaN results so it never
// collides with the boxed-value tag space.
#define CANONICAL_NAN 0x7FF8000000000000ULL
```

### Pattern 4: Branch on "is it a double?" first

```c
if (is_double(v)) return fast_float_op(to_double(v));
return slow_path(v);   // int / ptr / immediate
```

Because floats are the no-op fast path in NaN-boxing, test for them first.

---

## Best Practices

- **Make the fast path branch-predictable.** Order tag checks so the common case (small int or double) is the first, predicted branch. A mispredict can cost more than the work.
- **Sign-extend tagged integers correctly.** Untagging must use an *arithmetic* shift, or negative numbers come back wrong.
- **Pick quiet NaNs, never signaling.** Signaling NaNs can raise FP exceptions; box only into quiet-NaN space.
- **Document the bit layout as law.** Write the exact masks and tag constants in one header with a diagram. Everyone touching the VM must agree on it.
- **Centralize encode/decode.** All boxing/tagging goes through a handful of `inline` functions, never ad-hoc bit-twiddling at call sites.
- **Test the boundaries.** Tagged-int overflow, the SMI range edge, the largest pointer, the canonical NaN — these are exactly where bugs hide.
- **Keep a debug "describe value" function.** Given a raw word, print whether it's a double, int, pointer, or immediate. Invaluable when debugging.

---

## Edge Cases & Pitfalls

- **Logical vs arithmetic shift on untag.** Untag a negative tagged int with a logical shift and you get a huge positive number. Use signed (arithmetic) shift.
- **Tagged-int overflow.** `(a << 1)` can overflow the word for near-maximal ints; runtimes detect overflow and promote to a boxed bignum/HeapNumber.
- **The real NaN vs boxed values.** A genuine `NaN` result from `0.0/0.0` must use a bit pattern that doesn't collide with any boxed tag — hence the *canonical* NaN convention.
- **Negative-zero and infinities.** `-0.0` and `±Inf` are normal doubles (exponent all ones but fraction *zero* for Inf), so they pass `is_double` — make sure your NaN test checks the fraction, not just the exponent.
- **Pointer alignment assumptions.** If any object is *under*-aligned (e.g., a `char`-aligned interior pointer), its low bits aren't zero and tagging breaks. Only tag pointers you control the allocation of.
- **Multiplication of tagged ints.** Unlike add/sub, multiply needs an explicit untag of one operand, or the tag bits multiply into garbage.
- **48-bit pointer assumption.** NaN-boxing silently assumes the top 16 bits of a pointer are sign-extension filler. On systems that use those bits, this breaks (see `professional.md`).

---

## Common Mistakes

1. **Untagging with `>>` (logical) instead of arithmetic shift.** Corrupts negative integers.
2. **Forgetting to fix the tag after arithmetic.** `a + b` on two tagged ints yields `2(a+b)+2`, off by the tag.
3. **Testing only the exponent for NaN.** Infinity has the same all-ones exponent but zero fraction; you'll misclassify it as boxed.
4. **Boxing into a signaling NaN.** Raises FP exceptions on some platforms; use quiet NaNs.
5. **Tagging a pointer that isn't aligned.** Its low bits aren't zero; the tag corrupts the address.
6. **Assuming SMIs cover all integers.** They don't; large ints fall off the fast path to HeapNumber/bignum.
7. **Hard-coding the 48-bit pointer width.** Works today on x86-64/ARM64 userspace, but it's an architectural assumption, not a law.
8. **Scattering bit masks across the codebase.** Guarantees that one place gets the layout subtly wrong.

---

## Tricky Points

- **The tag lives in *unused* bits, so it's "free" — until you use the value.** The cost is deferred to every untag, not paid at storage time. Whether tagging wins depends on the read/write ratio of the workload.
- **NaN-boxing inverts the common/rare distinction.** Boxing makes ints fast and doubles slow (doubles get boxed); NaN-boxing makes doubles fast and ints "fast enough" (ints live in the payload). Choose based on whether your language's hot values are integers or floats.
- **There's a "nun-boxing" inverse.** Instead of pointers being the special-cased payload and doubles canonical, you can make *pointers* canonical and offset all doubles by a constant so no real value collides with NaN. JavaScriptCore's encoding is closer to this spirit. The choice tunes which operation is cheapest.
- **Tag checks interact with the branch predictor.** A polymorphic site (sometimes int, sometimes pointer) mispredicts and stalls; a monomorphic site is nearly free. This is why these encodings pair with inline caches and hidden classes.
- **Alignment guarantees are an ABI contract, not a hardware law.** They hold because the allocator promises them. Tag only memory you allocated under that promise.

---

## Apply it

1. Find a real component where **Boxing, Tagging & NaN-Boxing** affects an interface or dependency.
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

- Which boundary is most affected by Boxing, Tagging & NaN-Boxing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
