# Memory-Safety Mechanisms — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Memory-Safety Mechanisms** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Rust: Ownership Makes Free Happen Exactly Once, At The Right Time

Rust's foundation is **ownership**. Every value has exactly one owner (a binding). When the owner goes out of scope, Rust automatically runs the value's **`drop`** (its destructor) — freeing heap memory, closing files, etc. — *exactly once*. You never call `free`; the compiler inserts the drop at the precise scope exit.

This single rule eliminates an entire bug family:

- **Double-free is impossible** — drop runs once, at scope exit, inserted by the compiler. You can't call it twice.
- **Memory leaks from forgetting to free are mostly gone** — drop is automatic (cycles via `Rc` are the exception).
- **Use-after-free is impossible** — see borrowing below; a reference can't outlive the value it points at.

When you assign or pass a value, ownership **moves** by default. After `let b = a;`, the binding `a` is *invalidated* — using it is a compile error. This is how Rust prevents the C++ trap where two objects own the same buffer and both free it (double-free) or one frees while the other still uses it (UAF).

### 2. Borrowing and Aliasing XOR Mutability

Moving everything everywhere would be painful, so Rust lets you **borrow** — take a reference without taking ownership. There are two kinds, and the rule between them is the heart of Rust safety:

> **Aliasing XOR Mutability:** at any given moment, for a given value, you may have **either** any number of shared references `&T` (read-only) **or** exactly one mutable reference `&mut T` (read-write) — **never both at once.**

Why this rule gives safety: the deepest cause of memory corruption is **a mutation happening while another part of the code holds a pointer that assumes the data didn't change** — e.g. you hold a pointer into a `Vec`, then something pushes to it, the `Vec` reallocates, and your pointer now dangles. Aliasing-XOR-mutability makes that *un-typable*: if someone can mutate (has `&mut`), nobody else can hold a reference at the same time; if anyone is reading (`&T`), nobody can mutate. The classic "iterator invalidation" and "modify-while-borrowed" bugs become compile errors.

This is also why Rust prevents data races *at compile time*: a data race requires two threads, one writing, no synchronization — i.e. aliasing + mutation across threads. The same rule (extended by the `Send`/`Sync` traits) forbids it.

### 3. Lifetimes: References Can't Outlive Their Data

A **lifetime** is the compile-time span over which a reference is valid. The borrow checker proves that **every reference's lifetime is contained within the lifetime of the data it points to.** If you try to return a reference to a local variable (which dies when the function returns), the checker rejects it — that's exactly the C "dangling pointer to a stack frame" bug, caught at compile time:

```rust
fn dangling() -> &i32 {
    let x = 5;
    &x            // ERROR: `x` does not live long enough
}                 // x is dropped here; the reference would dangle
```

Most lifetimes are *inferred* ("lifetime elision"); you write explicit ones (`'a`) only when the relationships are ambiguous (e.g. a function returning a reference derived from one of several inputs). Lifetimes are a *compile-time* device — they have **zero runtime representation or cost**. They're proof annotations, not pointers.

### 4. `unsafe`: The Audited Escape Hatch (and Why It's Not Cheating)

Rust cannot statically verify *everything* — it can't prove a raw pointer from C is valid, can't check that two non-overlapping slices really don't overlap, can't reason about hardware MMIO. So it provides **`unsafe`**: a block where five extra powers are unlocked (deref raw pointers, call `unsafe` fns, access `union` fields, access/modify mutable statics, implement `unsafe` traits).

The crucial design insight: `unsafe` **does not turn off the borrow checker** for the surrounding code. It marks a *small, greppable region* where the human asserts invariants the compiler can't check. The safety contract is: *the code inside `unsafe` must uphold the same invariants the checker would have enforced, so that safe code calling it can never trigger UB.* A well-written `unsafe` block is wrapped in a safe API whose preconditions guarantee soundness.

This is the senior mental shift: Rust doesn't claim *no* unsafe code exists. It claims unsafe code is **confined to a small, auditable surface** (`std`'s `Vec`, `HashMap`, etc. are built on `unsafe` internally, audited once, exposed safely). The CVE-relevant question becomes "is the `unsafe` correct?" instead of "is *every line of the program* correct?" — a vastly smaller audit. Tools like Miri (an interpreter that detects UB in `unsafe` code) and the borrow checker's containment make this tractable.

### 5. Managed Runtimes: Safety as a Runtime Property

Java, Go, C#, and JavaScript get memory safety from the **runtime**, not the type system:

- **Spatial:** array/slice indexing inserts a **bounds check**; an out-of-range index throws/panics (`ArrayIndexOutOfBoundsException`, Go panic) instead of corrupting memory. JITs eliminate provable checks (loop-invariant hoisting, range analysis).
- **Temporal:** there is *no manual free*. A **tracing garbage collector** reclaims only unreachable objects, so any reference you still hold points to a live object — UAF and double-free are structurally impossible *for ordinary code*.
- **Type safety:** the verifier (JVM bytecode verifier) and the type system prevent type confusion — you can't reinterpret an `Object` as an `int[]` and read wild pointers.

This is robust and is why the vast majority of application code today is memory-safe by default. But a senior must know the three places it leaks.

### 6. Where Managed-Runtime Safety Leaks

**(a) Explicit escape hatches.** Every managed runtime ships a way out, for performance or interop:

- Java: `sun.misc.Unsafe` / `jdk.internal.misc.Unsafe` — raw off-heap memory, unchecked stores. JNI (calling C) leaves the safe world entirely.
- Go: `unsafe.Pointer` (pointer arithmetic, type punning) and **cgo** (calling C). Go is memory-safe *until* you use these.
- C#: `unsafe`/`fixed`/`stackalloc`, `Span<T>`, and P/Invoke.
- JS: generally no escape hatch in the language, but the *engine* and WebAssembly/native bindings are C++.

Using these correctly is possible; using them wrong reintroduces every classic bug. They exist precisely where performance/interop demand it, and that's where managed-runtime CVEs cluster.

**(b) Data races can break safety, not just correctness.** This is the subtle one. In **Java** and **Go**, a data race on a *multi-word* value can produce a **torn read** that violates type safety. Go's canonical example: an `interface` value is two words (type pointer + data pointer). If one goroutine writes a `(typeA, ptrA)` interface and another concurrently writes `(typeB, ptrB)`, an unsynchronized reader can observe `(typeA, ptrB)` — a *type pointer that doesn't match the data pointer*. Dereferencing it is **type confusion → memory corruption**, inside a "memory-safe" language. The Go memory model explicitly warns that racy programs are not guaranteed memory-safe. (Java's JMM keeps *individual* references atomic, so Java's exposure is narrower, but `long`/`double` tearing and broken publication can still produce surprising — though type-safe — states; the JVM's verifier keeps it from raw corruption in most cases. The Go interface-tearing case is the sharpest illustration.)

The takeaway: **GC ≠ full memory safety in the presence of data races.** Race-freedom is a *precondition* of the runtime's safety guarantee, not an independent nicety.

**(c) Runtime/JIT bugs.** The runtime itself is written in C++. A JIT miscompilation or a GC bug is a memory-safety bug *in the platform* (V8/JSC type-confusion CVEs are a whole genre). Application code is safe; the substrate is C++.

### 7. Swift ARC: Deterministic Safety With a Cycle Tax

Swift uses **Automatic Reference Counting**. The compiler inserts `retain`/`release` calls so each object's **strong reference count** is maintained; when it hits zero, `deinit` runs and the object is freed *immediately and deterministically* (no GC pauses). This gives temporal safety (you never free manually) with predictable timing and lower memory overhead than tracing GC — attractive for resource-constrained, latency-sensitive UI.

The cost ARC can't escape on its own is the **retain cycle**: object A strongly references B and B strongly references A. Neither count ever reaches zero, so both leak forever. ARC has no tracing pass to discover the cycle. The fix is *manual*: declare one side **`weak`** (doesn't increment the count; auto-nils to `nil` when the object deallocs — preserving safety) or **`unowned`** (doesn't increment; assumes the referent outlives — *if that assumption is wrong, you get a use-after-free*, so `unowned` is the one ARC feature that can reintroduce a temporal bug). The senior skill is choosing `weak` vs `unowned` correctly and recognizing closure-capture cycles.

### 8. The Through-Line: Confine Unsafety, Don't Pretend It's Gone

Across all three designs, the senior insight is the same: **safety at scale comes from shrinking the unsafe surface to something auditable, not from eliminating unsafe operations.**

- Rust: unsafety lives in `unsafe` blocks and audited library internals.
- Managed runtimes: unsafety lives in the runtime's C++, the `Unsafe`/cgo/FFI boundary, and racy code.
- Swift: unsafety re-enters only through `unowned` and `Unmanaged`/C interop.

When you audit a "safe" system for memory bugs, you go straight to those surfaces. That's where the 70% statistic's survivors hide.

---

## Code Examples

> Educational/defensive. Rust examples show *compile errors* that prevent bugs; managed examples show *where the guarantee ends*. No exploits.

### Rust prevents use-after-free at compile time

```rust
fn main() {
    let r;
    {
        let v = vec![1, 2, 3];
        r = &v[0];          // borrow into v
    }                       // v dropped here
    println!("{}", r);      // ERROR: `v` does not live long enough
}                           // borrow checker rejects: r would dangle
```

### Aliasing XOR mutability kills iterator invalidation

```rust
fn main() {
    let mut v = vec![1, 2, 3];
    for x in &v {           // shared borrow of v for the loop
        if *x == 2 {
            v.push(4);      // ERROR: cannot borrow `v` as mutable
        }                   // while it's borrowed as immutable
    }
}
```

In C++ this is the classic "push during range-for reallocates the vector, invalidating the iterator → UAF." Rust makes it a compile error.

### `unsafe` confined behind a safe API

```rust
/// Safe wrapper: splits a slice into two non-overlapping halves.
/// The `unsafe` is audited once; callers can never misuse it.
fn split_first(s: &mut [i32]) -> (&mut i32, &mut [i32]) {
    assert!(!s.is_empty());
    let ptr = s.as_mut_ptr();
    unsafe {
        // SAFETY: s is non-empty (asserted); the two regions are
        // disjoint by construction, so aliasing-XOR-mutability holds.
        (&mut *ptr, std::slice::from_raw_parts_mut(ptr.add(1), s.len() - 1))
    }
}
```

The danger is contained to the block; the public signature is fully safe. Reviewers audit the `// SAFETY:` justification, not the whole call graph.

### Go: a data race breaking type safety (conceptual, defensive)

```go
// DO NOT write code like this. It demonstrates WHY race-freedom is
// a PRECONDITION of Go's memory safety, not an optional nicety.
var shared interface{} // an interface is (type-ptr, data-ptr): two words

// goroutine 1: shared = int(42)        -> (intType,  &42)
// goroutine 2: shared = "hello"        -> (strType,  &"hello")
// An unsynchronized reader can observe a TORN value: (intType, &"hello")
// or (strType, &42). Using it dereferences a mismatched type pointer:
// TYPE CONFUSION -> memory corruption, INSIDE "memory-safe" Go.
```

The fix is trivial and is the point: synchronize (mutex/channel/atomic). The Go race detector (`-race`) exists precisely to find these, because the language's safety guarantee *assumes* you fixed them.

### Swift ARC: a retain cycle and its fix

```swift
class Node {
    var next: Node?          // strong
    weak var prev: Node?     // weak -> breaks the cycle, auto-nils safely
}
// Two Nodes linked both ways with STRONG refs would never dealloc (leak).
// `weak prev` lets ARC reclaim them; accessing a deallocated weak ref
// yields nil (safe) rather than a dangling pointer.
```

---

## Trade-offs

| Design | Spatial safety | Temporal safety | Runtime cost | Escape hatch | Failure mode |
|--------|----------------|-----------------|--------------|--------------|--------------|
| **Rust** | bounds checks (often elided) | ownership + borrow checker | ~zero | `unsafe` blocks | unsound `unsafe`; harder authoring |
| **Managed GC** (Java/Go/C#/JS) | bounds checks (JIT-elided) | tracing GC | GC pauses, footprint | `Unsafe`/cgo/FFI; **data races** | race-induced type confusion; FFI bugs; runtime CVEs |
| **Swift ARC** | bounds checks | reference counting | refcount traffic | `unowned`, `Unmanaged`, C interop | retain-cycle leaks; `unowned` UAF |
| **C/C++** | none by default | none by default | zero | the whole language | ~70% of severe CVEs |

---

## Coding Patterns

```text
RUST
  - Wrap every `unsafe` in a safe API with a documented // SAFETY: invariant.
  - Prefer ownership/borrowing over Rc<RefCell<>>; reach for interior
    mutability only when the data structure truly needs shared mutation.
  - Run Miri in CI to catch UB inside unsafe blocks.
  - Treat `unsafe` count as a metric: fewer, smaller, justified blocks.

MANAGED (Go/Java/C#)
  - Treat `unsafe`/cgo/JNI/P-Invoke as a reviewed, minimized boundary.
  - Run the race detector (`go test -race`, TSan) in CI — race-freedom is
    a precondition of the safety guarantee.
  - Never reinterpret memory across types without the language's blessing.

SWIFT
  - Default to `weak` for back-references / delegates; `unowned` only when
    you can PROVE the referent outlives the reference.
  - Use `[weak self]` in escaping closures to avoid capture cycles.
```

---

## Best Practices

- **State the guarantee's boundary explicitly.** "We're memory-safe except in the 200 lines of `unsafe`/cgo and assuming race-freedom (enforced by `-race` in CI)." Vague "we use a safe language" hides the real risk.
- **Minimize and audit `unsafe`/FFI.** Make it a small, reviewed surface with documented invariants. Gate additions in code review.
- **Run the race detector in CI for Go/Java/C#.** In Go especially, a race isn't just a wrong answer — it can break memory safety. Treat race-detector findings as release blockers.
- **Run Miri (Rust) / sanitizers across the FFI boundary.** Tools still help at the seams where the static guarantee stops.
- **In Swift, default to `weak`; justify every `unowned`.** `unowned` is the one ARC construct that can cause use-after-free.
- **Prefer the language's safe abstractions** (slices with length, `Vec`, `Span`, smart pointers) over raw pointers everywhere the guarantee permits.

---

## Edge Cases & Pitfalls

- **`unsafe` is viral if the invariant leaks.** A bug *inside* `unsafe` can corrupt memory that *safe* code then touches — the unsoundness escapes the block. The block is small; its blast radius may not be.
- **Go: `unsafe.Pointer` rules are subtle.** Only specific conversion patterns are valid; the GC may move/collect memory your `uintptr` math no longer protects. Misuse silently breaks under a future GC change.
- **Java publication bugs.** Even race-"safe" Java can publish a half-constructed object through a data race, exposing default-zero fields where you expected initialized ones (the double-checked-locking-before-JSR-133 lineage).
- **ARC `unowned` outliving assumption violated → UAF.** If the referent deallocates first, touching an `unowned` reference is a crash/UAF. This is the ARC version of a dangling pointer.
- **JIT/GC of the runtime is C++.** "Memory-safe language" doesn't mean "memory-safe platform"; engine CVEs (V8 type confusion) are real and frequent.
- **Rust safety doesn't cover logic bugs or `mem::forget` leaks.** Leaks are *safe* in Rust's model (you can `forget` a value); safety ≠ no-leaks.

---

## Common Mistakes

- Saying "Rust has no unsafe code." It has `unsafe`; the point is it's *confined and audited*, and `std` itself is built on it.
- Saying "Go/Java is memory-safe, so I don't need the race detector." A data race can break the safety guarantee (Go interface tearing). Race-freedom is a precondition.
- Using `unowned` in Swift as the default to avoid `weak`'s optionality — reintroduces UAF when lifetimes don't hold.
- Fighting the borrow checker by reaching for `Rc<RefCell<T>>` everywhere, moving compile-time checks to runtime panics (and back toward aliasing bugs).
- Assuming GC frees promptly; it frees *eventually*, which matters for non-memory resources (use `defer`/`try-with-resources`/`Drop`, not the GC, for files/sockets).

---

## Tricky Points

- **Why is aliasing-XOR-mutability *sufficient* for both UAF-freedom and race-freedom?** Because every memory-corrupting interaction reduces to "something mutated while an outstanding pointer assumed stability." Forbid simultaneous alias+mutate (single-thread: borrow rules; cross-thread: `Send`/`Sync`) and the entire family vanishes.
- **Why can a data race break *type* safety in Go but less so in Java?** Go interfaces/slices are multi-word (type+data); a non-atomic write can tear them into a mismatched pair, yielding a wrong type pointer. Java keeps single references atomic (no tearing of a reference), so racy Java tends to produce *wrong but type-valid* states rather than raw corruption — narrower, but still not a license to race.
- **Why is `unsafe` not a failure of Rust's design?** Because the alternative — making *every* operation statically provable — is impossible for FFI/hardware/some data structures. Confining unsafety to an auditable surface is the *realistic* form of safety at scale, and it demonstrably shrinks the bug surface (Android's Rust memory-bug rate fell sharply).
- **Why does ARC need *two* non-owning reference kinds (`weak` and `unowned`)?** `weak` is safe but costs an optional and a side-table lookup; `unowned` is cheaper but unsafe if the lifetime assumption breaks. It's a safety/performance knob for cycle-breaking.

---

## Apply it

1. State the system invariant that **Memory-Safety Mechanisms** must protect.
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

- Which invariant must remain true when Memory-Safety Mechanisms fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
