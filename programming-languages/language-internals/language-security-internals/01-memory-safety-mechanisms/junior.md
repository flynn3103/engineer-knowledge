# Memory-Safety Mechanisms — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory-Safety Mechanisms** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Two Halves: Spatial and Temporal Safety

Everything in memory safety reduces to two questions about any memory access:

1. **Am I inside the bounds of the thing I'm pointing at?** (Spatial.)
2. **Is the thing I'm pointing at still alive?** (Temporal.)

If a language can answer *yes* to both for **every** access, the program is memory-safe. If even one access can sneak through with *no* on either, the door is open.

Think of an allocation as a numbered hotel room block. Spatial safety is "don't enter rooms 200–210 if you booked 100–110." Temporal safety is "don't enter your room after you've checked out and the cleaners (the allocator) have given it to someone else."

### 2. The Bug Taxonomy

There is a small, finite, well-understood list of ways memory safety breaks. Learn these shapes and you can recognize almost every memory bug:

**Spatial bugs (bounds):**

- **Stack buffer overflow** — writing past a fixed-size array that lives on the stack. Dangerous because the stack also holds the *return address* — where the function will jump back to when it finishes. Corrupt that and you can hijack control flow.
- **Heap buffer overflow** — writing past a block you got from the allocator. Corrupts neighbouring heap data or the allocator's metadata.
- **Out-of-bounds read** — reading past the end. Often "just" a crash, but it can *leak* secret data (the classic Heartbleed bug was an OOB read that leaked private keys).

**Temporal bugs (lifetime):**

- **Use-after-free (UAF)** — you `free(p)`, then later read or write `*p`. Meanwhile the allocator handed that memory to a different part of the program. Now two pieces of code think they own the same bytes.
- **Double-free** — `free(p); free(p);`. The allocator's internal free-list gets corrupted, which an attacker can steer.
- **Dangling pointer** — keeping (and using) a pointer to a stack variable after the function returned, or to a heap block after it was freed.

**Other safety holes:**

- **Uninitialized read** — using memory before writing it. You read whatever bytes were left there. Non-deterministic bugs and information leaks.
- **Type confusion** — bytes are valid as type A but you access them as type B (e.g. a bad `union` access or downcast). Pointers inside become wild.
- **Null dereference** — `*p` when `p == NULL`. Usually a clean crash, but still a defect (and a denial-of-service vector).

### 3. Why C and C++ Let These Happen

C was designed in the 1970s to be a thin, fast layer over the hardware. A C array doesn't carry its length around. When you write `arr[i]`, the compiler emits "take the address of `arr`, add `i × element_size`, access that." There is **no check** that `i` is in range — that would cost a comparison and a branch on every access, and 1970s machines were slow. The *programmer* is responsible for never going out of bounds.

Similarly, C makes you call `malloc` to get heap memory and `free` to give it back. The language does not track whether you still have other pointers to that block when you free it. If you do, those pointers are now dangling, and using them is **undefined behavior**.

**Undefined behavior** is the crucial idea. The C standard says: if your program does something illegal (OOB access, UAF, etc.), the standard imposes *no requirements at all* on what happens. It might crash, might silently corrupt data, might appear to work, and crucially the *optimizer* is allowed to assume UB never happens — which can make the bug behave even more strangely. This is why memory bugs in C are so insidious: they often don't crash where the mistake is.

### 4. The Safe-Language Strategies (Overview)

There are four broad ways the industry buys memory safety. You'll meet all of them:

1. **Unsafe by default + discipline + tooling (C/C++).** The language gives no guarantees; you stay safe through care, conventions (always track sizes, always null pointers after freeing), and *tools* that catch mistakes — sanitizers in testing, hardened allocators in production. This is the legacy mountain the industry is trying to climb down from.

2. **Garbage collection (Java, Go, C#, JavaScript, Python).** The runtime inserts **bounds checks** on array access (spatial safety) and manages memory for you with a **garbage collector**, so you never `free` and therefore can't UAF or double-free (temporal safety). This is the most common form of safety today. (Caveat: GC languages still have escape hatches like Java's `sun.misc.Unsafe` and Go's `unsafe`/cgo, and concurrency data races can still break their safety — more on this at higher levels.)

3. **Ownership and borrowing, checked at compile time (Rust).** Rust enforces, *at compile time with zero runtime cost*, that there is a clear owner of every value, and that you can't use a value after it's gone or alias it mutably. Memory bugs become *compile errors*. You opt out only inside explicit `unsafe` blocks. (`senior.md` covers the borrow checker.)

4. **Automatic reference counting (Swift, Objective-C).** Each object carries a count of how many references point to it; when the count hits zero, the object is freed immediately. Safety from never-manually-freeing, like GC, but deterministic. (Its weakness is *reference cycles* — covered later.)

### 5. Bounds Checks: The Workhorse of Spatial Safety

The single most common safety mechanism you'll rely on is the **bounds check**. In Java, Go, C#, Python, Rust — when you index an array, the runtime (or compiled code) first checks `0 <= index < length`. If not, it throws/panics with a clear error (`ArrayIndexOutOfBoundsException`, `index out of range`, a Rust panic) *instead of* silently reading neighbouring memory.

This turns a *silent, exploitable corruption* into a *loud, contained crash*. That trade — a tiny per-access cost for converting catastrophe into a clean failure — is the foundation of safe languages. And modern compilers are clever: when they can *prove* an index is always in range (e.g. a `for i in 0..len` loop), they **eliminate the check** entirely, so you often pay nothing.

### 6. Garbage Collection: The Workhorse of Temporal Safety

If you never call `free`, you can never call it at the *wrong* time. That's the core insight behind garbage collection. The runtime periodically figures out which objects are still **reachable** (something can still get to them by following references from live variables) and reclaims the rest. An object that's still reachable is never freed, so a pointer to it can never dangle.

This eliminates use-after-free, double-free, and most dangling-pointer bugs by construction. The cost is *runtime overhead* (the GC has to run) and *less predictable timing* (pauses). For most applications that's a great trade; for hard-real-time or tiny embedded systems it can be unacceptable, which is part of why C/C++ and Rust still matter.

---

## Code Examples

> ⚠️ These examples *demonstrate the bugs so you can recognize them*. They are deliberately small and defensive — there are no exploits here, just "here is the broken access, here is why a safe language stops it, here is how you'd write it correctly."

### Spatial bug: out-of-bounds write in C

```c
#include <stdio.h>

int main(void) {
    int arr[5];                 // valid indices: 0..4
    for (int i = 0; i <= 5; i++) {   // BUG: <= goes to index 5
        arr[i] = i * i;         // arr[5] writes one int PAST the array
    }
    // The write to arr[5] lands on whatever memory follows `arr`.
    // C does NOT stop you. No error. Maybe a crash, maybe silent corruption.
    return 0;
}
```

The classic "off-by-one." `i <= 5` writes to `arr[0..5]` — six elements into a five-element array. C emits no check. The result is undefined behavior.

### The same logic in Go — caught at runtime

```go
package main

func main() {
    arr := [5]int{}
    for i := 0; i <= 5; i++ {
        arr[i] = i * i // panics at i==5: "index out of range [5] with length 5"
    }
}
```

Go inserts a bounds check. At `i == 5` the program *panics immediately* with a precise message, instead of silently corrupting memory. Same bug, but now it's a loud, debuggable crash at the exact bad line.

### Use-after-free in C

```c
#include <stdlib.h>
#include <string.h>

char *make_greeting(void) {
    char *buf = malloc(16);
    strcpy(buf, "hello");
    return buf;
}

int main(void) {
    char *g = make_greeting();
    free(g);          // memory returned to the allocator
    // ... later, by mistake ...
    g[0] = 'H';       // BUG: use-after-free. `g` is dangling.
    return 0;
}
```

After `free(g)`, the bytes `g` points at may be reused for something else. Writing through `g` now corrupts whatever lives there. Defensive habit: set `g = NULL;` right after freeing so a later use crashes cleanly instead of corrupting.

### Why GC languages can't have this bug

```java
String makeGreeting() {
    return "hello"; // allocated on the GC heap
}

void demo() {
    String g = makeGreeting();
    g = null;        // we drop our reference...
    // There is NO `free`. We cannot free `g` at the wrong time,
    // because we cannot free at all. The GC reclaims it ONLY when
    // nothing can reach it. Use-after-free is impossible by construction.
}
```

### Uninitialized read in C vs. zero-init in Go

```c
int x;            // C: uninitialized, value is garbage (leftover bytes)
printf("%d\n", x); // reads whatever was on the stack. UB to use it.
```

```go
var x int          // Go: ALWAYS zero-initialized to 0
fmt.Println(x)     // prints 0 deterministically. No garbage reads.
```

Many safe languages zero-initialize memory, closing the uninitialized-read hole entirely.

### Catching a C bug with AddressSanitizer (the workflow you'll actually use)

```bash
# Compile the buggy program with AddressSanitizer instrumentation:
clang -fsanitize=address -g overflow.c -o overflow

# Run it. ASan detects the bad access and prints a precise report:
./overflow
# =================================================================
# ==12345==ERROR: AddressSanitizer: stack-buffer-overflow ...
#   WRITE of size 4 at 0x... thread T0
#     #0 0x... in main overflow.c:6:9   <-- exact file and line
```

You don't have to *prevent* every bug by hand. You compile with `-fsanitize=address` during testing, and ASan turns the silent corruption into a precise, instant report naming the exact line. This is the single most important tool a C/C++ junior can adopt.

---

## Coding Patterns

These are habits that make a difference even as a junior.

```c
// 1. Always track sizes alongside buffers (never trust a bare pointer).
void process(const char *data, size_t len) {   // len travels WITH data
    for (size_t i = 0; i < len; i++) { /* ... */ }
}

// 2. Null after free so a later use crashes loudly, not silently.
free(p);
p = NULL;

// 3. Prefer the size-bounded function (snprintf) over the unbounded one (sprintf).
char buf[32];
snprintf(buf, sizeof(buf), "%d", value);  // never overflows buf
```

```go
// 4. In Go/Java/Rust, lean on the language: range loops can't go out of bounds.
for i, v := range items { // i is always valid; no manual index arithmetic
    _ = v
    _ = i
}
```

---

## Best Practices

- **Default to a memory-safe language** for new code unless you have a hard reason not to. This is now official guidance from security agencies (CISA/NSA).
- **In C/C++, always compile your tests with AddressSanitizer** (`-fsanitize=address`). It is nearly free to adopt and catches most of the bugs you'd otherwise ship.
- **Track the length of every buffer** explicitly. A pointer without a known length is an accident waiting to happen.
- **Prefer bounded library functions** (`snprintf`, `strncpy` used carefully, `memcpy` with checked sizes) over unbounded ones (`sprintf`, `strcpy`, `gets` — never use `gets`).
- **Initialize variables when you declare them.** Don't leave a variable to be filled in "later."
- **Set freed pointers to `NULL`** so a later accidental use fails fast.
- **Never disable bounds checks** in safe languages to "go faster" until you've measured that they actually matter (they usually don't — the optimizer removed most).

---

## Edge Cases & Pitfalls

- **A program that "works" is not proof of safety.** Memory bugs in C are undefined behavior; they can be present and dormant. Run sanitizers to find them.
- **Off-by-one is the most common spatial bug.** `<=` instead of `<`, or `len` instead of `len - 1`, walks exactly one element past the end. Watch loop bounds like a hawk.
- **`strcpy`/`sprintf`/`gets` have no idea how big your buffer is.** They write until they hit a terminator, overflowing happily. Treat them as hazards.
- **A null check is not a bounds check.** A pointer can be non-null and still point out of bounds or to freed memory.
- **GC does not mean "no memory bugs."** It means no *use-after-free* from manual frees. You can still leak (keep references you don't need) and still have data races corrupt memory in some runtimes. (More at higher levels.)
- **Sanitizers slow your program down** (ASan ~2×) and use more memory. They're for *testing*, not production.

---

## Common Mistakes

- Assuming "I'm careful" makes C memory-safe. The whole industry is careful and still produces the CVE statistics.
- Using `strcpy`/`sprintf` because the example you copied did.
- Forgetting that an array index can come from *untrusted input* — that's exactly how an OOB bug becomes a security hole.
- Reading a `malloc`'d buffer before writing it (`malloc` does *not* zero memory; `calloc` does).
- Thinking a `Segmentation fault` is the *only* symptom of a memory bug. Many memory bugs never segfault — they silently corrupt.

---

## Tricky Points

- **Why doesn't C just add bounds checks?** Because a C array is *just a pointer* — at the point of access, the length isn't even available. The language threw it away. Safe languages keep arrays as "pointer **+ length**" (a "fat" representation) so the check is *possible*.
- **Why is an out-of-bounds *read* dangerous if it doesn't corrupt anything?** It can *leak secrets*. Heartbleed read past a buffer and returned server memory — including private keys — to attackers.
- **Why is use-after-free worse than a simple crash?** Because the freed memory often gets *reused* for a different object. An attacker who can control *what* gets placed there can make your dangling pointer operate on attacker-chosen data. That's how UAF becomes code execution.

---

## Apply it

1. Choose one small, known input for **Memory-Safety Mechanisms**.
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

- What problem does Memory-Safety Mechanisms solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
