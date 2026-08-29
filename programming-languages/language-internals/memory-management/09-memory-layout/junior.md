# Memory Layout — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory Layout** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The hardware wants aligned data

The CPU reads memory in fixed-size, aligned chunks (often 8 bytes at a time, and 64 bytes per cache line). If a 4-byte integer sits neatly at an address divisible by 4, the CPU grabs it in one operation. If it straddles a boundary — say bytes 6 through 9 — the CPU may need **two** reads and some stitching, which is slower. On some architectures (older ARM, many DSPs) a misaligned read does not just go slow: it **faults** and crashes the program.

So compilers play it safe: they place each field at a "natural" address for its type. The rule is simple:

> A field of size *N* is placed at an offset that is a multiple of its alignment (usually *N*).

### 2. Padding fills the gaps

Consider this C struct:

```c
struct Bad {
    char  a;   // 1 byte
    int   b;   // 4 bytes
    char  c;   // 1 byte
};
```

You might expect 1 + 4 + 1 = 6 bytes. The actual size is **12**. Here is why, offset by offset:

| Offset | Bytes | Field | Note |
|-------:|:-----:|-------|------|
| 0      | 1     | `a`   | char, aligns anywhere |
| 1–3    | 3     | —     | **padding** so `b` lands on a multiple of 4 |
| 4–7    | 4     | `b`   | int, needs 4-byte alignment |
| 8      | 1     | `c`   | char |
| 9–11   | 3     | —     | **trailing padding** so the struct size is a multiple of 4 |

Total: 12 bytes. Six of them are wasted padding.

### 3. Field order changes the size

Now reorder the *same fields*, largest-to-smallest:

```c
struct Good {
    int   b;   // 4 bytes, offset 0
    char  a;   // 1 byte,  offset 4
    char  c;   // 1 byte,  offset 5
};             // offset 6,7: 2 bytes trailing padding -> size 8
```

Same data, but now the size is **8 bytes** instead of 12 — a 33% saving, just from ordering. The two `char`s share the gap that used to be wasted, and only 2 bytes of trailing padding remain.

> **The golden rule:** order struct fields from **largest alignment to smallest**. This minimizes padding almost every time.

### 4. Trailing padding and arrays

Why trailing padding at all? Because structs go into **arrays**. If `struct Good` were 6 bytes, then in an array `Good arr[2]`, the second element would start at offset 6 — and its `int b` would be misaligned. By rounding the struct size up to 8 (a multiple of its largest alignment), every element in an array stays aligned. The struct's *alignment* equals its largest field's alignment; its *size* is always a multiple of that alignment.

---

## Code Examples

### C — measure the difference

```c
#include <stdio.h>

struct Bad  { char a; int b; char c; };           // 12 bytes
struct Good { int b; char a; char c; };            // 8 bytes

int main(void) {
    printf("Bad  = %zu\n", sizeof(struct Bad));    // 12
    printf("Good = %zu\n", sizeof(struct Good));   // 8
    printf("sum of fields = %zu\n",
           sizeof(char) + sizeof(int) + sizeof(char)); // 6
    return 0;
}
```

The "sum of fields" (6) matches neither layout — proof that `sizeof` is *not* the sum of the parts.

### Go — `unsafe.Sizeof` and `Offsetof`

```go
package main

import (
    "fmt"
    "unsafe"
)

type Bad struct {
    A byte  // 1
    B int32 // 4
    C byte  // 1
}

type Good struct {
    B int32 // 4
    A byte  // 1
    C byte  // 1
}

func main() {
    fmt.Println(unsafe.Sizeof(Bad{}))  // 12
    fmt.Println(unsafe.Sizeof(Good{})) // 8

    // Where does each field actually live?
    fmt.Println(unsafe.Offsetof(Bad{}.A)) // 0
    fmt.Println(unsafe.Offsetof(Bad{}.B)) // 4  (offsets 1-3 are padding)
    fmt.Println(unsafe.Offsetof(Bad{}.C)) // 8
}
```

### Rust — `size_of` and the same rule

```rust
use std::mem::size_of;

struct Bad  { a: u8, b: u32, c: u8 }   // Rust may reorder; force C layout below
#[repr(C)] struct BadC  { a: u8, b: u32, c: u8 } // 12
#[repr(C)] struct GoodC { b: u32, a: u8, c: u8 } // 8

fn main() {
    println!("{}", size_of::<BadC>());  // 12
    println!("{}", size_of::<GoodC>()); // 8
    // Note: plain Rust structs (no repr) let the compiler reorder fields
    // for you, so `Bad` may already be 8. C/Go keep your declared order.
}
```

> Key difference to remember: **C and Go keep your field order exactly as written**, so ordering is *your* job. **Rust is allowed to reorder fields itself** unless you pin the layout with `#[repr(C)]`.

---

## Best Practices

1. **Order fields largest-alignment-first** when you control the order (Go, C, plain Rust where layout is unspecified anyway). Group your `int64`s/pointers, then `int32`s/`float`s, then `int16`s, then `byte`s/`bool`s.
2. **Measure, don't guess.** Print `sizeof`/`unsafe.Sizeof`/`size_of` and field offsets. Surprises are common.
3. **Group related small fields together** so they share one padding gap instead of each creating its own.
4. **Don't micro-optimize one-off structs.** A config struct you allocate once is not worth reordering for readability's sake. Save the effort for structs that exist in bulk.
5. **Keep a meaningful order when it aids readability**, and only reorder for size when the struct is genuinely hot or numerous.

---

## Edge Cases & Pitfalls

- **`sizeof` ≠ sum of fields.** This trips up nearly everyone the first time. Always account for padding.
- **Booleans cost more than a bit.** A `bool` takes a whole byte (sometimes more after padding), not one bit. Eight `bool` fields can balloon a struct; consider bit flags if it matters.
- **Empty structs are not always zero-sized.** In Go an empty struct is 0 bytes; in C `sizeof(struct{})` is 1 by language rule (so distinct objects get distinct addresses). Languages differ — check.
- **Nested structs carry their own alignment.** Embedding a struct whose largest field is 8 bytes raises the outer struct's alignment to 8, which can add padding before the nested field.
- **Reordering breaks binary layouts.** If a struct is read/written to disk, sent over a socket, or maps onto hardware registers, the field order is a contract. Do not reorder those without updating both sides.
- **The compiler may reorder for you (Rust).** Don't rely on declared order in Rust unless you used `#[repr(C)]` — and don't reorder a `#[repr(C)]` struct thinking it's free.

---

## Apply it

1. Choose one small, known input for **Memory Layout**.
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

- What problem does Memory Layout solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
