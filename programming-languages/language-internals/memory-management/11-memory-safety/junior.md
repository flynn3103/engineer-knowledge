# Memory Safety — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory Safety** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Two kinds of safety: spatial and temporal

Almost every memory bug falls into one of two buckets.

**Spatial safety** is about *location*. Every allocated object occupies a range of addresses. Spatial safety means you never read or write outside that range. The classic violation is the **buffer overflow**: you have a 10-element array and you touch index 10, 11, or -1. You are now reading or corrupting whatever memory happens to sit next to your array — another variable, a return address, allocator bookkeeping.

**Temporal safety** is about *time*. Memory has a lifetime: it becomes valid when allocated and invalid when freed (or when a local variable goes out of scope). Temporal safety means you never access memory outside its valid lifetime. The classic violation is **use-after-free**: you free a block, but a pointer still points at it, and later you dereference that pointer. The bytes might still be there, might be zeroed, or might have been reused for something completely different.

A memory-safe language guarantees *both*. A language like C guarantees *neither* on its own.

### The main categories of violation

You do not need to know how to exploit these — only to recognize them so you can prevent them. As a junior engineer your job is mostly to write code that cannot produce them in the first place.

- **Buffer overflow / underflow** — accessing index `n` or beyond in an `n`-element buffer (overflow), or before index 0 (underflow). Spatial.
- **Use-after-free** — dereferencing a pointer to already-freed memory. Temporal.
- **Double-free** — calling `free` twice on the same pointer; corrupts the allocator's internal data. Temporal.
- **Dangling pointer** — a pointer to an object that no longer exists (freed, or a local that went out of scope). Temporal.
- **Uninitialized read** — reading a variable before any value was written to it; you get leftover garbage bytes.
- **Null pointer dereference** — following a pointer that is null/zero. (Usually a crash rather than a silent corruption — relatively benign, but still a bug.)

### Why these are dangerous, not just buggy

A logic bug gives a wrong answer. A memory-safety bug can do something far worse: it can silently corrupt *unrelated* data, leak secrets that happened to sit in adjacent memory, or — in the hands of an attacker — let outside input overwrite the program's control flow and run attacker-chosen code. That is why memory-safety bugs dominate the *severe* CVE lists. They turn an ordinary mistake into a potential remote takeover.

### How safe languages prevent all of this

Most languages you have used are memory-safe, and they achieve it with a small set of design choices:

- **No raw pointer arithmetic.** You cannot fabricate an arbitrary address. References point at real objects, full stop.
- **Bounds checking.** Every array access is checked at runtime; an out-of-range index raises an exception/panic instead of corrupting memory. (Java throws `ArrayIndexOutOfBoundsException`, Python raises `IndexError`, Go panics.)
- **Automatic memory management (GC).** Memory is freed only when nothing can still reach it, so use-after-free and double-free are structurally impossible in safe code. Languages like Java, Go, Python, C#, and JavaScript all use this.
- **Mandatory initialization (or default values).** Variables start with a defined value (e.g., zero), so uninitialized reads don't happen.

There is a second, newer way to be safe — **Rust** — that achieves the same guarantees *without* a garbage collector, using compile-time ownership rules. You'll meet that idea properly in the middle and senior tiers; for now just know it exists.

---

## Code Examples

### Spatial violation (conceptual C) vs. safe languages

```c
// C — NOT memory-safe. This compiles and may "work" until it doesn't.
int arr[10];
arr[10] = 42;     // out of bounds — undefined behavior, silently corrupts neighbors
```

```python
# Python — bounds are checked. The mistake becomes a clean, catchable error.
arr = [0] * 10
arr[10] = 42       # raises IndexError: list assignment index out of range
```

```java
// Java — same idea, a thrown exception instead of corruption.
int[] arr = new int[10];
arr[10] = 42;      // throws ArrayIndexOutOfBoundsException
```

The C version is *more dangerous than a crash*: it might not crash at all, just quietly damage something else.

### Temporal violation (conceptual) vs. safe languages

```c
// C — use-after-free. The pointer outlives the object.
int *p = malloc(sizeof(int));
*p = 5;
free(p);
int x = *p;        // use-after-free — undefined behavior
```

```go
// Go — you cannot manually free. The GC keeps memory alive as long as
// any reference (here, p) can reach it, so use-after-free cannot happen.
p := new(int)
*p = 5
// no free() exists; memory is reclaimed only after p is unreachable
x := *p            // always valid
_ = x
```

### Uninitialized read

```c
// C — reading garbage.
int x;             // not initialized
printf("%d", x);   // reads whatever was on the stack — undefined behavior
```

```go
// Go — every variable has a defined zero value.
var x int          // x == 0, guaranteed
fmt.Println(x)     // prints 0, always
```

---

## Best Practices

1. **Default to a memory-safe language.** Unless you have a hard reason (existing C/C++ codebase, no runtime allowed), pick a safe language. The burden of proof is on choosing the unsafe option.
2. **Treat out-of-bounds exceptions as real bugs.** An `IndexError` or `ArrayIndexOutOfBoundsException` is the safe language catching a mistake. Fix the logic; don't just wrap it in a try/catch and move on.
3. **Initialize variables explicitly** even in languages with defaults, to make intent clear.
4. **Be suspicious of `unsafe`, `unchecked`, or FFI code.** These are the doors where memory safety stops. You'll learn to handle them carefully in later tiers; as a junior, prefer not to write them.
5. **Don't fight the garbage collector** by trying to "manually manage" memory through tricks. Let it do its job.

---

## Edge Cases & Pitfalls

- **"Memory-safe" ≠ "bug-free."** Safe languages still have null-related errors, logic errors, leaks, and concurrency bugs. Safety removes a *category*, not all bugs.
- **Garbage collection does not prevent memory *leaks*.** If you keep a reference around (e.g., an object stuck in a long-lived list or cache), the GC must keep it alive forever. That's a leak even in Java/Go/Python.
- **A NullPointerException is technically a memory-safety *protection* working.** The dereference of null was *caught* rather than allowed to corrupt memory. Annoying, but it's the system doing its job.
- **Some "safe" languages have unsafe corners.** Java has `sun.misc.Unsafe`, Go can have data races, and Rust has `unsafe` blocks. Safety is the default, not an absolute everywhere in the language.
- **Strings are buffers too.** Many of the worst historical overflows were string-handling bugs in C (`strcpy`, `gets`). In safe languages, strings are bounds-checked objects, which removes a huge class of these.

---

## Apply it

1. Choose one small, known input for **Memory Safety**.
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

- What problem does Memory Safety solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
