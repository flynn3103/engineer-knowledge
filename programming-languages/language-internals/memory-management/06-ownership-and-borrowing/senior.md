# Ownership & Borrowing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Ownership & Borrowing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Ownership is statically enforced, deterministic RAII

C++ gave us RAII: a destructor runs at scope exit. But C++ does not *prevent* you from holding a dangling pointer, double-freeing, or using-after-move — it just makes cleanup convenient. Rust's contribution is to make RAII **mandatory and verified**: the type system (affine moves) plus the borrow checker (lifetime/aliasing analysis) *prove* that every value is dropped exactly once and that no reference outlives its referent. The result is RAII's determinism with none of its footguns.

This is why "compile-time garbage collection" is an apt slogan: you get automatic reclamation, but the decision of *when* to reclaim is fixed at compile time (scope exit), not deferred to a runtime collector.

### The cost model is the selling point

The defining property of ownership is its **cost model**: drop is a scope-bound, statically-placed destructor call; a move is (often) a memcpy the optimizer frequently elides; a borrow is a pointer with zero runtime representation (lifetimes are erased). There is no allocator-wide scan, no write barrier, no marking. CPU spent on memory management is exactly the `malloc`/`free`-equivalent work and nothing more. This predictability — not raw throughput — is the reason latency-sensitive systems adopt it.

### What ownership cannot express cheaply

The model assumes a tree-shaped or DAG-shaped ownership graph: each value has one owner, references point "downward" or sideways with bounded lifetimes. Data that is naturally a **general graph with cycles** — doubly linked lists, observer graphs, arbitrary object meshes — does not fit. You can still build it (with `Rc`/`Weak`, arena indices, or `unsafe`), but you leave the zero-cost, statically-checked happy path. This is the structural limitation behind the senior trade-off.

## Ownership vs Garbage Collection

| Dimension | Ownership (Rust) | Tracing GC (Java/Go/C#) |
|---|---|---|
| **Runtime overhead** | None for the model itself | CPU for collection, write barriers, extra heap headroom |
| **Pauses** | None (deterministic drop) | Stop-the-world or concurrent pauses (sub-ms to many ms) |
| **When freed** | Deterministic (scope exit) | Non-deterministic (whenever GC runs) |
| **Cyclic data** | Leaks with `Rc`; needs `Weak`/arena | Collected automatically |
| **Developer effort** | High upfront (design ownership) | Low (allocate and forget) |
| **Memory footprint** | Tight, predictable | Higher (headroom for the collector) |
| **Non-memory resources** | Same model frees files/sockets/locks deterministically (RAII) | Needs `finally`/`defer`/`using`; GC finalizers are unreliable |
| **Throughput** | Excellent, predictable | Can be very high; a good GC can beat naive manual allocation in throughput |

The honest summary: **a tracing GC is, in many ways, more capable** — it collects cycles for free, requires no annotations, and modern collectors achieve excellent throughput. What it cannot offer is *determinism*: bounded, predictable latency and a known free-point. Ownership gives up the GC's automatic cycle handling and its low cognitive load to buy that determinism plus a smaller, runtime-free footprint. A subtle but important point: ownership's biggest win over GC is often **not memory but other resources** — files, locks, sockets, DB handles close deterministically via `Drop`, whereas GC finalizers are non-deterministic and discouraged.

## The Ownership Family of Languages

Rust did not invent ownership; it productized a research lineage and pushed it mainstream.

- **Cyclone (early 2000s, AT&T/Cornell)** — a safe dialect of C with **region-based memory management** and pointer kinds. The direct ancestor of Rust's lifetimes and the "borrow doesn't outlive owner" idea.
- **Linear/affine type theory** — the formal basis: a linear value is used *exactly* once, an affine value *at most* once. Rust's moves are affine; "use after move" is the type system enforcing affinity.
- **C++ move semantics + `unique_ptr`/`shared_ptr`** — the same ideas as conventions rather than guarantees. `unique_ptr` ≈ `Box`, `shared_ptr` ≈ `Arc`, but a moved-from C++ object is still *usable* (valid-but-unspecified), and nothing prevents dangling references. Rust's contribution is making these properties *checked*.
- **Swift** — uses automatic reference counting (ARC) pervasively, and has been adding an explicit **ownership** model (`borrowing`/`consuming` parameters, `~Copyable` types, non-copyable structs) to get Rust-like guarantees where they matter without abandoning ARC's ergonomics.
- **Val / Hylo** — a research language built on **mutable value semantics**: you program as if everything is a value (no visible references), and the compiler uses borrowing under the hood to avoid copies. An attempt to keep ownership's safety while removing lifetime annotations from the surface language.

The trend across all of these is the same: push memory-safety proofs to compile time, and make aliasing and mutation explicit. Rust is the current mainstream high-water mark; it is not the end of the line.

## Code Examples

### Why a doubly linked list is hard

```rust
// Naively, each node owns its neighbor — but a doubly linked list needs
// node A to point to B AND B to point back to A. Two owners of one edge.
struct Node {
    next: Option<Box<Node>>, // forward ownership: a tree, fine
    prev: ???,               // backward pointer: cannot be Box (double-own)
}
```

`Box` can't express the back-pointer (it would imply two owners). The idiomatic fix is `Rc<RefCell<Node>>` for shared mutable nodes with `Weak<RefCell<Node>>` for the `prev` edge — or, in performance code, an arena:

```rust
// Arena / index-based: sidestep ownership entirely.
struct Node { next: Option<usize>, prev: Option<usize>, val: i32 }
struct List { nodes: Vec<Node> }   // the Vec owns all nodes; links are indices
```

Indices are "pointers the borrow checker doesn't track." You trade pointer-chasing safety for borrow-checker freedom; bounds-checking still protects you from true memory unsafety. This is how high-performance Rust (compilers, ECS game engines) routinely represents graphs.

### Deterministic resource release (the GC can't match this)

```rust
struct Connection { /* ... */ }
impl Drop for Connection {
    fn drop(&mut self) { /* close socket, flush, release pool slot */ }
}

fn handle() {
    let conn = Connection { /* ... */ };
    // ... use conn ...
} // socket closed HERE, deterministically, even on early return or panic
```

In a GC language, the socket closes "eventually," when a finalizer runs — or never. Ownership ties the resource's release to a precise, predictable point. This is frequently the strongest practical argument for the model.

## Design Trade-offs

- **Determinism vs convenience.** Choose ownership when bounded latency, tight memory, or deterministic resource cleanup are first-class requirements (OS, embedded, trading, databases, browsers). Choose GC when developer velocity and easy data structures dominate and you can absorb pauses (most web backends, scripting, line-of-business apps).
- **Where the complexity lives.** Ownership concentrates complexity at *API boundaries* — designing who owns what, lifetime relationships in public types. Get the ownership architecture right early; retrofitting it is painful.
- **Escape hatches are a spectrum, not a cliff.** `Box` → `Rc`/`Arc` → `RefCell`/`Mutex` → arena indices → `unsafe` is a ladder of increasing flexibility and decreasing static guarantee. Senior judgment is climbing exactly as high as the problem requires and no higher.
- **`unsafe` is a containment boundary, not an off-switch.** Good Rust isolates `unsafe` behind safe APIs that uphold invariants (the way `Vec`, `Rc`, and `Mutex` are implemented). The goal is a small, audited unsafe core under a large safe surface.

## Best Practices

- **Design ownership before writing code.** Sketch the ownership tree of your domain types first; the borrow checker is mostly enforcing decisions you should have made consciously anyway.
- **Reach for arena/index representations for graphs.** Don't `Rc<RefCell>` your way through a graph-heavy system if a `Vec`-backed arena with indices is cleaner and faster.
- **Treat `Rc`/`Arc` as a localized GC and budget for it.** Atomic refcount bumps cost; cycles leak. Know where you've opted into reference counting and why.
- **Keep `unsafe` blocks tiny, documented, and behind safe abstractions.** Every `unsafe` block should carry a comment stating the invariant it upholds and why it holds.
- **Pick the language for the data shape, not the hype.** If the domain is fundamentally a mutable cyclic graph and latency isn't critical, a GC language may be the senior choice.

## Edge Cases & Pitfalls

- **Self-referential structs and `async`.** A struct holding a reference into its own field breaks the move-invalidates-references assumption. `async` futures are commonly self-referential, which is why `Pin` exists — covered in depth at the professional level.
- **`Rc`/`Arc` cycle leaks in production.** The single way to leak in safe Rust. Reference counting cannot reclaim cycles; only `Weak` or breaking the cycle helps. This is a real, recurring production bug class.
- **`Drop` order subtleties.** Values drop in reverse declaration order within a scope; struct fields drop in declaration order. Resource-release ordering bugs hide here (e.g., dropping a lock before the data it protects).
- **Over-cloning to escape the checker.** Sprinkling `.clone()` to silence errors can quietly turn an O(1) program into an O(n) one. The clone is a real cost the GC version wouldn't pay; treat repeated clones as a design smell.
- **Mistaking `Rc<RefCell<T>>` for free.** It's effectively single-threaded GC with runtime borrow checks and panic risk — most of what ownership was supposed to avoid. Sometimes correct, but never the "default safe" choice it looks like.

---

## Apply it

1. State the system invariant that **Ownership & Borrowing** must protect.
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

- Which invariant must remain true when Ownership & Borrowing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
