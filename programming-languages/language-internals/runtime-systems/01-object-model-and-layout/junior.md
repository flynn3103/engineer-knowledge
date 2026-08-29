# Object Model & Layout — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Object Model & Layout** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A Field Is Just an Offset

Take this C struct:

```c
struct Point {
    int x;   // offset 0
    int y;   // offset 4
};
```

`struct Point` is 8 bytes. `x` lives at offset 0, `y` at offset 4. When you write `p.y`, the compiler emits "load 4 bytes from address-of-`p` + 4." The name `y` exists only in your source code; at runtime there is only the number 4.

This is the single most important idea on this page: **field access is a constant offset, computed at compile time, free at runtime.** Most of the clever machinery in fast runtimes (hidden classes, shapes) exists to *preserve* this property — to keep field access as a fixed `+offset` rather than a dictionary lookup.

### 2. Alignment: The CPU Likes Round Addresses

The CPU does not read memory one byte at a time. It reads in chunks, and it is fastest (or on some chips, *only correct*) when a value sits at an address that is a multiple of its size. A 4-byte `int` "wants" to start at an address divisible by 4. An 8-byte `double` or pointer wants an address divisible by 8.

This requirement is called **alignment**. A type's alignment is usually equal to its size (for primitives). The rule: **a field of alignment A must be placed at an offset that is a multiple of A.**

### 3. Padding: The Price of Alignment

What happens when fields don't naturally line up? The compiler inserts **padding** — wasted filler bytes — to push the next field onto an aligned offset.

```c
struct Bad {
    char  a;   // offset 0, size 1
    // 3 bytes of PADDING here, so the int is aligned to 4
    int   b;   // offset 4, size 4
    char  c;   // offset 8, size 1
    // 3 bytes of PADDING at the end, so the struct's size is a multiple of 4
};
// sizeof(Bad) == 12, even though 1 + 4 + 1 = 6 bytes of real data.
```

Half the struct is air. The struct's own alignment is the **largest** alignment of its fields (here 4, because of `b`), and the total size is rounded up to a multiple of that — which is why there's trailing padding too.

### 4. Reordering Fields Shrinks the Struct

Here is the trick that looks like magic. Take the same three fields and reorder them, biggest-alignment-first:

```c
struct Good {
    int   b;   // offset 0, size 4
    char  a;   // offset 4, size 1
    char  c;   // offset 5, size 1
    // 2 bytes of trailing padding
};
// sizeof(Good) == 8.
```

Same data, **12 bytes shrank to 8** — a 33% saving — purely by reordering. The general rule of thumb: **declare fields from largest alignment to smallest.** Pointers and 8-byte values first, then 4-byte, then 2-byte, then bytes. The padding collapses.

For one struct, 4 bytes is nothing. For a million-element array of that struct, it's 4 MB of pure waste — and worse, it means fewer objects fit in each cache line, so your loops touch more memory and run slower.

### 5. The Object Header: Bytes You Didn't Declare

In C and Rust, a plain struct is *just* your fields (plus padding). Nothing extra. But in most managed runtimes, every object carries a **header** the runtime needs:

- **Java (HotSpot):** every object has a **mark word** (hash code, lock state, GC age bits) and a **class pointer** (which class is this?). On a 64-bit JVM that's typically 12–16 bytes *before your first field even starts*.
- **Python (CPython):** every object begins with a **reference count** and a **type pointer**. A bare `object` is already 16 bytes; a Python `int` is ~28 bytes.
- **C++ with virtual methods:** an object with virtual functions carries a hidden **vtable pointer** (8 bytes) so the runtime can find the right method.
- **Go, Rust, C structs:** *no per-object header* for plain values. This is a big reason they're memory-lean.

The lesson: **a 4-byte `int` field can cost you 20+ bytes once you make it a heap object in a managed language.** Headers are the tax for features like garbage collection, reflection, and dynamic typing.

### 6. Boxed vs Inline

When you put a number inside a container, it can live one of two ways:

- **Inline (unboxed):** the bytes of the number sit directly inside the container. `struct Point { int x; }` stores `x`'s four bytes *in* the Point. Fast, compact, one memory access.
- **Boxed:** the container holds a *pointer* to a separate heap object that holds the number. Java's `Integer`, Python's `int`, a `List<Integer>` of boxed integers. Each access is a pointer hop, and each number carries a full object header.

A `int[]` in Java is a tight block of 4-byte integers (inline). An `Integer[]` is an array of *pointers*, each pointing to a separate ~16-byte heap object (boxed). Same logical data, wildly different memory and speed. Knowing which you have is a junior-level superpower.

### 7. Array of Structs vs Struct of Arrays (a First Look)

Say you have 1,000 particles, each with a position and a velocity. Two ways to store them:

```
AoS (Array of Structs):   [ {pos,vel}, {pos,vel}, {pos,vel}, ... ]
SoA (Struct of Arrays):   { pos:[...,...,...], vel:[...,...,...] }
```

If your loop only reads `pos` for all particles, **SoA is faster**: all the positions are packed together, so each cache line you fetch is 100% useful. With **AoS**, every cache line you fetch also drags in the `vel` you didn't want, wasting bandwidth.

If you usually touch *all* fields of one particle at a time, **AoS wins** — everything for one particle is together. There's no universal winner; it depends on your access pattern. We'll go deeper in `middle.md`. For now: **layout should follow how you read the data.**

---

## Code Examples

### C — Watching padding happen

```c
#include <stdio.h>
#include <stddef.h>

struct Bad  { char a; int b; char c; };   // poorly ordered
struct Good { int b; char a; char c; };   // well ordered

int main(void) {
    printf("sizeof(Bad)  = %zu\n", sizeof(struct Bad));   // 12
    printf("sizeof(Good) = %zu\n", sizeof(struct Good));  // 8

    printf("offset a=%zu b=%zu c=%zu (Bad)\n",
        offsetof(struct Bad, a), offsetof(struct Bad, b), offsetof(struct Bad, c));
    // a=0  b=4  c=8   <- note the gap: b is NOT at offset 1
    return 0;
}
```

Run it. The compiler told you, in numbers, exactly where padding went. `b` is at offset 4, not 1, because of the 3 padding bytes after `a`.

### C — Packing to remove padding (with a warning)

```c
#include <stdio.h>

#pragma pack(push, 1)
struct Packed { char a; int b; char c; };  // forced to 6 bytes, no padding
#pragma pack(pop)

int main(void) {
    printf("sizeof(Packed) = %zu\n", sizeof(struct Packed));  // 6
    return 0;
}
```

`#pragma pack(1)` says "no padding, ever." The struct is now 6 bytes — but `b` is now *misaligned* (offset 1). On some CPUs that's slower; on a few it's a crash. Use packing only for wire formats (network/file structs), never as a default. We'll revisit this in `middle.md`.

### Java — Boxed vs inline, the size surprise

```java
// int[] is a tight block of 4-byte integers — inline.
int[] inline = new int[1_000_000];        // ~4 MB of data

// Integer[] is an array of pointers, each to a separate heap object — boxed.
Integer[] boxed = new Integer[1_000_000]; // ~4 MB of pointers
for (int i = 0; i < boxed.length; i++) boxed[i] = i;  // + ~16 MB of Integer objects
```

The `int[]` is one compact array. The `Integer[]` is an array of 8-byte pointers *plus* a million separate `Integer` objects, each carrying a 12–16 byte header around a single 4-byte value. Same logical data, roughly 5x the memory and far worse cache behavior. **Prefer primitive arrays for bulk numeric data.**

### Python — Every object carries a header

```python
import sys

print(sys.getsizeof(0))          # ~28 bytes for a single small int!
print(sys.getsizeof([]))         # ~56 bytes for an empty list
print(sys.getsizeof("a"))        # ~50 bytes for a one-char string
```

A Python `int` is not 4 or 8 bytes — it's a full heap object with a reference count and a type pointer baked in, so even the number `0` costs ~28 bytes. This is why number-crunching in pure Python is slow and memory-heavy, and why NumPy (which stores raw, header-free C arrays) is so much leaner and faster.

### Go — Struct alignment, the same rules as C

```go
package main

import (
    "fmt"
    "unsafe"
)

type Bad  struct { a byte; b int32; c byte }  // poorly ordered
type Good struct { b int32; a byte; c byte }  // well ordered

func main() {
    fmt.Println(unsafe.Sizeof(Bad{}))   // 12
    fmt.Println(unsafe.Sizeof(Good{}))  // 8
}
```

Go has the same padding and alignment rules as C. `unsafe.Sizeof` and `unsafe.Offsetof` let you inspect them. Field ordering matters in Go too — `go vet` and tools like `fieldalignment` will warn you about wasteful structs.

### Rust — Plain structs are just your fields (the compiler may even reorder them)

```rust
struct Point { x: i32, y: i32 }   // 8 bytes, no header

fn main() {
    println!("{}", std::mem::size_of::<Point>());  // 8
}
```

A Rust struct, like a C one, has **no per-object header** — `Point` is exactly 8 bytes. Unlike C, the Rust compiler is *allowed to reorder your fields* to minimize padding automatically (unless you ask for a fixed layout with `#[repr(C)]`). So you often get the "Good" packing for free.

---

## Coding Patterns

### Pattern 1: Order fields largest-alignment-first

```c
// Instead of declaring in "logical" order, group by size:
struct Entity {
    void*    parent;   // 8-byte pointer first
    uint64_t id;       // 8
    int32_t  x, y;     // 4 + 4
    int16_t  hp;       // 2
    uint8_t  flags;    // 1
    bool     alive;    // 1
};  // packs tightly, minimal padding
```

Pointers and 8-byte values first, then 4, then 2, then 1-byte fields. The padding collapses on its own.

### Pattern 2: Prefer primitive arrays over boxed collections for bulk numbers

```java
int[] scores = new int[n];          // good: tight, inline
// not:
List<Integer> scores = new ArrayList<>();  // boxed: header per element
```

### Pattern 3: Use packed layout *only* for wire structs

```c
#pragma pack(push, 1)
struct WirePacket { uint8_t type; uint32_t length; uint16_t checksum; };
#pragma pack(pop)
// Exact 7-byte layout to match a network protocol. NOT for in-memory hot data.
```

### Pattern 4: Reach for SoA when a loop touches one field across many objects

```c
// AoS: struct Particle { float x, y, z, vx, vy, vz; } particles[N];
// SoA, if your update loop only reads positions:
struct Particles { float x[N], y[N], z[N], vx[N], vy[N], vz[N]; };
// Updating all x[] now streams contiguous memory — cache-friendly and vectorizable.
```

### Pattern 5: Measure size, don't guess

```c
printf("%zu\n", sizeof(struct Thing));          // C
```
```go
fmt.Println(unsafe.Sizeof(Thing{}))              // Go
```
```rust
println!("{}", std::mem::size_of::<Thing>());    // Rust
```

Always confirm with a real number before and after you reorder. Surprises are common.

---

## Best Practices

- **Group fields by descending alignment.** It's free and routinely shrinks structs 20–40%.
- **Measure `sizeof` before and after.** Don't trust your mental arithmetic; the tool is exact.
- **Use primitive arrays (`int[]`, `float[]`) for bulk numeric data.** Avoid boxed collections in hot paths.
- **Reserve `#pragma pack` / `repr(packed)` for wire and file formats.** Never apply it to in-memory hot structures — misalignment costs more than the padding you saved.
- **Let the layout follow the access pattern.** Loop over one field across many objects? Lean SoA. Touch whole objects? AoS.
- **Know your language's per-object header cost.** ~16 bytes in Java/Python is the difference between "this fits in cache" and "it doesn't."
- **Don't fight your runtime early.** Get it correct, profile, then optimize the layout of the structures that actually show up hot.
- **Separate hot fields from cold fields** when an object is huge but loops only touch a few fields (introduced properly in `senior.md`).

---

## Edge Cases & Pitfalls

- **The "sum of my fields" trap.** A struct is almost never the sum of its field sizes. Padding makes it bigger. Always check `sizeof`.
- **Declaration order matters.** `{char, int, char}` and `{int, char, char}` hold identical data but have different sizes. The compiler (in C/Go) does not reorder for you.
- **Boxed numbers everywhere.** A `Map<String, List<Integer>>` in Java can be mostly headers and pointers. The actual numbers are a tiny fraction of the memory.
- **`#pragma pack` makes misaligned fields.** It removes padding but the fields are now off-grid. On x86 it's a slowdown; on some ARM/embedded chips it faults. Don't reach for it casually.
- **A one-char Python string costs ~50 bytes.** Tiny logical data, large physical cost, because of the universal object header. Bulk text belongs in `bytes`/`bytearray` or NumPy, not lists of strings.
- **Arrays of objects are arrays of pointers** in managed languages. `User[]` in Java is a row of pointers, each to a scattered heap object — bad for cache. A flat struct array (where the language allows it) is far better.
- **Endianness in wire structs.** When you pack a struct to send over the network, the byte *order within* a multi-byte field (big-endian vs little-endian) matters. Two machines must agree, or the numbers come out scrambled.
- **Trailing padding is real.** Even if your last field is a single byte, the struct's size is rounded up to its alignment, so there can be padding at the *end* you never see.

---

## Apply it

1. Choose one small, known input for **Object Model & Layout**.
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

- What problem does Object Model & Layout solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
